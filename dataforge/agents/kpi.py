"""KPIDiscoveryAgent — The Scorekeeper (v2 contract).

Discovers domain-specific Key Performance Indicators from cleaned data
using deterministic domain templates. LLM enhancement is a future
extension; this rule-based core always works offline.

Frozen contract (docs/v2/AGENTS.md §9):
- Phase: 4 — Deep Analysis
- Inputs: ``cleaned_data`` (+ optional ``profile``, ``business_domain``)
- Outputs: ``discovered_kpis``
- Retry: 2
- Failure: SKIP
- Timeout: 30s
- LLM: optional (rule-based fallback is the default path)
"""

from typing import Any

import pandas as pd

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.state import GraphState

__all__ = ["KPIDiscoveryAgent"]


class KPIDiscoveryAgent(Agent):
    """Discovers KPIs via domain templates + pandas computation."""

    phase: ExecutionPhase = ExecutionPhase.DEEP_ANALYSIS
    required_inputs: list[str] = ["cleaned_data"]
    produced_outputs: list[str] = ["discovered_kpis"]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=2)
    failure_policy: FailurePolicy = FailurePolicy.SKIP
    timeout_seconds: int = 30

    # KPI templates per domain. Each spec:
    #   kind: row_count | column_sum | column_mean | column_max |
    #         column_min | distinct_count | ratio
    #   column/columns/numerator/denominator: keyword lists for discovery
    DOMAIN_TEMPLATES: dict[str, list[dict[str, Any]]] = {
        "retail": [
            {
                "name": "Total Revenue",
                "abbreviation": "REV",
                "description": "Sum of revenue across all orders",
                "formula": "sum(revenue)",
                "kind": "column_sum",
                "column": ["revenue", "sales", "total", "amount", "price"],
                "unit": "currency",
            },
            {
                "name": "Average Order Value",
                "abbreviation": "AOV",
                "description": "Mean revenue per order",
                "formula": "mean(revenue)",
                "kind": "column_mean",
                "column": ["revenue", "sales", "total", "amount", "price"],
                "unit": "currency",
            },
            {
                "name": "Order Count",
                "abbreviation": "ORD",
                "description": "Total number of orders",
                "formula": "count(rows)",
                "kind": "row_count",
                "unit": "count",
            },
            {
                "name": "Unique Products",
                "abbreviation": "SKU",
                "description": "Distinct products sold",
                "formula": "nunique(product)",
                "kind": "distinct_count",
                "column": ["product", "sku", "item", "name"],
                "unit": "count",
            },
        ],
        "hr": [
            {
                "name": "Headcount",
                "abbreviation": "HC",
                "description": "Total number of employees",
                "formula": "count(rows)",
                "kind": "row_count",
                "unit": "count",
            },
            {
                "name": "Average Salary",
                "abbreviation": "AVG_SAL",
                "description": "Mean employee salary",
                "formula": "mean(salary)",
                "kind": "column_mean",
                "column": ["salary", "wage", "pay", "compensation"],
                "unit": "currency",
            },
            {
                "name": "Salary Range",
                "abbreviation": "SAL_RNG",
                "description": "Max minus min salary",
                "formula": "max(salary) - min(salary)",
                "kind": "range",
                "column": ["salary", "wage", "pay", "compensation"],
                "unit": "currency",
            },
            {
                "name": "Departments",
                "abbreviation": "DEPT",
                "description": "Distinct departments",
                "formula": "nunique(department)",
                "kind": "distinct_count",
                "column": ["department", "dept", "team", "division"],
                "unit": "count",
            },
        ],
        "finance": [
            {
                "name": "Total Volume",
                "abbreviation": "VOL",
                "description": "Sum of transaction amounts",
                "formula": "sum(amount)",
                "kind": "column_sum",
                "column": ["amount", "balance", "transaction", "value"],
                "unit": "currency",
            },
            {
                "name": "Average Transaction",
                "abbreviation": "AVG_TXN",
                "description": "Mean transaction amount",
                "formula": "mean(amount)",
                "kind": "column_mean",
                "column": ["amount", "balance", "transaction", "value"],
                "unit": "currency",
            },
            {
                "name": "Transaction Count",
                "abbreviation": "TXN",
                "description": "Total number of transactions",
                "formula": "count(rows)",
                "kind": "row_count",
                "unit": "count",
            },
        ],
        "general": [
            {
                "name": "Row Count",
                "abbreviation": "ROWS",
                "description": "Total number of records",
                "formula": "count(rows)",
                "kind": "row_count",
                "unit": "count",
            },
        ],
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
        self.name = "KPIDiscoveryAgent"

    async def execute(self, state: GraphState) -> AgentResult:
        """Discover KPIs for the dataset's business domain."""
        df = state.get("cleaned_data")
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return AgentResult(
                decision=AgentDecision.SKIP,
                message="No cleaned data available, skipping KPI discovery",
                data_updates={"discovered_kpis": []},
                quality_score=0.0,
                execution_notes=["missing cleaned_data"],
            )

        _bd = state.get("business_domain") or "general"
        domain = (_bd.value if hasattr(_bd, "value") else str(_bd)).lower()
        templates = self.DOMAIN_TEMPLATES.get(domain, self.DOMAIN_TEMPLATES["general"])
        # Always include the generic row-count KPI for comparability.
        if domain != "general":
            templates = templates + self.DOMAIN_TEMPLATES["general"]

        temporal_col = self._find_temporal_column(df)
        kpis: list[dict[str, Any]] = []
        succeeded = 0
        for spec in templates:
            try:
                value = self._compute(df, spec)
            except Exception:
                continue
            if value is None:
                continue
            succeeded += 1
            trend = self._trend(df, spec, temporal_col)
            kpis.append(
                {
                    "name": spec["name"],
                    "abbreviation": spec.get("abbreviation"),
                    "description": spec.get("description", ""),
                    "formula": spec.get("formula", ""),
                    "value": value,
                    "unit": spec.get("unit"),
                    "trend": trend,
                    "benchmark": None,
                    "is_on_track": None,
                    "metrics": [],
                    "domain": domain,
                    "confidence": 0.85 if trend != "stable" else 0.7,
                }
            )

        quality = round(succeeded / max(len(templates), 1), 3)
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Discovered {len(kpis)} KPIs for domain '{domain}'",
            data_updates={"discovered_kpis": kpis},
            metadata={"domain": domain, "templates": len(templates), "computed": succeeded},
            quality_score=quality,
            execution_notes=[f"{succeeded}/{len(templates)} templates computed"],
        )

    # -- helpers ---------------------------------------------------------
    def _find_column(self, df: pd.DataFrame, keywords: list[str]) -> str | None:
        cols = {c.lower(): c for c in df.columns}
        for kw in keywords:
            for lowered, original in cols.items():
                if kw in lowered:
                    return original
        numeric = df.select_dtypes(include="number").columns.tolist()
        return numeric[0] if numeric else None

    def _find_temporal_column(self, df: pd.DataFrame) -> str | None:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col
        return None

    def _compute(self, df: pd.DataFrame, spec: dict[str, Any]) -> float | int | None:
        kind = spec.get("kind")
        if kind == "row_count":
            return int(len(df))
        col = self._find_column(df, spec.get("column", []))
        if col is None:
            return None
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty and kind != "distinct_count":
            return None
        if kind == "column_sum":
            return float(series.sum())
        if kind == "column_mean":
            return float(series.mean())
        if kind == "column_max":
            return float(series.max())
        if kind == "column_min":
            return float(series.min())
        if kind == "range":
            return float(series.max() - series.min())
        if kind == "distinct_count":
            return int(df[col].nunique())
        if kind == "ratio":
            num = self._find_column(df, spec.get("numerator", []))
            den = self._find_column(df, spec.get("denominator", []))
            if num is None or den is None:
                return None
            den_sum = float(pd.to_numeric(df[den], errors="coerce").sum())
            if den_sum == 0:
                return None
            return float(pd.to_numeric(df[num], errors="coerce").sum() / den_sum)
        return None

    def _trend(
        self, df: pd.DataFrame, spec: dict[str, Any], temporal_col: str | None
    ) -> str:
        """Compare second-half vs first-half on temporal order (MoM-style)."""
        if temporal_col is None or spec.get("kind") == "distinct_count":
            return "stable"
        try:
            ordered = df.sort_values(temporal_col)
            halves = max(len(ordered) // 2, 1)
            first = self._compute(ordered.iloc[:halves], spec)
            second = self._compute(ordered.iloc[halves:], spec)
            if first is None or second is None or first == 0:
                return "stable"
            change = (second - first) / abs(first)
            if change > 0.05:
                return "increasing"
            if change < -0.05:
                return "decreasing"
            return "stable"
        except Exception:
            return "stable"
