# DataForge AI v2.0 — GRAPHSTATE

> The Single Source of Truth — State Model Reference

---

## Design Principles

1. **Immutability:** State is never mutated in place. Every update returns a new `GraphState` via `model_copy(update={...})`
2. **Single Source of Truth:** All agent outputs live in `GraphState.data`. No agent maintains private state.
3. **Typed Accessors:** Well-known keys have typed properties to eliminate dict-key typos.
4. **Serializable:** Entire state (except DataFrames) serializes to JSON. DataFrames serialize to Parquet.
5. **Auditable:** Every state transition is recorded in `agent_history`.

---

## GraphState Model

```python
class GraphState(BaseModel):
    """Central state model flowing through the entire graph."""

    # ════════════════════════════════════════════════════════════
    # IMMUTABLE INPUT (set once at creation, never modified)
    # ════════════════════════════════════════════════════════════
    input_dataset_path: str          # Path to uploaded file
    input_query: str | None = None   # Optional user question
    output_dir: str = "./output"     # Output directory
    execution_id: str                # Unique run identifier (UUID)
    start_time: str                  # ISO timestamp

    # ════════════════════════════════════════════════════════════
    # MUTABLE DATA (the pipeline's shared memory)
    # ════════════════════════════════════════════════════════════
    data: dict[str, Any] = {}
    # Well-known keys documented below in the Data Dictionary

    # ════════════════════════════════════════════════════════════
    # EXECUTION TRACKING
    # ════════════════════════════════════════════════════════════
    current_phase: int = 1                        # Current execution phase (1-7)
    current_step: str = "start"                   # Current node name
    steps_completed: list[str] = []               # Ordered list of completed agents
    steps_skipped: list[str] = []                 # Agents that were skipped
    agent_history: list[AgentHistoryEntry] = []   # Full execution history

    # ════════════════════════════════════════════════════════════
    # QUALITY & RETRY
    # ════════════════════════════════════════════════════════════
    agent_visit_count: dict[str, int] = {}        # Per-agent invocation count
    global_step_count: int = 0                     # Total steps (loop detection)
    max_global_steps: int = 35                     # Hard limit
    quality_warnings: list[str] = []               # Non-fatal quality issues
    quality_errors: list[str] = []                 # Fatal quality issues

    # ════════════════════════════════════════════════════════════
    # OBSERVABILITY
    # ════════════════════════════════════════════════════════════
    logs: list[LogEntry] = []                     # Structured log entries
    metrics: dict[str, Any] = {}                  # Timing, token usage, etc.
    end_time: str | None = None                   # Set on completion
```

---

## Data Dictionary

These are the well-known keys in `GraphState.data`. Every key is documented with its producer, type, and consumers.

### Phase 1: Data Intake

| Key | Type | Producer | Consumers | Description |
|---|---|---|---|---|
| `raw_data` | `pd.DataFrame` | DataValidationAgent | DataCleaningAgent | Original loaded data |
| `file_metadata` | `FileMetadata` | DataValidationAgent | ExecutiveReportAgent | File format, encoding, size, row/col counts |
| `validation_report` | `ValidationReport` | DataValidationAgent | ExecutiveReportAgent | Validation checks and results |

### Phase 2: Data Preparation

| Key | Type | Producer | Consumers | Description |
|---|---|---|---|---|
| `cleaned_data` | `pd.DataFrame` | DataCleaningAgent | All subsequent agents | Cleaned dataset (the primary working dataset) |
| `cleaning_report` | `CleaningReport` | DataCleaningAgent | InsightGenerationAgent, ExecutiveReportAgent | Summary of all cleaning actions |
| `cleaning_decisions` | `list[CleaningDecision]` | DataCleaningAgent | ExecutiveReportAgent | Individual explained cleaning decisions |

### Phase 3: Data Understanding

| Key | Type | Producer | Consumers | Description |
|---|---|---|---|---|
| `schema_info` | `SchemaInfo` | SchemaDetectionAgent | BusinessDomainDetectionAgent, ProfilingAgent | Semantic types, keys, relationships |
| `business_domain` | `BusinessDomain` | BusinessDomainDetectionAgent | KPIDiscoveryAgent, FeatureEngineeringAgent, InsightGenerationAgent | Detected business domain |
| `domain_confidence` | `float` | BusinessDomainDetectionAgent | PlannerAgent | Confidence score (0.0-1.0) |
| `domain_signals` | `list[DomainSignal]` | BusinessDomainDetectionAgent | ExecutiveReportAgent | Evidence for domain classification |
| `business_objectives` | `list[BusinessObjective]` | BusinessObjectiveDetectionAgent | InsightGenerationAgent, ExecutiveReportAgent | What business questions can be answered |
| `answerable_questions` | `list[str]` | BusinessObjectiveDetectionAgent | InsightGenerationAgent | Specific questions the data can answer |

### Phase 4: Deep Analysis

