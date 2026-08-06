# SchemaDetectionAgent — 📐 The Cartographer

## Purpose

SchemaDetectionAgent automatically detects semantic types, keys, and data structure from cleaned tabular data. It provides deep understanding of column types, relationships, and data characteristics beyond simple dtypes.

## Responsibilities

### Semantic Type Detection

Automatically detects semantic meaning for columns:

- **Identifiers:** ID patterns (customer_id, employee_id, order_id, product_id, etc.)
- **Contact Information:** Email, phone, URL
- **Financial:** Currency, percentage
- **Geographic:** Latitude, longitude, ZIP/postal codes, country, state, city
- **Technical:** UUID, IP address
- **Temporal:** Date, time, timestamp
- **Business:** Salary, revenue, price, discount, quantity, category, status

### Key Detection

- **Primary Key Candidates:** Columns with high uniqueness (>95%) and low null percentage (<5%)
- **Foreign Key Candidates:** Columns with limited cardinality whose values are subsets of other columns

### Column Type Categorization

- **Numeric Measures:** Continuous numeric columns with high cardinality
- **Dimensions:** Categorical columns with low/medium cardinality
- **Identifiers:** Primary keys and ID-like columns
- **Datetime Columns:** Date, time, timestamp columns
- **Categorical Columns:** Low cardinality discrete values
- **Numeric Columns:** All numeric dtypes
- **Boolean Columns:** True/False, Yes/No, 1/0 patterns
- **Text Columns:** High cardinality strings or long text

### Column Analysis

For each column, detects:

- Nullable columns (contains null values)
- Constant columns (single unique value)
- High cardinality columns (>50 unique values)
- Low cardinality columns (<10 unique values)
- JSON columns (JSON-formatted strings)
- Array columns (list/array data)
- Hierarchical columns (geographic or organizational hierarchies)
- Derived columns (heuristic patterns)

## Inputs

| Key | Type | Required | Description |
|---|---|---|---|
| `cleaned_data` | `pd.DataFrame` | Yes | Cleaned dataset from DataCleaningAgent |

## Outputs

| Key | Type | Description |
|---|---|---|
| `schema_info` | `SchemaInfo` | Complete schema information including semantic types, keys, relationships |
| `column_profiles` | `dict[str, ColumnProfile]` | Per-column profiles with statistics and metadata |
| `dataset_profile` | `DatasetProfile` | Overall dataset profile with summary statistics |
| `primary_key_candidates` | `list[str]` | Detected primary key candidates |
| `foreign_key_candidates` | `dict[str, str]` | Detected foreign key relationships |
| `semantic_column_types` | `dict[str, str]` | Semantic type per column |
| `measure_columns` | `list[str]` | Continuous numeric columns for aggregation |
| `dimension_columns` | `list[str]` | Categorical columns for grouping |
| `identifier_columns` | `list[str]` | ID and key columns |
| `datetime_columns` | `list[str]` | Temporal columns |
| `categorical_columns` | `list[str]` | Categorical columns |
| `numeric_columns` | `list[str]` | All numeric columns |
| `boolean_columns` | `list[str]` | Boolean columns |
| `text_columns` | `list[str]` | Free text columns |
| `schema_summary` | `str` | Human-readable summary of detected schema |
| `schema_confidence` | `float` | Confidence score (0.0-1.0) |

## Algorithms

### Semantic Type Detection

Uses deterministic heuristics with two-stage detection:

1. **Column Name Matching:** Checks column names against semantic keyword dictionaries
2. **Pattern Matching:** Applies regex patterns to sample values for semantic types

**Pattern Thresholds:**
- Email: 80% match threshold
- Phone: 70% match threshold
- URL: 80% match threshold
- UUID: 90% match threshold
- IP Address: 90% match threshold
- Currency: 70% match threshold
- Percentage: 80% match threshold
- Latitude: 90% match threshold
- Longitude: 90% match threshold
- ZIP/Postal Code: 80% match threshold
- JSON: 80% match threshold

### Primary Key Detection

**Criteria:**
- Unique percentage ≥ 95%
- Null percentage < 5%

**Algorithm:**
1. Calculate unique percentage for each column
2. Calculate null percentage for each column
3. Filter columns meeting both criteria
4. Sort by uniqueness (descending) and null percentage (ascending)

### Foreign Key Detection

