"""Unit tests for core components."""

import pytest

from dataforge.core.models import ExecutionPhase
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
        assert state.current_phase == 1  # DATA_INTAKE
        assert state.steps_completed == []
        assert state.steps_skipped == []
        assert state.agent_history == []
        assert state.agent_visit_count == {}
        assert state.global_step_count == 0
        assert state.max_global_steps == 35
        assert state.quality_warnings == []
        assert state.quality_errors == []
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
        assert new_state.logs[0].level == "INFO"
        assert new_state.logs[0].agent == "TestAgent"
        assert new_state.logs[0].message == "Test message"

    def test_add_agent_result(self) -> None:
        """Test adding agent result."""
        state = GraphState(input_dataset_path="test.csv")
        result = {"success": True, "message": "Test"}
        new_state = state.add_agent_result("TestAgent", result)

        assert len(state.agent_history) == 0
        assert len(new_state.agent_history) == 1
        assert "TestAgent" in new_state.steps_completed
        assert new_state.agent_history[0].agent_name == "TestAgent"
        assert new_state.global_step_count == 1
        assert new_state.agent_visit_count["TestAgent"] == 1

    def test_update_step(self) -> None:
        """Test updating current step."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.update_step("new_step")

        assert state.current_step == "start"
        assert new_state.current_step == "new_step"

    def test_update_phase(self) -> None:
        """Test updating execution phase."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.update_phase(2)

        assert state.current_phase == 1
        assert new_state.current_phase == 2

    def test_update_phase_with_enum(self) -> None:
        """Test updating execution phase with enum."""
        from dataforge.core.models import ExecutionPhase

        state = GraphState(input_dataset_path="test.csv")
        new_state = state.update_phase(ExecutionPhase.DATA_PREPARATION)

        assert state.current_phase == 1
        assert new_state.current_phase == 2

    def test_add_quality_warning(self) -> None:
        """Test adding quality warning."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.add_quality_warning("Test warning")

        assert state.quality_warnings == []
        assert new_state.quality_warnings == ["Test warning"]

    def test_add_quality_error(self) -> None:
        """Test adding quality error."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.add_quality_error("Test error")

        assert state.quality_errors == []
        assert new_state.quality_errors == ["Test error"]

    def test_should_continue(self) -> None:
        """Test should_continue method."""
        state = GraphState(input_dataset_path="test.csv")

        assert state.should_continue() is True

        # Simulate reaching max steps
        state = state.model_copy(update={"global_step_count": 35})
        assert state.should_continue() is False

    def test_get_agent_visit_count(self) -> None:
        """Test getting agent visit count."""
        state = GraphState(input_dataset_path="test.csv")

        assert state.get_agent_visit_count("TestAgent") == 0

        state = state.add_agent_result("TestAgent", {})
        assert state.get_agent_visit_count("TestAgent") == 1

    def test_has_exceeded_max_retries(self) -> None:
        """Test checking if agent exceeded max retries."""
        state = GraphState(input_dataset_path="test.csv")

        # Agent not visited yet
        assert state.has_exceeded_max_retries("TestAgent", 3) is False

        # Agent visited 3 times (at limit)
        for _ in range(3):
            state = state.add_agent_result("TestAgent", {})

        assert state.has_exceeded_max_retries("TestAgent", 3) is False

        # Agent visited 4 times (exceeded)
        state = state.add_agent_result("TestAgent", {})
        assert state.has_exceeded_max_retries("TestAgent", 3) is True

    def test_typed_accessors(self) -> None:
        """Test typed accessors for well-known state keys."""
        state = GraphState(input_dataset_path="test.csv")

        # Initially all accessors return None
        assert state.raw_data is None
        assert state.file_metadata is None
        assert state.cleaned_data is None
        assert state.cleaning_report is None
        assert state.business_domain is None
        assert state.schema_info is None
        assert state.profile is None
        assert state.discovered_kpis is None
        assert state.statistics is None
        assert state.business_insights is None
        assert state.visualizations is None
        assert state.dashboard is None
        assert state.report_html is None
        assert state.report_pdf is None
        assert state.report_json is None
        assert state.execution_trace is None

        # Set some data and verify accessors
        state = state.set("raw_data", "test_data")
        assert state.raw_data == "test_data"

        state = state.set("business_domain", "retail")
        assert state.business_domain == "retail"

    def test_add_skip(self) -> None:
        """Test recording agent skip."""
        state = GraphState(input_dataset_path="test.csv")
        new_state = state.add_skip("TestAgent", "Test reason")

        assert state.steps_skipped == []
        assert new_state.steps_skipped == ["TestAgent"]
        assert len(new_state.logs) == 1
        assert "Skipped TestAgent" in new_state.logs[0].message

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

    def test_save_checkpoint_basic(self, tmp_path) -> None:
        """Test basic checkpoint save."""
        state = GraphState(input_dataset_path="test.csv", output_dir=str(tmp_path))
        checkpoint_dir = state.save_checkpoint()

        assert checkpoint_dir.exists()
        assert (checkpoint_dir / "checkpoint.json").exists()

    def test_save_checkpoint_with_dataframe(self, tmp_path) -> None:
        """Test checkpoint save with DataFrame data."""
        import pandas as pd

        try:
            df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
            state = GraphState(input_dataset_path="test.csv", output_dir=str(tmp_path))
            state = state.set("raw_data", df)

            checkpoint_dir = state.save_checkpoint()

            assert checkpoint_dir.exists()
            assert (checkpoint_dir / "checkpoint.json").exists()
            assert (checkpoint_dir / "data_raw_data.parquet").exists()
        except Exception as e:
            if "pyarrow" in str(e).lower() or "fastparquet" in str(e).lower():
                pytest.skip("PyArrow not available for Parquet serialization")
            raise

    def test_load_checkpoint_basic(self, tmp_path) -> None:
        """Test basic checkpoint load."""
        state = GraphState(
            input_dataset_path="test.csv",
            output_dir=str(tmp_path),
            input_query="test query",
        )
        checkpoint_dir = state.save_checkpoint()

        loaded_state = GraphState.load_checkpoint(checkpoint_dir)

        assert loaded_state.input_dataset_path == state.input_dataset_path
        assert loaded_state.input_query == state.input_query
        assert loaded_state.execution_id == state.execution_id
        assert loaded_state.current_phase == state.current_phase

    def test_load_checkpoint_with_dataframe(self, tmp_path) -> None:
        """Test checkpoint load with DataFrame data."""
        import pandas as pd

        try:
            df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
            state = GraphState(input_dataset_path="test.csv", output_dir=str(tmp_path))
            state = state.set("raw_data", df)
            checkpoint_dir = state.save_checkpoint()

            loaded_state = GraphState.load_checkpoint(checkpoint_dir)

            assert loaded_state.raw_data is not None
            assert loaded_state.raw_data.equals(df)
        except Exception as e:
            if "pyarrow" in str(e).lower() or "fastparquet" in str(e).lower():
                pytest.skip("PyArrow not available for Parquet serialization")
            raise

    def test_checkpoint_preserves_execution_state(self, tmp_path) -> None:
        """Test that checkpoint preserves execution state."""
        state = GraphState(input_dataset_path="test.csv", output_dir=str(tmp_path))
        state = state.update_phase(ExecutionPhase.DATA_PREPARATION)
        state = state.update_step("TestAgent")
        state = state.add_agent_result("TestAgent", {"message": "test"})
        state = state.add_quality_warning("test warning")
        state = state.add_quality_error("test error")

        checkpoint_dir = state.save_checkpoint()
        loaded_state = GraphState.load_checkpoint(checkpoint_dir)

        assert loaded_state.current_phase == ExecutionPhase.DATA_PREPARATION
        assert loaded_state.current_step == "TestAgent"
        assert len(loaded_state.agent_history) == 1
        assert loaded_state.quality_warnings == ["test warning"]
        assert loaded_state.quality_errors == ["test error"]

    def test_checkpoint_version_validation(self, tmp_path) -> None:
        """Test checkpoint version validation."""
        import json

        state = GraphState(input_dataset_path="test.csv", output_dir=str(tmp_path))
        checkpoint_dir = state.save_checkpoint()

        # Modify checkpoint version to be incompatible
        metadata_path = checkpoint_dir / "checkpoint.json"
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        metadata["checkpoint_version"] = "1.0.0"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Loading should fail with version validation enabled
        try:
            GraphState.load_checkpoint(checkpoint_dir, validate_version=True)
            assert False, "Should have raised DataForgeError"
        except Exception as e:
            assert "version mismatch" in str(e).lower()

        # Loading should succeed with version validation disabled
        loaded_state = GraphState.load_checkpoint(checkpoint_dir, validate_version=False)
        assert loaded_state.input_dataset_path == "test.csv"

    def test_checkpoint_missing_metadata(self, tmp_path) -> None:
        """Test loading checkpoint with missing metadata."""
        from dataforge.shared.errors import DataForgeError

        checkpoint_dir = tmp_path / "checkpoints" / "test"
        checkpoint_dir.mkdir(parents=True)

        try:
            GraphState.load_checkpoint(checkpoint_dir)
            assert False, "Should have raised DataForgeError"
        except DataForgeError as e:
            assert "not found" in str(e).lower()

    def test_checkpoint_custom_directory(self, tmp_path) -> None:
        """Test saving checkpoint to custom directory."""
        custom_dir = tmp_path / "custom_checkpoint"
        state = GraphState(input_dataset_path="test.csv")

        checkpoint_dir = state.save_checkpoint(custom_dir)

        assert checkpoint_dir == custom_dir
        assert checkpoint_dir.exists()
        assert (checkpoint_dir / "checkpoint.json").exists()


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


