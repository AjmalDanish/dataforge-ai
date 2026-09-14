"""InsightGenerationAgent — The Storyteller (v2 contract).

Synthesizes profile, statistics, KPIs and domain context into ranked,
business-grade insights. Rule-based core (always works offline); LLM
narrative synthesis is a future extension point.

Frozen contract (docs/v2/AGENTS.md §11):
- Phase: 6 — Synthesis
- Inputs: ``cleaned_data`` (+ optional ``profile``, ``statistics``,
  ``discovered_kpis``, ``business_domain``, ``business_objectives``)
- Outputs: ``business_insights``
- Retry: 2
- Failure: SKIP (report generates without narrative)
- Timeout: 45s
- LLM: optional (rule-based synthesis is the default path)
"""

from typing import Any

import pandas as pd

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.state import GraphState

__all__ = ["InsightGenerationAgent"]


class InsightGenerationAgent(Agent):
    """Synthesizes business insights from all prior analysis."""

    phase: ExecutionPhase = ExecutionPhase.SYNTHESIS
    required_inputs: list[str] = ["cleaned_data"]
    produced_outputs: list[str] = ["business_insights"]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=2)
    failure_policy: FailurePolicy = FailurePolicy.SKIP
    timeout_seconds: int = 45

    MAX_INSIGHTS: int = 10

    # Severity rank for ordering (higher = more important).
    SEVERITY_RANK: dict[str, int] = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)
        self.name = "InsightGenerationAgent"

    async def execute(self, state: GraphState) -> AgentResult:
        """Generate ranked business insights."""
        df = state.get("cleaned_data")
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return AgentResult(
                decision=AgentDecision.SKIP,
                message="No cleaned data available, skipping insight generation",
                data_updates={"business_insights": []},
                quality_score=0.0,
                execution_notes=["missing cleaned_data"],
            )

        domain = (state.get("business_domain") or "general").lower()
        statistics = state.get("statistics") or {}
        profile = state.get("profile") or {}
        kpis = state.get("discovered_kpis") or []

        insights: list[dict[str, Any]] = []
        insights += self._from_correlations(statistics)
        insights += self._from_outliers(df, statistics)
        insights += self._from_kpis(kpis, domain)
        insights += self._from_quality(df, profile)
        insights += self._from_distribution(statistics)

        insights = self._rank(insights)[: self.MAX_INSIGHTS]
        for rank, insight in enumerate(insights, start=1):
            insight["rank"] = rank

        # Always close with one actionable recommendation when we found anything.
        if insights:
            recommendation = self._recommendation(insights, domain)
            recommendation["rank"] = len(insights) + 1
            insights.append(recommendation)
            insights = insights[: self.MAX_INSIGHTS]

        quality = round(min(len(insights) / 5, 1.0), 3)
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Generated {len(insights)} business insights for domain '{domain}'",
            data_updates={"business_insights": insights},
            metadata={
                "domain": domain,
                "insight_count": len(insights),
                "categories": sorted({i["category"] for i in insights}),
            },
            quality_score=quality,
            execution_notes=[i["title"] for i in insights],
        )

    # -- insight builders ------------------------------------------------
    def _make(
        self,
        category: str,
        title: str,
        summary: str,
        supporting_data: dict[str, Any],
        severity: str,
        business_action: str,
        confidence: float,
    ) -> dict[str, Any]:
        return {
            "category": category,
            "title": title,
            "summary": summary,
            "supporting_data": supporting_data,
            "severity": severity,
            "business_action": business_action,
            "confidence": confidence,
        }

    def _from_correlations(self, statistics: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        significant = (statistics.get("correlations") or {}).get("significant", [])
        for corr in significant[:3]:
            cols = corr.get("columns", [])
            if len(cols) != 2:
                continue
            r = corr.get("correlation", 0.0)
            strength = corr.get("strength", "moderate")
            direction = corr.get("direction", "positive")
            out.append(
                self._make(
                    category="correlations",
                    title=f"{cols[0]} moves with {cols[1]}",
                    summary=(
                        f"{strength.title()} {direction} correlation between "
                        f"{cols[0]} and {cols[1]} (r={r:.2f}). Changes in one "
                        f"reliably accompany changes in the other."
                    ),
                    supporting_data={
                        "columns": cols,
                        "correlation": r,
                        "strength": strength,
                        "direction": direction,
                    },
                    severity="medium",
                    business_action=(
                        f"Use {cols[0]} as a lever or early indicator for {cols[1]}."
                    ),
                    confidence=0.85 if strength == "strong" else 0.7,
                )
            )
        return out

    def _from_outliers(
        self, df: pd.DataFrame, statistics: dict[str, Any]
    ) -> list[dict[str, Any]]:
        out = []
        outliers = statistics.get("outliers") or {}
        for col, indices in list(outliers.items())[:3]:
            count = len(indices) if isinstance(indices, (list, tuple)) else 0
            if count == 0:
                continue
            pct = 100 * count / max(len(df), 1)
            out.append(
                self._make(
                    category="anomalies",
                    title=f"Unusual values in {col}",
                    summary=(
                        f"{count} outlier values detected in {col} "
                        f"({pct:.1f}% of rows) via the IQR method. These may be "
                        f"errors, edge cases, or high-value exceptions."
                    ),
                    supporting_data={
                        "column": col,
                        "outlier_count": count,
                        "outlier_pct": round(pct, 2),
                    },
                    severity="high" if pct > 5 else "medium",
                    business_action=f"Review the {count} outlier rows in {col} before acting on averages.",
                    confidence=0.8,
                )
            )
        return out

    def _from_kpis(self, kpis: list[dict[str, Any]], domain: str) -> list[dict[str, Any]]:
        out = []
        for kpi in kpis[:4]:
            name = kpi.get("name", "KPI")
            value = kpi.get("value")
            trend = (kpi.get("trend") or "stable").lower()
            if value is None:
                continue
            if trend == "increasing":
                category, severity = "trends", "medium"
                summary = f"{name} is trending up (current: {value:.2f}). Momentum is positive."
                action = f"Double down on what is driving {name} upward."
            elif trend == "decreasing":
                category, severity = "risks", "high"
                summary = f"{name} is trending down (current: {value:.2f}). This needs attention."
                action = f"Investigate the decline in {name} before it compounds."
            else:
                category, severity = "top_performers", "medium"
                summary = f"{name} stands at {value:.2f} for {domain} data."
                action = f"Benchmark {name} against prior periods to confirm the baseline."
            out.append(
                self._make(
                    category=category,
                    title=f"{name}: {value:.2f}",
                    summary=summary,
                    supporting_data={
                        "kpi": name,
                        "value": value,
                        "trend": trend,
                        "formula": kpi.get("formula", ""),
                    },
                    severity=severity,
                    business_action=action,
                    confidence=float(kpi.get("confidence", 0.7)),
                )
            )
        return out

    def _from_quality(
        self, df: pd.DataFrame, profile: dict[str, Any]
    ) -> list[dict[str, Any]]:
        missing_ratio = profile.get("overall_missing_ratio")
        if missing_ratio is None:
            try:
                missing_ratio = float(df.isna().mean().mean())
            except Exception:
                return []
        if missing_ratio < 0.1:
            return []
        return [
            self._make(
                category="risks",
                title="Data completeness risk",
                summary=(
                    f"{100 * missing_ratio:.1f}% of values are missing. Insights "
                    f"built on thin data can mislead."
                ),
                supporting_data={"missing_ratio": round(float(missing_ratio), 3)},
                severity="high" if missing_ratio >= 0.3 else "medium",
                business_action="Fix collection for the sparsest columns, then re-run analysis.",
                confidence=0.9,
            )
        ]

    def _from_distribution(self, statistics: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        descriptive = statistics.get("descriptive_stats") or {}
        for col, stats in list(descriptive.items())[:2]:
            mean = stats.get("mean")
            median = stats.get("median")
            if mean is None or median is None or median == 0:
                continue
            skew = (mean - median) / abs(median)
            if abs(skew) < 0.2:
                continue
            direction = "right-skewed (a few large values pull the average up)"
            if skew < 0:
                direction = "left-skewed (a few small values drag the average down)"
            out.append(
                self._make(
                    category="trends",
                    title=f"{col} is skewed",
                    summary=f"{col} is {direction}. Prefer the median ({median:.2f}) over the mean ({mean:.2f}).",
                    supporting_data={
                        "column": col,
                        "mean": mean,
                        "median": median,
                        "skew_ratio": round(skew, 3),
                    },
                    severity="low",
                    business_action=f"Report {col} with medians and quartiles, not averages.",
                    confidence=0.75,
                )
            )
        return out

    def _recommendation(
        self, insights: list[dict[str, Any]], domain: str
    ) -> dict[str, Any]:
        top = insights[0]["title"] if insights else "the data"
        return self._make(
            category="recommendations",
            title="Recommended next step",
            summary=(
                f"Start with '{top}'. Validate it against source systems, "
                f"then set a {domain} baseline to track."
            ),
            supporting_data={"based_on": top},
            severity="low",
            business_action="Assign an owner and a review date for the top finding.",
            confidence=0.65,
        )

    def _rank(self, insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            insights,
            key=lambda i: (
                self.SEVERITY_RANK.get(i.get("severity", "low"), 1),
                i.get("confidence", 0.0),
            ),
            reverse=True,
        )