**Criteria:**
- Cardinality ≤ 100 (limited unique values)
- Values are subset of a primary key candidate's values
- Overlap ratio ≥ 50%

**Algorithm:**
1. Get primary key candidates
2. For each non-PK column with limited cardinality:
   - Check if values are subset of any PK column
   - Calculate overlap ratio
   - If overlap ≥ 50%, mark as FK candidate

### Cardinality Determination

- **Low:** ≤ 10 unique values
- **Medium:** 11-50 unique values
- **High:** > 50 unique values

### Confidence Calculation

Confidence score based on four factors:

1. **Primary Key Detection:** 0.2 if PK detected, 0.0 otherwise
2. **Semantic Type Coverage:** (semantic types / columns) × 0.3
3. **Analysis Completeness:** (analyzed columns / columns) × 0.3
4. **Data Quality:** (1 - average null percentage) × 0.2

## Configuration Thresholds

| Threshold | Default | Description |
|---|---|---|
| `high_cardinality_threshold` | 50 | Minimum unique values for high cardinality |
| `low_cardinality_threshold` | 10 | Maximum unique values for low cardinality |
| `unique_threshold_for_key` | 0.95 | Minimum unique percentage for PK candidate |
| `foreign_key_cardinality_threshold` | 100 | Maximum unique values for FK candidate |
| `constant_column_threshold` | 0.99 | Minimum same-value percentage for constant column |

## Examples

### Example 1: Employee Dataset

```python
import pandas as pd
from dataforge.agents.schema import SchemaDetectionAgent
from dataforge.core.state import GraphState

# Create sample employee data
df = pd.DataFrame({
    "employee_id": [1, 2, 3, 4, 5],
    "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
    "email": ["alice@example.com", "bob@example.com", ...],
    "salary": [50000.0, 60000.0, 70000.0, 80000.0, 90000.0],
    "department": ["Sales", "Engineering", "Sales", "Marketing", "Engineering"],
    "hire_date": pd.to_datetime(["2020-01-01", "2019-05-15", ...]),
})

# Create state
state = GraphState(
    input_dataset_path="employees.csv",
    execution_id="test-execution",
    start_time=datetime.now().isoformat(),
    data={"cleaned_data": df},
    current_phase=ExecutionPhase.DATA_UNDERSTANDING,
)

# Execute agent
agent = SchemaDetectionAgent()
result = await agent.execute(state)

# Results
print(result.data_updates["primary_key_candidates"])
# Output: ["employee_id"]

print(result.data_updates["semantic_column_types"])
# Output: {
#     "employee_id": "employee_id",
#     "name": None,
#     "email": "email",
#     "salary": "salary",
#     "department": None,
#     "hire_date": "hire_date"
# }

print(result.data_updates["measure_columns"])
# Output: ["salary"]

print(result.data_updates["dimension_columns"])
# Output: ["department", "name"]
```

### Example 2: E-commerce Dataset

```python
df = pd.DataFrame({
    "order_id": [1001, 1002, 1003, 1004, 1005],
    "customer_id": [101, 102, 101, 103, 102],
    "product_id": [501, 502, 501, 503, 502],
    "quantity": [2, 1, 3, 1, 2],
    "price": ["$100.00", "$200.00", "$150.00", "$300.00", "$250.00"],
    "discount": ["10%", "15%", "20%", "5%", "12%"],
    "status": ["completed", "pending", "shipped", "completed", "pending"],
})

result = await agent.execute(state)

print(result.data_updates["primary_key_candidates"])
# Output: ["order_id"]

print(result.data_updates["foreign_key_candidates"])
# Output: {"customer_id": "customer_id", "product_id": "product_id"}

print(result.data_updates["semantic_column_types"])
# Output: {
#     "order_id": "order_id",
#     "customer_id": "customer_id",
#     "product_id": "product_id",
#     "quantity": "quantity",
#     "price": "price",  # Detected from column name
#     "discount": "discount",  # Detected from column name
#     "status": "status"
# }
```

## Failure Modes

### Error Conditions

| Condition | Behavior |
|---|---|
| Missing `cleaned_data` | Returns ERROR decision with quality_score=0.0 |
| Empty dataframe | Returns ERROR decision with quality_score=0.0 |
| Exception during execution | Returns ERROR decision with quality_score=0.0 |

### Degraded Behavior