# ============================================================================
# DOMAIN MODELS TESTS (v2)
# ============================================================================


class TestBusinessDomain:
    """Tests for BusinessDomain enum."""

    def test_business_domain_values(self) -> None:
        """Test BusinessDomain has all expected values."""
        from dataforge.core.models import BusinessDomain

        assert BusinessDomain.RETAIL.value == "retail"
        assert BusinessDomain.FINANCE.value == "finance"
        assert BusinessDomain.HR.value == "hr"
        assert BusinessDomain.HEALTHCARE.value == "healthcare"
        assert BusinessDomain.MARKETING.value == "marketing"
        assert BusinessDomain.SAAS.value == "saas"
        assert BusinessDomain.REAL_ESTATE.value == "real_estate"
        assert BusinessDomain.EDUCATION.value == "education"
        assert BusinessDomain.LOGISTICS.value == "logistics"
        assert BusinessDomain.GENERAL.value == "general"

    def test_business_domain_display_name(self) -> None:
        """Test get_display_name method."""
        from dataforge.core.models import BusinessDomain

        assert BusinessDomain.RETAIL.get_display_name() == "Retail"
        assert BusinessDomain.REAL_ESTATE.get_display_name() == "Real Estate"
        assert BusinessDomain.GENERAL.get_display_name() == "General"


