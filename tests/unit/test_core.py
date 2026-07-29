"""Unit tests for core components."""

import pytest

from dataforge.core.state import GraphState

# Import infrastructure first to register providers
from dataforge.infrastructure.llm_providers import AnthropicProvider, OpenAIProvider

# Skip provider tests if packages aren't installed
pytestmark = pytest.mark.skipif(
    OpenAIProvider is None and AnthropicProvider is None,
    reason="LLM provider packages not installed",
)
from dataforge.core.llm import (
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMProviderFactory,
    LLMResponse,
)
from dataforge.core.logger import StructuredLogger
from dataforge.shared.errors import ConfigurationError, DataForgeError
from dataforge.shared.utils import (
    deep_update,
    format_bytes,
    format_duration,
    generate_execution_id,
    get_timestamp,
    sanitize_filename,
    truncate_string,
)


class TestGraphState:
    """Tests for GraphState."""

    def test_initial_state(self) -> None:
        """Test initial state creation."""
        state = GraphState(input_dataset_path="test.csv")

        assert state.input_dataset_path == "test.csv"
        assert state.input_query is None
        assert state.output_dir == "./output"
        assert state.current_step == "start"
        assert state.steps_completed == []
        assert state.agent_history == []
        assert state.validation_status == "pending"
        assert state.retry_count == 0
        assert state.max_retries == 3
        assert isinstance(state.data, dict)
        assert isinstance(state.logs, list)
        assert isinstance(state.metrics, dict)

    def test_get_data(self) -> None:
        """Test getting data from state."""
        state = GraphState(input_dataset_path="test.csv")
        state = state.set("test_key", "test_value")

        assert state.get("test_key") == "test_value"
        assert state.get("nonexistent") is None
        assert state.get("nonexistent", "default") == "default"

    def test_set_data(self) -> None:
        """Test setting data in state."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.set("key", "value")

        assert state.get("key") is None  # Original unchanged
        assert new_state.get("key") == "value"

    def test_add_log(self) -> None:
        """Test adding log entries."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.add_log("INFO", "TestAgent", "Test message")

        assert len(state.logs) == 0
        assert len(new_state.logs) == 1
        assert new_state.logs[0]["level"] == "INFO"
        assert new_state.logs[0]["agent"] == "TestAgent"
        assert new_state.logs[0]["message"] == "Test message"

    def test_add_agent_result(self) -> None:
        """Test adding agent result."""
        state = GraphState(input_dataset_path="test.csv")
        result = {"success": True, "message": "Test"}
        new_state = state.add_agent_result("TestAgent", result)

        assert len(state.agent_history) == 0
        assert len(new_state.agent_history) == 1
        assert "TestAgent" in new_state.steps_completed
        assert new_state.agent_history[0]["agent"] == "TestAgent"

    def test_update_step(self) -> None:
        """Test updating current step."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.update_step("new_step")

        assert state.current_step == "start"
        assert new_state.current_step == "new_step"

    def test_increment_retry(self) -> None:
        """Test incrementing retry count."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.increment_retry()

        assert state.retry_count == 0
        assert new_state.retry_count == 1

    def test_add_metric(self) -> None:
        """Test adding metrics."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.add_metric("test_metric", 42)

        assert "test_metric" not in state.metrics
        assert new_state.metrics["test_metric"] == 42

    def test_mark_complete(self) -> None:
        """Test marking analysis as complete."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.mark_complete()

        assert state.end_time is None
        assert new_state.end_time is not None


class TestLLMComponents:
    """Tests for LLM components."""

    def test_llm_message(self) -> None:
        """Test LLM message creation."""
        msg = LLMMessage(role="user", content="Test")

        assert msg.role == "user"
        assert msg.content == "Test"

    def test_llm_response(self) -> None:
        """Test LLM response creation."""
        response = LLMResponse(
            content="Response", model="gpt-4", tokens_used=100, provider="openai"
        )

        assert response.content == "Response"
        assert response.model == "gpt-4"
        assert response.tokens_used == 100
        assert response.provider == "openai"

    def test_llm_config(self) -> None:
        """Test LLM configuration."""
        config = LLMConfig(provider="openai", model="gpt-4", temperature=0.7)

        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7

    def test_llm_provider_factory(self) -> None:
        """Test LLM provider factory."""
        assert LLMProviderFactory.is_registered("openai")
        if AnthropicProvider is not None:
            assert LLMProviderFactory.is_registered("anthropic")
        assert not LLMProviderFactory.is_registered("nonexistent")

    def test_llm_provider_list(self) -> None:
        """Test listing providers."""
        providers = LLMProviderFactory.list_providers()

        assert "openai" in providers
        if AnthropicProvider is not None:
            assert "anthropic" in providers


