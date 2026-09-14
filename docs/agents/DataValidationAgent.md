# DataValidationAgent — The Gatekeeper

> First line of defense. Validates the input file before any processing.

## Purpose

The DataValidationAgent is the first intelligent agent of DataForge AI v2. It inspects datasets and identifies problems without modifying data. Its responsibility is to validate the input file, detect data quality issues, and produce a comprehensive validation report.

## Architecture

### Position in Pipeline
- **Phase**: 1 — Data Intake
- **Position**: First agent in the pipeline
- **Dependencies**: None (first agent)
- **Consumers**: DataCleaningAgent, ExecutiveReportAgent

### Agent Properties
| Property | Value |
|---|---|
| Phase | ExecutionPhase.DATA_INTAKE (1) |
| Required Inputs | `input_dataset_path` |
| Produced Outputs | `raw_data`, `file_metadata`, `validation_report` |
| Retry Policy | 1 retry (file issues are usually non-transient) |
| Failure Policy | FailurePolicy.HALT (bad input = no analysis) |
| Timeout | 30 seconds |
| LLM Usage | No (pure rule-based validation) |

### Validation Thresholds
| Threshold | Default | Description |
|---|---|---|
| `max_file_size_mb` | 100.0 | Maximum file size in MB |
| `max_rows` | 1,000,000 | Maximum rows allowed |
| `max_columns` | 1,000 | Maximum columns allowed |
| `null_threshold` | 0.5 | Null percentage threshold for warning (50%) |
| `duplicate_threshold` | 0.1 | Duplicate row percentage threshold for warning (10%) |
| `high_cardinality_threshold` | 10,000 | Unique values threshold for high cardinality warning |

## Inputs

### Required Inputs
- `input_dataset_path` (str): Path to the input file

### Optional Inputs
None

## Outputs

### GraphState Updates
The agent populates the following keys in `GraphState.data`:

| Key | Type | Description |
|---|---|---|
| `raw_data` | `pd.DataFrame` | Original loaded data |
| `file_metadata` | `FileMetadata` | File format, encoding, size, row/col counts |
| `validation_report` | `ValidationReport` | Complete validation report |
| `validation_score` | `float` | Overall validation score (0.0-1.0) |
| `validation_summary` | `str` | Human-readable summary |
| `validation_issues` | `list[ValidationIssue]` | List of all validation issues |
| `recommendations` | `list[str]` | Recommendations for fixing issues |

### AgentResult
- `decision`: `AgentDecision.CONTINUE`, `AgentDecision.RETRY`, or `AgentDecision.ERROR`
- `message`: Human-readable status message
- `quality_score`: Validation score (0.0-1.0)
- `execution_duration`: Execution time in seconds
- `execution_notes`: List of execution notes
- `metrics`: Dictionary of validation metrics

## Validation Rules

### 1. File-Level Validation
- **File existence**: Check if file exists
- **File readability**: Check if file is readable
- **Supported format**: Check if file extension is supported (.csv, .xlsx, .xls, .parquet, .json, .jsonl, .ndjson)
- **File size**: Check if file size exceeds `max_file_size_mb`
- **Row count**: Check if row count exceeds `max_rows`
- **Column count**: Check if column count exceeds `max_columns`

### 2. Structure Validation
- **Empty dataset**: Check if DataFrame is empty
- **No columns**: Check if DataFrame has no columns
- **Duplicate columns**: Check for duplicate column names

### 3. Data Quality Validation
- **High null percentage**: Detect columns with null percentage > `null_threshold`
- **Duplicate rows**: Detect duplicate rows exceeding `duplicate_threshold`
- **Mixed data types**: Detect columns with mixed data types
- **Invalid dates**: Detect date columns with invalid values
- **Invalid numeric values**: Detect numeric columns with non-numeric values
- **Constant columns**: Detect columns with constant values
- **High cardinality**: Detect columns with unique values > `high_cardinality_threshold`
- **Outlier candidates**: Detect potential outliers using IQR method (1.5 × IQR)
- **Encoding issues**: Detect non-ASCII characters in string columns

## Validation Scoring

The validation score is calculated based on the severity and count of issues:

| Severity | Weight per Issue |
|---|---|
| Error | 0.3 |
| Warning | 0.1 |
| Info | 0.05 |

**Formula**: `score = 1.0 - (error_count × 0.3) - (warning_count × 0.1) - (info_count × 0.05)`

**Decision Logic**:
- `error_count > 0`: `AgentDecision.ERROR`
- `score < 0.5`: `AgentDecision.RETRY`
- `score >= 0.5`: `AgentDecision.CONTINUE`

## Validation Report

### ValidationReport Structure
```python
class ValidationReport(BaseModel):
    is_valid: bool                    # Overall validation status
    total_issues: int                 # Total number of issues
    error_count: int                  # Number of errors
    warning_count: int                # Number of warnings
    info_count: int                   # Number of info messages
    issues: list[ValidationIssue]     # List of all issues
    columns_affected: list[str]       # Columns with issues
    recommendations: list[str]         # Recommendations for fixing issues
    generated_at: str                 # When report was generated
```

