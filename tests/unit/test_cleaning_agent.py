"""Unit tests for DataCleaningAgent."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import numpy as np
import pytest

from dataforge.agents.cleaning import DataCleaningAgent
from dataforge.core.models import CleaningRule, ExecutionPhase
from dataforge.core.state import GraphState


@pytest.fixture
def agent() -> DataCleaningAgent:
    """Create DataCleaningAgent instance."""
    return DataCleaningAgent()


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create sample DataFrame with various data quality issues."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "Alice", "Eve"],
        "age": [30, 25, 35, 30, 28],
        "salary": [50000.0, 60000.0, 70000.0, 50000.0, 55000.0],
        "department": ["Engineering", "Sales", "Engineering", "Engineering", "Marketing"],
    })


@pytest.fixture
def dataframe_with_issues() -> pd.DataFrame:
    """Create DataFrame with various data quality issues."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 1],  # Duplicate row
        "name": ["Alice", "Bob", "Charlie", "Alice", "Eve", "Alice"],
        "age": [30, 25, 35, 30, 28, 30],
        "salary": [50000.0, np.nan, 70000.0, 50000.0, 55000.0, 50000.0],  # Missing value
        "department": ["Engineering", "Sales", "Engineering", "Engineering", "Marketing", "Engineering"],
        "empty_col": [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],  # Empty column
        "const_col": [1, 1, 1, 1, 1, 1],  # Constant column
        "whitespace": ["  Alice  ", "  Bob  ", "  Charlie  ", "  Alice  ", "  Eve  ", "  Alice  "],
        "mixed_case": ["ALICE", "bob", "CHARLIE", "ALICE", "EVE", "ALICE"],
        "invalid_numeric": [1.0, 2.0, np.inf, 4.0, 5.0, 1.0],
        "invalid_category": ["Valid", "NA", "Valid", "Valid", "NULL", "Valid"],
    })


@pytest.fixture
def state(sample_dataframe: pd.DataFrame) -> GraphState:
    """Create GraphState with sample data."""
    return GraphState(
        input_dataset_path="test.csv",
        execution_id="test-123",
        start_time="2024-01-01T00:00:00",
        data={"raw_data": sample_dataframe},
        current_phase=ExecutionPhase.DATA_PREPARATION,
    )


class TestDataCleaningAgentInit:
    """Tests for DataCleaningAgent initialization."""

    def test_agent_properties(self, agent: DataCleaningAgent) -> None:
        """Test agent properties are set correctly."""
        assert agent.name == "DataCleaningAgent"
        assert agent.phase == ExecutionPhase.DATA_PREPARATION
        assert agent.required_inputs == ["raw_data"]
        assert "cleaned_data" in agent.produced_outputs
        assert "cleaning_report" in agent.produced_outputs
        assert agent.retry_policy.max_retries == 2
        assert agent.timeout_seconds == 60

    def test_agent_thresholds(self, agent: DataCleaningAgent) -> None:
        """Test cleaning thresholds are set correctly."""
        assert agent.missing_value_threshold == 0.7
        assert agent.outlier_iqr_multiplier == 1.5
        assert agent.constant_column_threshold == 0.95