class TestBusinessObjective:
    """Tests for BusinessObjective model."""

    def test_business_objective_creation(self) -> None:
        """Test creating a BusinessObjective."""
        from dataforge.core.models import BusinessObjective

        objective = BusinessObjective(
            objective="Increase customer retention",
            category="growth",
            priority="high",
            confidence=0.8,
            keywords=["retention", "churn", "customer"],
        )

        assert objective.objective == "Increase customer retention"
        assert objective.category == "growth"
        assert objective.priority == "high"
        assert objective.confidence == 0.8
        assert objective.keywords == ["retention", "churn", "customer"]

    def test_business_objective_defaults(self) -> None:
        """Test BusinessObjective default values."""
        from dataforge.core.models import BusinessObjective

        objective = BusinessObjective(objective="Test objective")

        assert objective.category == "general"
        assert objective.priority == "medium"
        assert objective.confidence == 0.5
        assert objective.keywords == []

    def test_business_objective_confidence_validation(self) -> None:
        """Test BusinessObjective confidence validation."""
        from dataforge.core.models import BusinessObjective
        from pydantic import ValidationError

        # Valid confidence
        BusinessObjective(objective="Test", confidence=0.0)
        BusinessObjective(objective="Test", confidence=1.0)

        # Invalid confidence
        with pytest.raises(ValidationError):
            BusinessObjective(objective="Test", confidence=-0.1)

        with pytest.raises(ValidationError):
            BusinessObjective(objective="Test", confidence=1.1)

    def test_business_objective_immutability(self) -> None:
        """Test BusinessObjective is immutable."""
        from dataforge.core.models import BusinessObjective

        objective = BusinessObjective(objective="Test")

        with pytest.raises(Exception):  # FrozenInstanceError
            objective.objective = "Modified"


class TestBusinessInsight:
    """Tests for BusinessInsight model."""

    def test_business_insight_creation(self) -> None:
        """Test creating a BusinessInsight."""
        from dataforge.core.models import BusinessInsight

        insight = BusinessInsight(
            category="performance",
            title="Sales increased by 20%",
            summary="Q3 sales show significant growth",
            impact="high",
            confidence=0.9,
            action="Increase inventory for Q4",
            data_sources=["sales", "revenue"],
        )

        assert insight.category == "performance"
        assert insight.title == "Sales increased by 20%"
        assert insight.summary == "Q3 sales show significant growth"
        assert insight.impact == "high"
        assert insight.confidence == 0.9
        assert insight.action == "Increase inventory for Q4"
        assert insight.data_sources == ["sales", "revenue"]

    def test_business_insight_defaults(self) -> None:
        """Test BusinessInsight default values."""
        from dataforge.core.models import BusinessInsight

        insight = BusinessInsight(
            category="test",
            title="Test",
            summary="Test summary",
        )

        assert insight.impact == "medium"
        assert insight.confidence == 0.7
        assert insight.action is None
        assert insight.data_sources == []
        assert insight.created_at is not None  # Timestamp generated

    def test_business_insight_serialization(self) -> None:
        """Test BusinessInsight can be serialized."""
        from dataforge.core.models import BusinessInsight

        insight = BusinessInsight(
            category="test",
            title="Test",
            summary="Test summary",
        )

        serialized = insight.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["category"] == "test"
        assert serialized["title"] == "Test"


