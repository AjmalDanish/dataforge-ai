"""Plotly implementation of the ChartEngine interface."""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dataforge.infrastructure.interfaces import ChartEngine


class PlotlyChartEngine(ChartEngine):
    """Plotly implementation of the ChartEngine interface.

    Creates interactive HTML charts using Plotly Express and Graph Objects.
    """

    async def create_bar_chart(
        self,
        data: pd.DataFrame,
        x_column: str,
        y_column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a bar chart.

        Args:
            data: Input data (pandas DataFrame).
            x_column: Column name for x-axis.
            y_column: Column name for y-axis.
            title: Chart title.
            **kwargs: Additional chart options (color, hover_data, etc.).

        Returns:
            HTML string containing the interactive chart.
        """
        color = kwargs.get("color")
        hover_data = kwargs.get("hover_data")
        orientation = kwargs.get("orientation", "v")

        if orientation == "h":
            fig = px.bar(
                data,
                x=y_column,
                y=x_column,
                title=title,
                color=color,
                hover_data=hover_data,
                orientation="h",
            )
        else:
            fig = px.bar(
                data,
                x=x_column,
                y=y_column,
                title=title,
                color=color,
                hover_data=hover_data,
            )

        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    async def create_line_chart(
        self,
        data: pd.DataFrame,
        x_column: str,
        y_column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a line chart.

        Args:
            data: Input data (pandas DataFrame).
            x_column: Column name for x-axis (typically temporal).
            y_column: Column name for y-axis.
            title: Chart title.
            **kwargs: Additional chart options (color, markers, etc.).

        Returns:
            HTML string containing the interactive chart.
        """
        color = kwargs.get("color")
        markers = kwargs.get("markers", False)
        line_group = kwargs.get("line_group")

        fig = px.line(
            data,
            x=x_column,
            y=y_column,
            title=title,
            color=color,
            markers=markers,
            line_group=line_group,
        )

        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    async def create_scatter_plot(
        self,
        data: pd.DataFrame,
        x_column: str,
        y_column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a scatter plot.

        Args:
            data: Input data (pandas DataFrame).
            x_column: Column name for x-axis.
            y_column: Column name for y-axis.
            title: Chart title.
            **kwargs: Additional chart options (color, size, hover_data, etc.).

        Returns:
            HTML string containing the interactive chart.
        """
        color = kwargs.get("color")
        size = kwargs.get("size")
        hover_data = kwargs.get("hover_data")
        trendline = kwargs.get("trendline")

        fig = px.scatter(
            data,
            x=x_column,
            y=y_column,
            title=title,
            color=color,
            size=size,
            hover_data=hover_data,
            trendline=trendline,
        )

        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    async def create_histogram(
        self,
        data: pd.DataFrame,
        column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a histogram.

        Args:
            data: Input data (pandas DataFrame).
            column: Column name to plot.
            title: Chart title.
            **kwargs: Additional chart options (color, nbins, etc.).

        Returns:
            HTML string containing the interactive chart.
        """
        color = kwargs.get("color")
        nbins = kwargs.get("nbins")
        marginal = kwargs.get("marginal")

        fig = px.histogram(
            data,
            x=column,
            title=title,
            color=color,
            nbins=nbins,
            marginal=marginal,
        )

        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    async def create_box_plot(
        self,
        data: pd.DataFrame,
        column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a box plot.

        Args:
            data: Input data (pandas DataFrame).
            column: Column name to plot.
            title: Chart title.
            **kwargs: Additional chart options (color, points, etc.).

        Returns:
            HTML string containing the interactive chart.
        """
        color = kwargs.get("color")
        points = kwargs.get("points", "outliers")
        notched = kwargs.get("notched", False)

        fig = px.box(
            data,
            y=column,
            title=title,
            color=color,
            points=points,
            notched=notched,
        )

        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    async def create_correlation_heatmap(
        self,
        data: pd.DataFrame,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a correlation heatmap.

        Args:
            data: Input data (pandas DataFrame).
            title: Chart title.
            **kwargs: Additional chart options (color_scale, etc.).

        Returns:
            HTML string containing the interactive chart.
        """
        # Select only numeric columns for correlation
        numeric_data = data.select_dtypes(include="number")
        correlation_matrix = numeric_data.corr()

        color_scale = kwargs.get("color_scale", "RdBu")
        text_auto = kwargs.get("text_auto", True)

        fig = go.Figure(
            data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.columns,
                colorscale=color_scale,
                text=correlation_matrix.values if text_auto else None,
                texttemplate="%{text:.2f}" if text_auto else None,
                textfont={"size": 10},
                colorbar={"title": "Correlation"},
            )
        )

        fig.update_layout(
            title=title,
            xaxis={"side": "bottom"},
            yaxis={"side": "left"},
            margin={"l": 100, "r": 100, "b": 100, "t": 100},
        )

        return fig.to_html(full_html=False, include_plotlyjs="cdn")