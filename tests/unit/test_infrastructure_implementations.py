"""Unit tests for infrastructure implementations."""

import json
from datetime import datetime

import pandas as pd
import pytest

from dataforge.core.models import (
    BusinessDomain,
    BusinessInsight,
    DatasetProfile,
    KPI,
)
from dataforge.infrastructure.chart_engines import PlotlyChartEngine
from dataforge.infrastructure.report_renderers import Jinja2HTMLRenderer


# ============================================================================
# PLOTLY CHART ENGINE TESTS
# ============================================================================


class TestPlotlyChartEngine:
    """Tests for PlotlyChartEngine implementation."""

    @pytest.fixture
    def engine(self) -> PlotlyChartEngine:
        """Create a PlotlyChartEngine instance."""
        return PlotlyChartEngine()

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        """Create sample data for testing."""
        return pd.DataFrame({
            "category": ["A", "B", "C", "D"],
            "value": [10, 20, 15, 25],
            "x": [1, 2, 3, 4],
            "y": [5, 10, 7, 12],
        })

    @pytest.mark.asyncio
    async def test_create_bar_chart(self, engine: PlotlyChartEngine, sample_data: pd.DataFrame) -> None:
        """Test creating a bar chart."""
        html = await engine.create_bar_chart(
            sample_data,
            x_column="category",
            y_column="value",
            title="Test Bar Chart",
        )

        assert isinstance(html, str)
        assert "Test Bar Chart" in html
        assert "plotly" in html.lower()

    @pytest.mark.asyncio
    async def test_create_bar_chart_with_color(self, engine: PlotlyChartEngine, sample_data: pd.DataFrame) -> None:
        """Test creating a bar chart with color."""
        html = await engine.create_bar_chart(
            sample_data,
            x_column="category",
            y_column="value",
            title="Test Bar Chart",
            color="category",
        )

        assert isinstance(html, str)
        assert "Test Bar Chart" in html

    @pytest.mark.asyncio
    async def test_create_line_chart(self, engine: PlotlyChartEngine, sample_data: pd.DataFrame) -> None:
        """Test creating a line chart."""
        html = await engine.create_line_chart(
            sample_data,
            x_column="x",
            y_column="y",
            title="Test Line Chart",
        )

        assert isinstance(html, str)
        assert "Test Line Chart" in html

    @pytest.mark.asyncio
    async def test_create_scatter_plot(self, engine: PlotlyChartEngine, sample_data: pd.DataFrame) -> None:
        """Test creating a scatter plot."""
        html = await engine.create_scatter_plot(
            sample_data,
            x_column="x",
            y_column="y",
            title="Test Scatter Plot",
        )

        assert isinstance(html, str)
        assert "Test Scatter Plot" in html

    @pytest.mark.asyncio
    async def test_create_histogram(self, engine: PlotlyChartEngine, sample_data: pd.DataFrame) -> None:
        """Test creating a histogram."""
        html = await engine.create_histogram(
            sample_data,
            column="value",
            title="Test Histogram",
        )

        assert isinstance(html, str)
        assert "Test Histogram" in html

    @pytest.mark.asyncio
    async def test_create_box_plot(self, engine: PlotlyChartEngine, sample_data: pd.DataFrame) -> None:
        """Test creating a box plot."""
        html = await engine.create_box_plot(
            sample_data,
            column="value",
            title="Test Box Plot",
        )

        assert isinstance(html, str)
        assert "Test Box Plot" in html

    @pytest.mark.asyncio
    async def test_create_correlation_heatmap(self, engine: PlotlyChartEngine, sample_data: pd.DataFrame) -> None:
        """Test creating a correlation heatmap."""
        html = await engine.create_correlation_heatmap(
            sample_data,
            title="Test Correlation Heatmap",
        )

        assert isinstance(html, str)
        assert "Test Correlation Heatmap" in html


# ============================================================================
# JINJA2 HTML RENDERER TESTS
# ============================================================================


