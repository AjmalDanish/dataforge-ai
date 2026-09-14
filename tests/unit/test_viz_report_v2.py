"""Unit tests for VisualizationAgent v2 dashboard and executive reporting."""

import json

import pandas as pd
import pytest

from dataforge.agents.base import AgentDecision
from dataforge.agents.reporting import ReportingAgent
from dataforge.agents.visualization import VisualizationAgent
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase
from dataforge.core.state import GraphState


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "order_date": pd.to_datetime(
                ["2021-01-01", "2021-02-01", "2021-03-01", "2021-04-01", "2021-05-01"]
            ),
            "revenue": [100.0, 200.0, 300.0, 400.0, 500.0],
            "quantity": [1.0, 2.0, 3.0, 4.0, 5.0],
            "region": ["E", "W", "E", "W", "E"],
        }
    )


@pytest.fixture
def kpis():
    return [
        {
            "name": "Total Revenue",
            "value": 1500.0,
            "trend": "increasing",
            "formula": "sum(revenue)",
            "confidence": 0.85,
        }
    ]


@pytest.fixture
def state(df, kpis):
    return GraphState(
        input_dataset_path="/test/data.csv",
        current_phase=ExecutionPhase.OUTPUT,
        data={
            "cleaned_data": df,
            "profile": {
                "numeric_columns": ["revenue", "quantity"],
                "categorical_columns": ["region"],
                "overall_missing_ratio": 0.0,
            },
            "statistics": {"correlations": {"significant": []}, "outliers": {}},
            "discovered_kpis": kpis,
            "business_domain": "retail",
            "business_insights": [
                {
                    "category": "trends",
                    "title": "Revenue is climbing",
                    "summary": "Revenue trends upward.",
                    "severity": "medium",
                    "business_action": "Keep going.",
                    "confidence": 0.8,
                }
            ],
        },
    )


class TestVisualizationDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_produced(self, state, tmp_path):
        logger = StructuredLogger("test-viz", tmp_path)
        agent = VisualizationAgent(
            logger=logger, output_dir=str(tmp_path / "visualizations")
        )
        result = await agent.execute(state)
        assert result.decision == AgentDecision.CONTINUE
        dashboard = result.data_updates["dashboard"]
        assert dashboard["kpi_cards"]
        assert dashboard["trend_chart"] is not None
        assert len(dashboard["layout"]) >= 2

    @pytest.mark.asyncio
    async def test_kpi_card_files_exist(self, state, tmp_path):
        logger = StructuredLogger("test-viz", tmp_path)
        agent = VisualizationAgent(
            logger=logger, output_dir=str(tmp_path / "visualizations")
        )
        result = await agent.execute(state)
        for card in result.data_updates["visualizations"]:
            if card["type"] == "kpi_card":
                assert (tmp_path / "visualizations" / card["file_name"]).exists()

    @pytest.mark.asyncio
    async def test_missing_data_skips(self, tmp_path):
        logger = StructuredLogger("test-viz", tmp_path)
        agent = VisualizationAgent(
            logger=logger, output_dir=str(tmp_path / "visualizations")
        )
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.OUTPUT,
            data={},
        )
        result = await agent.execute(state)
        assert result.decision == AgentDecision.SKIP


class TestExecutiveReport:
    @pytest.mark.asyncio
    async def test_report_files_and_keys(self, state, tmp_path):
        logger = StructuredLogger("test-report", tmp_path)
        agent = ReportingAgent(logger=logger, output_dir=str(tmp_path / "report"))
        result = await agent.execute(state)
        assert result.decision == AgentDecision.CONTINUE
        assert (tmp_path / "report" / "report.html").exists()
        assert (tmp_path / "report" / "report.json").exists()
        assert result.data_updates["report_html"].endswith("report.html")
        assert result.data_updates["report_json"].endswith("report.json")

    @pytest.mark.asyncio
    async def test_executive_summary_in_html(self, state, tmp_path):
        logger = StructuredLogger("test-report", tmp_path)
        agent = ReportingAgent(logger=logger, output_dir=str(tmp_path / "report"))
        await agent.execute(state)
        html = (tmp_path / "report" / "report.html").read_text(encoding="utf-8")
        assert "Executive Summary" in html
        assert "Total Revenue" in html
        assert "Revenue is climbing" in html

    @pytest.mark.asyncio
    async def test_json_has_v2_sections(self, state, tmp_path):
        logger = StructuredLogger("test-report", tmp_path)
        agent = ReportingAgent(logger=logger, output_dir=str(tmp_path / "report"))
        await agent.execute(state)
        report = json.loads((tmp_path / "report" / "report.json").read_text())
        assert report["executive_summary"]["headline"]
        assert len(report["kpis"]) == 1
        assert len(report["business_insights"]) == 1
