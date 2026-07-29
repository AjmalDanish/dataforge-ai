"""Statistical Analysis Agent - Performs statistical tests and analysis."""

from typing import Any

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


class StatisticalAnalysisAgent(Agent):
    """Performs statistical analysis on numeric data.

    Executes statistical tests and analysis on numeric columns:
    - Descriptive statistics (mean, median, std, quartiles)
    - Correlation analysis
    - Distribution tests (normality, skewness, kurtosis)
    - Group comparisons (if categorical columns present)
    - Outlier detection

    Generates statistical insights and recommendations for visualization.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
    ):
        """Initialize the Statistical Analysis Agent.

        Args:
            llm_provider: LLM provider instance.
            logger: Structured logger instance.
        """
        super().__init__(llm_provider, logger)
        self.name = "StatisticalAnalysisAgent"

    async def execute(self, state: GraphState) -> AgentResult:
        """Perform statistical analysis on the data.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with statistical analysis results.
        """
        import pandas as pd

        df = state.get("raw_data")
        if df is None:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No data available for statistical analysis",
            )

        if len(df) == 0:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="Empty dataset provided for statistical analysis",
            )

        self.logger.info(
            "Starting statistical analysis",
            agent=self.name,
            rows=len(df),
            columns=len(df.columns),
        )

        try:
            # Get numeric columns from profile
            profile = state.get("profile", {})
            numeric_columns = profile.get("numeric_columns", [])

            if not numeric_columns:
                self.logger.warning(
                    "No numeric columns found",
                    agent=self.name,
                )
                # Not an error - just continue without statistical analysis
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="No numeric columns available for statistical analysis",
                    data_updates={"statistics": {}, "insights": state.get("insights", [])},
                    metadata={"numeric_column_count": 0},
                )

            # Perform statistical analysis
            statistics = self._compute_statistics(df, numeric_columns)
            correlations = self._compute_correlations(df, numeric_columns)
            distribution_tests = self._test_distributions(df, numeric_columns)

            # Detect outliers
            outliers = self._detect_outliers(df, numeric_columns)

            # Group comparisons if categorical columns exist
            categorical_columns = profile.get("categorical_columns", [])
            group_tests = {}
            if categorical_columns:
                group_tests = self._perform_group_tests(df, numeric_columns, categorical_columns)

            # Combine all results
            statistical_results = {
                "descriptive_stats": statistics,
                "correlations": correlations,
                "distribution_tests": distribution_tests,
                "outliers": outliers,
                "group_tests": group_tests,
                "numeric_column_count": len(numeric_columns),
            }

            # Generate statistical insights
            insights = await self._generate_statistical_insights(df, statistical_results, profile)

            self.logger.info(
                "Statistical analysis complete",
                agent=self.name,
                numeric_columns=len(numeric_columns),
                significant_correlations=len(correlations.get("significant", [])),
                outliers_detected=sum(len(o) for o in outliers.values()),
                insights_generated=len(insights),
            )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Completed statistical analysis on {len(numeric_columns)} numeric columns: "
                f"{len(correlations.get('significant', []))} significant correlations, "
                f"{sum(len(o) for o in outliers.values())} outliers detected",
                data_updates={
                    "statistics": statistical_results,
                    "insights": state.get("insights", []) + insights,
                },
                metadata={
                    "numeric_column_count": len(numeric_columns),
                    "significant_correlations": len(correlations.get("significant", [])),
                    "outliers_detected": sum(len(o) for o in outliers.values()),
                    "insights_generated": len(insights),
                },
            )

        except Exception as e:
            self.logger.error(
                "Statistical analysis failed",
                agent=self.name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Statistical analysis failed: {str(e)}",
                metadata={"error_type": type(e).__name__, "error_message": str(e)},
            )

    def _compute_statistics(self, df, numeric_columns: list[str]) -> dict[str, dict[str, Any]]:
        """Compute descriptive statistics.

        Args:
            df: Pandas DataFrame.
            numeric_columns: List of numeric column names.

        Returns:
            Dictionary of statistics per column.
        """
        stats = {}

        for col in numeric_columns:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if len(series) == 0:
                continue

            stats[col] = {
                "count": len(series),
                "mean": float(series.mean()) if len(series) > 0 else None,
                "median": float(series.median()) if len(series) > 0 else None,
                "std": float(series.std()) if len(series) > 0 else None,
                "min": float(series.min()) if len(series) > 0 else None,
                "max": float(series.max()) if len(series) > 0 else None,
                "q25": float(series.quantile(0.25)) if len(series) > 0 else None,
                "q75": float(series.quantile(0.75)) if len(series) > 0 else None,
                "skewness": float(series.skew()) if len(series) >= 3 else None,
                "kurtosis": float(series.kurtosis()) if len(series) >= 4 else None,
                "variance": float(series.var()) if len(series) > 0 else None,
            }

        return stats

    def _compute_correlations(self, df, numeric_columns: list[str]) -> dict[str, Any]:
        """Compute pairwise correlations between numeric columns.

        Args:
            df: Pandas DataFrame.
            numeric_columns: List of numeric column names.

        Returns:
            Dictionary with correlation matrix and significant correlations.
        """
        import pandas as pd

        # Get only numeric columns that exist
        available_columns = [c for c in numeric_columns if c in df.columns]

        if len(available_columns) < 2:
            return {"matrix": {}, "significant": []}

        # Compute correlation matrix
        corr_matrix = df[available_columns].corr()

        # Convert to nested dict
        corr_dict = {}
        significant = []

        for i, col1 in enumerate(available_columns):
            for col2 in available_columns[i + 1 :]:
                corr_val = (
                    float(corr_matrix.loc[col1, col2])
                    if pd.notna(corr_matrix.loc[col1, col2])
                    else 0.0
                )

                corr_dict[f"{col1}_{col2}"] = corr_val

                # Flag significant correlations (|r| > 0.5)
                if abs(corr_val) > 0.5:
                    significant.append(
                        {
                            "columns": [col1, col2],
                            "correlation": corr_val,
                            "strength": "strong" if abs(corr_val) > 0.7 else "moderate",
                            "direction": "positive" if corr_val > 0 else "negative",
                        }
                    )

        return {"matrix": corr_dict, "significant": significant}

    def _test_distributions(self, df, numeric_columns: list[str]) -> dict[str, dict[str, Any]]:
        """Test distribution characteristics.

        Args:
            df: Pandas DataFrame.
            numeric_columns: List of numeric column names.

        Returns:
            Dictionary of distribution test results.
        """
        from scipy import stats as scipy_stats

        results = {}

        for col in numeric_columns:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if len(series) < 3:
                continue

            # Skewness and kurtosis
            skewness = float(series.skew()) if len(series) >= 3 else None
            kurtosis = float(series.kurtosis()) if len(series) >= 4 else None

            # Shapiro-Wilk test for normality (requires >= 3 samples)
            shapiro_stat = None
            shapiro_p = None
            is_normal = None

            if len(series) >= 3:
                try:
                    shapiro_stat, shapiro_p = scipy_stats.shapiro(series)
                    is_normal = float(shapiro_p) > 0.05
                except Exception:
                    pass

            results[col] = {
                "skewness": skewness,
                "kurtosis": kurtosis,
                "is_skewed": skewness is not None and abs(skewness) > 1.0,
                "is_heavy_tailed": kurtosis is not None and kurtosis > 3.0,
                "shapiro_stat": float(shapiro_stat) if shapiro_stat is not None else None,
                "shapiro_p": float(shapiro_p) if shapiro_p is not None else None,
                "is_normal": is_normal,
            }

        return results

    def _detect_outliers(self, df, numeric_columns: list[str]) -> dict[str, list[int]]:
        """Detect outliers using IQR method.

        Args:
            df: Pandas DataFrame.
            numeric_columns: List of numeric column names.

        Returns:
            Dictionary mapping column names to list of outlier indices.
        """
        outliers = {}

        for col in numeric_columns:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if len(series) < 4:
                continue

            # IQR method
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            # Find outliers
            outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
            outlier_indices = df[outlier_mask].index.tolist()

            outliers[col] = outlier_indices

        return outliers

    def _perform_group_tests(
        self, df, numeric_columns: list[str], categorical_columns: list[str]
    ) -> dict[str, Any]:
        """Perform group-based statistical tests.

        Args:
            df: Pandas DataFrame.
            numeric_columns: List of numeric column names.
            categorical_columns: List of categorical column names.

        Returns:
            Dictionary of group test results.
        """
        from scipy import stats as scipy_stats

        results = {}

        for cat_col in categorical_columns:
            if cat_col not in df.columns:
                continue

            groups = df.groupby(cat_col)

            # Get groups with enough data
            valid_groups = {name: group for name, group in groups if len(group) >= 3}

            if len(valid_groups) < 2:
                continue

            # Compare across groups for each numeric column
            for num_col in numeric_columns:
                if num_col not in df.columns:
                    continue

                group_values = [group[num_col].dropna().values for _, group in valid_groups.items()]

                # Skip if any group has insufficient data
                if any(len(v) < 3 for v in group_values):
                    continue

                # ANOVA test
                try:
                    f_stat, p_value = scipy_stats.f_oneway(*group_values)

                    key = f"{num_col}_by_{cat_col}"
                    results[key] = {
                        "categorical_column": cat_col,
                        "numeric_column": num_col,
                        "f_statistic": float(f_stat),
                        "p_value": float(p_value),
                        "significant": float(p_value) < 0.05,
                        "group_names": list(valid_groups.keys()),
                        "group_means": [
                            float(group[num_col].mean()) for _, group in valid_groups.items()
                        ],
                    }
                except Exception:
                    pass

        return results

    async def _generate_statistical_insights(
        self, df, statistical_results: dict[str, Any], profile: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate insights from statistical analysis.

        Args:
            df: Pandas DataFrame.
            statistical_results: Statistical analysis results.
            profile: Data profile.

        Returns:
            List of insight dictionaries.
        """
        insights = []

        # Insights about correlations
        significant_correlations = statistical_results.get("correlations", {}).get(
            "significant", []
        )

        for corr in significant_correlations:
            strength = corr.get("strength", "moderate")
            direction = corr.get("direction", "positive")
            columns_str = " and ".join(corr["columns"])

            insights.append(
                {
                    "type": "correlation",
                    "message": f"Strong {direction} correlation ({corr['correlation']:.2f}) found between {columns_str}",
                    "severity": "info" if strength == "moderate" else "warning",
                    "columns": corr["columns"],
                    "correlation": corr["correlation"],
                }
            )

        # Insights about outliers
        outliers = statistical_results.get("outliers", {})
        total_outliers = sum(len(indices) for indices in outliers.values())

        if total_outliers > 0:
            insights.append(
                {
                    "type": "outlier",
                    "message": f"Detected {total_outliers} outlier values across {len(outliers)} columns",
                    "severity": "warning",
                    "columns": list(outliers.keys()),
                    "outlier_count": total_outliers,
                }
            )

        # Insights about distributions
        distribution_tests = statistical_results.get("distribution_tests", {})
        non_normal_columns = [
            col for col, tests in distribution_tests.items() if tests.get("is_normal") is False
        ]

        if non_normal_columns:
            insights.append(
                {
                    "type": "distribution",
                    "message": f"{len(non_normal_columns)} columns do not follow normal distribution: {', '.join(non_normal_columns[:3])}",
                    "severity": "info",
                    "columns": non_normal_columns,
                }
            )

        # Insights about group differences
        group_tests = statistical_results.get("group_tests", {})
        significant_group_tests = [
            (key, result)
            for key, result in group_tests.items()
            if result.get("significant") is True
        ]

        for key, result in significant_group_tests:
            cat_col = result["categorical_column"]
            num_col = result["numeric_column"]

            insights.append(
                {
                    "type": "group_difference",
                    "message": f"Significant differences found in {num_col} across {cat_col} groups (p={result['p_value']:.4f})",
                    "severity": "info",
                    "columns": [cat_col, num_col],
                    "p_value": result["p_value"],
                }
            )

        # Insights about skewness
        skewed_columns = [
            col for col, tests in distribution_tests.items() if tests.get("is_skewed") is True
        ]

        if skewed_columns:
            insights.append(
                {
                    "type": "skewness",
                    "message": f"{len(skewed_columns)} columns show significant skewness: {', '.join(skewed_columns[:3])}",
                    "severity": "info",
                    "columns": skewed_columns,
                }
            )

        return insights
