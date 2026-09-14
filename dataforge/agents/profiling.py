"""ProfilingAgent — The Analyst (v2 contract).

Deep statistical profiling of every column in ``cleaned_data``.

Frozen contract (docs/v2/AGENTS.md §7):
- Phase: 4 — Deep Analysis
- Inputs: ``cleaned_data``
- Outputs: ``profile``
- Retry: 2
- Failure: SKIP (degraded reporting)
- Timeout: 60s
- LLM: No (fully rule-based, Pandas/NumPy/SciPy)
"""

import math
import warnings
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.state import GraphState

__all__ = ["ProfilingAgent", "DataProfilingAgent"]


class ProfilingAgent(Agent):
    """Deep statistical profiling of every column.

    Produces a single ``profile`` dictionary that is consumed by
    FeatureEngineeringAgent, KPIDiscoveryAgent, StatisticalAnalysisAgent,
    InsightGenerationAgent and VisualizationAgent.

    Per-column profile:
    - Type (numeric, categorical, temporal, boolean, text)
    - Cardinality (unique count, unique ratio)
    - Completeness (missing count, missing ratio)
    - Distribution (mean, median, std, skewness, kurtosis for numeric)
    - Top values (for categorical)
    - Range (min, max, IQR for numeric)
    - Outlier count (IQR method)
    - Temporal pattern (for date columns: granularity, range, gaps)

    Dataset-level profile:
    - Correlation matrices (Pearson, Spearman)
    - Significant correlations (|r| > 0.5 with p-value)
    - Overall missing ratio
    - Duplicate row count
    """

    # v2 agent contract
    phase: ExecutionPhase = ExecutionPhase.DEEP_ANALYSIS
    required_inputs: list[str] = ["cleaned_data"]
    produced_outputs: list[str] = ["profile"]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=2)
    failure_policy: FailurePolicy = FailurePolicy.SKIP
    timeout_seconds: int = 60

    # Semantic type thresholds
    LOW_CARDINALITY_THRESHOLD: int = 10
    UNIQUE_RATIO_THRESHOLD: float = 0.2
    HIGH_CARDINALITY_THRESHOLD: int = 100
    TOP_VALUES_LIMIT: int = 10
    SIGNIFICANT_CORRELATION_THRESHOLD: float = 0.5

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize ProfilingAgent.

        Args:
            llm_provider: LLM provider instance (unused — rule-based agent).
            logger: Structured logger instance.
            retry_policy: Retry policy override.
            failure_policy: Failure policy override.
            timeout_seconds: Timeout override in seconds.
        """
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)
        # Preserve the historical agent name so the existing v1 planner and
        # graph routing (which key off "DataProfilingAgent") remain compatible.
        self.name = "DataProfilingAgent"

    async def execute(self, state: GraphState) -> AgentResult:
        """Execute deep statistical profiling.

        Args:
            state: Current graph state.

        Returns:
            AgentResult carrying the ``profile`` data update.
        """
        try:
            cleaned_data = state.data.get("cleaned_data")

            if cleaned_data is None or not isinstance(cleaned_data, pd.DataFrame):
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data not found or invalid",
                    quality_score=0.0,
                    execution_notes=["No cleaned_data available for profiling"],
                )

            if cleaned_data.empty:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data is empty",
                    quality_score=0.0,
                    execution_notes=["Empty dataset cannot be profiled"],
                )

            if cleaned_data.shape[1] == 0:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data has no columns",
                    quality_score=0.0,
                    execution_notes=["Dataset with zero columns cannot be profiled"],
                )

            if self.logger:
                self.logger.info(
                    "Starting data profiling",
                    agent=self.name,
                    rows=len(cleaned_data),
                    columns=len(cleaned_data.columns),
                )

            profile = self._build_profile(cleaned_data)

            n_rows = profile["n_rows"]
            n_columns = profile["n_columns"]
            quality_score = 1.0 - profile["overall_missing_ratio"]

            if self.logger:
                self.logger.info(
                    "Profiling complete",
                    agent=self.name,
                    numeric_columns=profile["numeric_column_count"],
                    categorical_columns=profile["categorical_column_count"],
                )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=(
                    f"Profiled {n_columns} columns: "
                    f"{profile['numeric_column_count']} numeric, "
                    f"{profile['categorical_column_count']} categorical"
                ),
                quality_score=quality_score,
                execution_notes=[
                    f"Profiled {n_rows} rows and {n_columns} columns",
                    f"{profile['numeric_column_count']} numeric, "
                    f"{profile['categorical_column_count']} categorical, "
                    f"{profile['temporal_column_count']} temporal, "
                    f"{profile['boolean_column_count']} boolean, "
                    f"{profile['text_column_count']} text",
                ],
                data_updates={"profile": profile},
                metrics={
                    "n_rows": n_rows,
                    "n_columns": n_columns,
                    "numeric_column_count": profile["numeric_column_count"],
                    "categorical_column_count": profile["categorical_column_count"],
                    "temporal_column_count": profile["temporal_column_count"],
                    "boolean_column_count": profile["boolean_column_count"],
                    "text_column_count": profile["text_column_count"],
                    "duplicate_row_count": profile["duplicate_row_count"],
                    "overall_missing_ratio": profile["overall_missing_ratio"],
                },
            )

        except Exception as e:
            if self.logger:
                self.logger.error(
                    "Profiling failed",
                    agent=self.name,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Profiling failed: {str(e)}",
                quality_score=0.0,
                execution_notes=[f"Error: {str(e)}"],
                metadata={"error_type": type(e).__name__, "error_message": str(e)},
            )

    # ════════════════════════════════════════════════════════════════
    # PROFILE ASSEMBLY
    # ════════════════════════════════════════════════════════════════

    def _build_profile(self, df: pd.DataFrame) -> dict[str, Any]:
        """Build the complete dataset profile.

        This method is pure: it never mutates ``df``.

        Args:
            df: Cleaned DataFrame.

        Returns:
            Complete profile dictionary.
        """
        columns: dict[Any, dict[str, Any]] = {}
        numeric_columns: list[Any] = []
        categorical_columns: list[Any] = []
        temporal_columns: list[Any] = []
        text_columns: list[Any] = []
        boolean_columns: list[Any] = []

        for col in df.columns:
            series = df[col]
            semantic_type = self._infer_type(series)

            col_profile: dict[str, Any] = {
                "name": col,
                "dtype": str(series.dtype),
                "type": semantic_type,
                "cardinality": self._cardinality(series),
                "completeness": self._completeness(series),
                "distribution": None,
                "range": None,
                "outlier_count": None,
                "top_values": [],
                "temporal_pattern": None,
            }

            if semantic_type == "numeric":
                numeric_columns.append(col)
                col_profile["distribution"] = self._numeric_distribution(series)
                col_profile["range"] = self._numeric_range(series)
                col_profile["outlier_count"] = self._numeric_outlier_count(series)
            elif semantic_type == "categorical":
                categorical_columns.append(col)
                col_profile["top_values"] = self._top_values(series)
            elif semantic_type == "temporal":
                temporal_columns.append(col)
                col_profile["temporal_pattern"] = self._temporal_pattern(series)
            elif semantic_type == "boolean":
                boolean_columns.append(col)
            else:  # text
                text_columns.append(col)

            columns[col] = col_profile

        total_cells = len(df) * len(df.columns)
        missing_total = int(df.isna().sum().sum())
        overall_missing_ratio = (missing_total / total_cells) if total_cells else 0.0
        duplicate_row_count = int(df.duplicated().sum())

        correlations = self._correlations(df, numeric_columns)

        return {
            "n_rows": len(df),
            "n_columns": len(df.columns),
            "columns": columns,
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "temporal_columns": temporal_columns,
            "text_columns": text_columns,
            "boolean_columns": boolean_columns,
            "has_numeric_columns": len(numeric_columns) > 0,
            "has_categorical_columns": len(categorical_columns) > 0,
            "numeric_column_count": len(numeric_columns),
            "categorical_column_count": len(categorical_columns),
            "temporal_column_count": len(temporal_columns),
            "boolean_column_count": len(boolean_columns),
            "text_column_count": len(text_columns),
            "overall_missing_ratio": overall_missing_ratio,
            "duplicate_row_count": duplicate_row_count,
            "correlations": correlations,
        }

    # ════════════════════════════════════════════════════════════════
    # SEMANTIC TYPE INFERENCE
    # ════════════════════════════════════════════════════════════════

    def _infer_type(self, series: pd.Series) -> str:
        """Infer the semantic type of a series.

        Args:
            series: Pandas Series.

        Returns:
            One of "numeric", "categorical", "temporal", "boolean", "text".
        """
        # All-null columns have no observable type; classify as categorical so
        # they are never reported as numeric (no distribution can be computed).
        if series.notna().sum() == 0:
            return "categorical"

        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if pd.api.types.is_numeric_dtype(series):
            return "numeric"
        if pd.api.types.is_datetime64_any_dtype(series):
            return "temporal"
        if isinstance(series.dtype, pd.CategoricalDtype):
            return "categorical"

        # Object/string columns: detect temporal first.
        if self._looks_temporal(series):
            return "temporal"

        non_null = series.dropna()
        n = len(non_null)
        if n == 0:
            return "categorical"

        n_unique = int(series.nunique(dropna=True))
        if n_unique <= self.LOW_CARDINALITY_THRESHOLD or (n_unique / n) < self.UNIQUE_RATIO_THRESHOLD:
            return "categorical"
        return "text"

    def _looks_temporal(self, series: pd.Series) -> bool:
        """Heuristically determine if an object series holds date/time values.

        Args:
            series: Object-dtype Pandas Series.

        Returns:
            True if the series appears to be temporal.
        """
        non_null = series.dropna()
        if len(non_null) == 0:
            return False

        # Numeric strings ("1", "2", "3") are not dates, even though
        # pandas can technically parse them as epoch offsets.
        if non_null.astype(str).str.match(r"^-?\d+(\.\d+)?$").all():
            return False

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                converted = pd.to_datetime(non_null, errors="coerce")
            return bool(converted.notna().all())
        except Exception:
            return False

    # ════════════════════════════════════════════════════════════════
    # PER-COLUMN HELPERS
    # ════════════════════════════════════════════════════════════════

    def _cardinality(self, series: pd.Series) -> dict[str, Any]:
        """Compute cardinality metrics."""
        n_unique = int(series.nunique(dropna=True))
        n = int(series.notna().sum())
        unique_ratio = (n_unique / n) if n else None
        if n_unique <= self.LOW_CARDINALITY_THRESHOLD:
            level = "low"
        elif n_unique <= self.HIGH_CARDINALITY_THRESHOLD:
            level = "medium"
        else:
            level = "high"
        return {
            "unique_count": n_unique,
            "unique_ratio": (float(unique_ratio) if unique_ratio is not None else None),
            "level": level,
        }

    def _completeness(self, series: pd.Series) -> dict[str, Any]:
        """Compute missing-value completeness metrics."""
        non_null_count = int(series.notna().sum())
        missing_count = int(series.isna().sum())
        n = len(series)
        missing_ratio = (missing_count / n) if n else 0.0
        return {
            "non_null_count": non_null_count,
            "missing_count": missing_count,
            "missing_ratio": missing_ratio,
        }

    def _numeric_distribution(self, series: pd.Series) -> dict[str, Any] | None:
        """Compute distribution statistics for a numeric series."""
        clean = self._finite(series)
        if len(clean) == 0:
            return None

        mean = float(clean.mean())
        median = float(clean.median())
        std = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0

        skewness: float | None = None
        kurtosis: float | None = None
        if len(clean) > 1 and clean.nunique() > 1:
            skewness = self._safe_stat(scipy_stats.skew, clean)
            kurtosis = self._safe_stat(scipy_stats.kurtosis, clean)

        return {
            "mean": mean,
            "median": median,
            "std": std,
            "skewness": skewness,
            "kurtosis": kurtosis,
        }

    def _numeric_range(self, series: pd.Series) -> dict[str, Any] | None:
        """Compute min/max/quartiles/IQR for a numeric series."""
        clean = self._finite(series)
        if len(clean) == 0:
            return None

        q1 = float(clean.quantile(0.25))
        q3 = float(clean.quantile(0.75))
        return {
            "min": float(clean.min()),
            "max": float(clean.max()),
            "q1": q1,
            "q3": q3,
            "iqr": q3 - q1,
        }

    def _numeric_outlier_count(self, series: pd.Series) -> int | None:
        """Count outliers using the IQR (Tukey fences) method."""
        clean = self._finite(series)
        if len(clean) == 0:
            return None

        q1 = clean.quantile(0.25)
        q3 = clean.quantile(0.75)
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        return int(((clean < lower_fence) | (clean > upper_fence)).sum())

    def _top_values(self, series: pd.Series) -> list[dict[str, Any]]:
        """Compute the most frequent values for a categorical series."""
        total = int(series.notna().sum())
        if total == 0:
            return []
        counts = series.value_counts(dropna=True).head(self.TOP_VALUES_LIMIT)
        return [
            {
                "value": value,
                "count": int(count),
                "frequency": float(count) / total,
            }
            for value, count in counts.items()
        ]

    def _temporal_pattern(self, series: pd.Series) -> dict[str, Any] | None:
        """Compute temporal pattern (granularity, range, gaps)."""
        converted = pd.to_datetime(series, errors="coerce")
        non_null = converted.dropna()
        if len(non_null) == 0:
            return None

        sorted_values = non_null.sort_values()
        min_v = sorted_values.iloc[0]
        max_v = sorted_values.iloc[-1]

        if len(sorted_values) == 1 or sorted_values.nunique() <= 1:
            granularity = "single"
            gap_count = 0
        else:
            span = max_v - min_v
            granularity = self._granularity_from_timedelta(span)
            diffs = sorted_values.diff().dropna()
            median_diff = diffs.median()
            gap_count = int((diffs > median_diff).sum())

        return {
            "granularity": granularity,
            "min": self._format_timestamp(min_v),
            "max": self._format_timestamp(max_v),
            "gap_count": gap_count,
        }

    # ════════════════════════════════════════════════════════════════
    # CORRELATIONS
    # ════════════════════════════════════════════════════════════════

    def _correlations(
        self, df: pd.DataFrame, numeric_columns: list[Any]
    ) -> dict[str, dict[str, Any]]:
        """Compute Pearson and Spearman correlation matrices with significance."""
        if len(numeric_columns) < 2:
            empty = {"matrix": {}, "significant": []}
            return {"pearson": dict(empty), "spearman": dict(empty)}

        return {
            "pearson": self._correlation_matrix(df, numeric_columns, method="pearson"),
            "spearman": self._correlation_matrix(df, numeric_columns, method="spearman"),
        }

    def _correlation_matrix(
        self, df: pd.DataFrame, numeric_columns: list[Any], method: str
    ) -> dict[str, Any]:
        """Build a symmetric correlation matrix plus significant pairs."""
        matrix: dict[Any, dict[Any, float | None]] = {
            col: {} for col in numeric_columns
        }
        significant: list[dict[str, Any]] = []

        for i, col_a in enumerate(numeric_columns):
            for col_b in numeric_columns[i:]:
                if col_a == col_b:
                    correlation = 1.0
                    p_value: float | None = 0.0
                else:
                    correlation, p_value = self._pairwise_correlation(
                        df[col_a], df[col_b], method
                    )

                matrix[col_a][col_b] = correlation
                matrix[col_b][col_a] = correlation

                if (
                    col_a != col_b
                    and correlation is not None
                    and abs(correlation) > self.SIGNIFICANT_CORRELATION_THRESHOLD
                ):
                    significant.append(
                        {
                            "column_a": col_a,
                            "column_b": col_b,
                            "correlation": correlation,
                            "p_value": p_value,
                            "strength": (
                                "strong" if abs(correlation) > 0.7 else "moderate"
                            ),
                            "direction": (
                                "positive" if correlation > 0 else "negative"
                            ),
                        }
                    )

        return {"matrix": matrix, "significant": significant}

    def _pairwise_correlation(
        self, s1: pd.Series, s2: pd.Series, method: str
    ) -> tuple[float | None, float | None]:
        """Compute pairwise correlation with p-value, ignoring missing values."""
        mask = s1.notna() & s2.notna()
        if int(mask.sum()) < 2:
            return None, None

        x = s1[mask]
        y = s2[mask]

        # Constant columns have undefined correlation.
        if x.nunique() <= 1 or y.nunique() <= 1:
            return None, None

        try:
            if method == "pearson":
                result = scipy_stats.pearsonr(x, y)
            else:
                result = scipy_stats.spearmanr(x, y)
        except Exception:
            return None, None

        statistic = getattr(result, "statistic", None)
        p_value = getattr(result, "pvalue", None)

        if statistic is None or (isinstance(statistic, float) and math.isnan(statistic)):
            return None, None

        p_float = float(p_value) if p_value is not None else None
        return float(statistic), p_float

    # ════════════════════════════════════════════════════════════════
    # UTILITY HELPERS
    # ════════════════════════════════════════════════════════════════

    def _finite(self, series: pd.Series) -> pd.Series:
        """Drop null and infinite values from a series."""
        return series.replace([np.inf, -np.inf], np.nan).dropna()

    def _safe_stat(self, func: Any, values: pd.Series) -> float | None:
        """Invoke a scipy stat function, returning None on failure/NaN."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = func(values, nan_policy="omit")
        except Exception:
            return None

        if result is None:
            return None
        try:
            if math.isnan(float(result)):
                return None
        except (TypeError, ValueError):
            return None
        return float(result)

    def _granularity_from_timedelta(self, td: pd.Timedelta) -> str:
        """Map a time span to a human-readable granularity label."""
        days = td.total_seconds() / 86400.0
        if days >= 365:
            return "yearly"
        if days >= 28:
            return "monthly"
        if days >= 7:
            return "weekly"
        if days >= 1:
            return "daily"
        if days >= 1 / 24:
            return "hourly"
        if days >= 1 / 1440:
            return "minute"
        return "second"

    def _format_timestamp(self, ts: pd.Timestamp) -> str:
        """Format a timestamp as date (when midnight) or full ISO string."""
        ts = pd.Timestamp(ts)
        if ts.hour == 0 and ts.minute == 0 and ts.second == 0 and ts.microsecond == 0:
            return ts.strftime("%Y-%m-%d")
        return ts.isoformat()


# Backward-compatible alias for the v1 class name, which is still referenced
# by the legacy planner, graph workflow and existing tests.
DataProfilingAgent = ProfilingAgent
