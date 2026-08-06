# DataCleaningAgent — 🧹 The Janitor

**Automatically detect and fix data quality issues. Every decision is explained and logged.**

---

## Overview

DataCleaningAgent is responsible for cleaning validated datasets and producing a complete audit trail of all modifications. It operates in Phase 2 (Data Preparation) and receives `raw_data` from DataValidationAgent.

---

## Responsibilities

- Handle missing values (drop column >70%, impute, flag)
- Remove duplicate rows
- Handle duplicate columns
- Normalize data types
- Normalize dates
- Trim strings and clean whitespace
- Normalize case (lowercase)
- Handle invalid numeric values (inf, -inf)
- Treat outliers using IQR method (flag only, don't remove)
- Handle invalid categories (empty strings, 'NA', 'NULL', etc.)
- Remove empty columns
- Remove constant columns (>95% same value)

---

## Agent Properties

| Property | Value |
|---|---|
| **Phase** | 2 — Data Preparation |
| **Inputs** | `raw_data` |
| **Outputs** | `cleaned_data`, `cleaning_report`, `cleaning_rules_applied`, `rows_removed`, `columns_removed`, `missing_values_fixed`, `duplicates_removed`, `cleaning_summary`, `cleaning_confidence`, `original_data_checksum`, `cleaned_data_checksum` |
| **Retry** | 2 |
| **Failure** | **HALT** (dirty data = unreliable analysis) |
| **Timeout** | 60s |
| **LLM** | Optional (for explaining decisions in natural language) |

---

## Cleaning Operations

### 1. Missing Value Handling

| Condition | Action | Rationale |
|---|---|---|
| >70% missing | Drop column | Too much data loss, unreliable |
| Numeric column | Impute with median | Robust to outliers |
| Categorical column | Impute with mode | Most common value |

### 2. Duplicate Row Handling

| Detection Method | Action | Rationale |
|---|---|---|
| `df.duplicated()` | Remove | Exact duplicates add no value |

### 3. Duplicate Column Handling

| Detection Method | Action | Rationale |
|---|---|---|
| Column equality check | Drop (keep first) | Redundant data |

### 4. Empty Column Handling

| Detection Method | Action | Rationale |
|---|---|---|
| `df.isnull().all()` | Drop | No data in column |

### 5. Constant Column Handling

| Detection Method | Action | Rationale |
|---|---|---|
| >95% same value | Drop | No variability, no analytical value |

### 6. Data Type Normalization

| Detection Method | Action | Rationale |
|---|---|---|
| `pd.to_numeric()` | Cast | Convert string numbers to numeric |

### 7. Date Normalization

| Detection Method | Action | Rationale |
|---|---|---|
| `pd.to_datetime()` | Cast | Standardize date formats |

### 8. Invalid Numeric Handling

| Detection Method | Action | Rationale |
|---|---|---|
| `np.isinf()` | Flag (replace with NaN) | Infinite values break analysis |

### 9. String Cleaning

| Detection Method | Action | Rationale |
|---|---|---|
| `.strip()` | Trim | Remove leading/trailing whitespace |

### 10. Case Normalization

| Detection Method | Action | Rationale |
|---|---|---|
| `.lower()` | Lowercase | Standardize text values |

### 11. Outlier Handling

| Detection Method | Action | Rationale |
|---|---|---|
| IQR method (1.5 × IQR) | Flag (don't remove) | Outliers may be valid data, analyst should decide |

### 12. Invalid Category Handling

| Detection Method | Action | Rationale |
|---|---|---|
| `['', 'NA', 'NULL', 'null', 'None']` | Flag (replace with NaN) | Standardize missing value representation |

---

## Cleaning Report Structure

```json
{
  "total_issues_found": 23,
  "total_issues_fixed": 20,
  "rows_before": 1000,
  "rows_after": 985,
  "columns_before": 12,
  "columns_after": 11,
  "decisions": [
    {
      "issue": "Column 'revenue' has 3% missing values",
      "action": "Imputed with median (45,230.00)",
      "rationale": "Low missing rate, numeric column, median is robust to outliers",
      "rows_affected": 30,
      "column": "revenue"
    }
  ]
}
```

---

## Data Safety

- **Original dataset is never modified**
- **Always creates a new cleaned dataset**
- **GraphState retains both original and cleaned data**
- **Checksums generated for both original and cleaned data**

---

## Cleaning Confidence Score

The agent calculates a cleaning confidence score (0.0 to 1.0) based on:

- **Data impact ratio**: Percentage of data cells affected by cleaning
- **Action severity**: Drop actions penalized more than impute/flag actions
- **Number of rules applied**: Fewer rules = higher confidence

Formula:
```
confidence = 1.0 - (data_impact_ratio * 0.5 + severity_score * 0.5)
```

---

## Examples

### Example 1: Clean Dataset

```python
from dataforge.agents import DataCleaningAgent
from dataforge.core.state import GraphState
import pandas as pd

# Create agent
agent = DataCleaningAgent()

# Create state with clean data
state = GraphState(
    input_dataset_path="data.csv",
    execution_id="test-123",
    start_time="2024-01-01T00:00:00",
    data={"raw_data": pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "age": [30, 25, 35],
    })},
    current_phase=ExecutionPhase.DATA_PREPARATION,
)

# Execute cleaning
result = await agent.execute(state)

# Access cleaned data
cleaned_data = result.data_updates["cleaned_data"]
cleaning_report = result.data_updates["cleaning_report"]
cleaning_rules = result.data_updates["cleaning_rules_applied"]
```

### Example 2: Dataset with Issues

```python
# Create state with data quality issues
state = GraphState(
    input_dataset_path="data.csv",
    execution_id="test-123",
    start_time="2024-01-01T00:00:00",
    data={"raw_data": pd.DataFrame({
        "id": [1, 2, 3, 1],  # Duplicate row
        "name": ["Alice", "Bob", "Charlie", "Alice"],
        "age": [30, 25, 35, 30],
        "salary": [50000.0, np.nan, 70000.0, 50000.0],  # Missing value
        "empty_col": [np.nan, np.nan, np.nan, np.nan],  # Empty column
    })},
    current_phase=ExecutionPhase.DATA_PREPARATION,
)

# Execute cleaning
result = await agent.execute(state)

# Check cleaning summary
print(result.data_updates["cleaning_summary"])
# Output: "Cleaned dataset from 4x5 to 3x4. Removed 1 rows, 1 columns. Fixed 1 missing values, 1 duplicates. Applied 4 rules."

# Check cleaning confidence
print(f"Cleaning confidence: {result.data_updates['cleaning_confidence']:.2%}")
# Output: "Cleaning confidence: 82.50%"
```

---

## Failure Modes

### 1. No Raw Data

**Condition**: `raw_data` not in `state.data`

**Behavior**: Returns `AgentResult.ERROR` with message "No raw_data found in state"

**Quality Score**: 0.0

### 2. Empty DataFrame

**Condition**: `raw_data` is empty DataFrame

**Behavior**: Returns `AgentResult.CONTINUE` with empty cleaned_data

**Quality Score**: 1.0 (nothing to clean)

### 3. Wrong Phase

**Condition**: `state.current_phase != ExecutionPhase.DATA_PREPARATION`

**Behavior**: `can_execute()` returns `False`

---

## GraphState Changes

### Inputs (Required)

- `raw_data`: pandas DataFrame from DataValidationAgent

### Outputs (All Populated)

- `cleaned_data`: Cleaned pandas DataFrame (never modifies original)
- `cleaning_report`: Dictionary with cleaning statistics
- `cleaning_rules_applied`: List of CleaningRule objects
- `rows_removed`: Integer count of removed rows
- `columns_removed`: Integer count of removed columns
- `missing_values_fixed`: Integer count of fixed missing values
- `duplicates_removed`: Integer count of removed duplicates
- `cleaning_summary`: Human-readable summary string
- `cleaning_confidence`: Float between 0.0 and 1.0
- `original_data_checksum`: MD5 checksum of original data
- `cleaned_data_checksum`: MD5 checksum of cleaned data

### Unchanged State

- `input_dataset_path`
- `input_query`
- `output_dir`
- `execution_id`
- `start_time`
- `agent_history`
- `logs`
- `metrics`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DataValidationAgent                        │
│                    (Phase 1: Data Intake)                     │
│  Output: raw_data, validation_report, file_metadata         │
└────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     DataCleaningAgent                         │
│                    (Phase 2: Data Preparation)                 │
│  Input: raw_data                                           │
│  Output: cleaned_data, cleaning_report, cleaning_rules_applied │
└────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     SchemaDetectionAgent                      │
│                    (Phase 3: Data Understanding)                │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration Thresholds

| Threshold | Default | Description |
|---|---|---|
| `missing_value_threshold` | 0.7 | Drop column if >70% missing |
| `outlier_iqr_multiplier` | 1.5 | IQR multiplier for outlier detection |
| `constant_column_threshold` | 0.95 | Drop column if >95% same value |

These can be customized by subclassing DataCleaningAgent and overriding the threshold attributes.

---

## v1 Equivalent

None — entirely new agent for DataForge AI v2.0.