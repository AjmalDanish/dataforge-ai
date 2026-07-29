"""Tests for implemented agents (planner, evaluator, ingestion, profiling)."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

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
    """Create a mock logger for testing."""
    return StructuredLogger("test-exec-id", tmp_path)


class TestPlannerAgent:
    """Tests for Planner Agent."""

    @pytest.fixture
    def planner(self, mock_logger):
        return PlannerAgent(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_initial_state(self, planner):
        """Test planner decision for initial state."""
        state = GraphState(input_dataset_path="test.csv")

        result = await planner.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert result.next_agent_suggestion == "DataIngestionAgent"
        assert result.metadata["reason"] == "initial_state"

    @pytest.mark.asyncio
    async def test_after_ingestion_success(self, planner):
        """Test planner after successful ingestion."""
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2, 3]})
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("raw_data", df)
        state = state.update_step("DataIngestionAgent")
        state = state.add_agent_result("DataIngestionAgent", {"success": True})

        result = await planner.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert result.next_agent_suggestion == "DataProfilingAgent"
        assert "data_loaded_successfully" in result.metadata["reason"]

    @pytest.mark.asyncio
    async def test_after_ingestion_failure(self, planner):
        """Test planner after failed ingestion."""
        state = GraphState(input_dataset_path="test.csv")
        state = state.update_step("DataIngestionAgent")
        state = state.add_agent_result("DataIngestionAgent", {"success": False})

        result = await planner.execute(state)

        assert result.decision == AgentDecision.ERROR
        assert "No data loaded" in result.message

    @pytest.mark.asyncio
    async def test_after_profiling_with_numeric(self, planner):
        """Test planner after profiling with numeric columns."""
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("profile", {"has_numeric_columns": True, "numeric_column_count": 3})
        state = state.update_step("DataProfilingAgent")
        state = state.add_agent_result("DataProfilingAgent", {"success": True})

        result = await planner.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert result.next_agent_suggestion == "StatisticalAnalysisAgent"

    @pytest.mark.asyncio
    async def test_after_profiling_no_numeric(self, planner):
        """Test planner after profiling without numeric columns."""
        state = GraphState(input_dataset_path="test.csv")
        state = state.set(
            "profile", {"has_numeric_columns": False, "has_categorical_columns": True}
        )
        state = state.update_step("DataProfilingAgent")
        state = state.add_agent_result("DataProfilingAgent", {"success": True})
        # Add steps_completed so planner knows profiling is done
        state = state.model_copy(update={"steps_completed": ["DataProfilingAgent"]})

        result = await planner.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert result.next_agent_suggestion == "VisualizationAgent"

    @pytest.mark.asyncio
    async def test_after_evaluator_passed(self, planner):
        """Test planner after successful evaluation."""
        state = GraphState(input_dataset_path="test.csv")
        state = state.update_step("EvaluatorAgent")
        state = state.set("validation_status", "passed")
        state = state.add_agent_result("EvaluatorAgent", {"success": True})
        # Add steps_completed so planner knows evaluator is done
        state = state.model_copy(update={"steps_completed": ["EvaluatorAgent"]})

        result = await planner.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert result.next_agent_suggestion == "ReportingAgent"

    @pytest.mark.asyncio
    async def test_after_evaluator_failed(self, planner):
        """Test planner after failed evaluation."""
        state = GraphState(
            input_dataset_path="test.csv",
            validation_status="failed",
            failed_checks=["has_insights"],
            retry_count=0,
            profile={"has_numeric_columns": True, "has_categorical_columns": True},
            statistics={"correlations": {"significant": []}},
            visualizations=[],
            steps_completed=[
                "DataIngestionAgent",
                "DataProfilingAgent",
                "StatisticalAnalysisAgent",
                "VisualizationAgent",
                "EvaluatorAgent",
            ],
        )

        result = await planner.execute(state)

        assert result.decision == AgentDecision.REPLAN
        assert "Validation failed" in result.message
        assert result.data_updates["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_max_retries(self, planner):
        """Test planner respects max retries."""
        state = GraphState(input_dataset_path="test.csv")
        state = state.update_step("EvaluatorAgent")
        state = state.set("validation_status", "failed")
        state = state.set("failed_checks", ["has_insights"])
        state = state.set("retry_count", 3)  # At max
        state = state.add_agent_result("EvaluatorAgent", {"success": True})
        # Add steps_completed so planner knows evaluator is done
        state = state.model_copy(
            update={
                "steps_completed": ["EvaluatorAgent"],
                "validation_status": "failed",
                "failed_checks": ["has_insights"],
                "retry_count": 3,
            }
        )

        result = await planner.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert "max_retries_exceeded" in result.metadata["reason"]
        assert result.next_agent_suggestion == "ReportingAgent"

    @pytest.mark.asyncio
    async def test_after_reporting(self, planner):
        """Test planner after reporting is complete."""
        state = GraphState(input_dataset_path="test.csv")
        state = state.update_step("ReportingAgent")
        state = state.add_agent_result("ReportingAgent", {"success": True})

        result = await planner.execute(state)

        assert result.decision == AgentDecision.COMPLETE
        assert "Analysis complete" in result.message


class TestEvaluatorAgent:
    """Tests for Evaluator Agent."""

    @pytest.fixture
    def evaluator(self, mock_logger):
        return EvaluatorAgent(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_all_checks_pass(self, evaluator, tmp_path):
        """Test evaluator when all checks pass."""
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("raw_data", df)
        state = state.set("profile", {"overall_missing_ratio": 0.1})
        state = state.set("insights", [{"type": "info", "message": "Test1"}] * 3)
        state = state.update_step("VisualizationAgent")
        state = state.add_agent_result("DataIngestionAgent", {"success": True})
        state = state.add_agent_result("DataProfilingAgent", {"success": True})
        state = state.add_agent_result("StatisticalAnalysisAgent", {"success": True})

        result = await evaluator.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert result.data_updates["validation_status"] == "passed"
        assert "All validation checks passed" in result.message

    @pytest.mark.asyncio
    async def test_no_data(self, evaluator):
        """Test evaluator when no data exists."""
        state = GraphState(input_dataset_path="test.csv")
        state.update_step("VisualizationAgent")

        result = await evaluator.execute(state)

        assert result.decision == AgentDecision.REPLAN
        assert result.data_updates["validation_status"] == "failed"
        assert "has_data" in result.data_updates["failed_checks"]

    @pytest.mark.asyncio
    async def test_insufficient_insights(self, evaluator):
        """Test evaluator with insufficient insights."""
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2, 3]})
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("raw_data", df)
        state = state.set("insights", [{"type": "info", "message": "Test1"}])  # Only 1 insight
        state.update_step("VisualizationAgent")
        state = state.add_agent_result("DataProfilingAgent", {"success": True})

        result = await evaluator.execute(state)

        assert result.decision == AgentDecision.REPLAN
        assert "has_insights" in result.data_updates["failed_checks"]

    @pytest.mark.asyncio
    async def test_insufficient_depth(self, evaluator):
        """Test evaluator with insufficient analysis depth."""
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2, 3]})
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("raw_data", df)
        state = state.set("profile", {"overall_missing_ratio": 0.0})
        state.set("insights", [{"type": "info", "message": "Test"}] * 3)
        state.update_step("VisualizationAgent")
        state = state.add_agent_result("DataIngestionAgent", {"success": True})
        # Missing profiling or stats/viz

        result = await evaluator.execute(state)

        assert result.decision == AgentDecision.REPLAN
        assert "sufficient_depth" in result.data_updates["failed_checks"]


class TestDataIngestionAgent:
    """Tests for Data Ingestion Agent."""

    @pytest.fixture
    def ingestion(self, tmp_path, mock_logger):
        return DataIngestionAgent(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_successful_csv_ingestion(self, ingestion, tmp_path):
        """Test successful CSV ingestion."""
        import pandas as pd

        # Create test CSV
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        df.to_csv(csv_file, index=False)

        state = GraphState(input_dataset_path=str(csv_file))

        result = await ingestion.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert "Loaded" in result.message
        assert "raw_data" in result.data_updates
        assert len(result.data_updates["raw_data"]) == 3

    @pytest.mark.asyncio
    async def test_file_not_found(self, ingestion, tmp_path):
        """Test ingestion with non-existent file."""
        state = GraphState(input_dataset_path=str(tmp_path / "nonexistent.csv"))

        result = await ingestion.execute(state)

        assert result.decision == AgentDecision.ERROR
        assert "File not found" in result.message

    @pytest.mark.asyncio
    async def test_empty_file(self, ingestion, tmp_path):
        """Test ingestion with empty CSV."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("a,b\n")

        state = GraphState(input_dataset_path=str(csv_file))

        result = await ingestion.execute(state)

        assert result.decision == AgentDecision.ERROR
        assert "File is empty" in result.message