class TestDataCleaningAgentExecute:
    """Tests for DataCleaningAgent.execute method."""

    @pytest.mark.asyncio
    async def test_execute_clean_data(self, agent: DataCleaningAgent, state: GraphState) -> None:
        """Test execution with clean data."""
        result = await agent.execute(state)

        assert result.decision.name == "CONTINUE"
        assert "cleaned_data" in result.data_updates
        assert "cleaning_report" in result.data_updates
        assert "cleaning_rules_applied" in result.data_updates
        assert isinstance(result.data_updates["cleaned_data"], pd.DataFrame)
        assert result.quality_score is not None
        assert result.quality_score > 0.5  # Clean data should have reasonable confidence (case normalization and outlier detection still apply)

    @pytest.mark.asyncio
    async def test_execute_with_issues(self, agent: DataCleaningAgent, dataframe_with_issues: pd.DataFrame) -> None:
        """Test execution with data quality issues."""
        state = GraphState(
            input_dataset_path="test.csv",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            data={"raw_data": dataframe_with_issues},
            current_phase=ExecutionPhase.DATA_PREPARATION,
        )

        result = await agent.execute(state)

        assert result.decision.name == "CONTINUE"
        assert "cleaned_data" in result.data_updates
        assert "cleaning_rules_applied" in result.data_updates
        rules = result.data_updates["cleaning_rules_applied"]
        assert len(rules) > 0  # Should have applied some cleaning rules

    @pytest.mark.asyncio
    async def test_execute_no_raw_data(self, agent: DataCleaningAgent) -> None:
        """Test execution with no raw_data in state."""
        state = GraphState(
            input_dataset_path="test.csv",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            data={},
            current_phase=ExecutionPhase.DATA_PREPARATION,
        )

        result = await agent.execute(state)

        assert result.decision.name == "ERROR"
        assert "No raw_data found" in result.message
        assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_execute_empty_dataframe(self, agent: DataCleaningAgent) -> None:
        """Test execution with empty DataFrame."""
        state = GraphState(
            input_dataset_path="test.csv",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            data={"raw_data": pd.DataFrame()},
            current_phase=ExecutionPhase.DATA_PREPARATION,
        )

        result = await agent.execute(state)

        assert result.decision.name == "CONTINUE"
        assert "cleaned_data" in result.data_updates

    @pytest.mark.asyncio
    async def test_execute_original_data_unchanged(self, agent: DataCleaningAgent, state: GraphState) -> None:
        """Test that original data is not modified."""
        original_data = state.data["raw_data"].copy()
        original_id = id(state.data["raw_data"])

        await agent.execute(state)

        # Original data should be unchanged
        assert id(state.data["raw_data"]) == original_id
        pd.testing.assert_frame_equal(state.data["raw_data"], original_data)

    @pytest.mark.asyncio
    async def test_execute_checksums_generated(self, agent: DataCleaningAgent, state: GraphState) -> None:
        """Test that checksums are generated for original and cleaned data."""
        result = await agent.execute(state)

        assert "original_data_checksum" in result.data_updates
        assert "cleaned_data_checksum" in result.data_updates
        assert isinstance(result.data_updates["original_data_checksum"], str)
        assert isinstance(result.data_updates["cleaned_data_checksum"], str)
        assert len(result.data_updates["original_data_checksum"]) > 0
        assert len(result.data_updates["cleaned_data_checksum"]) > 0


class TestDataCleaningAgentDuplicateColumns:
    """Tests for duplicate column handling."""

    def test_handle_duplicate_columns(self, agent: DataCleaningAgent) -> None:
        """Test duplicate column detection and removal."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [1, 2, 3],  # Duplicate of col1
            "col3": [4, 5, 6],
        })

        df_clean, rules = agent._handle_duplicate_columns(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "duplicate_column"
        assert rules[0].action == "drop"
        assert "col2" not in df_clean.columns
        assert "col1" in df_clean.columns

    def test_handle_no_duplicate_columns(self, agent: DataCleaningAgent) -> None:
        """Test with no duplicate columns."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
            "col3": [7, 8, 9],
        })

        df_clean, rules = agent._handle_duplicate_columns(df)

        assert len(rules) == 0
        assert len(df_clean.columns) == 3


class TestDataCleaningAgentEmptyColumns:
    """Tests for empty column handling."""

    def test_handle_empty_columns(self, agent: DataCleaningAgent) -> None:
        """Test empty column detection and removal."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [np.nan, np.nan, np.nan],  # Empty column
            "col3": [4, 5, 6],
        })

        df_clean, rules = agent._handle_empty_columns(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "empty_column"
        assert rules[0].action == "drop"
        assert "col2" not in df_clean.columns
        assert "col1" in df_clean.columns

    def test_handle_no_empty_columns(self, agent: DataCleaningAgent) -> None:
        """Test with no empty columns."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
            "col3": [7, 8, 9],
        })

        df_clean, rules = agent._handle_empty_columns(df)

        assert len(rules) == 0
        assert len(df_clean.columns) == 3


class TestDataCleaningAgentConstantColumns:
    """Tests for constant column handling."""

    def test_handle_constant_columns(self, agent: DataCleaningAgent) -> None:
        """Test constant column detection and removal."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [1, 1, 1],  # Constant column
            "col3": [4, 5, 6],
        })

        df_clean, rules = agent._handle_constant_columns(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "constant_column"
        assert rules[0].action == "drop"
        assert "col2" not in df_clean.columns
        assert "col1" in df_clean.columns

    def test_handle_no_constant_columns(self, agent: DataCleaningAgent) -> None:
        """Test with no constant columns."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
            "col3": [7, 8, 9],
        })

        df_clean, rules = agent._handle_constant_columns(df)

        assert len(rules) == 0
        assert len(df_clean.columns) == 3