### ValidationIssue Structure
```python
class ValidationIssue(BaseModel):
    issue_type: str                   # Type of issue
    severity: str                     # Severity: error, warning, info
    column: str | None                # Column where issue occurred
    row_indices: list[int]            # Row indices where issue occurred
    message: str                      # Issue description
    suggestion: str | None            # Suggested fix
    count: int                        # Number of occurrences
```

## Failure Modes

### Error Conditions
- File not found
- File is not readable
- Unsupported file format
- File size exceeds limit
- Row/column count exceeds limit
- Empty dataset
- No columns
- Duplicate columns

### Error Handling
The agent never crashes. All errors are caught and converted to structured `ValidationReport` with appropriate `ValidationIssue` entries.

## Examples

### Example 1: Valid CSV File
```python
from dataforge.agents import DataValidationAgent
from dataforge.core.state import GraphState

agent = DataValidationAgent()
state = GraphState(
    input_dataset_path="data.csv",
    execution_id="test-123",
    start_time="2024-01-01T00:00:00",
)

result = await agent.execute(state)
# Result: decision=CONTINUE, quality_score=1.0, message="Validation passed successfully"
```

### Example 2: CSV with Missing Values
```python
# CSV file with 80% missing values in column 'age'
result = await agent.execute(state)
# Result: decision=RETRY, quality_score=0.7, message="Validation passed with low quality score"
# Issues: [ValidationIssue(issue_type="high_null_percentage", severity="warning", column="age")]
```

### Example 3: Missing File
```python
state = GraphState(
    input_dataset_path="/nonexistent/file.csv",
    execution_id="test-123",
    start_time="2024-01-01T00:00:00",
)

result = await agent.execute(state)
# Result: decision=ERROR, quality_score=0.0, message="File not found"
```

## State Changes

### Before Execution
```python
GraphState(
    input_dataset_path="data.csv",
    data={},
    current_phase=1,
    steps_completed=[],
)
```

### After Execution
```python
GraphState(
    input_dataset_path="data.csv",
    data={
        "raw_data": pd.DataFrame(...),
        "file_metadata": FileMetadata(...),
        "validation_report": ValidationReport(...),
        "validation_score": 0.95,
        "validation_summary": "Validation passed: 2 issue(s) found...",
        "validation_issues": [ValidationIssue(...)],
        "recommendations": ["Consider imputing missing values..."],
    },
    current_phase=1,
    steps_completed=["DataValidationAgent"],
    agent_history=[AgentHistoryEntry(...)],
)
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DataValidationAgent                       │
├─────────────────────────────────────────────────────────────┤
│  Input: GraphState.input_dataset_path                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  File Validation                                      │   │
│  │  - Check existence                                   │   │
│  │  - Check format                                      │   │
│  │  - Check size limits                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                              ↓                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Data Loading (FileReaders)                          │   │
│  │  - CSVReader                                         │   │
│  │  - ExcelReader                                       │   │
│  │  - ParquetReader                                     │   │
│  │  - JSONReader                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                              ↓                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Structure Validation                                 │   │
│  │  - Empty dataset check                                │   │
│  │  - No columns check                                   │   │
│  │  - Duplicate columns check                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                              ↓                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Data Quality Validation                              │   │
│  │  - Missing values                                     │   │
│  │  - Duplicate rows                                     │   │
│  │  - Mixed data types                                   │   │
│  │  - Invalid dates                                      │   │
│  │  - Invalid numeric values                             │   │
│  │  - Constant columns                                   │   │
│  │  - High cardinality                                   │   │
│  │  - Outlier candidates                                 │   │
│  │  - Encoding issues                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                              ↓                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Validation Report Generation                         │   │
│  │  - Calculate validation score                         │   │
│  │  - Generate recommendations                            │   │
│  │  - Create summary                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                              ↓                                │
│  Output: AgentResult                                      │
│  - decision: CONTINUE | RETRY | ERROR                      │
│  - quality_score: 0.0 - 1.0                               │
│  - data_updates: raw_data, file_metadata, validation_report│
└─────────────────────────────────────────────────────────────┘
```

## Best Practices

1. **Always validate first**: The DataValidationAgent should always be the first agent in the pipeline
2. **Review validation report**: Always check the validation report before proceeding with analysis
3. **Handle errors gracefully**: The agent never crashes; all errors are converted to structured reports
4. **Customize thresholds**: Adjust validation thresholds based on your specific use case
5. **Monitor validation scores**: Track validation scores over time to identify data quality trends

## Related Components

- **FileReaders**: CSVReader, ExcelReader, ParquetReader, JSONReader
- **Core Models**: ValidationReport, ValidationIssue, FileMetadata
- **BaseAgent**: Agent base class with execute() contract
- **GraphState**: Central state model flowing through the pipeline

## Future Enhancements

- Add more validation rules (e.g., data type constraints, value ranges)
- Support for custom validation rules
- Integration with data profiling for deeper analysis
- Support for streaming data validation
- Real-time validation monitoring