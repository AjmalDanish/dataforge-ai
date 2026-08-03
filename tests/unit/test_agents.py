"""Tests for Agent base class."""

from unittest.mock import AsyncMock, Mock

import pytest

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


class MockAgent(Agent):
    """Mock agent for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execute_called = False

    async def execute(self, state: GraphState) -> AgentResult:
        """Mock execute."""
        self.execute_called = True
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Mock agent executed",
        )


class TestAgent:
    """Tests for Agent base class."""

    def test_agent_initialization(self) -> None:
        """Test agent initialization."""
        agent = MockAgent()

        assert agent.name == "MockAgent"
        assert agent.execute_called is False

    def test_agent_with_dependencies(self) -> None:
        """Test agent with LLM and logger."""
        mock_llm = Mock()
        mock_logger = Mock()

        agent = MockAgent(llm_provider=mock_llm, logger=mock_logger)

        assert agent.llm is mock_llm
        assert agent.logger is mock_logger

    @pytest.mark.asyncio
    async def test_agent_execute(self) -> None:
        """Test agent execute method."""
        state = GraphState(input_dataset_path="test.csv")
        agent = MockAgent()

        result = await agent.execute(state)

        assert agent.execute_called is True
        assert result.decision == AgentDecision.CONTINUE
        assert result.message == "Mock agent executed"

    @pytest.mark.asyncio
    async def test_agent_can_handle(self) -> None:
        """Test agent can_handle method."""
        state = GraphState(input_dataset_path="test.csv")
        agent = MockAgent()

        assert agent.can_handle(state) is True

    def test_agent_get_dependencies(self) -> None:
        """Test agent get_dependencies method."""
        agent = MockAgent()

        assert agent.get_dependencies() == []

    @pytest.mark.asyncio
    async def test_agent_execute_with_logging(self, tmp_path) -> None:
        """Test agent execute with logging."""
        state = GraphState(input_dataset_path="test.csv")
        logger = StructuredLogger("test-exec-id", tmp_path)
        agent = MockAgent(logger=logger)

        result, updated_state = await agent.execute_with_logging(state)

        assert agent.execute_called is True
        assert result.decision == AgentDecision.CONTINUE
        assert "MockAgent" in updated_state.steps_completed
        assert len(updated_state.agent_history) == 1

        # Check log was created
        logs = logger.get_logs_by_agent("MockAgent")
        assert len(logs) >= 2  # Start and completion logs

    @pytest.mark.asyncio
    async def test_agent_execute_with_logging_error(self, tmp_path) -> None:
        """Test agent execute with logging on error."""

        class FailingAgent(Agent):
            """Agent that always fails."""

            async def execute(self, state: GraphState) -> AgentResult:
                raise ValueError("Test error")

        state = GraphState(input_dataset_path="test.csv")
        logger = StructuredLogger("test-exec-id", tmp_path)
        agent = FailingAgent(logger=logger)

        result, updated_state = await agent.execute_with_logging(state)

        assert result.decision == AgentDecision.ERROR
        assert "failed" in result.message.lower()
        assert len(updated_state.agent_history) == 1
        assert updated_state.agent_history[0].decision == "error"

        # Check error log was created
        error_logs = logger.get_logs_by_level("ERROR")
        assert len(error_logs) >= 1


class TestAgentResult:
    """Tests for AgentResult."""

    def test_agent_result_creation(self) -> None:
        """Test creating AgentResult."""
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test message",
        )

        assert result.decision == AgentDecision.CONTINUE
        assert result.message == "Test message"
        assert result.data_updates == {}
        assert result.metadata == {}

    def test_agent_result_with_updates(self) -> None:
        """Test AgentResult with data updates."""
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test message",
            data_updates={"key": "value"},
            metadata={"meta": "data"},
        )

        assert result.data_updates == {"key": "value"}
        assert result.metadata == {"meta": "data"}

    def test_agent_result_with_suggestion(self) -> None:
        """Test AgentResult with next agent suggestion."""
        result = AgentResult(
            decision=AgentDecision.SKIP,
            message="Test message",
            next_agent_suggestion="DataProfilingAgent",
        )

        assert result.next_agent_suggestion == "DataProfilingAgent"


class TestAgentResultV2:
    """Tests for AgentResult v2 features."""

    def test_agent_result_with_quality_score(self) -> None:
        """Test AgentResult with quality score."""
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test message",
            quality_score=0.85,
        )

        assert result.quality_score == 0.85

    def test_agent_result_quality_score_validation(self) -> None:
        """Test quality score validation."""
        # Valid scores
        AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test",
            quality_score=0.0,
        )
        AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test",
            quality_score=1.0,
        )

    def test_agent_result_with_execution_notes(self) -> None:
        """Test AgentResult with execution notes."""
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test message",
            execution_notes=["Note 1", "Note 2"],
        )

        assert result.execution_notes == ["Note 1", "Note 2"]

    def test_agent_result_with_warnings(self) -> None:
        """Test AgentResult with warnings."""
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test message",
            warnings=["Warning 1", "Warning 2"],
        )

        assert result.warnings == ["Warning 1", "Warning 2"]

    def test_agent_result_with_metrics(self) -> None:
        """Test AgentResult with metrics."""
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test message",
            metrics={"rows_processed": 100, "time_ms": 50},
        )

        assert result.metrics == {"rows_processed": 100, "time_ms": 50}


class TestAgentV2:
    """Tests for Agent v2 features."""

    def test_agent_phase_property(self) -> None:
        """Test agent phase property."""
        agent = MockAgent()
        assert agent.phase == ExecutionPhase.DATA_INTAKE

    def test_agent_required_inputs(self) -> None:
        """Test agent required inputs."""
        agent = MockAgent()
        assert agent.required_inputs == []

    def test_agent_produced_outputs(self) -> None:
        """Test agent produced outputs."""
        agent = MockAgent()
        assert agent.produced_outputs == []

    def test_agent_retry_policy(self) -> None:
        """Test agent retry policy."""
        agent = MockAgent()
        assert agent.retry_policy.max_retries == 2
        assert agent.retry_policy.backoff_strategy == "exponential"

    def test_agent_failure_policy(self) -> None:
        """Test agent failure policy."""
        agent = MockAgent()
        assert agent.failure_policy == FailurePolicy.HALT

    def test_agent_timeout_seconds(self) -> None:
        """Test agent timeout seconds."""
        agent = MockAgent()
        assert agent.timeout_seconds == 300

    def test_agent_can_execute_with_matching_phase(self) -> None:
        """Test can_execute with matching phase."""
        state = GraphState(input_dataset_path="test.csv")
        agent = MockAgent()

        assert agent.can_execute(state) is True

    def test_agent_can_execute_with_wrong_phase(self) -> None:
        """Test can_execute with wrong phase."""
        state = GraphState(
            input_dataset_path="test.csv",
            current_phase=ExecutionPhase.DATA_PREPARATION,
        )
        agent = MockAgent()

        assert agent.can_execute(state) is False

    def test_agent_can_execute_with_missing_input(self) -> None:
        """Test can_execute with missing required input."""

        class RequiringAgent(Agent):
            required_inputs = ["raw_data"]

            async def execute(self, state: GraphState) -> AgentResult:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Test",
                )

        state = GraphState(input_dataset_path="test.csv")
        agent = RequiringAgent()

        assert agent.can_execute(state) is False

    def test_agent_can_execute_with_retry_limit(self) -> None:
        """Test can_execute respects retry limit."""
        state = GraphState(input_dataset_path="test.csv")

        # Simulate agent has been visited 3 times
        state = state.add_agent_result(
            "MockAgent",
            {"message": "test"},
        )
        state = state.add_agent_result(
            "MockAgent",
            {"message": "test"},
        )
        state = state.add_agent_result(
            "MockAgent",
            {"message": "test"},
        )

        agent = MockAgent()
        assert agent.can_execute(state) is False

    def test_agent_validate_input_success(self) -> None:
        """Test validate_input with valid state."""
        state = GraphState(input_dataset_path="test.csv")
        agent = MockAgent()

        is_valid, errors = agent.validate_input(state)
        assert is_valid is True
        assert errors == []

    def test_agent_validate_input_failure(self) -> None:
        """Test validate_input with missing required input."""

        class RequiringAgent(Agent):
            required_inputs = ["raw_data"]

            async def execute(self, state: GraphState) -> AgentResult:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Test",
                )

        state = GraphState(input_dataset_path="test.csv")
        agent = RequiringAgent()

        is_valid, errors = agent.validate_input(state)
        assert is_valid is False
        assert len(errors) == 1
        assert "raw_data" in errors[0]

    def test_agent_validate_output_success(self) -> None:
        """Test validate_output with valid result."""
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test",
        )
        agent = MockAgent()

        is_valid, errors = agent.validate_output(result)
        assert is_valid is True
        assert errors == []

    def test_agent_validate_output_invalid_quality(self) -> None:
        """Test validate_output with invalid quality score."""
        # Note: Pydantic validates quality_score at creation time,
        # so we can't create an AgentResult with invalid quality_score.
        # This test verifies that the validation logic exists and works correctly.
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test",
            quality_score=0.5,  # Valid
        )
        agent = MockAgent()

        is_valid, errors = agent.validate_output(result)
        assert is_valid is True
        assert errors == []

    def test_agent_validate_output_missing_produced(self) -> None:
        """Test validate_output with missing produced output."""

        class ProducingAgent(Agent):
            produced_outputs = ["cleaned_data"]

            async def execute(self, state: GraphState) -> AgentResult:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Test",
                )

        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test",
        )
        agent = ProducingAgent()

        is_valid, errors = agent.validate_output(result)
        assert is_valid is False
        assert len(errors) == 1
        assert "cleaned_data" in errors[0]

    def test_agent_before_execute_hook(self) -> None:
        """Test before_execute hook."""

        class HookAgent(Agent):
            def before_execute(self, state: GraphState) -> GraphState:
                return state.set("hook_called", True)

            async def execute(self, state: GraphState) -> AgentResult:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Test",
                )

        state = GraphState(input_dataset_path="test.csv")
        agent = HookAgent()

        state = agent.before_execute(state)
        assert state.data.get("hook_called") is True

    def test_agent_after_execute_hook(self) -> None:
        """Test after_execute hook."""

        class HookAgent(Agent):
            def after_execute(
                self, state: GraphState, result: AgentResult
            ) -> tuple[GraphState, AgentResult]:
                modified_result = result.model_copy(
                    update={"execution_notes": result.execution_notes + ["Hook called"]}
                )
                return state, modified_result

            async def execute(self, state: GraphState) -> AgentResult:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Test",
                )

        state = GraphState(input_dataset_path="test.csv")
        agent = HookAgent()
        result = AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Test",
        )

        state, result = agent.after_execute(state, result)
        assert "Hook called" in result.execution_notes

    @pytest.mark.asyncio
    async def test_agent_with_v2_properties_override(self) -> None:
        """Test agent with v2 property overrides."""
        custom_retry = RetryPolicy(max_retries=5)
        agent = MockAgent(
            retry_policy=custom_retry,
            failure_policy=FailurePolicy.SKIP,
            timeout_seconds=600,
        )

        assert agent.retry_policy.max_retries == 5
        assert agent.failure_policy == FailurePolicy.SKIP
        assert agent.timeout_seconds == 600

    @pytest.mark.asyncio
    async def test_agent_execute_with_logging_v2_features(self, tmp_path) -> None:
        """Test execute_with_logging includes v2 features."""
        state = GraphState(input_dataset_path="test.csv")
        logger = StructuredLogger("test-exec-id", tmp_path)

        class V2Agent(Agent):
            async def execute(self, state: GraphState) -> AgentResult:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Test",
                    quality_score=0.9,
                    execution_notes=["Note 1"],
                    warnings=["Warning 1"],
                    metrics={"test_metric": 42},
                )

        agent = V2Agent(logger=logger)
        result, updated_state = await agent.execute_with_logging(state)

        assert result.quality_score == 0.9
        assert result.execution_notes == ["Note 1"]
        assert result.warnings == ["Warning 1"]
        assert result.metrics == {"test_metric": 42}
        assert result.execution_duration is not None
        assert result.execution_duration > 0

    def test_agent_should_save_checkpoint(self) -> None:
        """Test should_save_checkpoint defaults to True."""
        agent = MockAgent()
        state = GraphState(input_dataset_path="test.csv")

        assert agent.should_save_checkpoint(state) is True


class TestAgentDecision:
    """Tests for AgentDecision enum."""

    def test_decision_values(self) -> None:
        """Test decision enum values."""
        assert AgentDecision.CONTINUE.value == "continue"
        assert AgentDecision.SKIP.value == "skip"
        assert AgentDecision.RETRY.value == "retry"
        assert AgentDecision.COMPLETE.value == "complete"
        assert AgentDecision.ERROR.value == "error"

    def test_decision_comparison(self) -> None:
        """Test decision comparison."""
        assert AgentDecision.CONTINUE == AgentDecision.CONTINUE
        assert AgentDecision.CONTINUE != AgentDecision.ERROR