class TestKPIMetric:
    """Tests for KPIMetric model."""

    def test_kpi_metric_creation(self) -> None:
        """Test creating a KPIMetric."""
        from dataforge.core.models import KPIMetric

        metric = KPIMetric(
            name="Monthly Revenue",
            value=125000,
            unit="USD",
            trend="increasing",
            benchmark=100000,
            is_on_track=True,
        )

        assert metric.name == "Monthly Revenue"
        assert metric.value == 125000
        assert metric.unit == "USD"
        assert metric.trend == "increasing"
        assert metric.benchmark == 100000
        assert metric.is_on_track is True

    def test_kpi_metric_defaults(self) -> None:
        """Test KPIMetric default values."""
        from dataforge.core.models import KPIMetric

        metric = KPIMetric(name="Test", value=100)

        assert metric.unit is None
        assert metric.trend == "stable"
        assert metric.benchmark is None
        assert metric.is_on_track is None

    def test_kpi_metric_with_int_value(self) -> None:
        """Test KPIMetric accepts int values."""
        from dataforge.core.models import KPIMetric

        metric = KPIMetric(name="Count", value=42)
        assert metric.value == 42
        assert isinstance(metric.value, int)


class TestKPI:
    """Tests for KPI model."""

    def test_kpi_creation(self) -> None:
        """Test creating a KPI."""
        from dataforge.core.models import BusinessDomain, KPI, KPIMetric

        kpi = KPI(
            name="Customer Retention Rate",
            description="Percentage of customers retained over a period",
            formula="retained_customers / total_customers * 100",
            value=85.5,
            unit="%",
            trend="increasing",
            benchmark=80.0,
            is_on_track=True,
            domain=BusinessDomain.SAAS,
            confidence=0.9,
            metrics=[
                KPIMetric(name="Retained Customers", value=850),
                KPIMetric(name="Total Customers", value=1000),
            ],
        )

        assert kpi.name == "Customer Retention Rate"
        assert kpi.value == 85.5
        assert kpi.domain == BusinessDomain.SAAS
        assert len(kpi.metrics) == 2

    def test_kpi_defaults(self) -> None:
        """Test KPI default values."""
        from dataforge.core.models import KPI

        kpi = KPI(
            name="Test KPI",
            description="Test description",
            formula="test",
        )

        assert kpi.value is None
        assert kpi.unit is None
        assert kpi.trend == "stable"
        assert kpi.benchmark is None
        assert kpi.is_on_track is None
        assert kpi.metrics == []
        assert kpi.domain is None
        assert kpi.confidence == 0.7

    def test_kpi_validation(self) -> None:
        """Test KPI validation."""
        from dataforge.core.models import KPI
        from pydantic import ValidationError

        # Valid confidence
        KPI(name="Test", description="Test", formula="test", confidence=0.0)
        KPI(name="Test", description="Test", formula="test", confidence=1.0)

        # Invalid confidence
        with pytest.raises(ValidationError):
            KPI(name="Test", description="Test", formula="test", confidence=1.5)


class TestCleaningRule:
    """Tests for CleaningRule model."""

    def test_cleaning_rule_creation(self) -> None:
        """Test creating a CleaningRule."""
        from dataforge.core.models import CleaningRule

        rule = CleaningRule(
            rule_type="missing_values",
            column="age",
            action="impute",
            reason="Missing values detected",
            affected_rows=5,
            before_value="null",
            after_value="35.2",
        )

        assert rule.rule_type == "missing_values"
        assert rule.column == "age"
        assert rule.action == "impute"
        assert rule.reason == "Missing values detected"
        assert rule.affected_rows == 5
        assert rule.before_value == "null"
        assert rule.after_value == "35.2"

    def test_cleaning_rule_defaults(self) -> None:
        """Test CleaningRule default values."""
        from dataforge.core.models import CleaningRule

        rule = CleaningRule(
            rule_type="test",
            action="drop",
            reason="Test reason",
        )

        assert rule.column is None
        assert rule.affected_rows == 0
        assert rule.before_value is None
        assert rule.after_value is None
        assert rule.timestamp is not None

    def test_cleaning_rule_validation(self) -> None:
        """Test CleaningRule validation."""
        from dataforge.core.models import CleaningRule
        from pydantic import ValidationError

        # Valid affected_rows
        CleaningRule(rule_type="test", action="drop", reason="test", affected_rows=0)
        CleaningRule(rule_type="test", action="drop", reason="test", affected_rows=100)

        # Invalid affected_rows
        with pytest.raises(ValidationError):
            CleaningRule(rule_type="test", action="drop", reason="test", affected_rows=-1)


