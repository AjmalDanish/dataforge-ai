"""Unit tests for KPIDiscoveryAgent."""

import pandas as pd
import pytest

from dataforge.agents.base import AgentDecision
from dataforge.agents.kpi import KPIDiscoveryAgent
from dataforge.core.models import ExecutionPhase, FailurePolicy
from dataforge.core.state import GraphState


@pytest.fixture
def agent():
    return KPIDiscoveryAgent()


@pytest.fixture
def retail_df():
    return pd.DataFrame(
        {
            "product": ["A", "B", "C", "D", "E"],
            "revenue": [100.0, 200.0, 300.0, 400.0, 500.0],
            "quantity": [1, 2, 3, 4, 5],
            "order_date": pd.to_datetime(
                ["2021-01-01", "2021-02-01", "2021-03-01", "2021-04-01", "2021-05-01"]
            ),
        }
    )


@pytest.fixture
def hr_df():
    return pd.DataFrame(
        {
            "employee": ["A", "B", "C", "D"],
            "salary": [50000.0, 60000.0, 70000.0, 80000.0],
            "department": ["Eng", "Eng", "HR", "HR"],
        }
    )


def _state(df, domain="retail"):
    return GraphState(
        input_dataset_path="/test/data.csv",
        current_phase=ExecutionPhase.DEEP_ANALYSIS,
        data={"cleaned_data": df, "business_domain": domain},
    )


class TestKPIContract:
    def test_phase(self, agent):
        assert agent.phase == ExecutionPhase.DEEP_ANALYSIS

    def test_inputs_outputs(self, agent):
        assert "cleaned_data" in agent.required_inputs
        assert "discovered_kpis" in agent.produced_outputs

    def test_failure_policy(self, agent):
        assert agent.failure_policy == FailurePolicy.SKIP

    def test_timeout(self, agent):
        assert agent.timeout_seconds == 60


class TestKPIExecute:
    @pytest.mark.asyncio
    async def test_retail_kpis(self, agent, retail_df):
        result = await agent.execute(_state(retail_df, "retail"))
        assert result.decision == AgentDecision.CONTINUE
        kpis = result.data_updates["discovered_kpis"]
        names = {k["name"] for k in kpis}
        # Revenue/orders come from the semantic model (dataforge.analytics.dashboard).
        assert {"Revenue", "Units sold"} <= names
        assert "Avg order value" not in names  # no order key -> no AOV
        rev = next(k for k in kpis if k["name"] == "Revenue")
        assert rev["value"] == pytest.approx(1500.0)
        assert rev["formula"] == "sum(revenue)"
        assert rev["trend"] in ("increasing", "decreasing", "stable")

    @pytest.mark.asyncio
    async def test_hr_kpis(self, agent, hr_df):
        result = await agent.execute(_state(hr_df, "hr"))
        names = {k["name"] for k in result.data_updates["discovered_kpis"]}
        assert "Headcount" in names
        assert "Average Salary" in names

    @pytest.mark.asyncio
    async def test_general_fallback(self, agent, hr_df):
        result = await agent.execute(_state(hr_df, "unknown_domain"))
        assert result.decision == AgentDecision.CONTINUE
        assert len(result.data_updates["discovered_kpis"]) >= 1

    @pytest.mark.asyncio
    async def test_missing_data_skips(self, agent):
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DEEP_ANALYSIS,
            data={},
        )
        result = await agent.execute(state)
        assert result.decision == AgentDecision.SKIP
        assert result.data_updates["discovered_kpis"] == []

    @pytest.mark.asyncio
    async def test_quality_score_range(self, agent, retail_df):
        result = await agent.execute(_state(retail_df, "retail"))
        assert 0.0 <= result.quality_score <= 1.0


class TestKPIColumnSelection:
    """KPIs are only computed from columns that actually match."""

    @pytest.mark.asyncio
    async def test_no_fallback_to_unrelated_columns(self):
        frame = pd.DataFrame({"id": range(1, 11), "price": [10.0] * 10, "sold_quantity": [2] * 10})
        state = GraphState(input_dataset_path="x.csv").set("cleaned_data", frame).set("business_domain", "retail")
        kpis = {k["name"]: k for k in (await KPIDiscoveryAgent().execute(state)).data_updates["discovered_kpis"]}

        # price x quantity is revenue; the index-like "id" is never used.
        assert kpis["Revenue"]["value"] == 200.0
        assert kpis["Revenue"]["formula"] == "sum(price * sold_quantity)"
        assert kpis["Units sold"]["value"] == 20.0
        assert kpis["Average Price"]["value"] == 10.0
        assert kpis["Average Price"]["formula"] == "mean(price)"

    @pytest.mark.asyncio
    async def test_identifier_columns_never_used(self):
        frame = pd.DataFrame({"employee_id": range(100, 110), "dept": ["a", "b"] * 5})
        state = GraphState(input_dataset_path="x.csv").set("cleaned_data", frame).set("business_domain", "hr")
        kpis = {k["name"] for k in (await KPIDiscoveryAgent().execute(state)).data_updates["discovered_kpis"]}
        assert "Average Salary" not in kpis
        assert "Salary Range" not in kpis


@pytest.mark.asyncio
async def test_exported_index_columns_never_feed_kpis():
    # "Unnamed: 0" contains the keyword "name" — it must not become "Unique Products".
    frame = pd.DataFrame({"Unnamed: 0": range(1, 13), "product_name": ["a", "b", "c"] * 4, "price": [5.0] * 12})
    state = GraphState(input_dataset_path="x.csv").set("cleaned_data", frame).set("business_domain", "retail")
    kpis = {k["name"]: k for k in (await KPIDiscoveryAgent().execute(state)).data_updates["discovered_kpis"]}
    assert kpis["Unique Products"]["value"] == 3
    assert "Unnamed" not in kpis["Unique Products"]["formula"]
