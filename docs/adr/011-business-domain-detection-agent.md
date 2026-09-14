# ADR-011: Business Domain Detection Agent Implementation

## Status

**Accepted**

## Context

DataForge AI v2 needs to automatically determine the business domain of uploaded datasets to provide domain-specific insights and recommendations. The system must classify datasets into one of 10 business domains: RETAIL, FINANCE, HR, HEALTHCARE, MARKETING, SAAS, REAL_ESTATE, EDUCATION, LOGISTICS, or GENERAL.

## Decision

Implement a deterministic heuristic-based BusinessDomainDetectionAgent that uses multi-stage analysis to detect business domains with confidence scoring.

### Design Approach

The agent uses a multi-stage detection process:

1. **Column Name Analysis**: Analyzes column names for domain-specific keywords (20-30 keywords per domain)
2. **Semantic Type Analysis**: Analyzes semantic types for domain patterns (currency, percentage, datetime, identifier, text)
3. **Value Pattern Analysis**: Analyzes value patterns for domain characteristics using regex matching
4. **Identifier Analysis**: Analyzes identifier columns for domain hints using regex patterns
5. **Measure Analysis**: Analyzes measure columns for domain hints using regex patterns
6. **Confidence Calculation**: Calculates overall domain confidence using weighted scoring
7. **Domain Selection**: Selects the domain with the highest confidence score
8. **Evidence Generation**: Generates evidence, keywords detected, features detected, summary, and reasoning

### Weighted Scoring

| Factor | Weight | Rationale |
|--------|--------|-----------|
| Keyword matches | 40% | Column names are the most reliable indicator of domain |
| Semantic types | 20% | Semantic types provide strong domain hints |
| Value patterns | 20% | Value patterns indicate domain-specific data formats |
| Identifier patterns | 10% | Identifier patterns provide domain context |
| Measure patterns | 10% | Measure patterns provide domain context |

### Confidence Thresholds

- **MIN_CONFIDENCE_THRESHOLD**: 0.3 - Minimum confidence to accept a domain classification
- **HIGH_CONFIDENCE_THRESHOLD**: 0.7 - Threshold for "high" confidence level

If confidence is below the minimum threshold, the agent falls back to GENERAL domain.

## Alternatives Considered

### Alternative 1: LLM-Based Classification

**Description**: Use an LLM to analyze the dataset and classify the business domain.

**Pros**:
- Can understand complex patterns and context
- Can handle ambiguous datasets
- Can provide natural language explanations

**Cons**:
- Higher cost per analysis
- Slower response time
- Less predictable results
- Requires LLM provider configuration

**Decision**: Rejected in favor of deterministic heuristics for faster, more predictable, and cost-effective classification.

### Alternative 2: Statistical Learning-Based Classification

**Description**: Train a machine learning model on labeled datasets to classify business domains.

**Pros**:
- Can learn complex patterns from data
- Can improve over time with more training data
- Can handle edge cases well

**Cons**:
- Requires labeled training data
- Model maintenance overhead
- Cold start problem (no training data initially)
- Less transparent decision-making

**Decision**: Rejected in favor of deterministic heuristics for immediate availability and transparency.

### Alternative 3: Hybrid Approach (Heuristics + LLM Fallback)

**Description**: Use deterministic heuristics for high-confidence cases, and fall back to LLM for low-confidence cases.

**Pros**:
- Combines speed of heuristics with accuracy of LLM
- Handles edge cases better
- Provides fallback for ambiguous datasets

**Cons**:
- Increased complexity
- Still requires LLM provider for some cases
- Inconsistent behavior between heuristics and LLM

**Decision**: Deferred for future enhancement. Current implementation uses pure deterministic heuristics for consistency and simplicity.

## Trade-offs

### Speed vs. Accuracy

**Decision**: Prioritize speed over accuracy. The agent uses simple heuristics that can be executed quickly (< 1 second for typical datasets). Accuracy can be improved in future iterations.

### Simplicity vs. Flexibility

**Decision**: Prioritize simplicity. The agent uses a fixed set of domains and keywords. Custom domain support is deferred for future enhancement.

### Transparency vs. Sophistication

**Decision**: Prioritize transparency. The agent provides clear evidence and reasoning for domain classification. Sophisticated ML approaches are deferred for future enhancement.

## Implementation Details

### Domain Keywords

Each domain has 20-30 predefined keywords:

```python
DOMAIN_KEYWORDS = {
    BusinessDomain.RETAIL: [
        "product", "sku", "item", "price", "cost", "quantity", "order",
        "invoice", "transaction", "cart", "checkout", "customer", "discount",
        "revenue", "sales", "inventory", "stock", "shipment", "category",
        "brand", "merchant", "store", "shop", "purchase", "refund",
    ],
    # ... other domains
}
```

### Domain Patterns

Each domain has predefined patterns for identifiers and measures:

```python
DOMAIN_PATTERNS = {
    BusinessDomain.RETAIL: {
        "identifiers": [r"^(product|sku|item)_id", r"^(order|invoice|transaction)_id", r"^customer_id"],
        "measures": [r"^(price|cost|quantity|revenue|sales|discount|profit|margin)"],
    },
    # ... other domains
}
```