class TestSchemaInfo:
    """Tests for SchemaInfo model."""

    def test_schema_info_creation(self) -> None:
        """Test creating a SchemaInfo."""
        from dataforge.core.models import SchemaInfo

        schema = SchemaInfo(
            columns={
                "id": {"dtype": "int64", "nullable": False},
                "name": {"dtype": "object", "nullable": True},
            },
            primary_keys=["id"],
            foreign_keys={"department_id": "departments.id"},
            temporal_columns=["created_at"],
            hierarchical_columns=["category"],
            semantic_types={"id": "identifier", "name": "text"},
            confidence=0.9,
        )

        assert len(schema.columns) == 2
        assert schema.primary_keys == ["id"]
        assert schema.foreign_keys == {"department_id": "departments.id"}
        assert schema.temporal_columns == ["created_at"]
        assert schema.hierarchical_columns == ["category"]
        assert schema.semantic_types == {"id": "identifier", "name": "text"}
        assert schema.confidence == 0.9

    def test_schema_info_defaults(self) -> None:
        """Test SchemaInfo default values."""
        from dataforge.core.models import SchemaInfo

        schema = SchemaInfo(columns={})

        assert schema.primary_keys == []
        assert schema.foreign_keys == {}
        assert schema.temporal_columns == []
        assert schema.hierarchical_columns == []
        assert schema.semantic_types == {}
        assert schema.confidence == 0.8


class TestColumnProfile:
    """Tests for ColumnProfile model."""

    def test_column_profile_creation(self) -> None:
        """Test creating a ColumnProfile."""
        from dataforge.core.models import ColumnProfile

        profile = ColumnProfile(
            name="age",
            dtype="int64",
            non_null_count=95,
            null_count=5,
            null_percentage=5.0,
            unique_count=80,
            unique_percentage=84.2,
            min_value=18,
            max_value=65,
            mean=41.5,
            std=12.3,
            semantic_type="age",
            is_key=False,
            cardinality="medium",
        )

        assert profile.name == "age"
        assert profile.dtype == "int64"
        assert profile.non_null_count == 95
        assert profile.null_count == 5
        assert profile.null_percentage == 5.0
        assert profile.unique_count == 80
        assert profile.unique_percentage == 84.2
        assert profile.min_value == 18
        assert profile.max_value == 65
        assert profile.mean == 41.5
        assert profile.std == 12.3
        assert profile.semantic_type == "age"
        assert profile.is_key is False
        assert profile.cardinality == "medium"

    def test_column_profile_defaults(self) -> None:
        """Test ColumnProfile default values."""
        from dataforge.core.models import ColumnProfile

        profile = ColumnProfile(
            name="test",
            dtype="object",
            non_null_count=100,
            null_count=0,
            null_percentage=0.0,
        )

        assert profile.unique_count is None
        assert profile.unique_percentage is None
        assert profile.min_value is None
        assert profile.max_value is None
        assert profile.mean is None
        assert profile.std is None
        assert profile.semantic_type is None
        assert profile.is_key is False
        assert profile.cardinality == "medium"

    def test_column_profile_validation(self) -> None:
        """Test ColumnProfile validation."""
        from dataforge.core.models import ColumnProfile
        from pydantic import ValidationError

        # Valid null_percentage
        ColumnProfile(
            name="test", dtype="object", non_null_count=90, null_count=10, null_percentage=10.0
        )
        ColumnProfile(
            name="test", dtype="object", non_null_count=0, null_count=100, null_percentage=100.0
        )

        # Invalid null_percentage
        with pytest.raises(ValidationError):
            ColumnProfile(
                name="test", dtype="object", non_null_count=100, null_count=0, null_percentage=-1.0
            )

        with pytest.raises(ValidationError):
            ColumnProfile(
                name="test", dtype="object", non_null_count=0, null_count=100, null_percentage=101.0
            )