class TestStructuredLogger:
    """Tests for StructuredLogger."""

    def test_logger_creation(self, tmp_path) -> None:
        """Test logger creation."""
        logger = StructuredLogger("test-exec-id", tmp_path)

        assert logger.execution_id == "test-exec-id"
        assert logger.output_dir == tmp_path
        assert logger.logs == []

    def test_log_levels(self, tmp_path, capsys) -> None:
        """Test different log levels."""
        logger = StructuredLogger("test-exec-id", tmp_path)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        captured = capsys.readouterr()

        assert "Debug message" in captured.out
        assert "Info message" in captured.out
        assert "Warning message" in captured.out
        assert "Error message" in captured.out
        assert "Critical message" in captured.out

    def test_log_count(self, tmp_path) -> None:
        """Test log count increases."""
        logger = StructuredLogger("test-exec-id", tmp_path)

        assert len(logger.get_logs()) == 0

        logger.info("Test 1")
        logger.info("Test 2")

        assert len(logger.get_logs()) == 2

    def test_filter_logs_by_level(self, tmp_path) -> None:
        """Test filtering logs by level."""
        logger = StructuredLogger("test-exec-id", tmp_path)

        logger.info("Info message")
        logger.error("Error message")
        logger.warning("Warning message")

        error_logs = logger.get_logs_by_level("ERROR")
        info_logs = logger.get_logs_by_level("INFO")

        assert len(error_logs) == 1
        assert len(info_logs) == 1
        assert error_logs[0]["message"] == "Error message"

    def test_filter_logs_by_agent(self, tmp_path) -> None:
        """Test filtering logs by agent."""
        logger = StructuredLogger("test-exec-id", tmp_path)

        logger.info("Message 1", agent="Agent1")
        logger.info("Message 2", agent="Agent2")
        logger.info("Message 3", agent="Agent1")

        agent1_logs = logger.get_logs_by_agent("Agent1")
        agent2_logs = logger.get_logs_by_agent("Agent2")

        assert len(agent1_logs) == 2
        assert len(agent2_logs) == 1

    def test_clear_logs(self, tmp_path) -> None:
        """Test clearing logs."""
        logger = StructuredLogger("test-exec-id", tmp_path)

        logger.info("Test")
        assert len(logger.get_logs()) == 1

        logger.clear_logs()
        assert len(logger.get_logs()) == 0


class TestErrors:
    """Tests for custom errors."""

    def test_dataforge_error(self) -> None:
        """Test base error."""
        error = DataForgeError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"

    def test_dataforge_error_with_details(self) -> None:
        """Test error with details."""
        error = DataForgeError("Test error", details={"key": "value"})

        assert "Test error" in str(error)
        assert "Details:" in str(error)

    def test_configuration_error(self) -> None:
        """Test configuration error."""
        error = ConfigurationError("Config failed")

        assert isinstance(error, DataForgeError)
        assert "Config failed" in str(error)


class TestUtilities:
    """Tests for utility functions."""

    def test_generate_execution_id(self) -> None:
        """Test execution ID generation."""
        id1 = generate_execution_id()
        id2 = generate_execution_id()

        assert id1 != id2
        assert len(id1) == 36  # UUID format

    def test_get_timestamp(self) -> None:
        """Test timestamp generation."""
        ts = get_timestamp()

        assert isinstance(ts, str)
        assert "T" in ts  # ISO format

    def test_sanitize_filename(self) -> None:
        """Test filename sanitization."""
        assert sanitize_filename("test file") == "test_file"
        assert sanitize_filename("test/file") == "test_file"
        assert sanitize_filename("test*file") == "test_file"
        assert sanitize_filename("test:file") == "test_file"

    def test_format_bytes(self) -> None:
        """Test byte formatting."""
        assert format_bytes(100) == "100.00 B"
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1024 * 1024) == "1.00 MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"

    def test_format_duration(self) -> None:
        """Test duration formatting."""
        assert format_duration(0.1) == "100ms"
        assert format_duration(1.5) == "1.5s"
        assert format_duration(65) == "1m 5s"
        assert format_duration(125) == "2m 5s"

    def test_truncate_string(self) -> None:
        """Test string truncation."""
        long_string = "a" * 150
        truncated = truncate_string(long_string, max_length=100)

        assert len(truncated) <= 100
        assert truncated.endswith("...")

        short_string = "test"
        assert truncate_string(short_string, max_length=100) == short_string

    def test_deep_update(self) -> None:
        """Test deep dictionary update."""
        dict1 = {"a": 1, "b": {"c": 2, "d": 3}}
        dict2 = {"b": {"d": 4, "e": 5}, "f": 6}

        result = deep_update(dict1, dict2)

        assert result["a"] == 1
        assert result["b"]["c"] == 2  # Unchanged
        assert result["b"]["d"] == 4  # Updated
        assert result["b"]["e"] == 5  # New
        assert result["f"] == 6  # New
