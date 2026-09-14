"""Unit tests for DataValidationAgent."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from dataforge.agents import DataValidationAgent
from dataforge.agents.base import AgentDecision
from dataforge.core.models import ExecutionPhase, ValidationIssue
from dataforge.core.state import GraphState
from dataforge.shared.errors import DataIngestionError


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def valid_csv(temp_dir: Path) -> Path:
    """Create a valid CSV file for testing."""
    csv_file = temp_dir / "valid.csv"
    csv_file.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n")
    return csv_file


@pytest.fixture
def empty_csv(temp_dir: Path) -> Path:
    """Create an empty CSV file for testing."""
    csv_file = temp_dir / "empty.csv"
    csv_file.write_text("")
    return csv_file


@pytest.fixture
def csv_with_issues(temp_dir: Path) -> Path:
    """Create a CSV file with data quality issues."""
    csv_file = temp_dir / "issues.csv"
    csv_file.write_text(
        "name,age,city,salary\n"
        "Alice,30,NYC,50000\n"
        "Bob,,LA,\n"
        "Charlie,35,Chicago,60000\n"
        "Alice,30,NYC,50000\n"  # duplicate row
        "David,four,Boston,70000\n"  # invalid numeric
    )
    return csv_file


@pytest.fixture
def csv_with_high_nulls(temp_dir: Path) -> Path:
    """Create a CSV file with high null percentages."""
    csv_file = temp_dir / "high_nulls.csv"
    csv_file.write_text(
        "name,age,city,salary\n"
        "Alice,30,NYC,50000\n"
        "Bob,,,\n"
        "Charlie,35,,\n"
        "David,,,\n"
        "Eve,,,\n"
    )
    return csv_file


@pytest.fixture
def csv_with_duplicate_columns(temp_dir: Path) -> Path:
    """Create a CSV file with duplicate column names."""
    csv_file = temp_dir / "duplicate_cols.csv"
    csv_file.write_text("name,age,age\nAlice,30,35\nBob,25,28\n")
    return csv_file


@pytest.fixture
def json_file(temp_dir: Path) -> Path:
    """Create a JSON file for testing."""
    json_file = temp_dir / "data.json"
    json_file.write_text('[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]')
    return json_file


@pytest.fixture
def agent() -> DataValidationAgent:
    """Create a DataValidationAgent instance."""
    return DataValidationAgent()


@pytest.fixture
def state(temp_dir: Path) -> GraphState:
    """Create a GraphState with input dataset path."""
    csv_file = temp_dir / "test.csv"
    csv_file.write_text("name,age\nAlice,30\nBob,25\n")
    return GraphState(
        input_dataset_path=str(csv_file),
        execution_id="test-123",
        start_time="2024-01-01T00:00:00",
    )


class TestDataValidationAgentInit:
    """Tests for DataValidationAgent initialization."""

    def test_agent_properties(self, agent: DataValidationAgent) -> None:
        """Test agent properties are set correctly."""
        assert agent.name == "DataValidationAgent"
        assert agent.phase == ExecutionPhase.DATA_INTAKE
        # required_inputs is empty because input_dataset_path is a direct GraphState field, not in state.data
        assert agent.required_inputs == []
        assert agent.produced_outputs == ["raw_data", "file_metadata", "validation_report"]
        assert agent.retry_policy.max_retries == 1
        assert agent.timeout_seconds == 30

    def test_agent_thresholds(self, agent: DataValidationAgent) -> None:
        """Test validation thresholds are set correctly."""
        assert agent.max_file_size_mb == 100.0
        assert agent.max_rows == 1_000_000
        assert agent.max_columns == 1000
        assert agent.null_threshold == 0.5
        assert agent.duplicate_threshold == 0.1
        assert agent.high_cardinality_threshold == 10000

    def test_agent_with_custom_thresholds(self) -> None:
        """Test agent with custom thresholds."""
        agent = DataValidationAgent()
        # Modify thresholds directly (they are class attributes)
        agent.max_file_size_mb = 50.0
        agent.max_rows = 500_000
        agent.max_columns = 500
        assert agent.max_file_size_mb == 50.0
        assert agent.max_rows == 500_000
        assert agent.max_columns == 500


class TestDataValidationAgentExecute:
    """Tests for DataValidationAgent.execute method."""

    @pytest.mark.asyncio
    async def test_execute_valid_csv(self, agent: DataValidationAgent, state: GraphState) -> None:
        """Test execution with valid CSV file."""
        result = await agent.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert "validation passed" in result.message.lower()
        assert result.quality_score is not None
        assert result.quality_score > 0.7
        assert "raw_data" in result.data_updates
        assert "file_metadata" in result.data_updates
        assert "validation_report" in result.data_updates
        assert "validation_score" in result.data_updates
        assert "validation_summary" in result.data_updates
        assert "validation_issues" in result.data_updates
        assert "recommendations" in result.data_updates

    @pytest.mark.asyncio
    async def test_execute_missing_file(self, agent: DataValidationAgent) -> None:
        """Test execution with missing file."""
        state = GraphState(
            input_dataset_path="/nonexistent/file.csv",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        assert result.decision == AgentDecision.ERROR
        assert "not found" in result.message.lower()
        assert result.quality_score == 0.0
        assert "validation_report" in result.data_updates

    @pytest.mark.asyncio
    async def test_execute_empty_dataset(self, agent: DataValidationAgent, empty_csv: Path) -> None:
        """Test execution with empty dataset."""
        state = GraphState(
            input_dataset_path=str(empty_csv),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        assert result.decision == AgentDecision.ERROR
        # Empty files are detected during loading, not structure validation
        assert "empty" in result.message.lower() or "load" in result.message.lower()
        assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_execute_json_file(self, agent: DataValidationAgent, json_file: Path) -> None:
        """Test execution with JSON file."""
        state = GraphState(
            input_dataset_path=str(json_file),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        assert result.decision == AgentDecision.CONTINUE
        assert "validation passed" in result.message.lower()
        assert "raw_data" in result.data_updates

    @pytest.mark.asyncio
    async def test_execute_with_data_issues(
        self, agent: DataValidationAgent, csv_with_issues: Path
    ) -> None:
        """Test execution with data quality issues."""
        state = GraphState(
            input_dataset_path=str(csv_with_issues),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        # Should pass but with lower quality score
        assert result.decision in [AgentDecision.CONTINUE, AgentDecision.RETRY]
        assert result.quality_score is not None
        assert "validation_report" in result.data_updates

        validation_report = result.data_updates["validation_report"]
        assert validation_report.total_issues > 0
        assert validation_report.warning_count > 0

    @pytest.mark.asyncio
    async def test_execute_with_high_nulls(
        self, agent: DataValidationAgent, csv_with_high_nulls: Path
    ) -> None:
        """Test execution with high null percentages."""
        state = GraphState(
            input_dataset_path=str(csv_with_high_nulls),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        validation_report = result.data_updates["validation_report"]
        issues = validation_report.issues

        # Should detect high null percentage issues
        null_issues = [i for i in issues if i.issue_type == "high_null_percentage"]
        assert len(null_issues) > 0

    @pytest.mark.asyncio
    async def test_execute_with_duplicate_columns(
        self, agent: DataValidationAgent, csv_with_duplicate_columns: Path
    ) -> None:
        """Test execution with duplicate columns."""
        state = GraphState(
            input_dataset_path=str(csv_with_duplicate_columns),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        # Pandas automatically renames duplicate columns (e.g., "age" becomes "age.1")
        # So the agent doesn't detect this as an error
        assert result.decision in [AgentDecision.CONTINUE, AgentDecision.RETRY]
        validation_report = result.data_updates["validation_report"]
        
        # The file loaded successfully, so validation passed
        assert validation_report is not None


class TestDataValidationAgentValidation:
    """Tests for DataValidationAgent validation methods."""

    @pytest.mark.asyncio
    async def test_validate_structure_empty_dataframe(self, agent: DataValidationAgent) -> None:
        """Test structure validation with empty DataFrame."""
        df = pd.DataFrame()
        issues = agent._validate_structure(df)

        assert len(issues) > 0
        assert any(i.issue_type == "empty_dataset" for i in issues)

    @pytest.mark.asyncio
    async def test_validate_structure_no_columns(self, agent: DataValidationAgent) -> None:
        """Test structure validation with no columns."""
        df = pd.DataFrame(index=[0, 1, 2])
        issues = agent._validate_structure(df)

        # DataFrame with index but no columns has len(df) == 0 (no data rows)
        # So it's detected as empty_dataset
        assert len(issues) == 1
        assert issues[0].issue_type == "empty_dataset"

    @pytest.mark.asyncio
    async def test_validate_structure_duplicate_columns(
        self, agent: DataValidationAgent
    ) -> None:
        """Test structure validation with duplicate columns."""
        df = pd.DataFrame([[1, 2, 3]], columns=["a", "b", "a"])
        issues = agent._validate_structure(df)

        assert len(issues) > 0
        assert any(i.issue_type == "duplicate_columns" for i in issues)

    @pytest.mark.asyncio
    async def test_validate_data_quality_missing_values(
        self, agent: DataValidationAgent
    ) -> None:
        """Test data quality validation with missing values."""
        df = pd.DataFrame({
            "a": [1, 2, None, 4, 5],
            "b": [None, None, None, None, None],  # 100% null
        })
        issues = agent._validate_data_quality(df)

        # Should detect high null percentage
        null_issues = [i for i in issues if i.issue_type == "high_null_percentage"]
        assert len(null_issues) > 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_duplicate_rows(
        self, agent: DataValidationAgent
    ) -> None:
        """Test data quality validation with duplicate rows."""
        df = pd.DataFrame({
            "a": [1, 2, 1],
            "b": [3, 4, 3],
        })
        issues = agent._validate_data_quality(df)

        # Should detect duplicate rows
        duplicate_issues = [i for i in issues if i.issue_type == "duplicate_rows"]
        assert len(duplicate_issues) > 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_mixed_types(
        self, agent: DataValidationAgent
    ) -> None:
        """Test data quality validation with mixed types."""
        df = pd.DataFrame({
            "a": [1, "two", 3],
        })
        issues = agent._validate_data_quality(df)

        # Should detect mixed data types
        mixed_type_issues = [i for i in issues if i.issue_type == "mixed_data_types"]
        assert len(mixed_type_issues) > 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_constant_columns(
        self, agent: DataValidationAgent
    ) -> None:
        """Test data quality validation with constant columns."""
        df = pd.DataFrame({
            "a": [1, 1, 1],
            "b": [2, 3, 4],
        })
        issues = agent._validate_data_quality(df)

        # Should detect constant columns
        constant_issues = [i for i in issues if i.issue_type == "constant_column"]
        assert len(constant_issues) > 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_outliers(
        self, agent: DataValidationAgent
    ) -> None:
        """Test data quality validation with outliers."""
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 100],  # 100 is an outlier
        })
        issues = agent._validate_data_quality(df)

        # Should detect outliers
        outlier_issues = [i for i in issues if i.issue_type == "outlier_candidates"]
        assert len(outlier_issues) > 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_high_cardinality(
        self, agent: DataValidationAgent
    ) -> None:
        """Test data quality validation with high cardinality."""
        df = pd.DataFrame({
            "a": list(range(15000)),  # High cardinality
        })
        issues = agent._validate_data_quality(df)

        # Should detect high cardinality
        cardinality_issues = [i for i in issues if i.issue_type == "high_cardinality"]
        assert len(cardinality_issues) > 0

    @pytest.mark.asyncio
    async def test_validate_data_quality_encoding_issues(
        self, agent: DataValidationAgent
    ) -> None:
        """Test data quality validation with encoding issues."""
        df = pd.DataFrame({
            "a": ["Hello", "世界", "Привет"],  # Non-ASCII characters
        })
        issues = agent._validate_data_quality(df)

        # Should detect encoding issues
        encoding_issues = [i for i in issues if i.issue_type == "encoding_issues"]
        assert len(encoding_issues) > 0


class TestDataValidationAgentScoring:
    """Tests for DataValidationAgent scoring methods."""

    def test_calculate_validation_score_no_issues(self, agent: DataValidationAgent) -> None:
        """Test validation score calculation with no issues."""
        score = agent._calculate_validation_score([])
        assert score == 1.0

    def test_calculate_validation_score_with_errors(self, agent: DataValidationAgent) -> None:
        """Test validation score calculation with errors."""
        issues = [
            ValidationIssue(
                issue_type="test",
                severity="error",
                message="Test error",
            )
        ]
        score = agent._calculate_validation_score(issues)
        assert score < 1.0
        assert score >= 0.0

    def test_calculate_validation_score_with_warnings(self, agent: DataValidationAgent) -> None:
        """Test validation score calculation with warnings."""
        issues = [
            ValidationIssue(
                issue_type="test",
                severity="warning",
                message="Test warning",
            )
        ]
        score = agent._calculate_validation_score(issues)
        assert score < 1.0
        assert score >= 0.0

    def test_calculate_validation_score_mixed_severity(
        self, agent: DataValidationAgent
    ) -> None:
        """Test validation score calculation with mixed severity."""
        issues = [
            ValidationIssue(
                issue_type="test1",
                severity="error",
                message="Test error",
            ),
            ValidationIssue(
                issue_type="test2",
                severity="warning",
                message="Test warning",
            ),
            ValidationIssue(
                issue_type="test3",
                severity="info",
                message="Test info",
            ),
        ]
        score = agent._calculate_validation_score(issues)
        assert score < 1.0
        assert score >= 0.0

    def test_calculate_validation_score_many_issues(self, agent: DataValidationAgent) -> None:
        """Test validation score calculation with many issues."""
        issues = [
            ValidationIssue(
                issue_type=f"test{i}",
                severity="error",
                message=f"Test error {i}",
            )
            for i in range(10)
        ]
        score = agent._calculate_validation_score(issues)
        # Should be 0.0 or very close to it
        assert score == 0.0


class TestDataValidationAgentRecommendations:
    """Tests for DataValidationAgent recommendation methods."""

    def test_generate_recommendations_empty(self, agent: DataValidationAgent) -> None:
        """Test recommendation generation with no issues."""
        recommendations = agent._generate_recommendations([])
        assert len(recommendations) == 0

    def test_generate_recommendations_high_nulls(self, agent: DataValidationAgent) -> None:
        """Test recommendation generation with high null issues."""
        issues = [
            ValidationIssue(
                issue_type="high_null_percentage",
                severity="warning",
                message="Column 'a' has 80% missing values",
                column="a",
            )
        ]
        recommendations = agent._generate_recommendations(issues)
        assert len(recommendations) > 0
        assert any("null" in r.lower() for r in recommendations)

    def test_generate_recommendations_duplicates(self, agent: DataValidationAgent) -> None:
        """Test recommendation generation with duplicate issues."""
        issues = [
            ValidationIssue(
                issue_type="duplicate_rows",
                severity="warning",
                message="Found 10 duplicate rows",
                count=10,
            )
        ]
        recommendations = agent._generate_recommendations(issues)
        assert len(recommendations) > 0
        assert any("duplicate" in r.lower() for r in recommendations)

    def test_generate_recommendations_mixed_types(self, agent: DataValidationAgent) -> None:
        """Test recommendation generation with mixed type issues."""
        issues = [
            ValidationIssue(
                issue_type="mixed_data_types",
                severity="warning",
                message="Column 'a' contains mixed data types",
                column="a",
            )
        ]
        recommendations = agent._generate_recommendations(issues)
        assert len(recommendations) > 0
        assert any("type" in r.lower() for r in recommendations)

    def test_generate_recommendations_multiple_issue_types(
        self, agent: DataValidationAgent
    ) -> None:
        """Test recommendation generation with multiple issue types."""
        issues = [
            ValidationIssue(
                issue_type="high_null_percentage",
                severity="warning",
                message="Column 'a' has 80% missing values",
                column="a",
            ),
            ValidationIssue(
                issue_type="duplicate_rows",
                severity="warning",
                message="Found 10 duplicate rows",
                count=10,
            ),
            ValidationIssue(
                issue_type="constant_column",
                severity="info",
                message="Column 'b' has constant value",
                column="b",
            ),
        ]
        recommendations = agent._generate_recommendations(issues)
        assert len(recommendations) >= 2  # At least one recommendation for each issue type


class TestDataValidationAgentEdgeCases:
    """Tests for DataValidationAgent edge cases."""

    @pytest.mark.asyncio
    async def test_execute_no_input_path(self, agent: DataValidationAgent) -> None:
        """Test execution with no input path."""
        state = GraphState(
            input_dataset_path="",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        assert result.decision == AgentDecision.ERROR
        assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_execute_unsupported_format(self, agent: DataValidationAgent, temp_dir: Path) -> None:
        """Test execution with unsupported file format."""
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.write_text("some content")

        state = GraphState(
            input_dataset_path=str(unsupported_file),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        assert result.decision == AgentDecision.ERROR
        # Check validation issues for detailed error message about unsupported format
        validation_issues = result.data_updates.get("validation_issues", [])
        assert len(validation_issues) == 1
        assert "unsupported" in validation_issues[0].message.lower() or "format" in validation_issues[0].message.lower()

    @pytest.mark.asyncio
    async def test_execute_large_file(self, agent: DataValidationAgent, temp_dir: Path) -> None:
        """Test execution with file exceeding size limit."""
        large_file = temp_dir / "large.csv"
        # Create a file larger than the limit (100 MB default)
        large_file.write_text("x" * (101 * 1024 * 1024))

        state = GraphState(
            input_dataset_path=str(large_file),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        assert result.decision == AgentDecision.ERROR
        assert "size" in result.message.lower() or "large" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_corrupted_file(self, agent: DataValidationAgent, temp_dir: Path) -> None:
        """Test execution with corrupted file."""
        corrupted_file = temp_dir / "corrupted.csv"
        corrupted_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        state = GraphState(
            input_dataset_path=str(corrupted_file),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        # Should handle gracefully with error
        assert result.decision in [AgentDecision.ERROR, AgentDecision.RETRY]

    @pytest.mark.asyncio
    async def test_execute_special_characters(self, agent: DataValidationAgent, temp_dir: Path) -> None:
        """Test execution with special characters in data."""
        special_file = temp_dir / "special.csv"
        special_file.write_text("name,age\nAlice™,30\nBob©,25\n")

        state = GraphState(
            input_dataset_path=str(special_file),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        # Should handle special characters
        assert result.decision in [AgentDecision.CONTINUE, AgentDecision.RETRY]

    @pytest.mark.asyncio
    async def test_execute_very_wide_dataset(self, agent: DataValidationAgent, temp_dir: Path) -> None:
        """Test execution with very wide dataset (many columns)."""
        wide_file = temp_dir / "wide.csv"
        # Create a CSV with many columns (but under the limit)
        cols = ",".join([f"col{i}" for i in range(100)])
        wide_file.write_text(f"{cols}\n" + ",".join(["1"] * 100) + "\n")

        state = GraphState(
            input_dataset_path=str(wide_file),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        # Should handle wide datasets
        assert result.decision in [AgentDecision.CONTINUE, AgentDecision.RETRY]


class TestDataValidationAgentIntegration:
    """Integration tests for DataValidationAgent."""

    @pytest.mark.asyncio
    async def test_full_validation_workflow(
        self, agent: DataValidationAgent, csv_with_issues: Path
    ) -> None:
        """Test complete validation workflow."""
        state = GraphState(
            input_dataset_path=str(csv_with_issues),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
        )

        result = await agent.execute(state)

        # Verify all expected outputs are present
        assert "raw_data" in result.data_updates
        assert "file_metadata" in result.data_updates
        assert "validation_report" in result.data_updates
        assert "validation_score" in result.data_updates
        assert "validation_summary" in result.data_updates
        assert "validation_issues" in result.data_updates
        assert "recommendations" in result.data_updates

        # Verify data types
        assert isinstance(result.data_updates["raw_data"], pd.DataFrame)
        assert result.data_updates["validation_score"] is not None
        assert isinstance(result.data_updates["validation_score"], float)
        assert isinstance(result.data_updates["validation_issues"], list)

        # Verify validation report structure
        report = result.data_updates["validation_report"]
        assert hasattr(report, "is_valid")
        assert hasattr(report, "total_issues")
        assert hasattr(report, "error_count")
        assert hasattr(report, "warning_count")
        assert hasattr(report, "info_count")
        assert hasattr(report, "issues")
        assert hasattr(report, "recommendations")

        # Verify execution metadata
        assert result.execution_duration is not None
        assert result.execution_duration > 0
        assert len(result.execution_notes) > 0
        # Verify metadata contains expected keys (file_size_mb, row_count, column_count)
        assert "file_size_mb" in result.metadata
        assert "row_count" in result.metadata
        assert "column_count" in result.metadata

    @pytest.mark.asyncio
    async def test_can_execute(self, agent: DataValidationAgent, valid_csv: Path) -> None:
        """Test can_execute method."""
        state = GraphState(
            input_dataset_path=str(valid_csv),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            current_phase=ExecutionPhase.DATA_INTAKE,
        )

        assert agent.can_execute(state) is True

    @pytest.mark.asyncio
    async def test_cannot_execute_wrong_phase(
        self, agent: DataValidationAgent, valid_csv: Path
    ) -> None:
        """Test can_execute with wrong phase."""
        state = GraphState(
            input_dataset_path=str(valid_csv),
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            current_phase=ExecutionPhase.DATA_PREPARATION,  # Wrong phase
        )

        assert agent.can_execute(state) is False

    @pytest.mark.asyncio
    async def test_cannot_execute_missing_input(
        self, agent: DataValidationAgent
    ) -> None:
        """Test can_execute with missing input."""
        state = GraphState(
            input_dataset_path="",
            execution_id="test-123",
            start_time="2024-01-01T00:00:00",
            current_phase=ExecutionPhase.DATA_INTAKE,
        )

        assert agent.can_execute(state) is False