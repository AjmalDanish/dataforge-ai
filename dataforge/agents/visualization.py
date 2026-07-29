"""Visualization Agent - Creates data visualizations."""

import json
from pathlib import Path
from typing import Any

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


class VisualizationAgent(Agent):
    """Creates visualizations for data exploration and insights.

    Generates various types of visualizations:
    - Histograms for distributions
    - Box plots for outlier detection
    - Scatter plots for correlations
    - Bar charts for categorical data
    - Heatmaps for correlation matrices
    - Line plots for temporal data

    Saves visualizations as HTML files and generates visualization insights.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
        output_dir: str = "output/visualizations",
    ):
        """Initialize the Visualization Agent.

        Args:
            llm_provider: LLM provider instance.
            logger: Structured logger instance.
            output_dir: Directory to save visualization files.
        """
        super().__init__(llm_provider, logger)
        self.name = "VisualizationAgent"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, state: GraphState) -> AgentResult:
        """Create visualizations for the data.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with visualization information.
        """
        import pandas as pd

        df = state.get("raw_data")
        if df is None:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No data available for visualization",
            )

        if len(df) == 0:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="Empty dataset provided for visualization",
            )

        self.logger.info(
            "Starting visualization generation",
            agent=self.name,
            rows=len(df),
            columns=len(df.columns),
            output_dir=str(self.output_dir),
        )

        try:
            # Get profile
            profile = state.get("profile", {})
            numeric_columns = profile.get("numeric_columns", [])
            categorical_columns = profile.get("categorical_columns", [])

            if not numeric_columns and not categorical_columns:
                self.logger.warning(
                    "No columns available for visualization",
                    agent=self.name,
                )
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="No columns available for visualization",
                    data_updates={"visualizations": [], "insights": state.get("insights", [])},
                    metadata={"visualization_count": 0},
                )

            # Create visualizations
            visualizations = []

            # Distribution plots for numeric columns
            if numeric_columns:
                numeric_viz = self._create_distribution_plots(df, numeric_columns, state)
                visualizations.extend(numeric_viz)

            # Box plots for numeric columns
            if numeric_columns:
                box_viz = self._create_box_plots(df, numeric_columns, state)
                visualizations.extend(box_viz)

            # Correlation heatmap if multiple numeric columns
            if len(numeric_columns) >= 2:
                corr_viz = self._create_correlation_heatmap(df, numeric_columns, state)
                if corr_viz:
                    visualizations.append(corr_viz)

            # Scatter plots for correlations
            statistics = state.get("statistics", {})
            correlations = statistics.get("correlations", {}).get("significant", [])
            if correlations:
                scatter_viz = self._create_scatter_plots(df, correlations, state)
                visualizations.extend(scatter_viz)

            # Bar charts for categorical columns
            if categorical_columns:
                bar_viz = self._create_bar_charts(df, categorical_columns, state)
                visualizations.extend(bar_viz)

            # Categorical vs numeric plots
            if categorical_columns and numeric_columns:
                cat_num_viz = self._create_categorical_numeric_plots(
                    df, categorical_columns, numeric_columns, state
                )
                visualizations.extend(cat_num_viz)

            # Generate visualization insights
            insights = await self._generate_visualization_insights(
                df, visualizations, profile, statistics
            )

            self.logger.info(
                "Visualization generation complete",
                agent=self.name,
                visualizations_created=len(visualizations),
                insights_generated=len(insights),
            )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Created {len(visualizations)} visualizations: "
                f"{sum(1 for v in visualizations if v['type'] == 'distribution')} distributions, "
                f"{sum(1 for v in visualizations if v['type'] == 'boxplot')} box plots, "
                f"{sum(1 for v in visualizations if v['type'] == 'correlation')} correlations",
                data_updates={
                    "visualizations": visualizations,
                    "insights": state.get("insights", []) + insights,
                },
                metadata={
                    "visualization_count": len(visualizations),
                    "output_dir": str(self.output_dir),
                    "insights_generated": len(insights),
                },
            )

        except Exception as e:
            self.logger.error(
                "Visualization generation failed",
                agent=self.name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Visualization generation failed: {str(e)}",
                metadata={"error_type": type(e).__name__, "error_message": str(e)},
            )

    def _create_distribution_plots(
        self, df, numeric_columns: list[str], state: GraphState
    ) -> list[dict[str, Any]]:
        """Create histogram distribution plots.

        Args:
            df: Pandas DataFrame.
            numeric_columns: List of numeric column names.
            state: Current graph state.

        Returns:
            List of visualization dictionaries.
        """
        import plotly.express as px

        visualizations = []

        for col in numeric_columns:
            if col not in df.columns:
                continue

            try:
                # Create histogram
                fig = px.histogram(
                    df,
                    x=col,
                    title=f"Distribution of {col}",
                    nbins=30,
                    marginal="box",
                )
                fig.update_layout(
                    xaxis_title=col,
                    yaxis_title="Count",
                    hovermode="x unified",
                )

                # Save as HTML
                filename = f"distribution_{col}.html"
                filepath = self.output_dir / filename
                fig.write_html(str(filepath))

                visualizations.append(
                    {
                        "type": "distribution",
                        "column": col,
                        "title": f"Distribution of {col}",
                        "file_path": str(filepath),
                        "file_name": filename,
                        "format": "html",
                    }
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to create distribution plot",
                    agent=self.name,
                    column=col,
                    error=str(e),
                )

        return visualizations

    def _create_box_plots(
        self, df, numeric_columns: list[str], state: GraphState
    ) -> list[dict[str, Any]]:
        """Create box plots for outlier detection.

        Args:
            df: Pandas DataFrame.
            numeric_columns: List of numeric column names.
            state: Current graph state.

        Returns:
            List of visualization dictionaries.
        """
        import plotly.express as px

        visualizations = []

        for col in numeric_columns:
            if col not in df.columns:
                continue

            try:
                # Create box plot
                fig = px.box(df, y=col, title=f"Box Plot of {col}")
                fig.update_layout(yaxis_title=col)

                # Save as HTML
                filename = f"boxplot_{col}.html"
                filepath = self.output_dir / filename
                fig.write_html(str(filepath))

                visualizations.append(
                    {
                        "type": "boxplot",
                        "column": col,
                        "title": f"Box Plot of {col}",
                        "file_path": str(filepath),
                        "file_name": filename,
                        "format": "html",
                    }
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to create box plot",
                    agent=self.name,
                    column=col,
                    error=str(e),
                )

        return visualizations

    def _create_correlation_heatmap(
        self, df, numeric_columns: list[str], state: GraphState
    ) -> dict[str, Any] | None:
        """Create correlation heatmap.

        Args:
            df: Pandas DataFrame.
            numeric_columns: List of numeric column names.
            state: Current graph state.

        Returns:
            Visualization dictionary or None if failed.
        """
        import plotly.figure_factory as ff

        try:
            # Compute correlation matrix
            corr_matrix = df[numeric_columns].corr()

            # Create heatmap
            fig = ff.create_annotated_heatmap(
                z=corr_matrix.values,
                x=list(corr_matrix.columns),
                y=list(corr_matrix.index),
                annotation_text=corr_matrix.round(2).values,
                colorscale="RdBu",
                showscale=True,
            )
            fig.update_layout(
                title="Correlation Heatmap",
                xaxis_title="",
                yaxis_title="",
            )

            # Save as HTML
            filename = "correlation_heatmap.html"
            filepath = self.output_dir / filename
            fig.write_html(str(filepath))

            return {
                "type": "correlation",
                "columns": numeric_columns,
                "title": "Correlation Heatmap",
                "file_path": str(filepath),
                "file_name": filename,
                "format": "html",
            }
        except Exception as e:
            self.logger.warning(
                "Failed to create correlation heatmap",
                agent=self.name,
                error=str(e),
            )
            return None

    def _create_scatter_plots(
        self, df, correlations: list[dict[str, Any]], state: GraphState
    ) -> list[dict[str, Any]]:
        """Create scatter plots for significant correlations.

        Args:
            df: Pandas DataFrame.
            correlations: List of significant correlation dictionaries.
            state: Current graph state.

        Returns:
            List of visualization dictionaries.
        """
        import plotly.express as px

        visualizations = []

        for corr in correlations:
            columns = corr.get("columns", [])
            if len(columns) != 2:
                continue

            col1, col2 = columns
            if col1 not in df.columns or col2 not in df.columns:
                continue

            try:
                # Create scatter plot
                fig = px.scatter(
                    df,
                    x=col1,
                    y=col2,
                    title=f"{col1} vs {col2} (r={corr['correlation']:.2f})",
                    trendline="ols" if len(df) > 10 else None,
                )
                fig.update_layout(xaxis_title=col1, yaxis_title=col2)

                # Save as HTML
                filename = f"scatter_{col1}_{col2}.html"
                filepath = self.output_dir / filename
                fig.write_html(str(filepath))

                visualizations.append(
                    {
                        "type": "scatter",
                        "columns": [col1, col2],
                        "title": f"{col1} vs {col2}",
                        "file_path": str(filepath),
                        "file_name": filename,
                        "format": "html",
                        "correlation": corr["correlation"],
                    }
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to create scatter plot",
                    agent=self.name,
                    columns=columns,
                    error=str(e),
                )

        return visualizations

    def _create_bar_charts(
        self, df, categorical_columns: list[str], state: GraphState
    ) -> list[dict[str, Any]]:
        """Create bar charts for categorical columns.

        Args:
            df: Pandas DataFrame.
            categorical_columns: List of categorical column names.
            state: Current graph state.

        Returns:
            List of visualization dictionaries.
        """
        import plotly.express as px

        visualizations = []

        for col in categorical_columns:
            if col not in df.columns:
                continue

            try:
                # Count values
                value_counts = df[col].value_counts().head(20)  # Limit to top 20

                # Create bar chart
                fig = px.bar(
                    x=value_counts.index,
                    y=value_counts.values,
                    title=f"Top Values for {col}",
                    labels={"x": col, "y": "Count"},
                )
                fig.update_layout(xaxis_title=col, yaxis_title="Count")

                # Save as HTML
                filename = f"bar_{col}.html"
                filepath = self.output_dir / filename
                fig.write_html(str(filepath))

                visualizations.append(
                    {
                        "type": "bar",
                        "column": col,
                        "title": f"Top Values for {col}",
                        "file_path": str(filepath),
                        "file_name": filename,
                        "format": "html",
                        "value_count": len(value_counts),
                    }
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to create bar chart",
                    agent=self.name,
                    column=col,
                    error=str(e),
                )

        return visualizations

    def _create_categorical_numeric_plots(
        self,
        df,
        categorical_columns: list[str],
        numeric_columns: list[str],
        state: GraphState,
    ) -> list[dict[str, Any]]:
        """Create categorical vs numeric plots.

        Args:
            df: Pandas DataFrame.
            categorical_columns: List of categorical column names.
            numeric_columns: List of numeric column names.
            state: Current graph state.

        Returns:
            List of visualization dictionaries.
        """
        import plotly.express as px

        visualizations = []
        statistics = state.get("statistics", {})
        group_tests = statistics.get("group_tests", {})

        # Only create plots for significant group differences
        significant_tests = [
            (key, result)
            for key, result in group_tests.items()
            if result.get("significant") is True
        ]

        # Limit to top 5 significant tests
        significant_tests = significant_tests[:5]

        for key, result in significant_tests:
            cat_col = result.get("categorical_column")
            num_col = result.get("numeric_column")

            if cat_col not in df.columns or num_col not in df.columns:
                continue

            try:
                # Create box plot by category
                fig = px.box(
                    df,
                    x=cat_col,
                    y=num_col,
                    title=f"{num_col} by {cat_col}",
                )
                fig.update_layout(xaxis_title=cat_col, yaxis_title=num_col)

                # Save as HTML
                filename = f"box_{num_col}_by_{cat_col}.html"
                filepath = self.output_dir / filename
                fig.write_html(str(filepath))

                visualizations.append(
                    {
                        "type": "categorical_numeric",
                        "columns": [cat_col, num_col],
                        "title": f"{num_col} by {cat_col}",
                        "file_path": str(filepath),
                        "file_name": filename,
                        "format": "html",
                        "p_value": result.get("p_value"),
                    }
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to create categorical-numeric plot",
                    agent=self.name,
                    columns=[cat_col, num_col],
                    error=str(e),
                )

        return visualizations

    async def _generate_visualization_insights(
        self,
        df,
        visualizations: list[dict[str, Any]],
        profile: dict[str, Any],
        statistics: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate insights from visualizations.

        Args:
            df: Pandas DataFrame.
            visualizations: List of visualization dictionaries.
            profile: Data profile.
            statistics: Statistical analysis results.

        Returns:
            List of insight dictionaries.
        """
        insights = []

        # Insights about visualizations created
        viz_types = {}
        for viz in visualizations:
            viz_type = viz.get("type", "unknown")
            viz_types[viz_type] = viz_types.get(viz_type, 0) + 1

        if viz_types:
            type_str = ", ".join([f"{v} {k}" for k, v in viz_types.items()])
            insights.append(
                {
                    "type": "visualization_summary",
                    "message": f"Generated {len(visualizations)} visualizations: {type_str}",
                    "severity": "info",
                    "visualization_types": viz_types,
                    "total_visualizations": len(visualizations),
                }
            )

        # Insights about correlations visualized
        scatter_plots = [v for v in visualizations if v.get("type") == "scatter"]
        if scatter_plots:
            insights.append(
                {
                    "type": "correlation_visualizations",
                    "message": f"Created {len(scatter_plots)} scatter plots for correlated features",
                    "severity": "info",
                    "correlation_count": len(scatter_plots),
                }
            )

        # Insights about distributions
        distributions = [v for v in visualizations if v.get("type") == "distribution"]
        if distributions:
            distribution_tests = statistics.get("distribution_tests", {})
            non_normal = [
                v["column"]
                for v in distributions
                if distribution_tests.get(v["column"], {}).get("is_normal") is False
            ]

            if non_normal:
                insights.append(
                    {
                        "type": "distribution_insights",
                        "message": f"Visualized {len(distributions)} distributions; "
                        f"{len(non_normal)} appear non-normal and may need transformation",
                        "severity": "info",
                        "non_normal_columns": non_normal,
                    }
                )

        # Insights about outliers
        box_plots = [v for v in visualizations if v.get("type") == "boxplot"]
        outliers = statistics.get("outliers", {})
        columns_with_outliers = [col for col, indices in outliers.items() if indices]

        if box_plots and columns_with_outliers:
            insights.append(
                {
                    "type": "outlier_insights",
                    "message": f"Box plots reveal outliers in {len(columns_with_outliers)} columns",
                    "severity": "warning" if len(columns_with_outliers) > 2 else "info",
                    "columns_with_outliers": columns_with_outliers,
                }
            )

        # Insights about group differences
        cat_num_plots = [v for v in visualizations if v.get("type") == "categorical_numeric"]
        if cat_num_plots:
            insights.append(
                {
                    "type": "group_difference_insights",
                    "message": f"Visualized {len(cat_num_plots)} significant group differences",
                    "severity": "info",
                    "group_difference_count": len(cat_num_plots),
                }
            )

        return insights
