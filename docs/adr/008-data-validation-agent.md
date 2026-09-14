# ADR 008: DataValidationAgent Implementation

## Status
Accepted

## Context
DataForge AI v2 requires a robust data validation mechanism as the first line of defense in the data analysis pipeline. The system needs to:

1. Validate input files before any processing
2. Detect and report data quality issues without modifying data
3. Provide actionable recommendations for fixing issues
4. Support multiple file formats (CSV, Excel, Parquet, JSON)
5. Handle errors gracefully without crashing

## Decision
Implement a DataValidationAgent that extends the BaseAgent class and provides comprehensive data validation capabilities.

### Architecture
```
DataValidationAgent (extends BaseAgent)
├── File Validation
│   ├── File existence check
│   ├── File format detection
│   ├── File size validation
│   └── Row/column count validation
├── Data Loading (via FileReaders)
│   ├── CSVReader
│   ├── ExcelReader
│   ├── ParquetReader
│   └── JSONReader
├── Structure Validation
│   ├── Empty dataset check
│   ├── No columns check
│   └── Duplicate columns check
├── Data Quality Validation
│   ├── Missing values detection
│   ├── Duplicate rows detection
│   ├── Mixed data types detection
│   ├── Invalid dates detection
│   ├── Invalid numeric values detection
│   ├── Constant columns detection
│   ├── High cardinality detection
│   ├── Outlier candidates detection
│   └── Encoding issues detection
└── Validation Report Generation
    ├── Validation score calculation
    ├── Recommendations generation
    └── Summary creation
```

### Key Design Decisions

1. **Separation of Concerns**: The agent validates data but does not modify it. Data cleaning is handled by a separate DataCleaningAgent.

2. **Rule-Based Validation**: The agent uses rule-based validation rather than LLM-based validation for:
   - Performance (faster execution)
   - Consistency (deterministic results)
   - Cost (no LLM API calls)
   - Reliability (no dependency on external services)

3. **Configurable Thresholds**: All validation thresholds are configurable as class attributes:
   ```python
   max_file_size_mb: float = 100.0
   max_rows: int = 1_000_000
   max_columns: int = 1000
   null_threshold: float = 0.5
   duplicate_threshold: float = 0.1
   high_cardinality_threshold: int = 10000
   ```

4. **Structured Error Handling**: All errors are caught and converted to structured ValidationReport objects:
   ```python
   try:
       df, metadata = await self._load_data(path)
   except DataIngestionError as e:
       issues.append(ValidationIssue(
           issue_type="load_error",
           severity="error",
           message=f"Failed to load file: {str(e)}",
           suggestion="Check file format and encoding",
       ))
       return self._create_error_result("Failed to load file", issues)
   ```

5. **Validation Scoring**: A weighted scoring system provides a single quality metric:
   - Errors: -0.3 per issue
   - Warnings: -0.1 per issue
   - Info: -0.05 per issue
   - Score range: 0.0 to 1.0

6. **Decision Logic**: The agent returns different decisions based on validation results:
   - `error_count > 0`: `AgentDecision.ERROR`
   - `score < 0.5`: `AgentDecision.RETRY`
   - `score >= 0.5`: `AgentDecision.CONTINUE`

### Validation Rules

| Rule | Severity | Description |
|------|----------|-------------|
| file_not_found | error | File does not exist |
| not_a_file | error | Path is not a file |
| file_too_large | error | File size exceeds limit |
| load_error | error | Failed to load file |
| empty_dataset | error | Dataset is empty |
| no_columns | error | Dataset has no columns |
| duplicate_columns | error | Duplicate column names |
| high_null_percentage | warning | Null percentage > threshold |
| duplicate_rows | warning | Duplicate row percentage > threshold |
| mixed_data_types | warning | Column contains mixed types |
| invalid_dates | warning | Date column has invalid values |
| invalid_numeric_values | warning | Numeric column has non-numeric values |
| constant_column | info | Column has constant value |
| high_cardinality | info | Column has high cardinality |
| outlier_candidates | info | Potential outliers detected |
| encoding_issues | info | Non-ASCII characters detected |

