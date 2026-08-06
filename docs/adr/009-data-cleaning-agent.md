# ADR 009: DataCleaningAgent Design Decisions

## Status

**Accepted**

## Context

DataForge AI v2.0 requires a data cleaning agent that operates in Phase 2 (Data Preparation) after DataValidationAgent. The agent must clean validated datasets while maintaining complete audit trails of all modifications.

## Decision

Implement DataCleaningAgent with rule-based cleaning operations and comprehensive audit logging.

## Alternatives Considered

### Alternative 1: LLM-Based Cleaning

**Description**: Use LLM to analyze data quality issues and suggest cleaning operations.

**Pros**:
- Can handle complex, context-specific cleaning rules
- Can provide natural language explanations
- Adapts to domain-specific requirements

**Cons**:
- Higher latency (LLM API calls)
- Higher cost (token usage)
- Non-deterministic results
- Harder to test and validate
- Requires LLM provider configuration

**Decision**: Not selected due to performance, cost, and determinism requirements.

### Alternative 2: Statistical Learning-Based Cleaning

**Description**: Use statistical methods to learn cleaning patterns from training data.

**Pros**:
- Can discover complex patterns
- Adapts to data characteristics
- Potentially higher accuracy

**Cons**:
- Requires training data
- Complex to implement and maintain
- Risk of overfitting
- Harder to explain decisions
- Cold start problem

**Decision**: Not selected due to complexity and lack of training data.

### Alternative 3: Rule-Based Cleaning (Selected)

**Description**: Predefined rules for common data quality issues with configurable thresholds.

**Pros**:
- Deterministic and reproducible
- Fast execution (no external dependencies)
- Easy to test and validate
- Clear audit trail
- Configurable thresholds
- Low latency
- No external dependencies

**Cons**:
- Limited to predefined rules
- Requires manual rule additions for new scenarios
- May miss complex patterns

**Decision**: Selected due to determinism, performance, and auditability requirements.

## Trade-offs

### 1. Outlier Handling

**Decision**: Flag outliers but don't remove them.

**Rationale**:
- Outliers may be valid data points (e.g., legitimate high-value transactions)
- Analyst should decide whether to remove or keep outliers
- Prevents accidental data loss
- Maintains data integrity

**Trade-off**: Analyst must manually review flagged outliers.

### 2. Missing Value Imputation

**Decision**: Use median for numeric, mode for categorical.

**Rationale**:
- Median is robust to outliers (unlike mean)
- Mode preserves most common category
- Simple and deterministic
- Well-understood statistical properties

**Trade-off**: May not be optimal for all distributions (e.g., skewed data).

### 3. Constant Column Threshold

**Decision**: Drop columns with >95% same value.

**Rationale**:
- High threshold prevents dropping columns with legitimate low variability
- 95% is a common threshold in data science
- Allows for rare but valid categories

**Trade-off**: May keep some columns with very low variability.

### 4. Missing Value Drop Threshold

**Decision**: Drop columns with >70% missing values.

**Rationale**:
- High missing rate indicates unreliable data
- Imputation would be speculative
- Better to remove than to guess

**Trade-off**: May lose useful columns if missing values are concentrated in specific rows.

### 5. String Case Normalization

**Decision**: Convert to lowercase only (not title case or upper case).

**Rationale**:
- Lowercase is the most common normalization
- Simple and deterministic
- Preserves original information

**Trade-off**: Loses case information (e.g., proper nouns).

### 6. Data Safety

**Decision**: Never modify original data; always create a copy.

**Rationale**:
- Allows rollback if needed
- Maintains audit trail
- Prevents data corruption
- Enables comparison between original and cleaned data

**Trade-off**: Uses more memory (2x data storage).

## Implementation Details

### Cleaning Pipeline Order

1. Duplicate columns (remove redundancy first)
2. Empty columns (remove no-value columns)
3. Constant columns (remove low-variability columns)
4. Duplicate rows (remove exact duplicates)
5. Missing values (impute or drop)
6. Type normalization (convert string numbers to numeric)
7. Date normalization (standardize date formats)
8. Invalid numeric values (handle inf/-inf)
9. String cleaning (trim whitespace)
10. Case normalization (lowercase)
11. Outlier detection (flag only)
12. Invalid category handling (standardize missing values)

### Confidence Score Calculation

```python
confidence = 1.0 - (data_impact_ratio * 0.5 + severity_score * 0.5)
```

Where:
- `data_impact_ratio` = affected cells / (rows × columns)
- `severity_score` = weighted average of action severities
  - Drop: 0.3 weight
  - Other: 0.1 weight
  - Flag: 0.05 weight

### Checksum Generation

Uses MD5 hash of DataFrame string representation with sorted columns to ensure consistency.

## Consequences

### Positive

- Deterministic cleaning results
- Complete audit trail
- High test coverage (98%)
- Fast execution (<60s for typical datasets)
- No external dependencies
- Configurable thresholds

### Negative

- Limited to predefined rules
- Analyst must review flagged outliers manually
- Case information lost in string normalization
- Higher memory usage (2x data storage)

### Neutral

- Confidence score may be conservative (penalizes all cleaning actions)
- Some cleaning operations (case normalization) are always applied

## Testing Strategy

### Unit Tests

- 43 comprehensive unit tests covering:
  - Agent initialization
  - Execute method with various data states
  - Individual cleaning operations
  - Edge cases (empty data, large datasets, etc.)
  - Integration tests
  - Confidence calculation
  - Checksum generation

### Coverage Target

- **Target**: >=90%
- **Achieved**: 98% (243 statements, 4 uncovered)

### Test Data

- Sample clean datasets
- Datasets with various quality issues
- Edge cases (empty, large, wide datasets)
- Real-world scenarios

## Future Improvements

### Short-Term

1. Add configurable cleaning rules via constructor parameters
2. Support custom imputation strategies
3. Add support for currency symbol stripping
4. Add support for encoding detection and conversion

### Long-Term

1. LLM-assisted cleaning rule suggestions
2. Machine learning-based outlier detection
3. Automated cleaning rule discovery
4. Support for streaming data cleaning

## References

- [AGENTS.md](../v2/AGENTS.md) - Agent architecture overview
- [ARCHITECTURE.md](../v2/ARCHITECTURE.md) - System architecture
- [CleaningRule Model](../../core/models.py) - CleaningRule data model
- [DataValidationAgent ADR](./008-data-validation-agent.md) - Preceding agent

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-06 | DataForge AI Team | Initial design decision |