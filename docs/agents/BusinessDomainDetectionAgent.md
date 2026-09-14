# BusinessDomainDetectionAgent — The Industry Expert

## Purpose

The BusinessDomainDetectionAgent determines the business domain represented by a dataset using deterministic heuristics with confidence scoring. It analyzes column names, semantic types, value patterns, identifiers, and measures to classify datasets into one of 10 business domains: RETAIL, FINANCE, HR, HEALTHCARE, MARKETING, SAAS, REAL_ESTATE, EDUCATION, LOGISTICS, or GENERAL.

## Responsibilities

- Analyze column names for domain-specific keywords
- Analyze semantic types for domain patterns
- Analyze value patterns for domain characteristics
- Analyze identifiers for domain hints
- Analyze measures for domain hints
- Calculate confidence scores for each domain
- Generate evidence and reasoning for classification
- Provide domain summary

## Phase

**Phase 3 — Data Understanding**

The agent operates in the Data Understanding phase, after schema detection has been completed.

## Inputs

| Key | Type | Description |
|-----|------|-------------|
| `cleaned_data` | `pd.DataFrame` | The cleaned dataset to analyze |
| `schema_info` | `SchemaInfo` | Schema information including semantic types |
| `column_profiles` | `dict[str, ColumnProfile]` | Column-level profiles |
| `dataset_profile` | `DatasetProfile` | Dataset-level profile |
| `semantic_column_types` | `dict[str, str]` | Semantic types per column |
| `measure_columns` | `list[str]` | List of measure column names |
| `dimension_columns` | `list[str]` | List of dimension column names |
| `identifier_columns` | `list[str]` | List of identifier column names |

## Outputs

| Key | Type | Description |
|-----|------|-------------|
| `business_domain` | `BusinessDomain` | The detected business domain |
| `business_domain_confidence` | `float` | Confidence score (0.0-1.0) |
| `business_domain_candidates` | `dict[str, float]` | All domain candidates with scores |
| `business_domain_evidence` | `list[str]` | Evidence items supporting the classification |
| `business_domain_summary` | `str` | Human-readable domain summary |
| `domain_keywords_detected` | `dict[str, list[str]]` | Keywords detected per domain |
| `domain_features_detected` | `dict[str, list[str]]` | Features detected per domain |
| `domain_reasoning` | `str` | Detailed reasoning for domain selection |

## Detection Algorithm

The agent uses a multi-stage detection process:

### Stage 1: Column Name Analysis

Analyzes column names for domain-specific keywords. Each domain has a predefined list of keywords (20-30 keywords per domain). The score is calculated based on the number of keyword matches.

### Stage 2: Semantic Type Analysis

Analyzes semantic types for domain patterns. Different domains have different semantic type preferences:
- **RETAIL/FINANCE**: currency, percentage, identifier
- **HR**: datetime, identifier
- **HEALTHCARE**: datetime, identifier, text
- **MARKETING**: percentage, identifier
- **SAAS**: datetime, identifier, percentage
- **REAL_ESTATE**: currency, identifier
- **EDUCATION**: datetime, identifier, percentage
- **LOGISTICS**: datetime, identifier, currency

### Stage 3: Value Pattern Analysis

Analyzes value patterns for domain characteristics using regex matching:
- **RETAIL/FINANCE**: Currency patterns (`$`, `€`, `£`, `¥`, `₹`)
- **RETAIL/FINANCE/MARKETING/SAAS**: Percentage patterns (`%`)

### Stage 4: Identifier Analysis

Analyzes identifier columns for domain hints using regex patterns:
- **RETAIL**: `product_id`, `order_id`, `customer_id`, `sku`
- **FINANCE**: `account_id`, `transaction_id`, `payment_id`
- **HR**: `employee_id`, `staff_id`, `worker_id`
- **HEALTHCARE**: `patient_id`, `diagnosis_id`, `procedure_id`
- **MARKETING**: `campaign_id`, `ad_id`, `lead_id`
- **SAAS**: `user_id`, `subscription_id`, `account_id`
- **REAL_ESTATE**: `property_id`, `listing_id`, `address`
- **EDUCATION**: `student_id`, `course_id`, `class_id`
- **LOGISTICS**: `shipment_id`, `order_id`, `tracking`