| Condition | Behavior |
|---|---|---|
| No primary key candidates | Continues with empty PK list |
| No foreign key candidates | Continues with empty FK dict |
| Low semantic type coverage | Continues with reduced confidence |
| High null percentages | Continues with lower quality score |

## GraphState Changes

### Phase 3 — Data Understanding

SchemaDetectionAgent operates in Phase 3 (Data Understanding) and modifies the following GraphState keys:

**New Keys Added:**
- `schema_info`: SchemaInfo object
- `column_profiles`: dict[str, ColumnProfile]
- `dataset_profile`: DatasetProfile
- `primary_key_candidates`: list[str]
- `foreign_key_candidates`: dict[str, str]
- `semantic_column_types`: dict[str, str]
- `measure_columns`: list[str]
- `dimension_columns`: list[str]
- `identifier_columns`: list[str]
- `datetime_columns`: list[str]
- `categorical_columns`: list[str]
- `numeric_columns`: list[str]
- `boolean_columns`: list[str]
- `text_columns`: list[str]
- `schema_summary`: str
- `schema_confidence`: float

**Agent History:**
- Adds AgentHistoryEntry with execution details

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    GraphState (Phase 3)                          │
├─────────────────────────────────────────────────────────────────┤
│  cleaned_data (from DataCleaningAgent)                          │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              SchemaDetectionAgent                         │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  Inputs: cleaned_data                                    │   │
│  │  Outputs: schema_info, column_profiles, dataset_profile  │   │
│  │           primary_key_candidates, foreign_key_candidates │   │
│  │           semantic_column_types, measure_columns, etc.   │   │
│  └─────────────────────────────────────────────────────────┘   │
│         ↓                                                        │
│  schema_info → BusinessDomainDetectionAgent, ProfilingAgent   │
└─────────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

### Time Complexity

- **Column Analysis:** O(n × c) where n = rows, c = columns
- **Primary Key Detection:** O(c × n) for uniqueness calculation
- **Foreign Key Detection:** O(c² × n) worst case, but limited by cardinality threshold
- **Overall:** O(n × c²) worst case, typically O(n × c) for most datasets

### Space Complexity

- **O(c × k)** where c = columns, k = average unique values per column
- Stores column profiles and schema information in memory

### Dataset Size Support

| Dataset Size | Performance |
|---|---|
| 10 rows | < 1 second |
| 100 rows | < 1 second |
| 10,000 rows | < 5 seconds |
| 100,000 rows | < 30 seconds |

## Design Decisions

### Deterministic vs. LLM-Based

**Decision:** Use deterministic heuristics instead of LLM-based detection.

**Rationale:**
- Faster execution (no API calls)
- Consistent results across runs
- No dependency on external services
- Lower cost
- Explainable decisions

**Trade-offs:**
- May miss subtle semantic patterns
- Requires manual pattern maintenance
- Limited to known patterns

### Column Name vs. Value Pattern Priority

**Decision:** Check column names first, then value patterns.

**Rationale:**
- Column names are more reliable indicators
- Faster (no need to sample values)
- More consistent across datasets

**Trade-offs:**
- May miss semantic types with generic names
- Requires comprehensive keyword dictionary

### Confidence Scoring

**Decision:** Multi-factor confidence calculation.

**Rationale:**
- Provides quality indicator
- Helps downstream agents make decisions
- Transparent about detection quality

**Factors:**
1. Primary key detection (20%)
2. Semantic type coverage (30%)
3. Analysis completeness (30%)
4. Data quality (20%)

## Dependencies

### Required

- `pandas` — DataFrame operations
- `numpy` — Numerical operations
- `pydantic` — Data validation

### Optional

- `llm_provider` — Not used (deterministic approach)
- `logger` — Structured logging (recommended)

## Related Agents

- **DataCleaningAgent** — Provides cleaned_data input
- **BusinessDomainDetectionAgent** — Consumes schema_info
- **ProfilingAgent** — Consumes schema_info

## Future Improvements

1. **Machine Learning-Based Detection:** Train models on labeled datasets for better semantic type detection
2. **Composite Key Detection:** Detect multi-column primary keys
3. **Relationship Inference:** Detect more complex relationships beyond FK
4. **Custom Pattern Registration:** Allow users to register custom semantic patterns
5. **Confidence Calibration:** Improve confidence scoring based on historical accuracy
6. **Incremental Detection:** Support streaming data with incremental schema updates