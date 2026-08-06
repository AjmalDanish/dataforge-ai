"""DataCleaningAgent — The Janitor.

Automatically detect and fix data quality issues.
Every decision is explained and logged.
"""

import hashlib
import re
from datetime import datetime
from typing import Any

import pandas as pd
import numpy as np

from dataforge.core.models import (
    CleaningRule,
    ExecutionPhase,
    FailurePolicy,
    RetryPolicy,
)
from dataforge.core.state import GraphState

from .base import Agent, AgentDecision, AgentResult


class DataCleaningAgent(Agent):
    """Cleans validated datasets and produces complete audit trail.

    Responsibilities:
    - Handle missing values (drop column >70%, impute, flag)
    - Remove duplicate rows
    - Handle duplicate columns
    - Normalize data types
    - Normalize dates
    - Trim strings
    - Clean whitespace
    - Normalize case
    - Handle invalid numeric values
    - Treat outliers (configurable)
    - Handle invalid categories
    - Remove empty columns
    - Remove constant columns (configurable)

    Phase: 2 — Data Preparation
    Inputs: raw_data
    Outputs: cleaned_data, cleaning_report, cleaning_rules_applied, rows_removed,
             columns_removed, missing_values_fixed, duplicates_removed,
             cleaning_summary, cleaning_confidence, original_data_checksum,
             cleaned_data_checksum
    """

    # Agent properties
    phase: ExecutionPhase = ExecutionPhase.DATA_PREPARATION
    required_inputs: list[str] = ["raw_data"]
    produced_outputs: list[str] = [
        "cleaned_data",
        "cleaning_report",
        "cleaning_rules_applied",
        "rows_removed",
        "columns_removed",
        "missing_values_fixed",
        "duplicates_removed",
        "cleaning_summary",
        "cleaning_confidence",
        "original_data_checksum",
        "cleaned_data_checksum",
    ]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=2)
    failure_policy: FailurePolicy = FailurePolicy.HALT
    timeout_seconds: int = 60

    # Cleaning thresholds (not Pydantic fields - just configuration)
    missing_value_threshold: float = 0.7  # Drop column if >70% missing
    outlier_iqr_multiplier: float = 1.5  # IQR multiplier for outlier detection
    constant_column_threshold: float = 0.95  # Drop column if >95% same value

    def __init__(
        self,
        llm_provider=None,
        logger=None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize DataCleaningAgent.

        Args:
            llm_provider: LLM provider instance (not used by this agent).
            logger: Structured logger instance.
            retry_policy: Retry policy override.
            failure_policy: Failure policy override.
            timeout_seconds: Timeout override in seconds.
        """
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)

    async def execute(self, state: GraphState) -> AgentResult:
        """Execute cleaning logic.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with cleaning results.
        """
        start_time = datetime.now()
        cleaning_rules: list[CleaningRule] = []

        # Get raw data from state
        raw_data = state.data.get("raw_data")
        if raw_data is None:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No raw_data found in state",
                quality_score=0.0,
            )

        # Create a copy to avoid modifying original
        df = raw_data.copy()

        # Calculate original checksum
        original_checksum = self._calculate_dataframe_checksum(raw_data)

        # Track metrics
        original_rows = len(df)
        original_columns = len(df.columns)
        rows_removed = 0
        columns_removed = 0
        missing_values_fixed = 0
        duplicates_removed = 0

        # 1. Handle duplicate columns
        df, dup_col_rules = self._handle_duplicate_columns(df)
        cleaning_rules.extend(dup_col_rules)
        columns_removed += len([r for r in dup_col_rules if r.action == "drop"])

        # 2. Handle empty columns
        df, empty_col_rules = self._handle_empty_columns(df)
        cleaning_rules.extend(empty_col_rules)
        columns_removed += len([r for r in empty_col_rules if r.action == "drop"])

        # 3. Handle constant columns
        df, const_col_rules = self._handle_constant_columns(df)
        cleaning_rules.extend(const_col_rules)
        columns_removed += len([r for r in const_col_rules if r.action == "drop"])

        # 4. Handle duplicate rows
        df, dup_row_rules = self._handle_duplicate_rows(df)
        cleaning_rules.extend(dup_row_rules)
        duplicates_removed = len([r for r in dup_row_rules if r.action == "drop"])
        rows_removed += duplicates_removed

        # 5. Handle missing values
        df, missing_rules = self._handle_missing_values(df)
        cleaning_rules.extend(missing_rules)
        missing_values_fixed = sum(r.affected_rows for r in missing_rules)

        # 6. Normalize data types
        df, type_rules = self._normalize_data_types(df)
        cleaning_rules.extend(type_rules)

        # 7. Normalize dates
        df, date_rules = self._normalize_dates(df)
        cleaning_rules.extend(date_rules)

        # 8. Handle invalid numeric values
        df, numeric_rules = self._handle_invalid_numeric(df)
        cleaning_rules.extend(numeric_rules)

        # 9. Trim strings and clean whitespace
        df, string_rules = self._clean_strings(df)
        cleaning_rules.extend(string_rules)

        # 10. Normalize case for string columns
        df, case_rules = self._normalize_case(df)
        cleaning_rules.extend(case_rules)

        # 11. Handle outliers (flag only, don't remove)
        df, outlier_rules = self._handle_outliers(df)
        cleaning_rules.extend(outlier_rules)

        # 12. Handle invalid categories
        df, category_rules = self._handle_invalid_categories(df)
        cleaning_rules.extend(category_rules)

        # Calculate cleaned checksum
        cleaned_checksum = self._calculate_dataframe_checksum(df)

        # Calculate cleaning confidence
        cleaning_confidence = self._calculate_cleaning_confidence(
            cleaning_rules, original_rows, original_columns
        )

        # Calculate final metrics
        final_rows = len(df)
        final_columns = len(df.columns)

        # Create cleaning summary
        cleaning_summary = (
            f"Cleaned dataset from {original_rows}x{original_columns} to "
            f"{final_rows}x{final_columns}. Removed {rows_removed} rows, "
            f"{columns_removed} columns. Fixed {missing_values_fixed} missing values, "
            f"{duplicates_removed} duplicates. Applied {len(cleaning_rules)} rules."
        )

        # Create cleaning report
        cleaning_report = {
            "total_issues_found": len(cleaning_rules),
            "total_issues_fixed": len([r for r in cleaning_rules if r.action != "flag"]),
            "rows_before": original_rows,
            "rows_after": final_rows,
            "columns_before": original_columns,
            "columns_after": final_columns,
            "decisions": [
                {
                    "issue": r.reason,
                    "action": r.action,
                    "rationale": r.reason,
                    "rows_affected": r.affected_rows,
                    "column": r.column,
                }
                for r in cleaning_rules
            ],
        }

        execution_duration = (datetime.now() - start_time).total_seconds()

        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=cleaning_summary,
            quality_score=cleaning_confidence,
            data_updates={
                "cleaned_data": df,
                "cleaning_report": cleaning_report,
                "cleaning_rules_applied": cleaning_rules,
                "rows_removed": rows_removed,
                "columns_removed": columns_removed,
                "missing_values_fixed": missing_values_fixed,
                "duplicates_removed": duplicates_removed,
                "cleaning_summary": cleaning_summary,
                "cleaning_confidence": cleaning_confidence,
                "original_data_checksum": original_checksum,
                "cleaned_data_checksum": cleaned_checksum,
            },
            execution_duration=execution_duration,
            execution_notes=[f"Applied {len(cleaning_rules)} cleaning rules"],
        )

    def _calculate_dataframe_checksum(self, df: pd.DataFrame) -> str:
        """Calculate MD5 checksum of DataFrame.

        Args:
            df: DataFrame to calculate checksum for.

        Returns:
            MD5 checksum as hex string.
        """
        # Sort columns to ensure consistent checksum
        df_sorted = df[sorted(df.columns)].copy()
        # Convert to string and hash
        df_str = df_sorted.to_string().encode("utf-8")
        return hashlib.md5(df_str).hexdigest()

    def _handle_duplicate_columns(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Handle duplicate columns.

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        # Find duplicate columns (same values)
        duplicate_cols = set()
        for i, col1 in enumerate(df_clean.columns):
            for col2 in df_clean.columns[i + 1 :]:
                if df_clean[col1].equals(df_clean[col2]):
                    duplicate_cols.add(col2)

        # Remove duplicate columns (keep first occurrence)
        for col in duplicate_cols:
            rules.append(
                CleaningRule(
                    rule_type="duplicate_column",
                    column=col,
                    action="drop",
                    reason=f"Column '{col}' is a duplicate of another column",
                    affected_rows=len(df_clean),
                    before_value=f"Column exists with {len(df_clean)} rows",
                    after_value="Column removed",
                )
            )
            df_clean = df_clean.drop(columns=[col])

        return df_clean, rules

    def _handle_empty_columns(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Handle empty columns (all NaN/None).

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        # Find empty columns
        empty_cols = df_clean.columns[df_clean.isnull().all()].tolist()

        # Remove empty columns
        for col in empty_cols:
            rules.append(
                CleaningRule(
                    rule_type="empty_column",
                    column=col,
                    action="drop",
                    reason=f"Column '{col}' is entirely empty (all NaN/None)",
                    affected_rows=len(df_clean),
                    before_value=f"Column with {len(df_clean)} null values",
                    after_value="Column removed",
                )
            )
            df_clean = df_clean.drop(columns=[col])

        return df_clean, rules

    def _handle_constant_columns(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Handle constant columns (same value in >95% of rows).

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        # Find constant columns
        for col in df_clean.columns:
            # Get value counts
            value_counts = df_clean[col].value_counts(dropna=False)
            if len(value_counts) > 0:
                most_common_ratio = value_counts.iloc[0] / len(df_clean)
                if most_common_ratio >= self.constant_column_threshold:
                    rules.append(
                        CleaningRule(
                            rule_type="constant_column",
                            column=col,
                            action="drop",
                            reason=f"Column '{col}' has {most_common_ratio:.1%} same value (>{self.constant_column_threshold:.0%} threshold)",
                            affected_rows=len(df_clean),
                            before_value=f"Most common value: {value_counts.index[0]}",
                            after_value="Column removed",
                        )
                    )
                    df_clean = df_clean.drop(columns=[col])

        return df_clean, rules

    def _handle_duplicate_rows(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Handle duplicate rows.

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        # Find duplicate rows
        duplicates = df_clean.duplicated()
        duplicate_count = duplicates.sum()

        if duplicate_count > 0:
            rules.append(
                CleaningRule(
                    rule_type="duplicate_rows",
                    column=None,
                    action="drop",
                    reason=f"Found {duplicate_count} duplicate rows ({duplicate_count/len(df_clean):.1%})",
                    affected_rows=duplicate_count,
                    before_value=f"{len(df_clean)} rows with {duplicate_count} duplicates",
                    after_value=f"{len(df_clean) - duplicate_count} unique rows",
                )
            )
            df_clean = df_clean.drop_duplicates()

        return df_clean, rules

    def _handle_missing_values(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Handle missing values.

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        # Check each column for missing values
        for col in df_clean.columns:
            missing_count = df_clean[col].isnull().sum()
            if missing_count == 0:
                continue

            missing_ratio = missing_count / len(df_clean)

            # If >70% missing, drop the column
            if missing_ratio > self.missing_value_threshold:
                rules.append(
                    CleaningRule(
                        rule_type="missing_values",
                        column=col,
                        action="drop",
                        reason=f"Column '{col}' has {missing_ratio:.1%} missing values (>{self.missing_value_threshold:.0%} threshold)",
                        affected_rows=len(df_clean),
                        before_value=f"{missing_count} missing values ({missing_ratio:.1%})",
                        after_value="Column removed",
                    )
                )
                df_clean = df_clean.drop(columns=[col])
            else:
                # Impute missing values
                if pd.api.types.is_numeric_dtype(df_clean[col]):
                    # Use median for numeric columns
                    median_val = df_clean[col].median()
                    if pd.notna(median_val):
                        df_clean[col] = df_clean[col].fillna(median_val)
                        rules.append(
                            CleaningRule(
                                rule_type="missing_values",
                                column=col,
                                action="impute",
                                reason=f"Imputed {missing_count} missing values with median ({median_val})",
                                affected_rows=missing_count,
                                before_value=f"{missing_count} missing values ({missing_ratio:.1%})",
                                after_value=f"Filled with median: {median_val}",
                            )
                        )
                else:
                    # Use mode for categorical/string columns
                    mode_val = df_clean[col].mode()
                    if len(mode_val) > 0:
                        mode_val = mode_val[0]
                        df_clean[col] = df_clean[col].fillna(mode_val)
                        rules.append(
                            CleaningRule(
                                rule_type="missing_values",
                                column=col,
                                action="impute",
                                reason=f"Imputed {missing_count} missing values with mode ('{mode_val}')",
                                affected_rows=missing_count,
                                before_value=f"{missing_count} missing values ({missing_ratio:.1%})",
                                after_value=f"Filled with mode: '{mode_val}'",
                            )
                        )

        return df_clean, rules

    def _normalize_data_types(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Normalize data types.

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        for col in df_clean.columns:
            original_dtype = str(df_clean[col].dtype)

            # Try to convert object/string columns to numeric if possible
            if pd.api.types.is_object_dtype(df_clean[col]) or pd.api.types.is_string_dtype(df_clean[col]):
                # Try numeric conversion
                try:
                    numeric_col = pd.to_numeric(df_clean[col], errors="coerce")
                    if not numeric_col.isnull().all():
                        df_clean[col] = numeric_col
                        new_dtype = str(df_clean[col].dtype)
                        if new_dtype != original_dtype:
                            rules.append(
                                CleaningRule(
                                    rule_type="type_normalization",
                                    column=col,
                                    action="cast",
                                    reason=f"Converted column '{col}' from {original_dtype} to {new_dtype}",
                                    affected_rows=len(df_clean),
                                    before_value=original_dtype,
                                    after_value=new_dtype,
                                )
                            )
                except Exception:
                    pass

        return df_clean, rules

    def _normalize_dates(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Normalize date columns.

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        for col in df_clean.columns:
            # Try to convert to datetime
            if pd.api.types.is_object_dtype(df_clean[col]) or pd.api.types.is_string_dtype(df_clean[col]):
                try:
                    # Try datetime conversion
                    date_col = pd.to_datetime(df_clean[col], errors="coerce")
                    # Check if conversion was successful (not all NaT)
                    if not date_col.isnull().all():
                        df_clean[col] = date_col
                        rules.append(
                            CleaningRule(
                                rule_type="date_normalization",
                                column=col,
                                action="cast",
                                reason=f"Converted column '{col}' to datetime",
                                affected_rows=len(df_clean),
                                before_value="object",
                                after_value="datetime64[ns]",
                            )
                        )
                except Exception:
                    pass

        return df_clean, rules

    def _handle_invalid_numeric(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Handle invalid numeric values (inf, -inf).

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        for col in df_clean.columns:
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                # Check for inf values
                inf_count = np.isinf(df_clean[col]).sum()
                if inf_count > 0:
                    # Replace inf with NaN
                    df_clean[col] = df_clean[col].replace([np.inf, -np.inf], np.nan)
                    rules.append(
                        CleaningRule(
                            rule_type="invalid_numeric",
                            column=col,
                            action="flag",
                            reason=f"Found {inf_count} infinite values in column '{col}', replaced with NaN",
                            affected_rows=inf_count,
                            before_value=f"{inf_count} inf/-inf values",
                            after_value="Replaced with NaN",
                        )
                    )

        return df_clean, rules

    def _clean_strings(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Clean strings (trim whitespace).

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        for col in df_clean.columns:
            if pd.api.types.is_object_dtype(df_clean[col]) or pd.api.types.is_string_dtype(df_clean[col]):
                # Check if column contains strings
                if df_clean[col].apply(lambda x: isinstance(x, str)).any():
                    original_values = df_clean[col].copy()
                    # Strip leading/trailing whitespace
                    df_clean[col] = df_clean[col].apply(
                        lambda x: x.strip() if isinstance(x, str) else x
                    )
                    # Check if any values changed
                    if not df_clean[col].equals(original_values):
                        changed_count = (
                            (df_clean[col] != original_values).sum()
                            if df_clean[col].dtype == original_values.dtype
                            else 0
                        )
                        if changed_count > 0:
                            rules.append(
                                CleaningRule(
                                    rule_type="string_cleaning",
                                    column=col,
                                    action="trim",
                                    reason=f"Trimmed whitespace from {changed_count} values in column '{col}'",
                                    affected_rows=changed_count,
                                    before_value="Values with leading/trailing whitespace",
                                    after_value="Trimmed values",
                                )
                            )

        return df_clean, rules

    def _normalize_case(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Normalize case for string columns (lowercase).

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        for col in df_clean.columns:
            if pd.api.types.is_object_dtype(df_clean[col]) or pd.api.types.is_string_dtype(df_clean[col]):
                # Check if column contains strings with mixed case
                if df_clean[col].apply(lambda x: isinstance(x, str)).any():
                    # Convert to lowercase
                    original_values = df_clean[col].copy()
                    df_clean[col] = df_clean[col].apply(
                        lambda x: x.lower() if isinstance(x, str) else x
                    )
                    # Check if any values changed
                    if not df_clean[col].equals(original_values):
                        changed_count = (
                            (df_clean[col] != original_values).sum()
                            if df_clean[col].dtype == original_values.dtype
                            else 0
                        )
                        if changed_count > 0:
                            rules.append(
                                CleaningRule(
                                    rule_type="case_normalization",
                                    column=col,
                                    action="lowercase",
                                    reason=f"Normalized case for {changed_count} values in column '{col}'",
                                    affected_rows=changed_count,
                                    before_value="Mixed case values",
                                    after_value="Lowercase values",
                                )
                            )

        return df_clean, rules

    def _handle_outliers(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Handle outliers using IQR method (flag only, don't remove).

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        for col in df_clean.columns:
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                # Calculate IQR
                Q1 = df_clean[col].quantile(0.25)
                Q3 = df_clean[col].quantile(0.75)
                IQR = Q3 - Q1

                if IQR > 0:
                    lower_bound = Q1 - self.outlier_iqr_multiplier * IQR
                    upper_bound = Q3 + self.outlier_iqr_multiplier * IQR

                    # Find outliers
                    outliers = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
                    outlier_count = outliers.sum()

                    if outlier_count > 0:
                        rules.append(
                            CleaningRule(
                                rule_type="outliers",
                                column=col,
                                action="flag",
                                reason=f"Found {outlier_count} outliers in column '{col}' using IQR method (bounds: [{lower_bound:.2f}, {upper_bound:.2f}])",
                                affected_rows=outlier_count,
                                before_value=f"{outlier_count} values outside bounds",
                                after_value="Flagged (not removed)",
                            )
                        )

        return df_clean, rules

    def _handle_invalid_categories(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CleaningRule]]:
        """Handle invalid categories (empty strings, 'NA', 'N/A', etc.).

        Args:
            df: Input DataFrame.

        Returns:
            Tuple of (cleaned DataFrame, cleaning rules).
        """
        rules: list[CleaningRule] = []
        df_clean = df.copy()

        # Common invalid category values
        invalid_values = ["", "NA", "N/A", "na", "n/a", "NULL", "null", "None", "none"]

        for col in df_clean.columns:
            if pd.api.types.is_object_dtype(df_clean[col]) or pd.api.types.is_string_dtype(df_clean[col]):
                # Check for invalid values
                invalid_mask = df_clean[col].isin(invalid_values)
                invalid_count = invalid_mask.sum()

                if invalid_count > 0:
                    # Replace with NaN
                    df_clean[col] = df_clean[col].replace(invalid_values, np.nan)
                    rules.append(
                        CleaningRule(
                            rule_type="invalid_category",
                            column=col,
                            action="flag",
                            reason=f"Found {invalid_count} invalid category values in column '{col}' (e.g., '', 'NA', 'NULL')",
                            affected_rows=invalid_count,
                            before_value=f"{invalid_count} invalid values",
                            after_value="Replaced with NaN",
                        )
                    )

        return df_clean, rules

    def _calculate_cleaning_confidence(
        self, rules: list[CleaningRule], original_rows: int, original_columns: int
    ) -> float:
        """Calculate cleaning confidence score.

        Args:
            rules: List of cleaning rules applied.
            original_rows: Original number of rows.
            original_columns: Original number of columns.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if len(rules) == 0:
            return 1.0

        # Calculate confidence based on:
        # - Number of rules applied (fewer is better)
        # - Severity of actions (drop is worse than impute/flag)
        # - Percentage of data affected

        # Calculate data impact
        rows_affected = sum(r.affected_rows for r in rules)
        data_impact_ratio = rows_affected / (original_rows * original_columns) if (original_rows * original_columns) > 0 else 0

        # Calculate action severity
        drop_count = len([r for r in rules if r.action == "drop"])
        flag_count = len([r for r in rules if r.action == "flag"])
        other_count = len(rules) - drop_count - flag_count

        # Severity weights
        severity_score = (drop_count * 0.3 + other_count * 0.1 + flag_count * 0.05) / len(rules)

        # Calculate final confidence
        confidence = 1.0 - (data_impact_ratio * 0.5 + severity_score * 0.5)
        return max(0.0, min(1.0, confidence))