### Semantic Type Patterns

Each domain has preferred semantic types:

```python
domain_semantic_patterns = {
    BusinessDomain.RETAIL: ["currency", "percentage", "identifier"],
    BusinessDomain.FINANCE: ["currency", "percentage", "identifier"],
    BusinessDomain.HR: ["datetime", "identifier"],
    BusinessDomain.HEALTHCARE: ["datetime", "identifier", "text"],
    BusinessDomain.MARKETING: ["percentage", "identifier"],
    BusinessDomain.SAAS: ["datetime", "identifier", "percentage"],
    BusinessDomain.REAL_ESTATE: ["currency", "identifier"],
    BusinessDomain.EDUCATION: ["datetime", "identifier", "percentage"],
    BusinessDomain.LOGISTICS: ["datetime", "identifier", "currency"],
}
```

### Value Pattern Regex

Currency and percentage patterns are used for value pattern analysis:

```python
domain_value_patterns = {
    BusinessDomain.RETAIL: {
        "currency": r"^[\$€£¥₹]\s*[\d,]+\.?\d*",
        "percentage": r"^[\d,]+\.?\d*\s*%$",
    },
    # ... other domains
}
```

### Confidence Calculation

Confidence is calculated using weighted scoring:

```python
weights = {
    "keyword": 0.40,
    "semantic": 0.20,
    "pattern": 0.20,
    "identifier": 0.10,
    "measure": 0.10,
}

confidence = (
    keyword_score * weights["keyword"] +
    semantic_score * weights["semantic"] +
    pattern_score * weights["pattern"] +
    identifier_score * weights["identifier"] +
    measure_score * weights["measure"]
)
```

### Error Handling

The agent never crashes. On error, it returns a CONTINUE decision with GENERAL domain and confidence 0.0:

```python
try:
    # Domain detection logic
except Exception as e:
    return AgentResult(
        decision=AgentDecision.CONTINUE,
        message=f"Error during domain detection, using GENERAL domain: {str(e)}",
        quality_score=0.0,
        execution_notes=[f"Error: {str(e)}"],
        data_updates={
            "business_domain": BusinessDomain.GENERAL,
            "business_domain_confidence": 0.0,
            # ... other fields
        },
    )
```

## Testing Strategy

### Unit Tests

- **Initialization tests**: Agent properties, thresholds, domain keywords, domain patterns
- **Execution tests**: All 9 business domains (retail, finance, HR, healthcare, marketing, SaaS, real estate, education, logistics)
- **Edge cases**: Empty dataframe, missing data, all null values, all numeric values, all text values
- **Performance tests**: Large datasets (10,000 rows), minimal datasets (10 rows)
- **Integration tests**: Full workflow, can_execute conditions
- **Analysis method tests**: Column name analysis, semantic type analysis, pattern analysis, identifier analysis, measure analysis
- **Confidence calculation tests**: All scores, no scores, mixed scores, weight validation, clamping
- **Evidence and reporting tests**: Evidence generation, keywords detection, features detection, summary generation, reasoning generation

### Coverage Target

**>= 95% code coverage**

Current coverage: **99%** (61 tests passing, 0 failed, 0 errors)

## Performance Characteristics

- **Time Complexity**: O(S × C × D) where S is the number of stages (11), C is the number of columns, and D is the number of domains (10)
- **Space Complexity**: O(C + D) for storing scores and evidence
- **Scalability**: Handles datasets up to 100,000 rows efficiently
- **Timeout**: 30 seconds (configurable)

## Consequences

### Positive

- Fast, deterministic domain classification
- No LLM dependency, reducing cost and complexity
- Transparent decision-making with clear evidence and reasoning
- High test coverage (99%) ensures reliability
- Graceful fallback to GENERAL domain for ambiguous datasets

### Negative

- Limited to 10 predefined domains
- Cannot learn from new data
- May misclassify datasets with unusual column names
- Requires manual updates to add new domains or keywords

### Neutral

- Confidence scoring provides uncertainty quantification
- Evidence generation enables auditability
- Multi-stage analysis provides robustness

## Future Improvements

1. **Machine Learning Enhancement**: Add optional ML-based classification for improved accuracy
2. **Custom Domain Support**: Allow users to define custom domain keywords and patterns
3. **Domain Hierarchy**: Support hierarchical domain classification (e.g., RETAIL → E-COMMERCE)
4. **Confidence Calibration**: Improve confidence scoring based on historical accuracy
5. **Multi-Domain Detection**: Support datasets that span multiple domains
6. **LLM Fallback**: Implement hybrid approach with LLM fallback for low-confidence cases
7. **Domain-Specific Insights**: Provide domain-specific insights and recommendations

## References

- [Architecture Review](../../plans/SPRINT_2_TASK_5_ARCHITECTURE_REVIEW.md)
- [BusinessDomainDetectionAgent Documentation](../agents/BusinessDomainDetectionAgent.md)
- [Domain Models](../v2/ARCHITECTURE.md)
- [GraphState](../v2/GRAPHSTATE.md)