class TestDataCleaningAgentDuplicateRows:
    """Tests for duplicate row handling."""

    def test_handle_duplicate_rows(self, agent: DataCleaningAgent) -> None:
        """Test duplicate row detection and removal."""
        df = pd.DataFrame({
            "col1": [1, 2, 3, 1],  # Row 0 and 3 are duplicates
            "col2": [4, 5, 6, 4],
        })

        df_clean, rules = agent._handle_duplicate_rows(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "duplicate_rows"
        assert rules[0].action == "drop"
        assert rules[0].affected_rows == 1
        assert len(df_clean) == 3

    def test_handle_no_duplicate_rows(self, agent: DataCleaningAgent) -> None:
        """Test with no duplicate rows."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
        })

        df_clean, rules = agent._handle_duplicate_rows(df)

        assert len(rules) == 0
        assert len(df_clean) == 3


class TestDataCleaningAgentMissingValues:
    """Tests for missing value handling."""

    def test_handle_missing_values_drop_column(self, agent: DataCleaningAgent) -> None:
        """Test dropping column with >70% missing values."""
        df = pd.DataFrame({
            "col1": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "col2": [1, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],  # 90% missing
        })

        df_clean, rules = agent._handle_missing_values(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "missing_values"
        assert rules[0].action == "drop"
        assert "col2" not in df_clean.columns

    def test_handle_missing_values_impute_numeric(self, agent: DataCleaningAgent) -> None:
        """Test imputing missing values in numeric column."""
        df = pd.DataFrame({
            "col1": [1, 2, np.nan, 4, 5],  # 20% missing
        })

        df_clean, rules = agent._handle_missing_values(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "missing_values"
        assert rules[0].action == "impute"
        assert rules[0].affected_rows == 1
        assert df_clean["col1"].isnull().sum() == 0

    def test_handle_missing_values_impute_categorical(self, agent: DataCleaningAgent) -> None:
        """Test imputing missing values in categorical column."""
        df = pd.DataFrame({
            "col1": ["A", "B", np.nan, "A", "B"],  # 20% missing
        })

        df_clean, rules = agent._handle_missing_values(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "missing_values"
        assert rules[0].action == "impute"
        assert rules[0].affected_rows == 1
        assert df_clean["col1"].isnull().sum() == 0

    def test_handle_no_missing_values(self, agent: DataCleaningAgent) -> None:
        """Test with no missing values."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
        })

        df_clean, rules = agent._handle_missing_values(df)

        assert len(rules) == 0


class TestDataCleaningAgentTypeNormalization:
    """Tests for data type normalization."""

    def test_normalize_numeric_conversion(self, agent: DataCleaningAgent) -> None:
        """Test numeric type conversion."""
        df = pd.DataFrame({
            "col1": ["1", "2", "3"],  # String numbers
        })

        df_clean, rules = agent._normalize_data_types(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "type_normalization"
        assert rules[0].action == "cast"
        assert pd.api.types.is_numeric_dtype(df_clean["col1"])

    def test_normalize_no_conversion_needed(self, agent: DataCleaningAgent) -> None:
        """Test with no conversion needed."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
        })

        df_clean, rules = agent._normalize_data_types(df)

        assert len(rules) == 0


class TestDataCleaningAgentDateNormalization:
    """Tests for date normalization."""

    def test_normalize_dates(self, agent: DataCleaningAgent) -> None:
        """Test date normalization."""
        df = pd.DataFrame({
            "col1": ["2024-01-01", "2024-01-02", "2024-01-03"],
        })

        df_clean, rules = agent._normalize_dates(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "date_normalization"
        assert rules[0].action == "cast"
        assert pd.api.types.is_datetime64_any_dtype(df_clean["col1"])

    def test_normalize_no_dates(self, agent: DataCleaningAgent) -> None:
        """Test with no date columns."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
        })

        df_clean, rules = agent._normalize_dates(df)

        assert len(rules) == 0