### Stage 5: Measure Analysis

Analyzes measure columns for domain hints using regex patterns:
- **RETAIL**: `price`, `cost`, `quantity`, `revenue`, `sales`, `discount`
- **FINANCE**: `balance`, `amount`, `interest`, `rate`, `principal`, `payment`
- **HR**: `salary`, `wage`, `bonus`, `commission`, `hours`, `overtime`
- **HEALTHCARE**: `dosage`, `vital`, `lab_result`, `cost`, `charge`
- **MARKETING**: `impression`, `click`, `conversion`, `ctr`, `cpa`, `spend`
- **SAAS**: `mrr`, `arr`, `arpu`, `ltv`, `cac`, `dau`, `mau`, `churn`
- **REAL_ESTATE**: `price`, `rent`, `sqft`, `bedrooms`, `bathrooms`, `value`
- **EDUCATION**: `grade`, `gpa`, `credit`, `score`, `attendance`
- **LOGISTICS**: `weight`, `volume`, `distance`, `duration`, `cost`

### Stage 6: Confidence Calculation

Calculates overall domain confidence using weighted scoring:

| Factor | Weight |
|--------|--------|
| Keyword matches | 40% |
| Semantic types | 20% |
| Value patterns | 20% |
| Identifier patterns | 10% |
| Measure patterns | 10% |

### Stage 7: Domain Selection

Selects the domain with the highest confidence score. If confidence is below the minimum threshold (0.3), falls back to GENERAL domain.

### Stage 8-11: Evidence and Reporting

Generates evidence, keywords detected, features detected, summary, and reasoning for the selected domain.

## Configuration Thresholds

| Threshold | Value | Description |
|-----------|-------|-------------|
| `MIN_CONFIDENCE_THRESHOLD` | 0.3 | Minimum confidence to accept a domain classification |
| `HIGH_CONFIDENCE_THRESHOLD` | 0.7 | Threshold for "high" confidence level |

## Examples

### Retail Domain

```python
# Input
{
    "product_id": [1, 2, 3],
    "product_name": ["Widget A", "Widget B", "Widget C"],
    "price": [19.99, 29.99, 39.99],
    "quantity": [10, 20, 30],
    "order_id": ["ORD001", "ORD002", "ORD003"],
    "customer_id": ["CUST001", "CUST002", "CUST003"],
}

# Output
{
    "business_domain": BusinessDomain.RETAIL,
    "business_domain_confidence": 0.85,
    "business_domain_summary": "Dataset classified as Retail domain with high confidence (85.0%). Key evidence: Column 'product_id' contains keyword 'product', Column 'price' has semantic type 'currency'",
}
```

### Finance Domain

```python
# Input
{
    "account_id": ["ACC001", "ACC002", "ACC003"],
    "balance": [1000.00, 2500.00, 5000.00],
    "transaction_id": ["TXN001", "TXN002", "TXN003"],
    "interest_rate": [0.05, 0.06, 0.07],
}

# Output
{
    "business_domain": BusinessDomain.FINANCE,
    "business_domain_confidence": 0.78,
    "business_domain_summary": "Dataset classified as Finance domain with high confidence (78.0%). Key evidence: Column 'account_id' contains keyword 'account', Column 'balance' has semantic type 'currency'",
}
```

### General Domain (Fallback)

```python
# Input
{
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "value": [100, 200, 300],
}

# Output
{
    "business_domain": BusinessDomain.GENERAL,
    "business_domain_confidence": 0.0,
    "business_domain_summary": "Dataset classified as General domain with low confidence (0.0%).",
}
```

## Failure Modes

| Condition | Behavior |
|-----------|----------|
| Missing or invalid `cleaned_data` | Returns ERROR decision with message "Cleaned data not found or invalid" |
| Empty dataframe | Returns ERROR decision with message "Cleaned data is empty" |
| Exception during execution | Returns CONTINUE with GENERAL domain and confidence 0.0 |

## GraphState Changes

The agent updates the GraphState with the following keys:

```python
state.data.update({
    "business_domain": BusinessDomain.RETAIL,
    "business_domain_confidence": 0.85,
    "business_domain_candidates": {
        "retail": 0.85,
        "finance": 0.15,
        # ...
    },
    "business_domain_evidence": [
        "Column 'product_id' contains keyword 'product'",
        "Column 'price' has semantic type 'currency'",
        # ...
    ],
    "business_domain_summary": "Dataset classified as Retail domain with high confidence (85.0%)...",
    "domain_keywords_detected": {
        "retail": ["product", "price", "quantity", "order"],
        # ...
    },
    "domain_features_detected": {
        "retail": ["currency: price", "identifier: product_id", "measure: quantity"],
        # ...
    },
    "domain_reasoning": "Selected Retail as the primary domain.\n\nDomain candidates ranked by confidence:\n1. Retail: 85.0%\n2. Finance: 15.0%\n\nSupporting evidence:\n1. Column 'product_id' contains keyword 'product'\n2. Column 'price' has semantic type 'currency'",
})
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│               BusinessDomainDetectionAgent                   │
├─────────────────────────────────────────────────────────────┤
│  Input: GraphState (cleaned_data, schema_info, etc.)         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Multi-Stage Detection Process                       │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  1. Column Name Analysis  (keyword matching)        │   │
│  │  2. Semantic Type Analysis  (pattern matching)      │   │
│  │  3. Value Pattern Analysis  (regex matching)        │   │
│  │  4. Identifier Analysis     (pattern matching)      │   │
│  │  5. Measure Analysis        (pattern matching)      │   │
│  │  6. Confidence Calculation   (weighted scoring)     │   │
│  │  7. Domain Selection         (max confidence)       │   │
│  │  8. Evidence Generation                             │   │
│  │  9. Keywords Detection                              │   │
│  │  10. Features Detection                             │   │
│  │  11. Summary & Reasoning                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Output: AgentResult (business_domain, confidence, etc.)     │
└─────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

- **Time Complexity**: O(S × C × D) where S is the number of stages (11), C is the number of columns, and D is the number of domains (10)
- **Space Complexity**: O(C + D) for storing scores and evidence
- **Scalability**: Handles datasets up to 100,000 rows efficiently
- **Timeout**: 30 seconds (configurable)

## Dependencies

- `pandas` for dataframe operations
- `re` for regex pattern matching
- `collections.defaultdict` for score aggregation
- `dataforge.core.models` for domain models
- `dataforge.core.state` for GraphState
- `dataforge.agents.base` for Agent base class

## Testing

The agent has comprehensive test coverage (99%) including:

- **Initialization tests**: Agent properties, thresholds, domain keywords, domain patterns
- **Execution tests**: All 9 business domains (retail, finance, HR, healthcare, marketing, SaaS, real estate, education, logistics)
- **Edge cases**: Empty dataframe, missing data, all null values, all numeric values, all text values
- **Performance tests**: Large datasets (10,000 rows), minimal datasets (10 rows)
- **Integration tests**: Full workflow, can_execute conditions
- **Analysis method tests**: Column name analysis, semantic type analysis, pattern analysis, identifier analysis, measure analysis
- **Confidence calculation tests**: All scores, no scores, mixed scores, weight validation, clamping
- **Evidence and reporting tests**: Evidence generation, keywords detection, features detection, summary generation, reasoning generation

## Related Components

- **SchemaDetectionAgent**: Provides semantic types and schema information used by this agent
- **BusinessObjectiveDetectionAgent**: Uses the detected business domain to identify business objectives
- **ProfilingAgent**: Uses the detected business domain to guide profiling analysis

## Future Improvements

1. **Machine Learning Enhancement**: Add optional ML-based classification for improved accuracy
2. **Custom Domain Support**: Allow users to define custom domain keywords and patterns
3. **Domain Hierarchy**: Support hierarchical domain classification (e.g., RETAIL → E-COMMERCE)
4. **Confidence Calibration**: Improve confidence scoring based on historical accuracy
5. **Multi-Domain Detection**: Support datasets that span multiple domains