class TestDatasetProfile:
    """Tests for DatasetProfile model."""

    def test_dataset_profile_creation(self) -> None:
        """Test creating a DatasetProfile."""
        from dataforge.core.models import ColumnProfile, DatasetProfile

        profile = DatasetProfile(
            row_count=1000,
            column_count=10,
            memory_usage_mb=5.2,
            duplicate_rows=10,
            duplicate_percentage=1.0,
            missing_values_total=50,
            missing_percentage=0.5,
            numeric_columns=["age", "salary"],
            categorical_columns=["department", "city"],
            temporal_columns=["created_at"],
            text_columns=["description"],
            boolean_columns=["is_active"],
            quality_score=0.95,
        )

        assert profile.row_count == 1000
        assert profile.column_count == 10
        assert profile.memory_usage_mb == 5.2
        assert profile.duplicate_rows == 10
        assert profile.duplicate_percentage == 1.0
        assert profile.missing_values_total == 50
        assert profile.missing_percentage == 0.5
        assert profile.numeric_columns == ["age", "salary"]
        assert profile.categorical_columns == ["department", "city"]
        assert profile.temporal_columns == ["created_at"]
        assert profile.text_columns == ["description"]
        assert profile.boolean_columns == ["is_active"]
        assert profile.quality_score == 0.95

    def test_dataset_profile_defaults(self) -> None:
        """Test DatasetProfile default values."""
        from dataforge.core.models import DatasetProfile

        profile = DatasetProfile(
            row_count=100, column_count=5, memory_usage_mb=1.0
        )

        assert profile.duplicate_rows == 0
        assert profile.duplicate_percentage == 0.0
        assert profile.missing_values_total == 0
        assert profile.missing_percentage == 0.0
        assert profile.numeric_columns == []
        assert profile.categorical_columns == []
        assert profile.temporal_columns == []
        assert profile.text_columns == []
        assert profile.boolean_columns == []
        assert profile.column_profiles == {}
        assert profile.quality_score == 1.0
        assert profile.generated_at is not None

    def test_dataset_profile_with_column_profiles(self) -> None:
        """Test DatasetProfile with nested ColumnProfile."""
        from dataforge.core.models import ColumnProfile, DatasetProfile

        column_profile = ColumnProfile(
            name="age",
            dtype="int64",
            non_null_count=100,
            null_count=0,
            null_percentage=0.0,
        )

        profile = DatasetProfile(
            row_count=100,
            column_count=1,
            memory_usage_mb=1.0,
            column_profiles={"age": column_profile},
        )

        assert "age" in profile.column_profiles
        assert profile.column_profiles["age"].name == "age"


class TestFileMetadata:
    """Tests for FileMetadata model."""

    def test_file_metadata_creation(self) -> None:
        """Test creating a FileMetadata."""
        from dataforge.core.models import FileMetadata

        metadata = FileMetadata(
            filename="data.csv",
            file_path="/path/to/data.csv",
            file_size_bytes=1024000,
            file_size_mb=1.024,
            file_format="csv",
            encoding="utf-8",
            row_count=1000,
            column_count=10,
            last_modified="2024-01-01T00:00:00",
        )

        assert metadata.filename == "data.csv"
        assert metadata.file_path == "/path/to/data.csv"
        assert metadata.file_size_bytes == 1024000
        assert metadata.file_size_mb == 1.024
        assert metadata.file_format == "csv"
        assert metadata.encoding == "utf-8"
        assert metadata.row_count == 1000
        assert metadata.column_count == 10
        assert metadata.last_modified == "2024-01-01T00:00:00"

    def test_file_metadata_defaults(self) -> None:
        """Test FileMetadata default values."""
        from dataforge.core.models import FileMetadata

        metadata = FileMetadata(
            filename="test.csv",
            file_path="/path/test.csv",
            file_size_bytes=1000,
            file_size_mb=0.001,
            file_format="csv",
        )

        assert metadata.encoding == "utf-8"
        assert metadata.row_count is None
        assert metadata.column_count is None
        assert metadata.created_at is not None
        assert metadata.last_modified is None

    def test_file_metadata_validation(self) -> None:
        """Test FileMetadata validation."""
        from dataforge.core.models import FileMetadata
        from pydantic import ValidationError

        # Valid sizes
        FileMetadata(
            filename="test.csv",
            file_path="/path/test.csv",
            file_size_bytes=0,
            file_size_mb=0.0,
            file_format="csv",
        )

        # Invalid sizes
        with pytest.raises(ValidationError):
            FileMetadata(
                filename="test.csv",
                file_path="/path/test.csv",
                file_size_bytes=-1,
                file_size_mb=0.0,
                file_format="csv",
            )


class TestValidationIssue:
    """Tests for ValidationIssue model."""

    def test_validation_issue_creation(self) -> None:
        """Test creating a ValidationIssue."""
        from dataforge.core.models import ValidationIssue

        issue = ValidationIssue(
            issue_type="missing_data",
            severity="error",
            column="age",
            row_indices=[1, 5, 10],
            message="Missing values in age column",
            suggestion="Impute with mean value",
            count=3,
        )

        assert issue.issue_type == "missing_data"
        assert issue.severity == "error"
        assert issue.column == "age"
        assert issue.row_indices == [1, 5, 10]
        assert issue.message == "Missing values in age column"
        assert issue.suggestion == "Impute with mean value"
        assert issue.count == 3

    def test_validation_issue_defaults(self) -> None:
        """Test ValidationIssue default values."""
        from dataforge.core.models import ValidationIssue

        issue = ValidationIssue(
            issue_type="test",
            severity="warning",
            message="Test message",
        )

        assert issue.column is None
        assert issue.row_indices == []
        assert issue.suggestion is None
        assert issue.count == 1

    def test_validation_issue_validation(self) -> None:
        """Test ValidationIssue validation."""
        from dataforge.core.models import ValidationIssue
        from pydantic import ValidationError

        # Valid count
        ValidationIssue(issue_type="test", severity="warning", message="test", count=1)
        ValidationIssue(issue_type="test", severity="warning", message="test", count=100)

        # Invalid count
        with pytest.raises(ValidationError):
            ValidationIssue(issue_type="test", severity="warning", message="test", count=0)


