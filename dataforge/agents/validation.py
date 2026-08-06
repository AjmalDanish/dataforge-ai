"""DataValidationAgent — The Gatekeeper.

First line of defense. Validates the input file before any processing.
Detects and reports data quality issues without modifying data.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from dataforge.core.models import (
    ExecutionPhase,
    FailurePolicy,
    FileMetadata,
    RetryPolicy,
    ValidationIssue,
    ValidationReport,
)
from dataforge.core.state import GraphState
from dataforge.infrastructure.readers import CSVReader, ExcelReader, JSONReader, ParquetReader
from dataforge.shared.container import DIContainer
from dataforge.shared.errors import DataIngestionError

from .base import Agent, AgentDecision, AgentResult


class DataValidationAgent(Agent):
    """Validates input dataset and detects data quality issues.

    Responsibilities:
    - Validate file exists, is readable, and has a supported extension
    - Detect file format (CSV, Excel, Parquet, JSON)
    - Load data with encoding fallback
    - Validate structure: non-empty, has columns, consistent row lengths
    - Detect data quality issues: missing values, duplicates, mixed types, etc.
    - Produce validation report with recommendations

    Phase: 1 — Data Intake
    Inputs: input_dataset_path
    Outputs: raw_data, file_metadata, validation_report
    """

    # Agent properties
    phase: ExecutionPhase = ExecutionPhase.DATA_INTAKE
    required_inputs: list[str] = []  # input_dataset_path is a direct GraphState field, not in state.data
    produced_outputs: list[str] = ["raw_data", "file_metadata", "validation_report"]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=1)
    failure_policy: FailurePolicy = FailurePolicy.HALT
    timeout_seconds: int = 30

    # Validation thresholds (not Pydantic fields - just configuration)
    max_file_size_mb: float = 100.0
    max_rows: int = 1_000_000
    max_columns: int = 1000
    null_threshold: float = 0.5
    duplicate_threshold: float = 0.1
    high_cardinality_threshold: int = 10000

    def __init__(
        self,
        llm_provider=None,
        logger=None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
        container: DIContainer | None = None,
    ):
        """Initialize DataValidationAgent.

        Args:
            llm_provider: LLM provider instance (not used by this agent).
            logger: Structured logger instance.
            retry_policy: Retry policy override.
            failure_policy: Failure policy override.
            timeout_seconds: Timeout override in seconds.
            container: DI container for resolving readers.
        """
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)
        self.container = container or DIContainer()

    def can_execute(self, state: GraphState) -> bool:
        """Check if this agent can execute on the current state.

        Overrides base can_execute to check for input_dataset_path presence.

        Args:
            state: Current graph state.

        Returns:
            True if agent can execute.
        """
        # Check phase compatibility
        if state.current_phase != self.phase:
            return False

        # Check that input_dataset_path is provided and not empty
        if not state.input_dataset_path or not state.input_dataset_path.strip():
            return False

        # Check retry limit
        visit_count = state.get_agent_visit_count(self.name)
        if visit_count > self.retry_policy.max_retries:
            return False

        return True

    async def execute(self, state: GraphState) -> AgentResult:
        """Execute validation logic.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with validation results.
        """
        start_time = datetime.now()
        issues: list[ValidationIssue] = []
        recommendations: list[str] = []

        # Get input path
        input_path = state.input_dataset_path
        if not input_path:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No input dataset path provided",
                quality_score=0.0,
            )

        path = Path(input_path)

        # Validate file exists and is readable
        if not path.exists():
            issues.append(
                ValidationIssue(
                    issue_type="file_not_found",
                    severity="error",
                    message=f"File not found: {input_path}",
                    suggestion="Check the file path and try again",
                )
            )
            return self._create_error_result("File not found", issues)

        if not path.is_file():
            issues.append(
                ValidationIssue(
                    issue_type="not_a_file",
                    severity="error",
                    message=f"Path is not a file: {input_path}",
                    suggestion="Provide a valid file path",
                )
            )
            return self._create_error_result("Not a file", issues)

        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            issues.append(
                ValidationIssue(
                    issue_type="file_too_large",
                    severity="error",
                    message=f"File size ({file_size_mb:.2f} MB) exceeds maximum ({self.max_file_size_mb} MB)",
                    suggestion=f"Reduce file size or increase max_file_size_mb threshold",
                )
            )
            return self._create_error_result("File too large", issues)

        # Load data using appropriate reader
        try:
            df, file_metadata = await self._load_data(path)
        except DataIngestionError as e:
            issues.append(
                ValidationIssue(
                    issue_type="load_error",
                    severity="error",
                    message=f"Failed to load file: {str(e)}",
                    suggestion="Check file format and encoding",
                )
            )
            return self._create_error_result("Failed to load file", issues)
        except Exception as e:
            issues.append(
                ValidationIssue(
                    issue_type="unexpected_error",
                    severity="error",
                    message=f"Unexpected error loading file: {str(e)}",
                    suggestion="Contact support",
                )
            )
            return self._create_error_result("Unexpected error", issues)

        # Validate structure
        issues.extend(self._validate_structure(df))

        # Validate data quality
        issues.extend(self._validate_data_quality(df))

        # Calculate validation score
        validation_score = self._calculate_validation_score(issues)

        # Generate recommendations
        recommendations = self._generate_recommendations(issues)

        # Create validation report
        validation_report = ValidationReport(
            is_valid=validation_score >= 0.7,
            total_issues=len(issues),
            error_count=sum(1 for i in issues if i.severity == "error"),
            warning_count=sum(1 for i in issues if i.severity == "warning"),
            info_count=sum(1 for i in issues if i.severity == "info"),
            issues=issues,
            columns_affected=list(set(i.column for i in issues if i.column)),
            recommendations=recommendations,
            generated_at=datetime.now().isoformat(),
        )

        # Calculate execution duration
        execution_duration = (datetime.now() - start_time).total_seconds()

        # Create data updates
        data_updates = {
            "raw_data": df,
            "file_metadata": file_metadata,
            "validation_report": validation_report,
            "validation_score": validation_score,
            "validation_summary": self._generate_summary(validation_report),
            "validation_issues": issues,
            "recommendations": recommendations,
        }

        # Determine decision
        if validation_report.error_count > 0:
            decision = AgentDecision.ERROR
            message = f"Validation failed with {validation_report.error_count} error(s)"
        elif validation_score < 0.5:
            decision = AgentDecision.RETRY
            message = f"Validation passed with low quality score ({validation_score:.2f})"
        else:
            decision = AgentDecision.CONTINUE
            message = f"Validation passed successfully (score: {validation_score:.2f})"

        return AgentResult(
            decision=decision,
            message=message,
            data_updates=data_updates,
            metadata={
                "file_size_mb": file_size_mb,
                "row_count": len(df),
                "column_count": len(df.columns),
            },
            quality_score=validation_score,
            execution_duration=execution_duration,
            execution_notes=[f"Found {len(issues)} validation issue(s)"],
            metrics={
                "validation_score": validation_score,
                "error_count": validation_report.error_count,
                "warning_count": validation_report.warning_count,
                "info_count": validation_report.info_count,
            },
        )

    async def _load_data(self, path: Path) -> tuple[pd.DataFrame, FileMetadata]:
        """Load data using appropriate reader.

        Args:
            path: Path to the file.

        Returns:
            Tuple of (DataFrame, FileMetadata).

        Raises:
            DataIngestionError: If file cannot be loaded.
        """
        # Determine file extension
        suffix = path.suffix.lower()

        # Select appropriate reader
        if suffix == ".csv":
            reader = CSVReader()
        elif suffix in [".xlsx", ".xls"]:
            reader = ExcelReader()
        elif suffix == ".parquet":
            reader = ParquetReader()
        elif suffix in [".json", ".jsonl", ".ndjson"]:
            reader = JSONReader()
        else:
            raise DataIngestionError(
                f"Unsupported file format: {suffix}",
                details={"supported_formats": [".csv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson"]},
            )

        # Load data
        df, metadata = await reader.read(path)

        # Enforce limits
        if len(df) > self.max_rows:
            raise DataIngestionError(
                f"Row count ({len(df)}) exceeds maximum ({self.max_rows})",
                details={"row_count": len(df), "max_rows": self.max_rows},
            )

        if len(df.columns) > self.max_columns:
            raise DataIngestionError(
                f"Column count ({len(df.columns)}) exceeds maximum ({self.max_columns})",
                details={"column_count": len(df.columns), "max_columns": self.max_columns},
            )

        return df, metadata

    def _validate_structure(self, df: pd.DataFrame) -> list[ValidationIssue]:
        """Validate DataFrame structure.

        Args:
            df: DataFrame to validate.

        Returns:
            List of validation issues.
        """
        issues: list[ValidationIssue] = []

        # Check if empty
        if df.empty:
            issues.append(
                ValidationIssue(
                    issue_type="empty_dataset",
                    severity="error",
                    message="Dataset is empty",
                    suggestion="Provide a non-empty dataset",
                )
            )
            return issues

        # Check if has columns
        if len(df.columns) == 0:
            issues.append(
                ValidationIssue(
                    issue_type="no_columns",
                    severity="error",
                    message="Dataset has no columns",
                    suggestion="Provide a dataset with columns",
                )
            )
            return issues

        # Check for duplicate columns
        duplicate_cols = df.columns[df.columns.duplicated()].tolist()
        if duplicate_cols:
            issues.append(
                ValidationIssue(
                    issue_type="duplicate_columns",
                    severity="error",
                    message=f"Found duplicate columns: {', '.join(duplicate_cols)}",
                    suggestion="Remove duplicate columns from the dataset",
                    column=duplicate_cols[0],
                    count=len(duplicate_cols),
                )
            )

        return issues

    def _validate_data_quality(self, df: pd.DataFrame) -> list[ValidationIssue]:
        """Validate data quality.

        Args:
            df: DataFrame to validate.

        Returns:
            List of validation issues.
        """
        issues: list[ValidationIssue] = []

        # Check for missing values
        null_percentages = (df.isnull().sum() / len(df)) * 100
        high_null_cols = null_percentages[null_percentages > self.null_threshold * 100]
        for col, pct in high_null_cols.items():
            issues.append(
                ValidationIssue(
                    issue_type="high_null_percentage",
                    severity="warning",
                    message=f"Column '{col}' has {pct:.1f}% missing values",
                    suggestion=f"Consider imputing or removing column '{col}'",
                    column=str(col),
                    count=int(df[col].isnull().sum()),
                )
            )

        # Check for duplicate rows
        duplicate_count = df.duplicated().sum()
        duplicate_percentage = (duplicate_count / len(df)) * 100
        if duplicate_percentage > self.duplicate_threshold * 100:
            issues.append(
                ValidationIssue(
                    issue_type="duplicate_rows",
                    severity="warning",
                    message=f"Found {duplicate_count} duplicate rows ({duplicate_percentage:.1f}%)",
                    suggestion="Remove duplicate rows from the dataset",
                    count=duplicate_count,
                )
            )

        # Check for mixed data types
        for col in df.columns:
            if df[col].dtype == "object":
                # Check if column contains mixed types
                sample_types = set(type(x).__name__ for x in df[col].dropna().head(100))
                if len(sample_types) > 1:
                    issues.append(
                        ValidationIssue(
                            issue_type="mixed_data_types",
                            severity="warning",
                            message=f"Column '{col}' contains mixed data types: {', '.join(sample_types)}",
                            suggestion=f"Standardize data types in column '{col}'",
                            column=col,
                        )
                    )

        # Check for invalid dates
        for col in df.columns:
            if df[col].dtype == "object":
                # Try to parse as datetime
                try:
                    pd.to_datetime(df[col], errors="coerce")
                    # Check if any values failed to parse
                    invalid_count = pd.to_datetime(df[col], errors="coerce").isnull().sum()
                    if invalid_count > 0 and invalid_count < len(df):
                        issues.append(
                            ValidationIssue(
                                issue_type="invalid_dates",
                                severity="warning",
                                message=f"Column '{col}' contains {invalid_count} invalid date values",
                                suggestion=f"Review date format in column '{col}'",
                                column=col,
                                count=invalid_count,
                            )
                        )
                except Exception:
                    pass

        # Check for invalid numeric values
        for col in df.columns:
            if df[col].dtype == "object":
                # Try to convert to numeric
                try:
                    numeric_values = pd.to_numeric(df[col], errors="coerce")
                    # Check if any values failed to convert
                    invalid_count = numeric_values.isnull().sum() - df[col].isnull().sum()
                    if invalid_count > 0:
                        issues.append(
                            ValidationIssue(
                                issue_type="invalid_numeric_values",
                                severity="warning",
                                message=f"Column '{col}' contains {invalid_count} invalid numeric values",
                                suggestion=f"Review numeric format in column '{col}'",
                                column=col,
                                count=invalid_count,
                            )
                        )
                except Exception:
                    pass

        # Check for constant columns
        for col in df.columns:
            if df[col].nunique() == 1:
                issues.append(
                    ValidationIssue(
                        issue_type="constant_column",
                        severity="info",
                        message=f"Column '{col}' has constant value",
                        suggestion=f"Consider removing constant column '{col}'",
                        column=col,
                    )
                )

        # Check for high cardinality columns
        for col in df.columns:
            if df[col].nunique() > self.high_cardinality_threshold:
                issues.append(
                    ValidationIssue(
                        issue_type="high_cardinality",
                        severity="info",
                        message=f"Column '{col}' has high cardinality ({df[col].nunique()} unique values)",
                        suggestion=f"Consider if column '{col}' is needed for analysis",
                        column=col,
                    )
                )

        # Check for outlier candidates (numeric columns only)
        for col in df.select_dtypes(include="number").columns:
            if df[col].notna().sum() > 0:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
                if outliers > 0:
                    issues.append(
                        ValidationIssue(
                            issue_type="outlier_candidates",
                            severity="info",
                            message=f"Column '{col}' has {outliers} potential outlier(s)",
                            suggestion=f"Review outliers in column '{col}'",
                            column=col,
                            count=outliers,
                        )
                    )

        # Check for encoding issues (string columns only)
        for col in df.select_dtypes(include="object").columns:
            # Check for non-ASCII characters
            non_ascii_count = df[col].astype(str).str.contains(r"[^\x00-\x7F]").sum()
            if non_ascii_count > 0:
                issues.append(
                    ValidationIssue(
                        issue_type="encoding_issues",
                        severity="info",
                        message=f"Column '{col}' contains {non_ascii_count} non-ASCII character(s)",
                        suggestion=f"Review encoding in column '{col}'",
                        column=col,
                        count=non_ascii_count,
                    )
                )

        return issues

    def _calculate_validation_score(self, issues: list[ValidationIssue]) -> float:
        """Calculate validation score based on issues.

        Args:
            issues: List of validation issues.

        Returns:
            Validation score (0.0-1.0).
        """
        if not issues:
            return 1.0

        # Weight issues by severity
        error_weight = 0.3
        warning_weight = 0.1
        info_weight = 0.05

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")

        # Calculate score (start from 1.0 and subtract based on issues)
        score = 1.0
        score -= error_count * error_weight
        score -= warning_count * warning_weight
        score -= info_count * info_weight

        # Ensure score is in valid range
        return max(0.0, min(1.0, score))

    def _generate_recommendations(self, issues: list[ValidationIssue]) -> list[str]:
        """Generate recommendations based on issues.

        Args:
            issues: List of validation issues.

        Returns:
            List of recommendations.
        """
        recommendations = []

        # Group issues by type
        issue_types = {}
        for issue in issues:
            if issue.issue_type not in issue_types:
                issue_types[issue.issue_type] = []
            issue_types[issue.issue_type].append(issue)

        # Generate recommendations for each issue type
        if "high_null_percentage" in issue_types:
            cols = [i.column for i in issue_types["high_null_percentage"]]
            recommendations.append(
                f"Consider imputing or removing columns with high null percentages: {', '.join(cols)}"
            )

        if "duplicate_rows" in issue_types:
            count = issue_types["duplicate_rows"][0].count
            recommendations.append(f"Remove {count} duplicate row(s) from the dataset")

        if "mixed_data_types" in issue_types:
            cols = [i.column for i in issue_types["mixed_data_types"]]
            recommendations.append(
                f"Standardize data types in columns with mixed types: {', '.join(cols)}"
            )

        if "invalid_dates" in issue_types:
            cols = [i.column for i in issue_types["invalid_dates"]]
            recommendations.append(
                f"Review and fix date format in columns: {', '.join(cols)}"
            )

        if "invalid_numeric_values" in issue_types:
            cols = [i.column for i in issue_types["invalid_numeric_values"]]
            recommendations.append(
                f"Review and fix numeric format in columns: {', '.join(cols)}"
            )

        if "constant_column" in issue_types:
            cols = [i.column for i in issue_types["constant_column"]]
            recommendations.append(
                f"Consider removing constant columns: {', '.join(cols)}"
            )

        return recommendations

    def _generate_summary(self, report: ValidationReport) -> str:
        """Generate validation summary.

        Args:
            report: Validation report.

        Returns:
            Summary string.
        """
        if report.is_valid:
            return f"Validation passed: {report.total_issues} issue(s) found ({report.error_count} errors, {report.warning_count} warnings, {report.info_count} info)"
        else:
            return f"Validation failed: {report.total_issues} issue(s) found ({report.error_count} errors, {report.warning_count} warnings, {report.info_count} info)"

    def _create_error_result(self, message: str, issues: list[ValidationIssue]) -> AgentResult:
        """Create error result.

        Args:
            message: Error message.
            issues: Validation issues.

        Returns:
            AgentResult with ERROR decision.
        """
        return AgentResult(
            decision=AgentDecision.ERROR,
            message=message,
            quality_score=0.0,
            data_updates={
                "validation_report": ValidationReport(
                    is_valid=False,
                    total_issues=len(issues),
                    error_count=sum(1 for i in issues if i.severity == "error"),
                    warning_count=sum(1 for i in issues if i.severity == "warning"),
                    info_count=sum(1 for i in issues if i.severity == "info"),
                    issues=issues,
                    columns_affected=list(set(i.column for i in issues if i.column)),
                    recommendations=[],
                    generated_at=datetime.now().isoformat(),
                ),
                "validation_score": 0.0,
                "validation_summary": f"Validation failed: {message}",
                "validation_issues": issues,
                "recommendations": [],
            },
        )