class TestDataProfilingAgent:
    """Tests for Data Profiling Agent."""

    @pytest.fixture
    def profiling(self, mock_logger):
        return DataProfilingAgent(logger=mock_logger)

    @pytest.mark.asyncio
    async def test_successful_profiling(self, profiling):
        """Test successful data profiling."""
        import pandas as pd

        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "name": ["Alice", "Bob", "Alice", "Bob", "Alice"],
                "age": [25, 30, 35, 40, 45],
                "salary": [50000.0, 60000.0, 70000.0, 80000.0, 90000.0],
            }
        )
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("raw_data", df)

        result = await profiling.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert "profiled" in result.message.lower()
        assert "profile" in result.data_updates
        profile = result.data_updates["profile"]
        assert profile["n_rows"] == 5
        assert profile["n_columns"] == 4
        assert len(profile["numeric_columns"]) == 3
        assert len(profile["categorical_columns"]) == 1

    @pytest.mark.asyncio
    async def test_no_data(self, profiling):
        """Test profiling with no data."""
        state = GraphState(input_dataset_path="test.csv")

        result = await profiling.execute(state)

        assert result.decision == AgentDecision.ERROR
        assert "No data available" in result.message

    @pytest.mark.asyncio
    async def test_generates_insights(self, profiling):
        """Test that profiling generates insights."""
        import pandas as pd

        df = pd.DataFrame(
            {
                "a": [1, None, 3],
                "b": ["x", "y", "z"],
            }
        )
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("raw_data", df)
        state = state.set("insights", [])

        result = await profiling.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        insights = result.data_updates.get("insights", [])
        assert len(insights) > 0