class TestValidationReport:
    """Tests for ValidationReport model."""

    def test_validation_report_creation(self) -> None:
        """Test creating a ValidationReport."""
        from dataforge.core.models import ValidationIssue, ValidationReport

        issues = [
            ValidationIssue(
                issue_type="missing_data",
                severity="error",
                message="Missing values",
                count=5,
            ),
            ValidationIssue(
                issue_type="invalid_format",
                severity="warning",
                message="Invalid format",
                count=2,
            ),
        ]

        report = ValidationReport(
            is_valid=False,
            total_issues=7,
            error_count=5,
            warning_count=2,
            info_count=0,
            issues=issues,
            columns_affected=["age", "email"],
            recommendations=["Impute missing values", "Fix email format"],
        )

        assert report.is_valid is False
        assert report.total_issues == 7
        assert report.error_count == 5
        assert report.warning_count == 2
        assert report.info_count == 0
        assert len(report.issues) == 2
        assert report.columns_affected == ["age", "email"]
        assert report.recommendations == ["Impute missing values", "Fix email format"]

    def test_validation_report_defaults(self) -> None:
        """Test ValidationReport default values."""
        from dataforge.core.models import ValidationReport

        report = ValidationReport(is_valid=True, total_issues=0)

        assert report.error_count == 0
        assert report.warning_count == 0
        assert report.info_count == 0
        assert report.issues == []
        assert report.columns_affected == []
        assert report.recommendations == []
        assert report.generated_at is not None

    def test_validation_report_validation(self) -> None:
        """Test ValidationReport validation."""
        from dataforge.core.models import ValidationReport
        from pydantic import ValidationError

        # Valid counts
        ValidationReport(is_valid=True, total_issues=0)
        ValidationReport(is_valid=False, total_issues=100)

        # Invalid counts
        with pytest.raises(ValidationError):
            ValidationReport(is_valid=True, total_issues=-1)


class TestRecommendation:
    """Tests for Recommendation model."""

    def test_recommendation_creation(self) -> None:
        """Test creating a Recommendation."""
        from dataforge.core.models import Recommendation

        recommendation = Recommendation(
            category="data_quality",
            title="Improve data completeness",
            description="Address missing values in critical columns",
            priority="high",
            impact="high",
            effort="medium",
            related_insights=["insight_1", "insight_2"],
            data_columns=["age", "salary"],
        )

        assert recommendation.category == "data_quality"
        assert recommendation.title == "Improve data completeness"
        assert recommendation.description == "Address missing values in critical columns"
        assert recommendation.priority == "high"
        assert recommendation.impact == "high"
        assert recommendation.effort == "medium"
        assert recommendation.related_insights == ["insight_1", "insight_2"]
        assert recommendation.data_columns == ["age", "salary"]

    def test_recommendation_defaults(self) -> None:
        """Test Recommendation default values."""
        from dataforge.core.models import Recommendation

        recommendation = Recommendation(
            category="test",
            title="Test",
            description="Test description",
        )

        assert recommendation.priority == "medium"
        assert recommendation.impact == "medium"
        assert recommendation.effort == "medium"
        assert recommendation.related_insights == []
        assert recommendation.data_columns == []


