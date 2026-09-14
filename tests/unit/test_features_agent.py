"""Unit tests for FeatureEngineeringAgent."""

import pandas as pd
import pytest

from dataforge.agents.base import AgentDecision
from dataforge.agents.features import FeatureEngineeringAgent
from dataforge.core.models import ExecutionPhase, FailurePolicy
from dataforge.core.state import GraphState


@pytest.fixture
def agent():
    return FeatureEngineeringAgent()


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "order_date": pd.to_datetime(
                ["2021-01-04", "2021-02-15", "2021-03-20", "2021-04-10", "2021-05-22"]
            ),
            "price": [10.0, 20.0, 30.0, 40.0, 100.0],
            "quantity": [1.0, 2.0, 3.0, 4.0, 5.0],
            "category": ["a", "b", "a", "b", "a"],
        }
    )


def _state(df):
    return GraphState(
        input_dataset_path="/test/data.csv",
        current_phase=ExecutionPhase.DEEP_ANALYSIS,
        data={"cleaned_data": df},
    )


class TestFeaturesContract:
    def test_phase(self, agent):
        assert agent.phase == ExecutionPhase.DEEP_ANALYSIS

    def test_inputs_outputs(self, agent):
        assert "cleaned_data" in agent.required_inputs
        assert "engineered_data" in agent.produced_outputs
        assert "new_features" in agent.produced_outputs

    def test_failure_policy(self, agent):
        assert agent.failure_policy == FailurePolicy.SKIP


class TestFeaturesExecute:
    @pytest.mark.asyncio
    async def test_temporal_extraction(self, agent, sample_df):
        result = await agent.execute(_state(sample_df))
        assert result.decision == AgentDecision.CONTINUE
        engineered = result.data_updates["engineered_data"]
        assert "order_date_month" in engineered.columns
        assert "order_date_year" in engineered.columns
        assert "order_date_is_weekend" in engineered.columns

    @pytest.mark.asyncio
    async def test_ratio_and_flag(self, agent, sample_df):
        result = await agent.execute(_state(sample_df))
        engineered = result.data_updates["engineered_data"]
        assert "price_per_quantity" in engineered.columns
        assert "is_high_price" in engineered.columns

    @pytest.mark.asyncio
    async def test_original_not_mutated(self, agent, sample_df):
        before = list(sample_df.columns)
        await agent.execute(_state(sample_df))
        assert list(sample_df.columns) == before

    @pytest.mark.asyncio
    async def test_feature_definitions(self, agent, sample_df):
        result = await agent.execute(_state(sample_df))
        for f in result.data_updates["new_features"]:
            assert {"name", "source_columns", "transformation"} <= set(f.keys())

    @pytest.mark.asyncio
    async def test_missing_data_skips(self, agent):
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DEEP_ANALYSIS,
            data={},
        )
        result = await agent.execute(state)
        assert result.decision == AgentDecision.SKIP