| Key | Type | Producer | Consumers | Description |
|---|---|---|---|---|
| `profile` | `DataProfile` | ProfilingAgent | FeatureEngineeringAgent, KPIDiscoveryAgent, StatisticalAnalysisAgent, VisualizationAgent | Complete column-level and dataset-level profile |
| `engineered_data` | `pd.DataFrame` | FeatureEngineeringAgent | StatisticalAnalysisAgent, VisualizationAgent | Dataset with derived features added |
| `new_features` | `list[FeatureDefinition]` | FeatureEngineeringAgent | InsightGenerationAgent, ExecutiveReportAgent | Descriptions of created features |
| `discovered_kpis` | `list[KPI]` | KPIDiscoveryAgent | InsightGenerationAgent, VisualizationAgent, ExecutiveReportAgent | Domain-specific KPIs with values and trends |

### Phase 5: Statistical Analysis

| Key | Type | Producer | Consumers | Description |
|---|---|---|---|---|
| `statistics` | `StatisticalResults` | StatisticalAnalysisAgent | InsightGenerationAgent, VisualizationAgent, ExecutiveReportAgent | Full statistical analysis results |

### Phase 6: Synthesis

| Key | Type | Producer | Consumers | Description |
|---|---|---|---|---|
| `business_insights` | `list[BusinessInsight]` | InsightGenerationAgent | VisualizationAgent, ExecutiveReportAgent | Synthesized business insights |

### Phase 7: Output

| Key | Type | Producer | Consumers | Description |
|---|---|---|---|---|
| `visualizations` | `list[Visualization]` | VisualizationAgent | ExecutiveReportAgent | Generated chart metadata |
| `dashboard` | `DashboardLayout` | VisualizationAgent | ExecutiveReportAgent | Dashboard configuration |
| `report_html` | `str` (path) | ExecutiveReportAgent | Presentation Layer | Path to HTML report |
| `report_pdf` | `str` (path) | ExecutiveReportAgent | Presentation Layer | Path to PDF report |
| `report_json` | `str` (path) | ExecutiveReportAgent | Presentation Layer | Path to JSON report |
| `execution_trace` | `ExecutionTrace` | ExecutiveReportAgent | Presentation Layer | Complete audit trail |

---

## Supporting Models

### AgentHistoryEntry

```python
class AgentHistoryEntry(BaseModel):
    agent_name: str
    timestamp: str
    duration_seconds: float
    decision: str                    # continue, skip, retry, error
    message: str
    quality_score: float | None
    data_keys_produced: list[str]
    metadata: dict[str, Any] = {}
```

### LogEntry

```python
class LogEntry(BaseModel):
    timestamp: str
    level: str                       # DEBUG, INFO, WARNING, ERROR
    agent: str
    message: str
    metadata: dict[str, Any] = {}
```

### ExecutionPhase

```python
class ExecutionPhase(IntEnum):
    DATA_INTAKE = 1
    DATA_PREPARATION = 2
    DATA_UNDERSTANDING = 3
    DEEP_ANALYSIS = 4
    STATISTICAL_ANALYSIS = 5
    SYNTHESIS = 6
    OUTPUT = 7
```

---

## Typed Accessors

To eliminate the fragile `state.data.get("raw_data")` pattern:

```python
class GraphState(BaseModel):
    # ... fields ...

    # Phase 1
    @property
    def raw_data(self) -> pd.DataFrame | None:
        return self.data.get("raw_data")

    @property
    def file_metadata(self) -> FileMetadata | None:
        return self.data.get("file_metadata")

    # Phase 2
    @property
    def cleaned_data(self) -> pd.DataFrame | None:
        return self.data.get("cleaned_data")

    @property
    def cleaning_report(self) -> CleaningReport | None:
        return self.data.get("cleaning_report")

    # Phase 3
    @property
    def business_domain(self) -> BusinessDomain | None:
        return self.data.get("business_domain")

    @property
    def schema_info(self) -> SchemaInfo | None:
        return self.data.get("schema_info")

    # Phase 4
    @property
    def profile(self) -> DataProfile | None:
        return self.data.get("profile")

    @property
    def discovered_kpis(self) -> list[KPI] | None:
        return self.data.get("discovered_kpis")

    # Phase 5
    @property
    def statistics(self) -> StatisticalResults | None:
        return self.data.get("statistics")

    # Phase 6
    @property
    def business_insights(self) -> list[BusinessInsight] | None:
        return self.data.get("business_insights")
```

---

## State Size Management

| Concern | Mitigation |
|---|---|
| DataFrames are large | Stored as references; serialized to Parquet for checkpoints |
| Logs grow unbounded | Capped at 500 entries; older logs archived to disk |
| Agent history grows | Kept in full (typically < 20 entries per run) |
| Visualization files | Stored as file paths, not inline content |

---

## v1 → v2 Migration

| v1 Field | v2 Equivalent | Change |
|---|---|---|
| `validation_status` | Removed | Quality tracked per-agent in `agent_history` |
| `validation_errors` | `quality_errors` | Renamed for clarity |
| `retry_count` | `agent_visit_count` | Per-agent tracking instead of global |
| `max_retries` | `max_global_steps` + per-agent `retry_policy` | Finer-grained control |
| `current_step` | `current_step` + `current_phase` | Added phase tracking |