class TestInsightEvidence:
    """Tests for InsightEvidence model."""

    def test_insight_evidence_creation(self) -> None:
        """Test creating an InsightEvidence."""
        from dataforge.core.models import InsightEvidence

        evidence = InsightEvidence(
            insight_id="insight_1",
            evidence_type="statistic",
            description="Mean age is 41.5 years",
            data_source="age",
            value=41.5,
            comparison="absolute",
            confidence=0.95,
            row_indices=[1, 2, 3, 4, 5],
        )

        assert evidence.insight_id == "insight_1"
        assert evidence.evidence_type == "statistic"
        assert evidence.description == "Mean age is 41.5 years"
        assert evidence.data_source == "age"
        assert evidence.value == 41.5
        assert evidence.comparison == "absolute"
        assert evidence.confidence == 0.95
        assert evidence.row_indices == [1, 2, 3, 4, 5]

    def test_insight_evidence_defaults(self) -> None:
        """Test InsightEvidence default values."""
        from dataforge.core.models import InsightEvidence

        evidence = InsightEvidence(
            evidence_type="test",
            description="Test description",
        )

        assert evidence.insight_id is None
        assert evidence.data_source is None
        assert evidence.value is None
        assert evidence.comparison == "absolute"
        assert evidence.confidence == 0.8
        assert evidence.row_indices is None

    def test_insight_evidence_with_different_value_types(self) -> None:
        """Test InsightEvidence accepts different value types."""
        from dataforge.core.models import InsightEvidence

        # Float value
        e1 = InsightEvidence(evidence_type="test", description="test", value=3.14)
        assert e1.value == 3.14

        # Int value
        e2 = InsightEvidence(evidence_type="test", description="test", value=42)
        assert e2.value == 42

        # String value
        e3 = InsightEvidence(evidence_type="test", description="test", value="high")
        assert e3.value == "high"


class TestBusinessGlossaryTerm:
    """Tests for BusinessGlossaryTerm model."""

    def test_business_glossary_term_creation(self) -> None:
        """Test creating a BusinessGlossaryTerm."""
        from dataforge.core.models import BusinessDomain, BusinessGlossaryTerm

        term = BusinessGlossaryTerm(
            term="Churn Rate",
            definition="Percentage of customers who stop using a service",
            domain=BusinessDomain.SAAS,
            synonyms=["attrition rate", "customer attrition"],
            examples=["Monthly churn rate of 5%"],
            confidence=0.95,
        )

        assert term.term == "Churn Rate"
        assert term.definition == "Percentage of customers who stop using a service"
        assert term.domain == BusinessDomain.SAAS
        assert term.synonyms == ["attrition rate", "customer attrition"]
        assert term.examples == ["Monthly churn rate of 5%"]
        assert term.confidence == 0.95

    def test_business_glossary_term_defaults(self) -> None:
        """Test BusinessGlossaryTerm default values."""
        from dataforge.core.models import BusinessGlossaryTerm

        term = BusinessGlossaryTerm(
            term="Test",
            definition="Test definition",
        )

        assert term.domain is None
        assert term.synonyms == []
        assert term.examples == []
        assert term.confidence == 0.9


class TestFeatureDefinition:
    """Tests for FeatureDefinition model."""

    def test_feature_definition_creation(self) -> None:
        """Test creating a FeatureDefinition."""
        from dataforge.core.models import FeatureDefinition

        feature = FeatureDefinition(
            name="age_group",
            description="Age grouped into categories",
            source_columns=["age"],
            transformation="bin",
            data_type="str",
            example_value="30-40",
            business_relevance="high",
        )

        assert feature.name == "age_group"
        assert feature.description == "Age grouped into categories"
        assert feature.source_columns == ["age"]
        assert feature.transformation == "bin"
        assert feature.data_type == "str"
        assert feature.example_value == "30-40"
        assert feature.business_relevance == "high"

    def test_feature_definition_defaults(self) -> None:
        """Test FeatureDefinition default values."""
        from dataforge.core.models import FeatureDefinition

        feature = FeatureDefinition(
            name="test",
            description="test",
            source_columns=["col1"],
            transformation="test",
            data_type="str",
            example_value="test",
        )

        assert feature.business_relevance == "medium"


class TestBusinessRule:
    """Tests for BusinessRule model."""

    def test_business_rule_creation(self) -> None:
        """Test creating a BusinessRule."""
        from dataforge.core.models import BusinessDomain, BusinessRule

        rule = BusinessRule(
            name="Age Validation",
            description="Employee age must be between 18 and 65",
            rule_type="validation",
            condition="age >= 18 and age <= 65",
            column="age",
            expected_value="18-65",
            severity="error",
            is_active=True,
            domain=BusinessDomain.HR,
        )

        assert rule.name == "Age Validation"
        assert rule.description == "Employee age must be between 18 and 65"
        assert rule.rule_type == "validation"
        assert rule.condition == "age >= 18 and age <= 65"
        assert rule.column == "age"
        assert rule.expected_value == "18-65"
        assert rule.severity == "error"
        assert rule.is_active is True
        assert rule.domain == BusinessDomain.HR

    def test_business_rule_defaults(self) -> None:
        """Test BusinessRule default values."""
        from dataforge.core.models import BusinessRule

        rule = BusinessRule(
            name="Test",
            description="Test",
            rule_type="test",
        )

        assert rule.condition is None
        assert rule.column is None
        assert rule.expected_value is None
        assert rule.severity == "warning"
        assert rule.is_active is True
        assert rule.domain is None
