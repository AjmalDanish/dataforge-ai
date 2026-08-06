"""SchemaDetectionAgent — The Cartographer.

Automatically detect semantic types, keys, and data structure.
Uses deterministic heuristics with confidence scoring.
"""

import re
from datetime import datetime
from typing import Any

import pandas as pd
import numpy as np

from dataforge.core.models import (
    ColumnProfile,
    DatasetProfile,
    ExecutionPhase,
    FailurePolicy,
    RetryPolicy,
    SchemaInfo,
)
from dataforge.core.state import GraphState

from .base import Agent, AgentDecision, AgentResult


class SchemaDetectionAgent(Agent):
    """Detects semantic types, keys, and data structure from cleaned data.

    Responsibilities:
    - Detect Primary Key candidates (unique, non-null columns)
    - Detect Foreign Key candidates (columns with limited cardinality matching other columns)
    - Detect Numeric Measures (continuous numeric columns)
    - Detect Dimensions (categorical columns used for grouping)
    - Detect Categorical Columns (low cardinality, discrete values)
    - Detect Continuous Variables (numeric, many unique values)
    - Detect Discrete Variables (numeric, few unique values)
    - Detect Boolean Columns (True/False, Yes/No, 1/0)
    - Detect Date Columns (date-only values)
    - Detect Time Columns (time-only values)
    - Detect Timestamp Columns (datetime values)
    - Detect Identifier Columns (ID-like patterns)
    - Detect UUID Columns (UUID format)
    - Detect Email Columns (email patterns)
    - Detect Phone Columns (phone number patterns)
    - Detect URL Columns (URL patterns)
    - Detect IP Address Columns (IP address patterns)
    - Detect Currency Columns (currency symbols/patterns)
    - Detect Percentage Columns (percentage patterns)
    - Detect Geographic Columns (country, state, city, zip)
    - Detect Latitude/Longitude Columns (coordinate patterns)
    - Detect ZIP/Postal Code Columns (postal code patterns)
    - Detect Text Columns (free text, high cardinality strings)
    - Detect JSON Columns (JSON-formatted strings)
    - Detect Array Columns (array/list data)
    - Detect High Cardinality Columns (>50 unique values)
    - Detect Low Cardinality Columns (<10 unique values)
    - Detect Nullable Columns (contains null values)
    - Detect Constant Columns (single unique value)
    - Detect Derived Columns (heuristic patterns)
    - Infer semantic meaning (Customer ID, Employee ID, Order ID, etc.)

    Phase: 3 — Data Understanding
    Inputs: cleaned_data
    Outputs: schema_info, column_profiles, dataset_profile, primary_key_candidates,
             foreign_key_candidates, semantic_column_types, measure_columns,
             dimension_columns, identifier_columns, datetime_columns,
             categorical_columns, numeric_columns, boolean_columns, text_columns,
             schema_summary, schema_confidence
    """

    # Agent properties
    phase: ExecutionPhase = ExecutionPhase.DATA_UNDERSTANDING
    required_inputs: list[str] = ["cleaned_data"]
    produced_outputs: list[str] = [
        "schema_info",
        "column_profiles",
        "dataset_profile",
        "primary_key_candidates",
        "foreign_key_candidates",
        "semantic_column_types",
        "measure_columns",
        "dimension_columns",
        "identifier_columns",
        "datetime_columns",
        "categorical_columns",
        "numeric_columns",
        "boolean_columns",
        "text_columns",
        "schema_summary",
        "schema_confidence",
    ]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=2)
    failure_policy: FailurePolicy = FailurePolicy.SKIP
    timeout_seconds: int = 30

    # Detection thresholds
    high_cardinality_threshold: int = 50
    low_cardinality_threshold: int = 10
    unique_threshold_for_key: float = 0.95  # 95% unique for PK candidate
    foreign_key_cardinality_threshold: int = 100  # FK candidates have limited cardinality
    constant_column_threshold: float = 0.99  # 99% same value for constant columns

    # Semantic type patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^[\d\s\-\+\(\)]{7,20}$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    IP_PATTERN = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    CURRENCY_PATTERN = re.compile(r'^[\$€£¥₹]\s*[\d,]+\.?\d*\s*([A-Z]{3})?$|^[\d,]+\.?\d*\s*[A-Z]{3}$')
    PERCENTAGE_PATTERN = re.compile(r'^[\d,]+\.?\d*\s*%$')
    LATITUDE_PATTERN = re.compile(r'^-?90(\.0+)?$|^-?[1-8]?\d(\.\d+)?$')
    LONGITUDE_PATTERN = re.compile(r'^-?180(\.0+)?$|^-?(1?[0-7]?[1-9]|[1-9]?[0-9])(\.\d+)?$')
    ZIP_PATTERN = re.compile(r'^\d{5}(-\d{4})?$|^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$')
    JSON_PATTERN = re.compile(r'^\s*\{.*\}\s*$|^\s*\[.*\]\s*$', re.DOTALL)

    # Semantic type keywords
    SEMANTIC_KEYWORDS = {
        "customer_id": ["customer", "client", "cust", "cid", "customer_id", "client_id"],
        "employee_id": ["employee", "emp", "staff", "worker", "employee_id", "emp_id"],
        "order_id": ["order", "invoice", "transaction", "order_id", "invoice_id", "transaction_id"],
        "product_id": ["product", "sku", "item", "product_id", "sku_id", "item_id"],
        "email": ["email", "mail", "contact_email"],
        "phone": ["phone", "tel", "mobile", "telephone", "contact_phone"],
        "salary": ["salary", "wage", "pay", "compensation", "income"],
        "revenue": ["revenue", "sales", "turnover", "income"],
        "price": ["price", "cost", "amount", "unit_price"],
        "discount": ["discount", "rebate", "reduction"],
        "quantity": ["quantity", "qty", "count", "amount", "number"],
        "country": ["country", "nation", "country_code"],
        "city": ["city", "town", "municipality", "location"],
        "department": ["department", "dept", "division", "unit"],
        "gender": ["gender", "sex"],
        "age": ["age", "years", "age_group"],
        "birth_date": ["birth", "dob", "born", "date_of_birth"],
        "join_date": ["join", "hire", "start", "joined", "hired", "start_date"],
        "termination_date": ["termination", "end", "exit", "left", "termination_date", "end_date"],
        "rating": ["rating", "score", "grade", "rating_value"],
        "category": ["category", "type", "class", "group"],
        "status": ["status", "state", "condition"],
    }

    def __init__(
        self,
        llm_provider=None,
        logger=None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize SchemaDetectionAgent.

        Args:
            llm_provider: LLM provider instance (not used by this agent).
            logger: Structured logger instance.
            retry_policy: Retry policy override.
            failure_policy: Failure policy override.
            timeout_seconds: Timeout override in seconds.
        """
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)

    async def execute(self, state: GraphState) -> AgentResult:
        """Execute schema detection logic.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with schema information and confidence score.
        """
        start_time = datetime.now()

        try:
            # Get cleaned data from state
            cleaned_data = state.data.get("cleaned_data")

            if cleaned_data is None or not isinstance(cleaned_data, pd.DataFrame):
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data not found or invalid",
                    quality_score=0.0,
                    execution_notes=["No cleaned data available for schema detection"],
                )

            if cleaned_data.empty:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data is empty",
                    quality_score=0.0,
                    execution_notes=["Empty dataset cannot be analyzed"],
                )

            # Detect schema
            schema_info = await self._detect_schema(cleaned_data)

            # Generate column profiles
            column_profiles = await self._generate_column_profiles(cleaned_data, schema_info)

            # Generate dataset profile
            dataset_profile = await self._generate_dataset_profile(cleaned_data, column_profiles)

            # Extract primary key candidates
            primary_key_candidates = schema_info.primary_keys

            # Extract foreign key candidates
            foreign_key_candidates = schema_info.foreign_keys

            # Extract semantic column types
            semantic_column_types = schema_info.semantic_types

            # Categorize columns
            measure_columns = self._extract_measure_columns(cleaned_data, column_profiles)
            dimension_columns = self._extract_dimension_columns(cleaned_data, column_profiles)
            identifier_columns = self._extract_identifier_columns(schema_info, column_profiles)
            datetime_columns = schema_info.temporal_columns
            categorical_columns = self._extract_categorical_columns(cleaned_data, column_profiles)
            numeric_columns = self._extract_numeric_columns(cleaned_data, column_profiles)
            boolean_columns = self._extract_boolean_columns(cleaned_data, column_profiles)
            text_columns = self._extract_text_columns(cleaned_data, column_profiles)

            # Generate schema summary
            schema_summary = self._generate_schema_summary(
                cleaned_data,
                schema_info,
                column_profiles,
            )

            # Calculate overall confidence
            schema_confidence = schema_info.confidence

            # Prepare data updates
            data_updates = {
                "schema_info": schema_info,
                "column_profiles": column_profiles,
                "dataset_profile": dataset_profile,
                "primary_key_candidates": primary_key_candidates,
                "foreign_key_candidates": foreign_key_candidates,
                "semantic_column_types": semantic_column_types,
                "measure_columns": measure_columns,
                "dimension_columns": dimension_columns,
                "identifier_columns": identifier_columns,
                "datetime_columns": datetime_columns,
                "categorical_columns": categorical_columns,
                "numeric_columns": numeric_columns,
                "boolean_columns": boolean_columns,
                "text_columns": text_columns,
                "schema_summary": schema_summary,
                "schema_confidence": schema_confidence,
            }

            execution_duration = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Schema detection complete. {len(column_profiles)} columns analyzed.",
                data_updates=data_updates,
                quality_score=schema_confidence,
                execution_duration=execution_duration,
                execution_notes=[
                    f"Detected {len(primary_key_candidates)} primary key candidates",
                    f"Detected {len(foreign_key_candidates)} foreign key candidates",
                    f"Detected {len(semantic_column_types)} semantic types",
                ],
                metadata={
                    "columns_analyzed": len(column_profiles),
                    "primary_keys": primary_key_candidates,
                    "foreign_keys": list(foreign_key_candidates.keys()),
                },
            )

        except Exception as e:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Schema detection failed: {str(e)}",
                quality_score=0.0,
                execution_notes=[f"Error: {str(e)}"],
            )

    async def _detect_schema(self, df: pd.DataFrame) -> SchemaInfo:
        """Detect the schema of the dataframe.

        Args:
            df: Input dataframe.

        Returns:
            SchemaInfo object with detected schema information.
        """
        columns = {}
        semantic_types = {}
        temporal_columns = []
        hierarchical_columns = []

        for col in df.columns:
            col_info = self._analyze_column(df, col)
            columns[col] = col_info

            if col_info.get("semantic_type"):
                semantic_types[col] = col_info["semantic_type"]

            if col_info.get("is_temporal"):
                temporal_columns.append(col)

            if col_info.get("is_hierarchical"):
                hierarchical_columns.append(col)

        # Detect primary keys
        primary_keys = self._detect_primary_keys(df, columns)

        # Detect foreign keys
        foreign_keys = self._detect_foreign_keys(df, columns)

        # Calculate overall confidence
        confidence = self._calculate_schema_confidence(columns, primary_keys, semantic_types)

        return SchemaInfo(
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            temporal_columns=temporal_columns,
            hierarchical_columns=hierarchical_columns,
            semantic_types=semantic_types,
            confidence=confidence,
        )

    def _analyze_column(self, df: pd.DataFrame, col: str) -> dict[str, Any]:
        """Analyze a single column.

        Args:
            df: Input dataframe.
            col: Column name.

        Returns:
            Dictionary with column analysis results.
        """
        series = df[col]
        col_info = {
            "name": col,
            "dtype": str(series.dtype),
            "nullable": series.isnull().any(),
            "null_percentage": (series.isnull().sum() / len(series)) * 100,
            "unique_count": series.nunique(),
            "unique_percentage": (series.nunique() / len(series)) * 100,
            "is_constant": series.nunique() <= 1,
            "cardinality": self._determine_cardinality(series),
        }

        # Detect semantic type
        semantic_type = self._detect_semantic_type(series, col)
        if semantic_type:
            col_info["semantic_type"] = semantic_type

        # Detect if temporal
        col_info["is_temporal"] = self._is_temporal_column(series)

        # Detect if hierarchical
        col_info["is_hierarchical"] = self._is_hierarchical_column(col)

        # Detect if numeric
        col_info["is_numeric"] = self._is_numeric_column(series)

        # Detect if boolean
        col_info["is_boolean"] = self._is_boolean_column(series)

        # Detect if categorical
        col_info["is_categorical"] = self._is_categorical_column(series)

        # Detect if text
        col_info["is_text"] = self._is_text_column(series)

        # Detect if JSON
        col_info["is_json"] = self._is_json_column(series)

        # Detect if array
        col_info["is_array"] = self._is_array_column(series)

        # Add basic statistics for numeric columns
        if col_info["is_numeric"]:
            col_info["min_value"] = series.min()
            col_info["max_value"] = series.max()
            col_info["mean"] = series.mean()
            col_info["std"] = series.std()

        return col_info

    def _detect_semantic_type(self, series: pd.Series, col_name: str) -> str | None:
        """Detect semantic type of a column.

        Args:
            series: Column data.
            col_name: Column name.

        Returns:
            Semantic type string or None.
        """
        # First check column name patterns
        col_lower = col_name.lower()

        for semantic_type, keywords in self.SEMANTIC_KEYWORDS.items():
            if any(keyword in col_lower for keyword in keywords):
                return semantic_type

        # Then check data patterns
        non_null_values = series.dropna().astype(str)

        if len(non_null_values) == 0:
            return None

        # Sample values for pattern matching
        sample_size = min(100, len(non_null_values))
        sample_values = non_null_values.sample(sample_size, random_state=42) if len(non_null_values) > sample_size else non_null_values

        # Check email pattern
        if self._matches_pattern(sample_values, self.EMAIL_PATTERN, 0.8):
            return "email"

        # Check phone pattern
        if self._matches_pattern(sample_values, self.PHONE_PATTERN, 0.7):
            return "phone"

        # Check URL pattern
        if self._matches_pattern(sample_values, self.URL_PATTERN, 0.8):
            return "url"

        # Check UUID pattern
        if self._matches_pattern(sample_values, self.UUID_PATTERN, 0.9):
            return "uuid"

        # Check IP address pattern
        if self._matches_pattern(sample_values, self.IP_PATTERN, 0.9):
            return "ip_address"

        # Check currency pattern
        if self._matches_pattern(sample_values, self.CURRENCY_PATTERN, 0.7):
            return "currency"

        # Check percentage pattern
        if self._matches_pattern(sample_values, self.PERCENTAGE_PATTERN, 0.8):
            return "percentage"

        # Check latitude pattern
        if self._matches_pattern(sample_values, self.LATITUDE_PATTERN, 0.9):
            return "latitude"

        # Check longitude pattern
        if self._matches_pattern(sample_values, self.LONGITUDE_PATTERN, 0.9):
            return "longitude"

        # Check ZIP/postal code pattern
        if self._matches_pattern(sample_values, self.ZIP_PATTERN, 0.8):
            return "postal_code"

        # Check for ID patterns (column name ends with _id or contains id)
        if col_lower.endswith("_id") or "_id_" in col_lower or col_lower in ["id", "identifier"]:
            return "identifier"

        # Check for date patterns in column name
        if any(word in col_lower for word in ["date", "time", "timestamp", "created", "updated", "modified"]):
            if self._is_temporal_column(series):
                return "datetime"

        return None

    def _matches_pattern(self, values: pd.Series, pattern: re.Pattern, threshold: float) -> bool:
        """Check if values match a pattern above a threshold.

        Args:
            values: Values to check.
            pattern: Regex pattern.
            threshold: Minimum proportion of matches.

        Returns:
            True if threshold is met.
        """
        if len(values) == 0:
            return False

        matches = sum(1 for v in values if pattern.match(str(v)))
        return (matches / len(values)) >= threshold

    def _is_temporal_column(self, series: pd.Series) -> bool:
        """Check if column is temporal.

        Args:
            series: Column data.

        Returns:
            True if temporal.
        """
        # Check if datetime type
        if pd.api.types.is_datetime64_any_dtype(series):
            return True

        # Try to parse as datetime
        non_null = series.dropna()
        if len(non_null) == 0:
            return False

        try:
            pd.to_datetime(non_null, errors="coerce")
            # Check if at least 80% parsed successfully
            parsed = pd.to_datetime(non_null, errors="coerce")
            return parsed.notna().sum() / len(non_null) >= 0.8
        except Exception:
            return False

    def _is_hierarchical_column(self, col_name: str) -> bool:
        """Check if column is hierarchical.

        Args:
            col_name: Column name.

        Returns:
            True if hierarchical.
        """
        col_lower = col_name.lower()
        hierarchical_keywords = [
            "country", "state", "province", "region", "city", "town",
            "district", "county", "zip", "postal", "location", "address",
            "category", "subcategory", "department", "division", "team",
        ]
        return any(keyword in col_lower for keyword in hierarchical_keywords)

    def _is_numeric_column(self, series: pd.Series) -> bool:
        """Check if column is numeric.

        Args:
            series: Column data.

        Returns:
            True if numeric.
        """
        return pd.api.types.is_numeric_dtype(series)

    def _is_boolean_column(self, series: pd.Series) -> bool:
        """Check if column is boolean.

        Args:
            series: Column data.

        Returns:
            True if boolean.
        """
        # Check boolean dtype
        if pd.api.types.is_bool_dtype(series):
            return True

        # Check for boolean-like values
        non_null = series.dropna()
        if len(non_null) == 0:
            return False

        unique_vals = set(str(v).lower() for v in non_null.unique())

        # Check for True/False
        if unique_vals <= {"true", "false"}:
            return True

        # Check for Yes/No
        if unique_vals <= {"yes", "no"}:
            return True

        # Check for 1/0
        if unique_vals <= {"1", "0", "1.0", "0.0"}:
            return True

        return False

    def _is_categorical_column(self, series: pd.Series) -> bool:
        """Check if column is categorical.

        Args:
            series: Column data.

        Returns:
            True if categorical.
        """
        # Check if categorical dtype
        try:
            from pandas.api.types import is_categorical_dtype
            if is_categorical_dtype(series):
                return True
        except (ImportError, AttributeError):
            pass

        # Check if string or object with low cardinality
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            unique_count = series.nunique()
            return unique_count <= self.high_cardinality_threshold

        return False

    def _is_text_column(self, series: pd.Series) -> bool:
        """Check if column is text.

        Args:
            series: Column data.

        Returns:
            True if text.
        """
        # Check if string/object type
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            return False

        # Check for high cardinality
        unique_count = series.nunique()
        if unique_count > self.high_cardinality_threshold:
            return True

        # Check for long strings
        non_null = series.dropna().astype(str)
        if len(non_null) == 0:
            return False

        avg_length = non_null.str.len().mean()
        return avg_length > 50

    def _is_json_column(self, series: pd.Series) -> bool:
        """Check if column contains JSON.

        Args:
            series: Column data.

        Returns:
            True if JSON.
        """
        non_null = series.dropna().astype(str)
        if len(non_null) == 0:
            return False

        # Sample values
        sample_size = min(50, len(non_null))
        sample_values = non_null.sample(sample_size, random_state=42) if len(non_null) > sample_size else non_null

        matches = sum(1 for v in sample_values if self.JSON_PATTERN.match(str(v)))
        return (matches / len(sample_values)) >= 0.8

    def _is_array_column(self, series: pd.Series) -> bool:
        """Check if column contains arrays.

        Args:
            series: Column data.

        Returns:
            True if array.
        """
        non_null = series.dropna()

        if len(non_null) == 0:
            return False

        # Check if any value is a list or array
        return any(isinstance(v, (list, np.ndarray)) for v in non_null.head(10))

    def _determine_cardinality(self, series: pd.Series) -> str:
        """Determine cardinality of a column.

        Args:
            series: Column data.

        Returns:
            Cardinality string: "low", "medium", or "high".
        """
        unique_count = series.nunique()

        if unique_count <= self.low_cardinality_threshold:
            return "low"
        elif unique_count <= self.high_cardinality_threshold:
            return "medium"
        else:
            return "high"

    def _detect_primary_keys(self, df: pd.DataFrame, columns: dict[str, dict]) -> list[str]:
        """Detect primary key candidates.

        Args:
            df: Input dataframe.
            columns: Column analysis results.

        Returns:
            List of primary key candidates.
        """
        pk_candidates = []

        for col, col_info in columns.items():
            # Check if column has high uniqueness
            unique_ratio = col_info["unique_percentage"]

            if unique_ratio >= (self.unique_threshold_for_key * 100):
                # Check if column has low null percentage
                if col_info["null_percentage"] < 5:
                    pk_candidates.append(col)

        # Sort by uniqueness (descending) and null percentage (ascending)
        pk_candidates.sort(
            key=lambda c: (
                -columns[c]["unique_percentage"],
                columns[c]["null_percentage"],
            )
        )

        return pk_candidates

    def _detect_foreign_keys(self, df: pd.DataFrame, columns: dict[str, dict]) -> dict[str, str]:
        """Detect foreign key candidates.

        Args:
            df: Input dataframe.
            columns: Column analysis results.

        Returns:
            Dictionary mapping FK column to PK column.
        """
        fk_candidates = {}

        # Get potential primary keys
        pk_candidates = self._detect_primary_keys(df, columns)

        for fk_col in df.columns:
            if fk_col in pk_candidates:
                continue  # Skip primary keys

            fk_info = columns[fk_col]

            # Check if column has limited cardinality
            if fk_info["unique_count"] > self.foreign_key_cardinality_threshold:
                continue

            # Check if column values are subset of any PK column
            fk_values = set(df[fk_col].dropna().astype(str))

            for pk_col in pk_candidates:
                pk_values = set(df[pk_col].dropna().astype(str))

                # Check if FK values are subset of PK values
                if fk_values and fk_values.issubset(pk_values):
                    # Check for reasonable overlap (at least 50%)
                    overlap_ratio = len(fk_values) / len(pk_values) if pk_values else 0
                    if overlap_ratio >= 0.5:
                        fk_candidates[fk_col] = pk_col
                        break

        return fk_candidates

    def _calculate_schema_confidence(
        self,
        columns: dict[str, dict],
        primary_keys: list[str],
        semantic_types: dict[str, str],
    ) -> float:
        """Calculate overall schema confidence.

        Args:
            columns: Column analysis results.
            primary_keys: Primary key candidates.
            semantic_types: Detected semantic types.

        Returns:
            Confidence score (0.0-1.0).
        """
        if not columns:
            return 0.0

        confidence_factors = []

        # Factor 1: Primary key detection
        if primary_keys:
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.0)

        # Factor 2: Semantic type coverage
        semantic_coverage = len(semantic_types) / len(columns)
        confidence_factors.append(semantic_coverage * 0.3)

        # Factor 3: Column analysis completeness
        analyzed_columns = sum(
            1 for col in columns.values()
            if any(col.get(k) for k in ["semantic_type", "is_temporal", "is_numeric", "is_boolean"])
        )
        analysis_coverage = analyzed_columns / len(columns)
        confidence_factors.append(analysis_coverage * 0.3)

        # Factor 4: Data quality (low null percentages)
        avg_null_percentage = sum(col["null_percentage"] for col in columns.values()) / len(columns)
        quality_factor = max(0, 1 - (avg_null_percentage / 100))
        confidence_factors.append(quality_factor * 0.2)

        return sum(confidence_factors)

    async def _generate_column_profiles(
        self,
        df: pd.DataFrame,
        schema_info: SchemaInfo,
    ) -> dict[str, ColumnProfile]:
        """Generate column profiles.

        Args:
            df: Input dataframe.
            schema_info: Schema information.

        Returns:
            Dictionary mapping column names to ColumnProfile objects.
        """
        column_profiles = {}

        for col in df.columns:
            series = df[col]
            col_info = schema_info.columns.get(col, {})

            # Initialize min/max/mean/std
            min_value = None
            max_value = None
            mean_val = None
            std_val = None

            # Add min/max for comparable types
            try:
                if pd.api.types.is_numeric_dtype(series):
                    min_value = float(series.min()) if pd.notna(series.min()) else None
                    max_value = float(series.max()) if pd.notna(series.max()) else None
                    mean_val = float(series.mean()) if pd.notna(series.mean()) else None
                    std_val = float(series.std()) if pd.notna(series.std()) else None
                elif pd.api.types.is_datetime64_any_dtype(series):
                    min_value = series.min().isoformat() if pd.notna(series.min()) else None
                    max_value = series.max().isoformat() if pd.notna(series.max()) else None
            except Exception:
                pass

            profile = ColumnProfile(
                name=col,
                dtype=str(series.dtype),
                non_null_count=series.notna().sum(),
                null_count=series.isna().sum(),
                null_percentage=(series.isna().sum() / len(series)) * 100,
                unique_count=series.nunique(),
                unique_percentage=(series.nunique() / len(series)) * 100,
                min_value=min_value,
                max_value=max_value,
                mean=mean_val,
                std=std_val,
                semantic_type=col_info.get("semantic_type"),
                is_key=col in schema_info.primary_keys,
                cardinality=col_info.get("cardinality", "medium"),
            )

            column_profiles[col] = profile

        return column_profiles

    async def _generate_dataset_profile(
        self,
        df: pd.DataFrame,
        column_profiles: dict[str, ColumnProfile],
    ) -> DatasetProfile:
        """Generate dataset profile.

        Args:
            df: Input dataframe.
            column_profiles: Column profiles.

        Returns:
            DatasetProfile object.
        """
        numeric_cols = [col for col, profile in column_profiles.items() if pd.api.types.is_numeric_dtype(df[col])]
        categorical_cols = [col for col in df.columns if self._is_categorical_column(df[col])]
        temporal_cols = [col for col in df.columns if self._is_temporal_column(df[col])]
        text_cols = [col for col in df.columns if self._is_text_column(df[col])]
        boolean_cols = [col for col in df.columns if self._is_boolean_column(df[col])]

        # Calculate missing values
        missing_total = df.isna().sum().sum()
        missing_percentage = (missing_total / (len(df) * len(df.columns))) * 100

        # Calculate duplicates
        duplicate_rows = df.duplicated().sum()
        duplicate_percentage = (duplicate_rows / len(df)) * 100

        return DatasetProfile(
            row_count=len(df),
            column_count=len(df.columns),
            memory_usage_mb=df.memory_usage(deep=True).sum() / (1024 * 1024),
            duplicate_rows=int(duplicate_rows),
            duplicate_percentage=float(duplicate_percentage),
            missing_values_total=int(missing_total),
            missing_percentage=float(missing_percentage),
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            temporal_columns=temporal_cols,
            text_columns=text_cols,
            boolean_columns=boolean_cols,
            column_profiles=column_profiles,
            quality_score=1.0 - (missing_percentage / 100),  # Simple quality score
        )

    def _extract_measure_columns(
        self,
        df: pd.DataFrame,
        column_profiles: dict[str, ColumnProfile],
    ) -> list[str]:
        """Extract measure columns (continuous numeric).

        Args:
            df: Input dataframe.
            column_profiles: Column profiles.

        Returns:
            List of measure column names.
        """
        measures = []

        for col, profile in column_profiles.items():
            if profile.cardinality == "high" and pd.api.types.is_numeric_dtype(df[col]):
                measures.append(col)

        return measures

    def _extract_dimension_columns(
        self,
        df: pd.DataFrame,
        column_profiles: dict[str, ColumnProfile],
    ) -> list[str]:
        """Extract dimension columns (categorical for grouping).

        Args:
            df: Input dataframe.
            column_profiles: Column profiles.

        Returns:
            List of dimension column names.
        """
        dimensions = []

        for col, profile in column_profiles.items():
            if profile.cardinality in ["low", "medium"]:
                dimensions.append(col)

        return dimensions

    def _extract_identifier_columns(
        self,
        schema_info: SchemaInfo,
        column_profiles: dict[str, ColumnProfile],
    ) -> list[str]:
        """Extract identifier columns.

        Args:
            schema_info: Schema information.
            column_profiles: Column profiles.

        Returns:
            List of identifier column names.
        """
        identifiers = []

        # Add primary keys
        identifiers.extend(schema_info.primary_keys)

        # Add columns with identifier semantic type
        for col, semantic_type in schema_info.semantic_types.items():
            if semantic_type in ["identifier", "uuid", "customer_id", "employee_id", "order_id", "product_id"]:
                if col not in identifiers:
                    identifiers.append(col)

        return identifiers

    def _extract_categorical_columns(
        self,
        df: pd.DataFrame,
        column_profiles: dict[str, ColumnProfile],
    ) -> list[str]:
        """Extract categorical columns.

        Args:
            df: Input dataframe.
            column_profiles: Column profiles.

        Returns:
            List of categorical column names.
        """
        return [col for col in df.columns if self._is_categorical_column(df[col])]

    def _extract_numeric_columns(
        self,
        df: pd.DataFrame,
        column_profiles: dict[str, ColumnProfile],
    ) -> list[str]:
        """Extract numeric columns.

        Args:
            df: Input dataframe.
            column_profiles: Column profiles.

        Returns:
            List of numeric column names.
        """
        return [col for col in df.columns if self._is_numeric_column(df[col])]

    def _extract_boolean_columns(
        self,
        df: pd.DataFrame,
        column_profiles: dict[str, ColumnProfile],
    ) -> list[str]:
        """Extract boolean columns.

        Args:
            df: Input dataframe.
            column_profiles: Column profiles.

        Returns:
            List of boolean column names.
        """
        return [col for col in df.columns if self._is_boolean_column(df[col])]

    def _extract_text_columns(
        self,
        df: pd.DataFrame,
        column_profiles: dict[str, ColumnProfile],
    ) -> list[str]:
        """Extract text columns.

        Args:
            df: Input dataframe.
            column_profiles: Column profiles.

        Returns:
            List of text column names.
        """
        return [col for col in df.columns if self._is_text_column(df[col])]

    def _generate_schema_summary(
        self,
        df: pd.DataFrame,
        schema_info: SchemaInfo,
        column_profiles: dict[str, ColumnProfile],
    ) -> str:
        """Generate schema summary.

        Args:
            df: Input dataframe.
            schema_info: Schema information.
            column_profiles: Column profiles.

        Returns:
            Schema summary string.
        """
        summary_parts = [
            f"Dataset contains {len(df)} rows and {len(df.columns)} columns.",
            f"Detected {len(schema_info.primary_keys)} primary key candidate(s): {', '.join(schema_info.primary_keys) or 'None'}.",
            f"Detected {len(schema_info.foreign_keys)} foreign key candidate(s).",
            f"Detected {len(schema_info.semantic_types)} semantic type(s).",
            f"Detected {len(schema_info.temporal_columns)} temporal column(s).",
            f"Schema confidence: {schema_info.confidence:.2%}.",
        ]

        return " ".join(summary_parts)