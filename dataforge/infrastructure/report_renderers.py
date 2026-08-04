"""Jinja2 implementation of the ReportRenderer interface."""

from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, Template

from dataforge.core.models import (
    BusinessInsight,
    DatasetProfile,
    KPI,
    ValidationReport,
)
from dataforge.infrastructure.interfaces import ReportRenderer


class Jinja2HTMLRenderer(ReportRenderer):
    """Jinja2 implementation of the ReportRenderer interface.

    Generates HTML reports using Jinja2 templates.
    """

    def __init__(self, templates_dir: str | Path | None = None):
        """Initialize the Jinja2 HTML renderer.

        Args:
            templates_dir: Directory containing Jinja2 templates.
                          If None, uses the default templates directory.
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates"

        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True,
        )

    async def render_html(
        self,
        data: pd.DataFrame,
        profile: DatasetProfile,
        insights: list[BusinessInsight],
        kpis: list[KPI],
        visualizations: dict[str, str],
        **kwargs: Any,
    ) -> str:
        """Render an HTML report.

        Args:
            data: Input data (pandas DataFrame).
            profile: Dataset profile information.
            insights: List of business insights.
            kpis: List of KPIs.
            visualizations: Dictionary mapping visualization names to HTML strings.
            **kwargs: Additional rendering options (validation_report, recommendations, etc.).

        Returns:
            HTML string containing the complete report.
        """
        validation_report = kwargs.get("validation_report")
        recommendations = kwargs.get("recommendations", [])

        # Use simple HTML generation for now
        return self._render_simple_html(
            data, profile, insights, kpis, visualizations, validation_report, recommendations
        )

    def _render_simple_html(
        self,
        data: pd.DataFrame,
        profile: DatasetProfile,
        insights: list[BusinessInsight],
        kpis: list[KPI],
        visualizations: dict[str, str],
        validation_report: ValidationReport | None,
        recommendations: list[Any],
    ) -> str:
        """Render a simple HTML report without templates."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "<title>DataForge AI Analysis Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }",
            ".section { margin-bottom: 30px; }",
            ".card { border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 5px; }",
            ".badge { padding: 4px 8px; border-radius: 3px; font-size: 12px; }",
            ".badge.high { background: #dc3545; color: white; }",
            ".badge.medium { background: #ffc107; color: #333; }",
            ".badge.low { background: #28a745; color: white; }",
            "h1 { color: #667eea; }",
            "h2 { color: #764ba2; border-bottom: 2px solid #667eea; padding-bottom: 10px; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>📊 DataForge AI Analysis Report</h1>",
        ]

        # Dataset Summary
        if profile:
            html_parts.extend([
                "<div class='section'>",
                "<h2>📋 Dataset Summary</h2>",
                f"<p><strong>Rows:</strong> {profile.row_count}</p>",
                f"<p><strong>Columns:</strong> {profile.column_count}</p>",
                f"<p><strong>Quality Score:</strong> {profile.quality_score:.2f}</p>",
                "</div>",
            ])

        # KPIs
        if kpis:
            html_parts.append("<div class='section'><h2>📈 Key Performance Indicators</h2>")
            for kpi in kpis:
                html_parts.extend([
                    "<div class='card'>",
                    f"<h3>{kpi.name}</h3>",
                    f"<p><strong>Description:</strong> {kpi.description}</p>",
                    f"<p><strong>Value:</strong> {kpi.value} {kpi.unit if kpi.unit else ''}</p>",
                    f"<p><strong>Trend:</strong> {kpi.trend}</p>",
                    f"<p><strong>Confidence:</strong> {kpi.confidence * 100:.1f}%</p>",
                    "</div>",
                ])
            html_parts.append("</div>")

        # Insights
        if insights:
            html_parts.append("<div class='section'><h2>💡 Business Insights</h2>")
            for insight in insights:
                badge_class = insight.impact
                html_parts.extend([
                    "<div class='card'>",
                    f"<h3>{insight.title}</h3>",
                    f"<p><strong>Category:</strong> {insight.category}</p>",
                    f"<p><strong>Summary:</strong> {insight.summary}</p>",
                    f"<p><strong>Impact:</strong> <span class='badge {badge_class}'>{insight.impact}</span></p>",
                    f"<p><strong>Confidence:</strong> {insight.confidence * 100:.1f}%</p>",
                    "</div>",
                ])
            html_parts.append("</div>")

        # Visualizations
        if visualizations:
            html_parts.append("<div class='section'><h2>📊 Visualizations</h2>")
            for chart_name, chart_html in visualizations.items():
                html_parts.extend([
                    "<div class='card'>",
                    f"<h3>{chart_name.replace('_', ' ').title()}</h3>",
                    chart_html,
                    "</div>",
                ])
            html_parts.append("</div>")

        # Recommendations
        if recommendations:
            html_parts.append("<div class='section'><h2>🎯 Recommendations</h2>")
            for rec in recommendations:
                html_parts.extend([
                    "<div class='card'>",
                    f"<h3>{rec.title}</h3>",
                    f"<p><strong>Description:</strong> {rec.description}</p>",
                    f"<p><strong>Priority:</strong> {rec.priority}</p>",
                    f"<p><strong>Impact:</strong> {rec.impact}</p>",
                    "</div>",
                ])
            html_parts.append("</div>")

        html_parts.extend([
            "<footer><p>Generated by DataForge AI v2.0</p></footer>",
            "</body>",
            "</html>",
        ])

        return "\n".join(html_parts)

    async def render_pdf(
        self,
        html_content: str,
        output_path: str | Path,
        **kwargs: Any,
    ) -> Path:
        """Render an HTML report to PDF.

        Note: This is a placeholder implementation. PDF rendering requires
        additional dependencies like WeasyPrint or similar.

        Args:
            html_content: HTML content to convert.
            output_path: Path where the PDF should be saved.
            **kwargs: Additional PDF generation options.

        Returns:
            Path to the generated PDF file.

        Raises:
            NotImplementedError: PDF rendering not yet implemented.
        """
        # Placeholder: PDF rendering requires WeasyPrint or similar
        raise NotImplementedError(
            "PDF rendering not yet implemented. "
            "Install WeasyPrint and implement this method."
        )

    async def render_json(
        self,
        data: pd.DataFrame,
        profile: DatasetProfile,
        insights: list[BusinessInsight],
        kpis: list[KPI],
        validation_report: ValidationReport | None = None,
        **kwargs: Any,
    ) -> str:
        """Render a JSON report.

        Args:
            data: Input data (pandas DataFrame).
            profile: Dataset profile information.
            insights: List of business insights.
            kpis: List of KPIs.
            validation_report: Optional validation report.
            **kwargs: Additional rendering options.

        Returns:
            JSON string containing the complete report.
        """
        import json

        # Convert DataFrame to dict for JSON serialization
        data_dict = data.to_dict(orient="records") if data is not None else []

        # Prepare report structure
        report = {
            "profile": profile.model_dump() if profile else None,
            "insights": [insight.model_dump() for insight in insights],
            "kpis": [kpi.model_dump() for kpi in kpis],
            "validation_report": (
                validation_report.model_dump() if validation_report else None
            ),
            "data_sample": data_dict[:100],  # Limit to 100 rows for JSON
            "data_row_count": len(data_dict) if data_dict else 0,
        }

        return json.dumps(report, indent=2, default=str)

    def get_supported_formats(self) -> list[str]:
        """Get the list of supported output formats.

        Returns:
            A list of format identifiers (e.g., "html", "pdf", "json").
        """
        return ["html", "json"]  # PDF not yet implemented