## Consequences

### Positive
1. **Robust Validation**: Comprehensive validation rules catch most data quality issues
2. **No Data Modification**: Agent respects the principle of not modifying data
3. **Structured Output**: ValidationReport provides structured, actionable information
4. **Configurable**: Thresholds can be customized for different use cases
5. **Error Resilient**: Never crashes; all errors are converted to structured reports
6. **Fast Execution**: Rule-based validation is faster than LLM-based validation

### Negative
1. **Fixed Rules**: Validation rules are fixed and cannot be customized without code changes
2. **No LLM Integration**: Does not leverage LLM for complex validation scenarios
3. **Limited Context**: Does not understand domain-specific validation requirements

### Neutral
1. **Single Responsibility**: Agent only validates; does not clean or modify data
2. **First Agent**: Must be the first agent in the pipeline
3. **No State Persistence**: Does not persist validation results beyond GraphState

## Alternatives Considered

### Alternative 1: LLM-Based Validation
Use LLM to validate data and generate recommendations.

**Pros**:
- Can understand complex validation scenarios
- Can generate natural language explanations
- Can adapt to different domains

**Cons**:
- Slower execution
- Higher cost (LLM API calls)
- Less consistent results
- Dependency on external services

**Decision**: Rule-based validation was chosen for performance, consistency, and cost reasons.

### Alternative 2: Combined Validation and Cleaning
Combine validation and cleaning in a single agent.

**Pros**:
- Fewer agents in the pipeline
- Tighter integration between validation and cleaning

**Cons**:
- Violates Single Responsibility Principle
- Harder to test and maintain
- Less flexible (cannot skip cleaning if validation passes)

**Decision**: Separation of concerns was chosen; validation and cleaning are separate agents.

### Alternative 3: External Validation Library
Use an external validation library (e.g., Great Expectations, Pandera).

**Pros**:
- Leverages existing, battle-tested code
- Rich feature set

**Cons**:
- Additional dependency
- May not fit perfectly with DataForge architecture
- Learning curve for team

**Decision**: Custom implementation was chosen for better integration with DataForge architecture and to avoid additional dependencies.

## Implementation Details

### File: `dataforge/agents/validation.py`
- Main agent implementation
- ~600 lines of code
- Extends BaseAgent
- Implements execute() method

### File: `tests/unit/test_validation_agent.py`
- Comprehensive unit tests
- ~500 lines of code
- Tests all validation rules
- Tests edge cases and error handling

### File: `docs/agents/DataValidationAgent.md`
- Comprehensive documentation
- Architecture diagrams
- Usage examples
- Best practices

## Testing Strategy

### Unit Tests
- Test agent initialization
- Test file validation
- Test data loading
- Test structure validation
- Test data quality validation
- Test validation scoring
- Test recommendations generation
- Test error handling
- Test edge cases

### Integration Tests
- Test full validation workflow
- Test integration with FileReaders
- Test GraphState updates
- Test can_execute() method

### Test Coverage
- Target: 80%+ code coverage
- Current: ~18% (needs improvement)

## Future Enhancements

1. **Custom Validation Rules**: Allow users to define custom validation rules
2. **Domain-Specific Validation**: Add domain-specific validation (e.g., email format, phone number format)
3. **Data Profiling Integration**: Integrate with DataProfilingAgent for deeper analysis
4. **Streaming Validation**: Support for streaming data validation
5. **Real-Time Monitoring**: Real-time validation monitoring and alerting
6. **Validation History**: Track validation history over time
7. **ML-Based Anomaly Detection**: Use ML for anomaly detection

## References
- [ADR 004: Domain Models](../adr/004-domain-models.md)
- [ADR 005: Infrastructure Interfaces](../adr/005-infrastructure-interfaces.md)
- [DataValidationAgent Documentation](../agents/DataValidationAgent.md)
- [BaseAgent Implementation](../../dataforge/agents/base.py)
- [ValidationReport Model](../../dataforge/core/models.py)