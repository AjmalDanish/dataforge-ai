"""FeatureEngineeringAgent — The Engineer (v2 contract).

Creates derived features enabling deeper KPI/insight discovery.
Fully rule-based (Pandas/NumPy); LLM suggestions are a future extension.

Frozen contract (docs/v2/AGENTS.md §8):
- Phase: 4 — Deep Analysis
- Inputs: ``cleaned_data`` (+ optional ``profile``, ``business_domain``)
- Outputs: ``engineered_data``, ``new_features``
- Retry: 2
- Failure: SKIP (analysis proceeds with original features)
- Timeout: 60s
- LLM: optional
"""

import numpy as np
import pandas as pd

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.state import GraphState

__all__ = ["FeatureEngineeringAgent"]


class FeatureEngineeringAgent(Agent):
    """Engineers temporal, ratio, binned and flag features."""

    phase: ExecutionPhase = ExecutionPhase.DEEP_ANALYSIS
    required_inputs: list[str] = ["cleaned_data"]
    produced_outputs: list[str] = ["engineered_data", "new_features"]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=2)
    failure_policy: FailurePolicy = FailurePolicy.SKIP
    timeout_seconds: int = 60

    MAX_NEW_FEATURES: int = 20

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)
        self.name = "FeatureEngineeringAgent"

    async def execute(self, state: GraphState) -> AgentResult:
        """Create derived features from cleaned data."""
        df = state.get("cleaned_data")
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return AgentResult(
                decision=AgentDecision.SKIP,
                message="No cleaned data available, skipping feature engineering",
                data_updates={"engineered_data": None, "new_features": []},
                quality_score=0.0,
                execution_notes=["missing cleaned_data"],
            )

        engineered = df.copy(deep=True)
        new_features: list[dict] = []

        self._extract_temporal(engineered, new_features)
        self._add_bins(engineered, new_features)
        self._add_ratios(engineered, new_features)
        self._add_flags(engineered, new_features)

        # Cap feature count for downstream cost control.
        new_features = new_features[: self.MAX_NEW_FEATURES]
        keep = set(df.columns) | {f["name"] for f in new_features}
        engineered = engineered[[c for c in engineered.columns if c in keep]]

        quality = round(min(len(new_features) / 4, 1.0), 3)
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Engineered {len(new_features)} new features",
            data_updates={"engineered_data": engineered, "new_features": new_features},
            metadata={
                "new_feature_count": len(new_features),
                "total_columns": len(engineered.columns),
            },
            quality_score=quality,
            execution_notes=[f["name"] for f in new_features],
        )

    # -- feature builders ------------------------------------------------
    def _record(
        self,
        new_features: list[dict],
        name: str,
        description: str,
        sources: list[str],
        transformation: str,
        dtype: str,
        example: object,
        relevance: str = "medium",
    ) -> None:
        new_features.append(
            {
                "name": name,
                "description": description,
                "source_columns": sources,
                "transformation": transformation,
                "data_type": dtype,
                "example_value": example,
                "business_relevance": relevance,
            }
        )

    def _extract_temporal(self, df: pd.DataFrame, new_features: list[dict]) -> None:
        for col in list(df.columns):
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
            series = pd.to_datetime(df[col], errors="coerce")
            for suffix, values, desc in (
                ("year", series.dt.year, "Calendar year"),
                ("month", series.dt.month, "Calendar month (1-12)"),
                ("quarter", series.dt.quarter, "Calendar quarter (1-4)"),
                ("dayofweek", series.dt.dayofweek, "Day of week (0=Monday)"),
            ):
                name = f"{col}_{suffix}"
                df[name] = values
                self._record(
                    new_features, name, f"{desc} extracted from {col}",
                    [col], "temporal_extract", "int64",
                    int(values.dropna().iloc[0]) if values.notna().any() else None,
                    "high",
                )
            weekend = (series.dt.dayofweek >= 5).astype("boolean")
            df[f"{col}_is_weekend"] = weekend
            self._record(
                new_features, f"{col}_is_weekend", f"Weekend flag from {col}",
                [col], "temporal_flag", "boolean",
                bool(weekend.dropna().iloc[0]) if weekend.notna().any() else None,
            )
            break  # one temporal column is enough for the MVP

    def _add_bins(self, df: pd.DataFrame, new_features: list[dict]) -> None:
        numeric = df.select_dtypes(include="number").columns.tolist()
        for col in numeric[:2]:
            series = pd.to_numeric(df[col], errors="coerce")
            if series.nunique() < 8:
                continue
            name = f"{col}_bin"
            try:
                df[name] = pd.qcut(series, q=4, duplicates="drop").astype(str)
            except Exception:
                try:
                    df[name] = pd.cut(series, bins=4).astype(str)
                except Exception:
                    continue
            self._record(
                new_features, name, f"Quartile bin of {col}",
                [col], "binning", "object",
                str(df[name].dropna().iloc[0]) if df[name].notna().any() else None,
            )

    def _add_ratios(self, df: pd.DataFrame, new_features: list[dict]) -> None:
        numeric = [
            c for c in df.select_dtypes(include="number").columns
            if (pd.to_numeric(df[c], errors="coerce") > 0).all()
        ]
        if len(numeric) < 2:
            return
        num, den = numeric[0], numeric[1]
        denom = pd.to_numeric(df[den], errors="coerce").replace(0, np.nan)
        ratio = pd.to_numeric(df[num], errors="coerce") / denom
        if ratio.notna().sum() == 0:
            return
        df[f"{num}_per_{den}"] = ratio
        self._record(
            new_features, f"{num}_per_{den}", f"Ratio of {num} to {den}",
            [num, den], "ratio", "float64",
            float(ratio.dropna().iloc[0]), "high",
        )
        df[f"{num}_times_{den}"] = pd.to_numeric(df[num], errors="coerce") * pd.to_numeric(
            df[den], errors="coerce"
        )
        self._record(
            new_features, f"{num}_times_{den}", f"Interaction of {num} and {den}",
            [num, den], "interaction", "float64",
            float(df[f"{num}_times_{den}"].dropna().iloc[0])
            if df[f"{num}_times_{den}"].notna().any() else None,
        )

    def _add_flags(self, df: pd.DataFrame, new_features: list[dict]) -> None:
        numeric = df.select_dtypes(include="number").columns.tolist()
        if not numeric:
            return
        col = numeric[0]
        series = pd.to_numeric(df[col], errors="coerce")
        threshold = float(series.quantile(0.75))
        name = f"is_high_{col}"
        df[name] = (series > threshold).astype("boolean")
        self._record(
            new_features, name, f"Top-quartile flag for {col} (> {threshold:.2f})",
            [col], "aggregation_flag", "boolean", True,
        )