class TestDataCleaningAgentInvalidNumeric:
    """Tests for invalid numeric value handling."""

    def test_handle_invalid_numeric(self, agent: DataCleaningAgent) -> None:
        """Test handling infinite values."""
        df = pd.DataFrame({
            "col1": [1.0, 2.0, np.inf, 4.0, -np.inf],
        })

        df_clean, rules = agent._handle_invalid_numeric(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "invalid_numeric"
        assert rules[0].action == "flag"
        assert rules[0].affected_rows == 2

    def test_handle_no_invalid_numeric(self, agent: DataCleaningAgent) -> None:
        """Test with no invalid numeric values."""
        df = pd.DataFrame({
            "col1": [1.0, 2.0, 3.0, 4.0, 5.0],
        })

        df_clean, rules = agent._handle_invalid_numeric(df)

        assert len(rules) == 0


class TestDataCleaningAgentStringCleaning:
    """Tests for string cleaning."""

    def test_clean_strings(self, agent: DataCleaningAgent) -> None:
        """Test string whitespace trimming."""
        df = pd.DataFrame({
            "col1": ["  Alice  ", "  Bob  ", "  Charlie  "],
        })

        df_clean, rules = agent._clean_strings(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "string_cleaning"
        assert rules[0].action == "trim"
        assert df_clean["col1"].iloc[0] == "Alice"

    def test_clean_no_strings(self, agent: DataCleaningAgent) -> None:
        """Test with no string columns."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
        })

        df_clean, rules = agent._clean_strings(df)

        assert len(rules) == 0


class TestDataCleaningAgentCaseNormalization:
    """Tests for case normalization."""

    def test_normalize_case(self, agent: DataCleaningAgent) -> None:
        """Test case normalization."""
        df = pd.DataFrame({
            "col1": ["ALICE", "Bob", "CHARLIE"],
        })

        df_clean, rules = agent._normalize_case(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "case_normalization"
        assert rules[0].action == "lowercase"
        assert df_clean["col1"].iloc[0] == "alice"

    def test_normalize_no_case_needed(self, agent: DataCleaningAgent) -> None:
        """Test with no case normalization needed."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
        })

        df_clean, rules = agent._normalize_case(df)

        assert len(rules) == 0


