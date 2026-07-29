"""Data Profiling Agent - Analyze data structure and characteristics."""

from datetime import datetime, timezone
from typing import Any

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


class DataProfilingAgent(Agent):
    """Agent for profiling dataset structure and characteristics.

    Analyzes:
    - Column names and data types
    - Missing value percentages
    - Unique value counts
    - Semantic type classification (numeric, categorical, temporal, text)
    - Identification of numeric and categorical columns
    - Detection of potential key columns
    - Detection of high-cardinality categorical columns

    Semantic Types:
    - numeric: Integer or float columns
    - temporal: DateTime columns
    - boolean: Boolean columns
    - categorical: Low cardinality strings
    - text: High cardinality strings

    Uses LLM to generate initial insights about data characteristics.
    """

    async def execute(self, state: GraphState) -> AgentResult:
        """Profile the dataset.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with profiling information and initial insights.
        """
        import pandas as pd

        df = state.get("raw_data")
        if df is None:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No data available for profiling",
            )

        self.logger.info(
            "Starting data profiling",
            agent=self.name,
            rows=len(df),
            columns=len(df.columns),
        )

        try:
            # Analyze columns
            columns_info = self._analyze_columns(df)

            # Classify columns
            numeric_columns = [
                name for name, info in columns_info.items() if info["type"] == "numeric"
            ]
            categorical_columns = [
                name for name, info in columns_info.items() if info["type"] == "categorical"
            ]

            # Build profile
            profile = {
                "n_rows": len(df),
                "n_columns": len(df.columns),
                "columns": columns_info,
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
                "has_numeric_columns": len(numeric_columns) > 0,
                "has_categorical_columns": len(categorical_columns) > 0,
                "numeric_column_count": len(numeric_columns),
                "categorical_column_count": len(categorical_columns),
                "overall_missing_ratio": df.isna().sum().sum() / (len(df) * len(df.columns)),
            }

            # Generate basic insights
            insights = await self._generate_basic_insights(df, profile)

            self.logger.info(
                "Profiling complete",
                agent=self.name,
                numeric_columns=len(numeric_columns),
                categorical_columns=len(categorical_columns),
                insights_generated=len(insights),
            )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Profiled {len(columns_info)} columns: {len(numeric_columns)} numeric, {len(categorical_columns)} categorical",
                data_updates={
                    "profile": profile,
                    "insights": state.get("insights", []) + insights,
                },
                metadata={
                    "column_count": len(columns_info),
                    "numeric_column_count": len(numeric_columns),
                    "categorical_column_count": len(categorical_columns),
                    "insights_generated": len(insights),
                },
            )

        except Exception as e:
            self.logger.error(
                "Profiling failed",
                agent=self.name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Profiling failed: {str(e)}",
                metadata={"error_type": type(e).__name__, "error_message": str(e)},
            )

    def _analyze_columns(self, df) -> dict[str, dict[str, Any]]:
        """Analyze each column's characteristics.

        Args:
            df: Pandas DataFrame.

        Returns:
            Dictionary mapping column names to their information.
        """
        columns_info: dict[str, dict[str, Any]] = {}

        for col in df.columns:
            dtype = str(df[col].dtype)
            n_unique = df[col].nunique()
            n_missing = df[col].isna().sum()
            missing_ratio = n_missing / len(df)

            # Infer semantic type
            semantic_type = self._infer_semantic_type(df[col], dtype, n_unique)

            columns_info[col] = {
                "name": str(col),
                "dtype": dtype,
                "type": semantic_type,
                "n_unique": n_unique,
                "n_missing": n_missing,
                "missing_ratio": missing_ratio,
                "is_high_cardinality": (semantic_type == "categorical" and n_unique > 100),
            }

        return columns_info

    def _infer_semantic_type(self, series, dtype: str, n_unique: int) -> str:
        """Infer semantic type from data.

        Args:
            series: Pandas Series.
            dtype: Pandas dtype string.
            n_unique: Number of unique values.

        Returns:
            Semantic type string.
        """
        import pandas as pd

        if pd.api.types.is_numeric_dtype(dtype):
            return "numeric"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return "temporal"
        elif pd.api.types.is_bool_dtype(dtype):
            return "boolean"
        else:
            # Categorical if low cardinality (<= 10 unique values or < 20% unique)
            if n_unique <= 10 or (n_unique / len(series) < 0.2):
                return "categorical"
            else:
                return "text"

    async def _generate_basic_insights(self, df, profile: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate basic insights about the data.

        Args:
            df: Pandas DataFrame.
            profile: Profile dictionary.

        Returns:
            List of insight dictionaries.
        """
        insights = []

        # Insight about data quality
        total_missing = sum(c["n_missing"] for c in profile["columns"].values())
        if total_missing > 0:
            missing_pct = (total_missing / profile["n_rows"] / profile["n_columns"]) * 100
            insights.append(
                {
                    "type": "data_quality",
                    "message": f"Dataset has {total_missing} missing values across {profile['n_columns']} columns ({missing_pct:.1f}%)",
                    "severity": "warning" if missing_pct > 10 else "info",
                }
            )

        # Insight about column types
        numeric_count = profile["numeric_column_count"]
        if numeric_count == 0:
            insights.append(
                {
                    "type": "data_structure",
                    "message": "No numeric columns found - statistical analysis will be skipped",
                    "severity": "warning",
                }
            )
        else:
            insights.append(
                {
                    "type": "data_structure",
                    "message": f"Found {numeric_count} numeric columns available for statistical analysis",
                    "severity": "info",
                }
            )

        # Insight about high cardinality
        high_cardinality_cols = [
            name for name, info in profile["columns"].items() if info.get("is_high_cardinality")
        ]
        if high_cardinality_cols:
            insights.append(
                {
                    "type": "data_structure",
                    "message": f"Found {len(high_cardinality_cols)} high-cardinality categorical columns",
                    "severity": "info",
                }
            )

        return insights
