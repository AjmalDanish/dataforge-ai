"""Tests for the planner, evaluator, ingestion and profiling agents."""

import pandas as pd
import pytest

from dataforge.agents.base import AgentDecision
from dataforge.agents.evaluator import EvaluatorAgent
from dataforge.agents.ingestion import DataIngestionAgent
from dataforge.agents.planner import PlannerAgent
from dataforge.agents.profiling import DataProfilingAgent
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


@pytest.fixture
def mock_logger(tmp_path):
    """Create a logger writing into the test's temp dir."""
    return StructuredLogger("test-exec-id", tmp_path)


@pytest.fixture
def df():
    return pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


def _done(state: GraphState, *agents: str, success: bool = True) -> GraphState:
    """Record agents as completed (planner bookkeeping included)."""
    for agent in agents:
        state = state.add_agent_result("PlannerAgent", {"success": True})
        state = state.add_agent_result(agent, {"success": success})
    return state


class TestPlannerAgent:
    """Routing rules of the v2 planner."""

    @pytest.fixture
    def planner(self, mock_logger):
        return PlannerAgent(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_initial_state(self, planner):
        result = await planner.execute(GraphState(input_dataset_path="test.csv"))
        assert result.decision == AgentDecision.CONTINUE
        assert result.next_agent_suggestion == "DataValidationAgent"
        assert result.metadata["reason"] == "initial_state"

    @pytest.mark.asyncio
    async def test_follows_pipeline_order(self, planner, df):
        state = GraphState(input_dataset_path="test.csv").set("raw_data", df)
        state = _done(state, "DataValidationAgent")
        result = await planner.execute(state)
        assert result.next_agent_suggestion == "DataCleaningAgent"

        state = _done(state.set("cleaned_data", df), "DataCleaningAgent")
        result = await planner.execute(state)
        assert result.next_agent_suggestion == "SchemaDetectionAgent"

    @pytest.mark.asyncio
    async def test_unmet_preconditions_are_skipped_over(self, planner, df):
        # No profile yet → statistics is not viable; insights is next in line.
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("raw_data", df).set("cleaned_data", df).set("business_domain", "hr")
        state = _done(
            state,
            "DataValidationAgent",
            "DataCleaningAgent",
            "SchemaDetectionAgent",
            "BusinessDomainDetectionAgent",
            "BusinessObjectiveDetectionAgent",
            "DataProfilingAgent",
            "FeatureEngineeringAgent",
            "KPIDiscoveryAgent",
        )
        result = await planner.execute(state)
        assert result.next_agent_suggestion == "InsightGenerationAgent"

    @pytest.mark.asyncio
    async def test_failed_agent_is_retried_then_skipped(self, planner, df):
        state = GraphState(input_dataset_path="test.csv").set("raw_data", df)
        state = _done(state, "DataValidationAgent")
        state = _done(state, "DataCleaningAgent", success=False)

        result = await planner.execute(state)
        assert result.decision == AgentDecision.RETRY
        assert result.next_agent_suggestion == "DataCleaningAgent"

        state = _done(state, "DataCleaningAgent", success=False)
        state = _done(state, "DataCleaningAgent", success=False)
        result = await planner.execute(state)
        assert result.metadata["reason"] == "quality_gate_skip"
        assert result.data_updates["steps_skipped"] == ["DataCleaningAgent"]
        # Nothing downstream can run without cleaned_data.
        assert result.decision == AgentDecision.ERROR

    @pytest.mark.asyncio
    async def test_failed_evaluation_remediates_then_reevaluates(self, planner, df):
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", df)
        state = state.set(
            "evaluation",
            {"passed": False, "failed_checks": ["has_insights"], "remediation": "InsightGenerationAgent"},
        )
        state = _done(state, "InsightGenerationAgent", "VisualizationAgent", "EvaluatorAgent")

        result = await planner.execute(state)
        assert result.decision == AgentDecision.REPLAN
        assert result.next_agent_suggestion == "InsightGenerationAgent"
        assert result.data_updates["pending_reevaluation"] is True

        state = _done(state.set("pending_reevaluation", True), "InsightGenerationAgent")
        result = await planner.execute(state)
        assert result.next_agent_suggestion == "EvaluatorAgent"
        assert result.data_updates["pending_reevaluation"] is False

    @pytest.mark.asyncio
    async def test_second_failed_evaluation_goes_to_report(self, planner, df):
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", df)
        state = state.set(
            "evaluation",
            {"passed": False, "failed_checks": ["has_insights"], "remediation": "InsightGenerationAgent"},
        )
        before_eval = [name for name, _ in PlannerAgent.PIPELINE][:-2]
        state = _done(state, *before_eval)
        state = _done(state, "EvaluatorAgent", "InsightGenerationAgent", "EvaluatorAgent")
        result = await planner.execute(state)
        assert result.next_agent_suggestion == "ReportingAgent"

    @pytest.mark.asyncio
    async def test_after_reporting_completes(self, planner, df):
        state = _done(GraphState(input_dataset_path="test.csv"), "ReportingAgent")
        result = await planner.execute(state)
        assert result.decision == AgentDecision.COMPLETE

    @pytest.mark.asyncio
    async def test_budget_exhausted_reports_then_completes(self, planner, df):
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", df)
        state = state.model_copy(update={"global_step_count": state.max_global_steps})
        result = await planner.execute(state)
        assert result.next_agent_suggestion == "ReportingAgent"

        state = _done(state, "ReportingAgent")
        result = await planner.execute(state)
        assert result.decision == AgentDecision.COMPLETE


class TestEvaluatorAgent:
    """Quality checks written to ``evaluation``."""

    @pytest.fixture
    def evaluator(self, mock_logger):
        return EvaluatorAgent(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_all_checks_pass(self, evaluator, df):
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", df)
        state = state.set("business_insights", [{"title": "x"}])
        state = state.set("visualizations", [{"type": "bar"}])
        state = state.set("profile", {"overall_missing_ratio": 0.1})

        result = await evaluator.execute(state)

        evaluation = result.data_updates["evaluation"]
        assert result.decision == AgentDecision.CONTINUE
        assert evaluation["passed"] is True
        assert evaluation["failed_checks"] == []
        assert result.quality_score == 1.0

    @pytest.mark.asyncio
    async def test_no_data(self, evaluator):
        result = await evaluator.execute(GraphState(input_dataset_path="test.csv"))
        evaluation = result.data_updates["evaluation"]
        assert evaluation["passed"] is False
        assert "has_data" in evaluation["failed_checks"]

    @pytest.mark.asyncio
    async def test_missing_insights_remediated_by_insight_agent(self, evaluator, df):
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", df)
        state = state.set("visualizations", [{"type": "bar"}])
        evaluation = (await evaluator.execute(state)).data_updates["evaluation"]
        assert evaluation["failed_checks"] == ["has_insights"]
        assert evaluation["remediation"] == "InsightGenerationAgent"

    @pytest.mark.asyncio
    async def test_poor_quality_has_no_remediation(self, evaluator, df):
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", df)
        state = state.set("business_insights", [{"title": "x"}])
        state = state.set("visualizations", [{"type": "bar"}])
        state = state.set("profile", {"overall_missing_ratio": 0.8})
        evaluation = (await evaluator.execute(state)).data_updates["evaluation"]
        assert evaluation["failed_checks"] == ["data_quality"]
        assert evaluation["remediation"] is None


class TestDataIngestionAgent:
    """Tests for Data Ingestion Agent."""

    @pytest.fixture
    def ingestion(self, mock_logger):
        return DataIngestionAgent(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_successful_csv_ingestion(self, ingestion, tmp_path, df):
        csv_file = tmp_path / "test.csv"
        df.to_csv(csv_file, index=False)

        result = await ingestion.execute(GraphState(input_dataset_path=str(csv_file)))

        assert result.decision == AgentDecision.CONTINUE
        assert "Loaded" in result.message
        assert len(result.data_updates["raw_data"]) == 3

    @pytest.mark.asyncio
    async def test_file_not_found(self, ingestion, tmp_path):
        state = GraphState(input_dataset_path=str(tmp_path / "nonexistent.csv"))
        result = await ingestion.execute(state)
        assert result.decision == AgentDecision.ERROR
        assert "File not found" in result.message

    @pytest.mark.asyncio
    async def test_empty_file(self, ingestion, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("a,b\n")
        result = await ingestion.execute(GraphState(input_dataset_path=str(csv_file)))
        assert result.decision == AgentDecision.ERROR
        assert "File is empty" in result.message


class TestDataProfilingAgent:
    """Tests for Data Profiling Agent."""

    @pytest.fixture
    def profiling(self, mock_logger):
        return DataProfilingAgent(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_successful_profiling(self, profiling):
        frame = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "name": ["Alice", "Bob", "Alice", "Bob", "Alice"],
                "age": [25, 30, 35, 40, 45],
                "salary": [50000.0, 60000.0, 70000.0, 80000.0, 90000.0],
            }
        )
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", frame)

        result = await profiling.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        profile = result.data_updates["profile"]
        assert profile["n_rows"] == 5
        assert profile["n_columns"] == 4
        assert len(profile["numeric_columns"]) == 3
        assert len(profile["categorical_columns"]) == 1

    @pytest.mark.asyncio
    async def test_no_data(self, profiling):
        result = await profiling.execute(GraphState(input_dataset_path="test.csv"))
        assert result.decision == AgentDecision.ERROR

    @pytest.mark.asyncio
    async def test_counts_missing_values(self, profiling):
        frame = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", "z"]})
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", frame)

        result = await profiling.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert result.data_updates["profile"]["overall_missing_ratio"] > 0