class TestDataCleaningAgentOutliers:
    """Tests for outlier handling."""

    def test_handle_outliers(self, agent: DataCleaningAgent) -> None:
        """Test outlier detection and flagging."""
        df = pd.DataFrame({
            "col1": [1, 2, 3, 4, 5, 100],  # 100 is an outlier
        })

        df_clean, rules = agent._handle_outliers(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "outliers"
        assert rules[0].action == "flag"
        assert rules[0].affected_rows >= 1

    def test_handle_no_outliers(self, agent: DataCleaningAgent) -> None:
        """Test with no outliers."""
        df = pd.DataFrame({
            "col1": [1, 2, 3, 4, 5],
        })

        df_clean, rules = agent._handle_outliers(df)

        assert len(rules) == 0


class TestDataCleaningAgentInvalidCategories:
    """Tests for invalid category handling."""

    def test_handle_invalid_categories(self, agent: DataCleaningAgent) -> None:
        """Test handling invalid category values."""
        df = pd.DataFrame({
            "col1": ["Valid", "NA", "Valid", "NULL", "Valid"],
        })

        df_clean, rules = agent._handle_invalid_categories(df)

        assert len(rules) == 1
        assert rules[0].rule_type == "invalid_category"
        assert rules[0].action == "flag"
        assert rules[0].affected_rows == 2

    def test_handle_no_invalid_categories(self, agent: DataCleaningAgent) -> None:
        """Test with no invalid categories."""
        df = pd.DataFrame({
            "col1": ["Valid", "Valid", "Valid"],
        })

        df_clean, rules = agent._handle_invalid_categories(df)

        assert len(rules) == 0


class TestDataCleaningAgentChecksum:
    """Tests for DataFrame checksum calculation."""

    def test_calculate_dataframe_checksum(self, agent: DataCleaningAgent) -> None:
        """Test DataFrame checksum calculation."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
        })

        checksum1 = agent._calculate_dataframe_checksum(df)
        checksum2 = agent._calculate_dataframe_checksum(df)

        assert checksum1 == checksum2
        assert len(checksum1) > 0

    def test_checksum_different_for_different_data(self, agent: DataCleaningAgent) -> None:
        """Test that checksum differs for different data."""
        df1 = pd.DataFrame({
            "col1": [1, 2, 3],
        })
        df2 = pd.DataFrame({
            "col1": [4, 5, 6],
        })

        checksum1 = agent._calculate_dataframe_checksum(df1)
        checksum2 = agent._calculate_dataframe_checksum(df2)

        assert checksum1 != checksum2


class TestDataCleaningAgentConfidence:
    """Tests for cleaning confidence calculation."""

    def test_calculate_cleaning_confidence_no_rules(self, agent: DataCleaningAgent) -> None:
        """Test confidence calculation with no rules."""
        confidence = agent._calculate_cleaning_confidence([], 100, 10)
        assert confidence == 1.0

    def test_calculate_cleaning_confidence_with_rules(self, agent: DataCleaningAgent) -> None:
        """Test confidence calculation with rules."""
        rules = [
            CleaningRule(
                rule_type="test",
                column="col1",
                action="flag",
                reason="Test",
                affected_rows=5,
            )
        ]
        confidence = agent._calculate_cleaning_confidence(rules, 100, 10)
        assert 0.0 <= confidence <= 1.0
        assert confidence < 1.0

    def test_calculate_cleaning_confidence_with_drops(self, agent: DataCleaningAgent) -> None:
        """Test confidence calculation with drop actions."""
        rules = [
            CleaningRule(
                rule_type="test",
                column="col1",
                action="drop",
                reason="Test",
                affected_rows=50,
            )
        ]
        confidence = agent._calculate_cleaning_confidence(rules, 100, 10)
        assert 0.0 <= confidence <= 1.0


class TestDataCleaningAgentIntegration:
    """Integration tests for DataCleaningAgent."""

    @pytest.mark.asyncio
    async def test_full_cleaning_workflow(self, agent: DataCleaningAgent, dataframe_with_issues: pd.DataFrame) -> None:
        """Test complete cleaning workflow."""
        state = GraphState(
            input_dataset_path="test.csv",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            data={"raw_data": dataframe_with_issues},
            current_phase=ExecutionPhase.DATA_PREPARATION,
        )

        result = await agent.execute(state)

        # Verify all expected outputs
        assert "cleaned_data" in result.data_updates
        assert "cleaning_report" in result.data_updates
        assert "cleaning_rules_applied" in result.data_updates
        assert "rows_removed" in result.data_updates
        assert "columns_removed" in result.data_updates
        assert "missing_values_fixed" in result.data_updates
        assert "duplicates_removed" in result.data_updates
        assert "cleaning_summary" in result.data_updates
        assert "cleaning_confidence" in result.data_updates
        assert "original_data_checksum" in result.data_updates
        assert "cleaned_data_checksum" in result.data_updates

        # Verify data types
        assert isinstance(result.data_updates["cleaned_data"], pd.DataFrame)
        assert isinstance(result.data_updates["cleaning_rules_applied"], list)
        assert isinstance(result.data_updates["rows_removed"], int)
        assert isinstance(result.data_updates["columns_removed"], int)
        assert isinstance(result.data_updates["missing_values_fixed"], int)
        assert isinstance(result.data_updates["duplicates_removed"], int)
        assert isinstance(result.data_updates["cleaning_confidence"], float)

        # Verify cleaning report structure
        report = result.data_updates["cleaning_report"]
        assert "total_issues_found" in report
        assert "total_issues_fixed" in report
        assert "rows_before" in report
        assert "rows_after" in report
        assert "columns_before" in report
        assert "columns_after" in report
        assert "decisions" in report

    @pytest.mark.asyncio
    async def test_can_execute(self, agent: DataCleaningAgent, sample_dataframe: pd.DataFrame) -> None:
        """Test can_execute method."""
        state = GraphState(
            input_dataset_path="test.csv",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            data={"raw_data": sample_dataframe},
            current_phase=ExecutionPhase.DATA_PREPARATION,
        )

        assert agent.can_execute(state) is True

    @pytest.mark.asyncio
    async def test_cannot_execute_wrong_phase(self, agent: DataCleaningAgent, sample_dataframe: pd.DataFrame) -> None:
        """Test can_execute with wrong phase."""
        state = GraphState(
            input_dataset_path="test.csv",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            data={"raw_data": sample_dataframe},
            current_phase=ExecutionPhase.DATA_INTAKE,  # Wrong phase
        )

        assert agent.can_execute(state) is False

    @pytest.mark.asyncio
    async def test_cannot_execute_missing_input(self, agent: DataCleaningAgent) -> None:
        """Test can_execute with missing input."""
        state = GraphState(
            input_dataset_path="test.csv",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            data={},  # No raw_data
            current_phase=ExecutionPhase.DATA_PREPARATION,
        )

        assert agent.can_execute(state) is False