"""Reporting Agent - Generates comprehensive analysis report."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


class ReportingAgent(Agent):
    """Generates a comprehensive analysis report.

    Creates a detailed report summarizing:
    - Data profile and characteristics
    - Statistical analysis results
    - Key insights and findings
    - Visualizations generated
    - Recommendations for further analysis

    Saves report as both HTML and JSON formats.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
        output_dir: str = "output",
    ):
        """Initialize the Reporting Agent.

        Args:
            llm_provider: LLM provider instance.
            logger: Structured logger instance.
            output_dir: Directory to save report files.
        """
        super().__init__(llm_provider, logger)
        self.name = "ReportingAgent"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, state: GraphState) -> AgentResult:
        """Generate comprehensive analysis report.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with report information.
        """
        self.logger.info(
            "Starting report generation",
            agent=self.name,
            output_dir=str(self.output_dir),
        )

        try:
            # Gather all analysis results
            raw_data = state.get("raw_data")
            profile = state.get("profile", {})
            statistics = state.get("statistics", {})
            visualizations = state.get("visualizations", [])
            insights = state.get("insights", [])
            logs = state.get("logs", [])

            # Validate we have something to report
            if profile is None and statistics is None:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="No analysis results available for reporting",
                )

            # Generate report content
            report_metadata = {
                "generated_at": datetime.now().isoformat(),
                "dataset_path": state.get("input_dataset_path", "unknown"),
                "total_rows": len(raw_data) if raw_data is not None else 0,
                "total_columns": len(raw_data.columns) if raw_data is not None else 0,
                "agents_completed": state.get("steps_completed", []),
            }

            # Generate HTML report
            html_report = self._generate_html_report(
                report_metadata, profile, statistics, visualizations, insights, logs
            )

            # Generate JSON report
            json_report = self._generate_json_report(
                report_metadata, profile, statistics, visualizations, insights, logs
            )

            # Save reports
            html_path = self.output_dir / "report.html"
            json_path = self.output_dir / "report.json"

            html_path.write_text(html_report, encoding="utf-8")
            json_path.write_text(json_report, encoding="utf-8")

            self.logger.info(
                "Report generation complete",
                agent=self.name,
                html_path=str(html_path),
                json_path=str(json_path),
                insights_count=len(insights),
                visualizations_count=len(visualizations),
            )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Generated comprehensive report: {len(insights)} insights, "
                f"{len(visualizations)} visualizations documented",
                data_updates={
                    "report": {
                        "html_path": str(html_path),
                        "json_path": str(json_path),
                        "insights_count": len(insights),
                        "visualizations_count": len(visualizations),
                        "generated_at": datetime.now().isoformat(),
                    }
                },
                metadata={
                    "html_path": str(html_path),
                    "json_path": str(json_path),
                    "insights_count": len(insights),
                    "visualizations_count": len(visualizations),
                },
            )

        except Exception as e:
            self.logger.error(
                "Report generation failed",
                agent=self.name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Report generation failed: {str(e)}",
                metadata={"error_type": type(e).__name__, "error_message": str(e)},
            )

    def _generate_html_report(
        self,
        metadata: dict[str, Any],
        profile: dict[str, Any],
        statistics: dict[str, Any],
        visualizations: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        logs: list[dict[str, Any]],
    ) -> str:
        """Generate HTML report.

        Args:
            metadata: Report metadata.
            profile: Data profile.
            statistics: Statistical analysis results.
            visualizations: List of visualizations.
            insights: List of insights.
            logs: Execution logs.

        Returns:
            HTML report as string.
        """
        html = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            "    <title>DataForge AI Analysis Report</title>",
            "    <style>",
            "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; color: #333; }",
            "        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }",
            "        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }",
            "        h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }",
            "        h3 { color: #7f8c8d; margin-top: 20px; }",
            "        .metadata { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }",
            "        .metadata-item { display: inline-block; margin-right: 20px; }",
            "        .metadata-label { font-weight: bold; color: #2c3e50; }",
            "        .section { margin: 30px 0; }",
            "        .insight { padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #bdc3c7; }",
            "        .insight.info { background: #d4edda; border-color: #28a745; }",
            "        .insight.warning { background: #fff3cd; border-color: #ffc107; }",
            "        .insight.error { background: #f8d7da; border-color: #dc3545; }",
            "        .insight-type { font-weight: bold; text-transform: uppercase; font-size: 12px; color: #7f8c8d; }",
            "        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }",
            "        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 5px; border: 1px solid #dee2e6; }",
            "        .stat-value { font-size: 24px; font-weight: bold; color: #3498db; }",
            "        .stat-label { color: #7f8c8d; font-size: 14px; }",
            "        .viz-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin: 20px 0; }",
            "        .viz-item { background: #f8f9fa; padding: 15px; border-radius: 5px; border: 1px solid #dee2e6; }",
            "        .viz-link { color: #3498db; text-decoration: none; }",
            "        .viz-link:hover { text-decoration: underline; }",
            "        .table { width: 100%; border-collapse: collapse; margin: 20px 0; }",
            "        .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }",
            "        .table th { background: #3498db; color: white; }",
            "        .table tr:hover { background: #f8f9fa; }",
            "        .tag { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-right: 5px; }",
            "        .tag.info { background: #d1ecf1; color: #0c5460; }",
            "        .tag.warning { background: #fff3cd; color: #856404; }",
            "        .tag.success { background: #d4edda; color: #155724; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <div class='container'>",
        ]

        # Header
        html.extend(
            [
                "        <h1>📊 DataForge AI Analysis Report</h1>",
                "",
                "        <div class='metadata'>",
            ]
        )

        for key, value in metadata.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            html.append(
                f"            <div class='metadata-item'><span class='metadata-label'>{key}:</span> {value}</div>"
            )

        html.extend(
            [
                "        </div>",
                "",
            ]
        )

        # Data Profile Section
        if profile:
            html.extend(
                [
                    "        <h2>📁 Data Profile</h2>",
                    "        <div class='stat-grid'>",
                    f"            <div class='stat-card'><div class='stat-value'>{profile.get('n_rows', 0):,}</div><div class='stat-label'>Rows</div></div>",
                    f"            <div class='stat-card'><div class='stat-value'>{profile.get('n_columns', 0):,}</div><div class='stat-label'>Columns</div></div>",
                    f"            <div class='stat-card'><div class='stat-value'>{profile.get('numeric_column_count', 0):,}</div><div class='stat-label'>Numeric Columns</div></div>",
                    f"            <div class='stat-card'><div class='stat-value'>{profile.get('categorical_column_count', 0):,}</div><div class='stat-label'>Categorical Columns</div></div>",
                    f"            <div class='stat-card'><div class='stat-value'>{profile.get('overall_missing_ratio', 0) * 100:.1f}%</div><div class='stat-label'>Missing Values</div></div>",
                    "        </div>",
                    "",
                ]
            )

            # Column details
            columns_info = profile.get("columns", {})
            if columns_info:
                html.extend(
                    [
                        "        <h3>Column Details</h3>",
                        "        <table class='table'>",
                        "            <thead><tr><th>Column</th><th>Type</th><th>Unique</th><th>Missing</th><th>Missing %</th></tr></thead>",
                        "            <tbody>",
                    ]
                )

                for col_name, col_info in columns_info.items():
                    missing_pct = (col_info.get("n_missing", 0) / profile.get("n_rows", 1)) * 100
                    html.append(
                        f"                <tr><td>{col_name}</td><td>{col_info.get('type', 'unknown')}</td>"
                        f"<td>{col_info.get('n_unique', 0):,}</td><td>{col_info.get('n_missing', 0):,}</td>"
                        f"<td>{missing_pct:.1f}%</td></tr>"
                    )

                html.extend(
                    [
                        "            </tbody>",
                        "        </table>",
                        "",
                    ]
                )

        # Statistical Analysis Section
        if statistics:
            html.extend(
                [
                    "        <h2>📈 Statistical Analysis</h2>",
                    "",
                ]
            )

            # Descriptive statistics
            desc_stats = statistics.get("descriptive_stats", {})
            if desc_stats:
                html.extend(
                    [
                        "        <h3>Descriptive Statistics</h3>",
                        "        <table class='table'>",
                        "            <thead><tr><th>Column</th><th>Mean</th><th>Median</th><th>Std</th><th>Min</th><th>Max</th></tr></thead>",
                        "            <tbody>",
                    ]
                )

                for col_name, stats in desc_stats.items():
                    html.append(
                        f"                <tr><td>{col_name}</td><td>{stats.get('mean', 0):.2f}</td>"
                        f"<td>{stats.get('median', 0):.2f}</td><td>{stats.get('std', 0):.2f}</td>"
                        f"<td>{stats.get('min', 0):.2f}</td><td>{stats.get('max', 0):.2f}</td></tr>"
                    )

                html.extend(
                    [
                        "            </tbody>",
                        "        </table>",
                        "",
                    ]
                )

            # Correlations
            correlations = statistics.get("correlations", {}).get("significant", [])
            if correlations:
                html.extend(
                    [
                        "        <h3>Significant Correlations</h3>",
                        "        <table class='table'>",
                        "            <thead><tr><th>Columns</th><th>Correlation</th><th>Strength</th><th>Direction</th></tr></thead>",
                        "            <tbody>",
                    ]
                )

                for corr in correlations:
                    cols_str = " ↔ ".join(corr.get("columns", []))
                    html.append(
                        f"                <tr><td>{cols_str}</td><td>{corr.get('correlation', 0):.3f}</td>"
                        f"<td><span class='tag info'>{corr.get('strength', 'unknown')}</span></td>"
                        f"<td><span class='tag {corr['direction'] == 'positive' and 'success' or 'warning'}'>{corr.get('direction', 'unknown')}</span></td></tr>"
                    )

                html.extend(
                    [
                        "            </tbody>",
                        "        </table>",
                        "",
                    ]
                )

            # Outliers
            outliers = statistics.get("outliers", {})
            if outliers:
                total_outliers = sum(len(indices) for indices in outliers.values())
                html.extend(
                    [
                        "        <h3>Outliers Detected</h3>",
                        f"        <p>Total outliers detected: <strong>{total_outliers:,}</strong> across {len(outliers)} columns</p>",
                        "        <ul>",
                    ]
                )

                for col_name, indices in outliers.items():
                    html.append(f"            <li>{col_name}: {len(indices)} outliers</li>")

                html.extend(
                    [
                        "        </ul>",
                        "",
                    ]
                )

        # Visualizations Section
        if visualizations:
            html.extend(
                [
                    "        <h2>📊 Visualizations</h2>",
                    "        <div class='viz-list'>",
                ]
            )

            for viz in visualizations:
                viz_type = viz.get("type", "unknown")
                title = viz.get("title", "Untitled")
                file_name = viz.get("file_name", "")
                rel_path = f"visualizations/{file_name}"

                html.append(f"            <div class='viz-item'>")
                html.append(f"                <strong>{title}</strong><br>")
                html.append(f"                <span class='tag info'>{viz_type}</span><br>")
                html.append(
                    f"                <a href='{rel_path}' class='viz-link' target='_blank'>View Visualization</a>"
                )
                html.append(f"            </div>")

            html.extend(
                [
                    "        </div>",
                    "",
                ]
            )

        # Insights Section
        if insights:
            html.extend(
                [
                    "        <h2>💡 Key Insights</h2>",
                    "",
                ]
            )

            # Group insights by type
            insights_by_type: dict[str, list[dict[str, Any]]] = {}
            for insight in insights:
                insight_type = insight.get("type", "unknown")
                if insight_type not in insights_by_type:
                    insights_by_type[insight_type] = []
                insights_by_type[insight_type].append(insight)

            for insight_type, type_insights in insights_by_type.items():
                html.append(f"        <h3>{insight_type.replace('_', ' ').title()}</h3>")

                for insight in type_insights:
                    severity = insight.get("severity", "info")
                    message = insight.get("message", "")
                    html.append(f"        <div class='insight {severity}'>")
                    html.append(f"            <div class='insight-type'>{insight_type}</div>")
                    html.append(f"            <div>{message}</div>")
                    html.append(f"        </div>")

            html.extend(
                [
                    "        <p><strong>Total Insights:</strong> {len(insights)}</p>".format(
                        len(insights=len(insights))
                    ),
                    "",
                ]
            )

        # Execution Log Section
        if logs:
            html.extend(
                [
                    "        <h2>📋 Execution Log</h2>",
                    "        <table class='table'>",
                    "            <thead><tr><th>Time</th><th>Level</th><th>Agent</th><th>Message</th></tr></thead>",
                    "            <tbody>",
                ]
            )

            for log in logs[-50:]:  # Show last 50 logs
                timestamp = log.get("timestamp", "")
                level = log.get("level", "INFO")
                agent = log.get("agent", "")
                message = log.get("message", "")

                tag_class = (
                    "info" if level == "INFO" else "warning" if level == "WARNING" else "error"
                )

                html.append(
                    f"                <tr><td>{timestamp.split('T')[1][:8] if 'T' in timestamp else timestamp}</td>"
                    f"<td><span class='tag {tag_class}'>{level}</span></td><td>{agent}</td><td>{message}</td></tr>"
                )

            html.extend(
                [
                    "            </tbody>",
                    "        </table>",
                    "",
                ]
            )

        # Footer
        html.extend(
            [
                "        <hr>",
                "        <p style='color: #7f8c8d; text-align: center;'>",
                f"            Generated by DataForge AI on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}",
                "        </p>",
                "    </div>",
                "</body>",
                "</html>",
            ]
        )

        return "\n".join(html)

    def _generate_json_report(
        self,
        metadata: dict[str, Any],
        profile: dict[str, Any],
        statistics: dict[str, Any],
        visualizations: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        logs: list[dict[str, Any]],
    ) -> str:
        """Generate JSON report.

        Args:
            metadata: Report metadata.
            profile: Data profile.
            statistics: Statistical analysis results.
            visualizations: List of visualizations.
            insights: List of insights.
            logs: Execution logs.

        Returns:
            JSON report as string.
        """
        report = {
            "metadata": metadata,
            "profile": profile,
            "statistics": statistics,
            "visualizations": visualizations,
            "insights": insights,
            "execution_logs": logs[-100:],  # Limit to last 100 logs
            "summary": {
                "total_insights": len(insights),
                "total_visualizations": len(visualizations),
                "numeric_columns": profile.get("numeric_column_count", 0),
                "categorical_columns": profile.get("categorical_column_count", 0),
                "significant_correlations": len(
                    statistics.get("correlations", {}).get("significant", [])
                ),
                "total_outliers": sum(
                    len(indices) for indices in statistics.get("outliers", {}).values()
                ),
            },
        }

        return json.dumps(report, indent=2, default=str)
