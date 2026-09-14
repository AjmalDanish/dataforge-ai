"""Unit tests for InsightGenerationAgent."""

import pandas as pd
import pytest

from dataforge.agents.base import AgentDecision
from dataforge.agents.insights import InsightGenerationAgent
from dataforge.core.models import ExecutionPhase, FailurePolicy
from dataforge.core.state import GraphState


@pytest.fixture
def agent():
    return InsightGenerationAgent()


@pytest.fixture
def rich_state():
    df = pd.DataFrame(
        {
            "price": [10.0, 20.0, 30.0, 40.0, 200.0],
            "quantity": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )
    statistics = {
        "descriptive_stats": {
            "price": {"mean": 60.0, "median": 30.0},
            "quantity": {"mean": 3.0, "median": 3.0},
        },
        "correlations": {
            "significant": [
                {
                    "columns": ["price", "quantity"],
                    "correlation": 0.82,
                    "strength": "strong",
                    "direction": "positive",
                }
            ]
        },
        "outliers": {"price": [4]},
        "distribution_tests": {},
        "group_tests": {},
    }
    return GraphState(
        input_dataset_path="/test/data.csv",
        current_phase=ExecutionPhase.SYNTHESIS,
        data={
            "cleaned_data": df,
            "statistics": statistics,
            "profile": {"overall_missing_ratio": 0.0},
            "discovered_kpis": [
                {
                    "name": "Total Revenue",
                    "value": 1500.0,
                    "trend": "increasing",
                    "formula": "sum(revenue)",
                    "confidence": 0.85,
                }
            ],
            "business_domain": "retail",
        },
    )


class TestInsightsContract:
    def test_phase(self, agent):
        assert agent.phase == ExecutionPhase.SYNTHESIS

    def test_inputs_outputs(self, agent):
        assert "cleaned_data" in agent.required_inputs
        assert "business_insights" in agent.produced_outputs

    def test_failure_policy(self, agent):
        assert agent.failure_policy == FailurePolicy.SKIP

    def test_timeout(self, agent):
        assert agent.timeout_seconds == 45


class TestInsightsExecute:
    @pytest.mark.asyncio
    async def test_generates_all_categories(self, agent, rich_state):
        result = await agent.execute(rich_state)
        assert result.decision == AgentDecision.CONTINUE
        cats = {i["category"] for i in result.data_updates["business_insights"]}
        assert "correlations" in cats
        assert "anomalies" in cats
        assert "recommendations" in cats

    @pytest.mark.asyncio
    async def test_insight_schema(self, agent, rich_state):
        result = await agent.execute(rich_state)
        for insight in result.data_updates["business_insights"]:
            assert {"category", "title", "summary", "severity", "business_action",
                    "confidence", "rank"} <= set(insight.keys())
            assert 0.0 <= insight["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_ranked_and_capped(self, agent, rich_state):
        result = await agent.execute(rich_state)
        insights = result.data_updates["business_insights"]
        assert len(insights) <= agent.MAX_INSIGHTS
        ranks = [i["rank"] for i in insights]
        assert ranks == sorted(ranks)

    @pytest.mark.asyncio
    async def test_missing_data_skips(self, agent):
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.SYNTHESIS,
            data={},
        )
        result = await agent.execute(state)
        assert result.decision == AgentDecision.SKIP
        assert result.data_updates["business_insights"] == []

    @pytest.mark.asyncio
    async def test_quality_risk_detected(self, agent):
        df = pd.DataFrame({"a": [1.0, None, None, None, 5.0]})
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.SYNTHESIS,
            data={"cleaned_data": df, "profile": {"overall_missing_ratio": 0.4}},
        )
        result = await agent.execute(state)
        cats = {i["category"] for i in result.data_updates["business_insights"]}
        assert "risks" in cats