class TestJinja2HTMLRenderer:
    """Tests for Jinja2HTMLRenderer implementation."""

    @pytest.fixture
    def renderer(self) -> Jinja2HTMLRenderer:
        """Create a Jinja2HTMLRenderer instance."""
        return Jinja2HTMLRenderer()

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        """Create sample data for testing."""
        return pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "age": [25, 30, 35, 40, 45],
            "salary": [50000, 60000, 70000, 80000, 90000],
        })

    @pytest.fixture
    def sample_profile(self) -> DatasetProfile:
        """Create a sample dataset profile."""
        return DatasetProfile(
            row_count=5,
            column_count=4,
            memory_usage_mb=0.001,
            duplicate_rows=0,
            duplicate_percentage=0.0,
            missing_values_total=0,
            missing_percentage=0.0,
            numeric_columns=["id", "age", "salary"],
            categorical_columns=["name"],
            temporal_columns=[],
            text_columns=[],
            boolean_columns=[],
            quality_score=1.0,
        )

    @pytest.fixture
    def sample_insights(self) -> list[BusinessInsight]:
        """Create sample business insights."""
        return [
            BusinessInsight(
                category="performance",
                title="Salary increases with age",
                summary="There is a positive correlation between age and salary",
                impact="high",
                confidence=0.9,
                action="Consider age-based compensation adjustments",
                data_sources=["age", "salary"],
            ),
            BusinessInsight(
                category="diversity",
                title="Balanced gender distribution",
                summary="The dataset has a balanced representation",
                impact="medium",
                confidence=0.8,
                data_sources=["name"],
            ),
        ]

    @pytest.fixture
    def sample_kpis(self) -> list[KPI]:
        """Create sample KPIs."""
        return [
            KPI(
                name="Average Salary",
                description="Average salary across all employees",
                formula="sum(salary) / count(salary)",
                value=70000,
                unit="USD",
                trend="increasing",
                benchmark=65000,
                is_on_track=True,
                domain=BusinessDomain.HR,
                confidence=0.95,
            ),
            KPI(
                name="Average Age",
                description="Average age of employees",
                formula="sum(age) / count(age)",
                value=35,
                unit="years",
                trend="stable",
                benchmark=35,
                is_on_track=True,
                domain=BusinessDomain.HR,
                confidence=0.95,
            ),
        ]

    @pytest.mark.asyncio
    async def test_render_html_basic(
        self,
        renderer: Jinja2HTMLRenderer,
        sample_data: pd.DataFrame,
        sample_profile: DatasetProfile,
        sample_insights: list[BusinessInsight],
        sample_kpis: list[KPI],
    ) -> None:
        """Test basic HTML rendering."""
        html = await renderer.render_html(
            data=sample_data,
            profile=sample_profile,
            insights=sample_insights,
            kpis=sample_kpis,
            visualizations={},
        )

        assert isinstance(html, str)
        assert "DataForge AI Analysis Report" in html
        assert "5" in html  # row count
        assert "Average Salary" in html
        assert "Salary increases with age" in html

    @pytest.mark.asyncio
    async def test_render_html_with_visualizations(
        self,
        renderer: Jinja2HTMLRenderer,
        sample_data: pd.DataFrame,
        sample_profile: DatasetProfile,
        sample_insights: list[BusinessInsight],
        sample_kpis: list[KPI],
    ) -> None:
        """Test HTML rendering with visualizations."""
        visualizations = {
            "test_chart": "<div>Test Chart HTML</div>",
        }

        html = await renderer.render_html(
            data=sample_data,
            profile=sample_profile,
            insights=sample_insights,
            kpis=sample_kpis,
            visualizations=visualizations,
        )

        assert isinstance(html, str)
        assert "Test Chart HTML" in html

    @pytest.mark.asyncio
    async def test_render_html_with_recommendations(
        self,
        renderer: Jinja2HTMLRenderer,
        sample_data: pd.DataFrame,
        sample_profile: DatasetProfile,
        sample_insights: list[BusinessInsight],
        sample_kpis: list[KPI],
    ) -> None:
        """Test HTML rendering with recommendations."""
        from dataforge.core.models import Recommendation

        recommendations = [
            Recommendation(
                category="data_quality",
                title="Improve data completeness",
                description="Address missing values in critical columns",
                priority="high",
                impact="high",
                effort="medium",
                related_insights=["insight_1"],
                data_columns=["age", "salary"],
            ),
        ]

        html = await renderer.render_html(
            data=sample_data,
            profile=sample_profile,
            insights=sample_insights,
            kpis=sample_kpis,
            visualizations={},
            recommendations=recommendations,
        )

        assert isinstance(html, str)
        assert "Improve data completeness" in html

    @pytest.mark.asyncio
    async def test_render_json(
        self,
        renderer: Jinja2HTMLRenderer,
        sample_data: pd.DataFrame,
        sample_profile: DatasetProfile,
        sample_insights: list[BusinessInsight],
        sample_kpis: list[KPI],
    ) -> None:
        """Test JSON rendering."""
        json_str = await renderer.render_json(
            data=sample_data,
            profile=sample_profile,
            insights=sample_insights,
            kpis=sample_kpis,
        )

        assert isinstance(json_str, str)
        
        # Parse JSON to verify structure
        report = json.loads(json_str)
        assert "profile" in report
        assert "insights" in report
        assert "kpis" in report
        assert "data_sample" in report
        assert "data_row_count" in report

    @pytest.mark.asyncio
    async def test_render_json_with_validation_report(
        self,
        renderer: Jinja2HTMLRenderer,
        sample_data: pd.DataFrame,
        sample_profile: DatasetProfile,
        sample_insights: list[BusinessInsight],
        sample_kpis: list[KPI],
    ) -> None:
        """Test JSON rendering with validation report."""
        from dataforge.core.models import ValidationIssue, ValidationReport

        validation_report = ValidationReport(
            is_valid=True,
            total_issues=0,
            error_count=0,
            warning_count=0,
            info_count=0,
            issues=[],
            columns_affected=[],
            recommendations=[],
        )

        json_str = await renderer.render_json(
            data=sample_data,
            profile=sample_profile,
            insights=sample_insights,
            kpis=sample_kpis,
            validation_report=validation_report,
        )

        assert isinstance(json_str, str)
        
        report = json.loads(json_str)
        assert "validation_report" in report
        assert report["validation_report"]["is_valid"] is True

    @pytest.mark.asyncio
    async def test_render_pdf_not_implemented(
        self,
        renderer: Jinja2HTMLRenderer,
    ) -> None:
        """Test PDF rendering raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await renderer.render_pdf("<html></html>", "output.pdf")

    def test_get_supported_formats(
        self,
        renderer: Jinja2HTMLRenderer,
    ) -> None:
        """Test getting supported formats."""
        formats = renderer.get_supported_formats()

        assert isinstance(formats, list)
        assert "html" in formats
        assert "json" in formats
        assert "pdf" not in formats  # PDF not yet implemented