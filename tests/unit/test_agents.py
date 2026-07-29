"""Tests for Agent base class."""

from unittest.mock import AsyncMock, Mock

import pytest

from dataforge.agents.base import Agent, AgentDecision, AgentResult
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
        assert updated_state.agent_history[0]["result"]["success"] is False

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
            decision=AgentDecision.REPLAN,
            message="Test message",
            next_agent_suggestion="DataProfilingAgent",
        )

        assert result.next_agent_suggestion == "DataProfilingAgent"


class TestAgentDecision:
    """Tests for AgentDecision enum."""

    def test_decision_values(self) -> None:
        """Test decision enum values."""
        assert AgentDecision.CONTINUE.value == "continue"
        assert AgentDecision.REPLAN.value == "replan"
        assert AgentDecision.COMPLETE.value == "complete"
        assert AgentDecision.ERROR.value == "error"

    def test_decision_comparison(self) -> None:
        """Test decision comparison."""
        assert AgentDecision.CONTINUE == AgentDecision.CONTINUE
        assert AgentDecision.CONTINUE != AgentDecision.ERROR
