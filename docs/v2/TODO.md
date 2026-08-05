# DataForge AI v2.0 — TODO

> Master Task List — Track Everything

---

## Project Status

| Field | Value |
|-------|-------|
| **Current Version** | v1.0.0 (Released, Frozen) |
| **Current Branch** | v2-development |
| **Current Sprint** | Sprint 1 - Foundation |
| **Overall Progress** | 7/7 Sprint 1 tasks complete (100%) |
| **Completed Sprint** | None |
| **Next Task** | Sprint 2: Data Agents |

---

## Branch Strategy

```
main (v1.0.0 - Frozen)
    ↓
v2-development (Active)
    ↓
Sprint-based development
```

---

## Legend

- `[ ]` Not started
- `[/]` In progress
- `[x]` Complete
- 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

# SECTION A: DATAFORGE AI v1.x MAINTENANCE (OPTIONAL)

> **IMPORTANT:** These tasks are optional improvements and are NOT blockers for DataForge AI v2 development.
>
> v1.0.0 has been released and frozen. Only critical bug fixes are allowed on the main branch.
> Minor improvements listed below may be addressed opportunistically but do not block v2 progress.

## Phase 0: v1.1 Stabilization

- [ ] 🔴 Wire LLMProvider into PlannerAgent for LLM-assisted routing
- [ ] 🔴 Enforce max_file_size_mb and max_rows in DataIngestionAgent
- [ ] 🟠 Upgrade langgraph from ^0.0.20 to latest stable
- [ ] 🟠 Add per-agent timeout via asyncio.wait_for()
- [ ] 🟠 Fix remaining v1 critical blockers
- [ ] 🟠 Add unit tests for VisualizationAgent
- [ ] 🟠 Add unit tests for ReportingAgent
- [ ] 🟡 Reach 80% test coverage

---

# SECTION B: DATAFORGE AI v2 DEVELOPMENT

> All v2 development happens on the `v2-development` branch.
> Sprint-based execution with clear deliverables and exit criteria.

## Sprint 1: Foundation (Week 1-2)

**Goal:** Build the v2 core — no agents yet, just the skeleton.

**Entry Criteria:** v2-development branch initialized
**Exit Criteria:** GraphState v2 passes all tests. BaseAgent v2 contract finalized. All core domain models defined. DI Container wires agents with dependencies.

### GraphState v2
- [x] 🔴 Add typed accessors for well-known state keys (raw_data, cleaned_data, profile, etc.)
- [x] 🔴 Add current_phase tracking (IntEnum 1-7)
- [x] 🔴 Add agent_visit_count (per-agent invocation counter)
- [x] 🔴 Add global_step_count with max_global_steps limit
- [x] 🔴 Add steps_skipped list
- [x] 🔴 Add quality_warnings and quality_errors lists
- [x] 🟠 Implement checkpoint serialization (JSON + Parquet)
- [x] 🟠 Implement checkpoint restoration

### BaseAgent v2
- [x] 🔴 Add required_inputs and produced_outputs declarations
- [x] 🔴 Add retry_policy (max_retries, backoff_strategy)
- [x] 🔴 Add failure_policy (HALT or SKIP)
- [x] 🔴 Add timeout_seconds
- [x] 🔴 Add can_execute(state) precondition checking
- [x] 🔴 Add quality_score to AgentResult
- [x] 🟠 Add execution_notes to AgentResult

### Core Domain Models
- [x] ✅ BusinessDomain enum + DomainRegistry
- [x] ✅ KPI model (name, formula, value, trend, benchmark)
- [x] ✅ BusinessInsight model (category, title, summary, action, confidence)
- [x] ✅ CleaningRule and CleaningDecision models
- [x] ✅ SchemaInfo model (semantic types, keys, relationships)
- [x] ✅ FileMetadata model
- [x] ✅ ValidationReport model
- [x] ✅ ExecutionPhase IntEnum

### Infrastructure Interfaces
- [x] ✅ FileReader ABC (read, validate_format)
- [x] ✅ ChartEngine ABC (create_bar, create_line, create_scatter, etc.)
- [x] ✅ ReportRenderer ABC (render_html, render_pdf, render_json)
- [x] ✅ PlotlyChartEngine implementation (bar, line, scatter, histogram, box plot, heatmap)
- [x] ✅ Jinja2HTMLRenderer implementation (HTML + JSON reports, templates)
- [x] ✅ DI Container (agent assembly with injected dependencies)

---

## Sprint 2: Data Agents (Week 3-4)

**Goal:** Build the first 3 processing agents (validation, cleaning, schema).

**Entry Criteria:** Sprint 1 complete
**Exit Criteria:** Upload a CSV → get validated, cleaned, schema-detected data. Cleaning report generated.

### DataValidationAgent
- [ ] 🔴 File existence, readability, extension validation
- [ ] 🔴 Format detection (CSV, Excel, Parquet, JSON)
- [ ] 🔴 Encoding detection and fallback (UTF-8 → Latin-1 → CP1252)
- [ ] 🔴 Size and row count enforcement
- [ ] 🔴 Structure validation (non-empty, has columns)
- [ ] 🟠 FileMetadata generation

### DataCleaningAgent
- [ ] 🔴 Missing value detection and handling (drop column >70%, impute, flag)
- [ ] 🔴 Duplicate row detection and removal
- [ ] 🔴 Invalid date detection and coercion
- [ ] 🔴 Incorrect type detection and casting
- [ ] 🔴 Cleaning decision logging with explanations
- [ ] 🔴 Cleaning report generation
- [ ] 🟠 Outlier flagging (IQR method)
- [ ] 🟠 Currency symbol stripping
- [ ] 🟠 Column name normalization (snake_case)
- [ ] 🟡 Mixed format detection and standardization
- [ ] 🟡 Encoding problem detection

### SchemaDetectionAgent
- [ ] 🔴 Semantic type detection (email, phone, URL, currency, ID, name, etc.)
- [ ] 🟠 Primary key candidate detection
- [ ] 🟠 Temporal column detection with granularity
- [ ] 🟡 Foreign key candidate detection
- [ ] 🟡 Hierarchical relationship detection

### File Readers
- [x] 🔴 CSVReader implementation
- [x] 🔴 ExcelReader implementation (openpyxl)
- [x] 🟠 ParquetReader implementation
- [x] 🟠 JSONReader implementation (records + lines format)
- [x] ✅ FileReader interface extension (peek_metadata method)
- [x] ✅ FileMetadata model update (column_names, sheet_names)
- [x] ✅ Error handling decorator (@handle_file_errors)
- [x] ✅ Encoding detection utilities
- [x] ✅ JSON format detection utilities
- [x] ✅ DI Container registration (readers_container.py)
- [x] ✅ Unit tests (test_readers.py)
- [x] ✅ Documentation (docs/agents/FileReaders.md)

---

## Sprint 3: Business Intelligence Agents (Week 5-6)

**Goal:** The differentiators — domain detection, objective detection, KPI discovery.

**Entry Criteria:** Sprint 2 complete
**Exit Criteria:** Domain detected. Business objectives identified. KPIs computed with trends.

### BusinessDomainDetectionAgent
- [ ] 🔴 Column name keyword matching against domain dictionaries
- [ ] 🔴 LLM-based domain classification
- [ ] 🔴 Rule-based fallback (no LLM)
- [ ] 🔴 Confidence scoring
- [ ] 🟠 Support 10 domains (retail, finance, HR, healthcare, marketing, SaaS, real estate, education, logistics, general)

### BusinessObjectiveDetectionAgent
- [ ] 🔴 LLM-powered business question generation
- [ ] 🟠 Domain-aware question templates as fallback

### KPIDiscoveryAgent
- [ ] 🔴 Domain-specific KPI templates
- [ ] 🔴 KPI value computation
- [ ] 🟠 KPI trend calculation (MoM, YoY where temporal data exists)
- [ ] 🟡 Benchmark context (industry averages)

### FeatureEngineeringAgent
- [ ] 🔴 Temporal feature extraction (month, day_of_week, quarter)
- [ ] 🟠 Ratio computation (when two related numeric columns exist)
- [ ] 🟠 Binning (age groups, price ranges)
- [ ] 🟡 Interaction features

### PlannerAgent v2
- [ ] 🔴 Phase-based execution plan
- [ ] 🔴 Per-agent quality gate (validate output after each agent)
- [ ] 🔴 Loop detection (step counter + visit counter)
- [ ] 🟠 Parallel agent dispatch (asyncio.gather for independent agents)
- [ ] 🟠 Dynamic plan adjustment based on data characteristics

### Graph v2
- [ ] 🔴 Wire all 13 agents as nodes
- [ ] 🔴 Conditional edges from Planner to all agents
- [ ] 🔴 All agents return to Planner
- [ ] 🟠 Checkpoint after each node
- [ ] 🟡 Crash recovery from latest checkpoint

---

## Sprint 4: Insights + Visualization (Week 7-8)

**Goal:** Generate actionable insights and executive-quality visualizations.

**Entry Criteria:** Sprint 3 complete
**Exit Criteria:** Insights generated. Visualizations created. Report template ready.

### InsightGenerationAgent
- [ ] 🔴 Insight category detection (top/bottom performers, trends, anomalies, risks, opportunities)
- [ ] 🔴 LLM synthesis of business insights
- [ ] 🟠 Insight ranking by business impact
- [ ] 🟠 Confidence scoring
- [ ] 🟡 Actionable recommendation generation

### VisualizationAgent v2
- [ ] 🔴 Chart type selection logic (data pattern → chart type mapping)
- [ ] 🔴 Dashboard layout (KPI cards + trend chart + distributions + heatmap)
- [ ] 🔴 KPI card visualization
- [ ] 🟠 Executive styling (colors, fonts, layout)
- [ ] 🟡 Responsive dashboard HTML

### ExecutiveReportAgent
- [ ] 🔴 Jinja2 HTML report template
- [ ] 🔴 Executive summary section (LLM-generated narrative)
- [ ] 🔴 All report sections (key metrics, domain, findings, risks, recommendations, etc.)
- [ ] 🟠 PDF generation (WeasyPrint)
- [ ] 🟠 JSON report generation
- [ ] 🟠 Execution trace inclusion
- [ ] 🟡 Professional formatting and styling

---

## Sprint 5: Web Interface (Week 9-10)

**Goal:** Build FastAPI backend and web UI for interactive analysis.

**Entry Criteria:** Sprint 4 complete
**Exit Criteria:** Upload via web → real-time progress → download results.

### FastAPI Backend
- [ ] 🔴 POST /api/analyze (file upload)
- [ ] 🔴 GET /api/status/{execution_id}
- [ ] 🔴 GET /api/results/{execution_id}
- [ ] 🟠 GET /api/download/{execution_id}/{format}
- [ ] 🟠 WebSocket /ws/{execution_id} (real-time events)
- [ ] 🟠 CORS, error handlers, request validation

### Web UI
- [ ] 🟠 Upload page (drag-and-drop, file validation, format indicator)
- [ ] 🔴 Graph visualization (SVG nodes, status badges, animations)
- [ ] 🟠 Results page (report viewer, chart gallery, download buttons)
- [ ] 🟡 Responsive design
- [ ] 🟡 Loading states and progress indicators

---

## Sprint 6: Polish & Release (Week 11-12)

**Goal:** Testing, documentation, performance, and release.

**Entry Criteria:** Sprint 5 complete
**Exit Criteria:** v2.0.0 released with 85% coverage and complete documentation.

### Testing
- [ ] 🔴 Reach 85% test coverage
- [ ] 🟠 Integration test: full pipeline on 5 domain-specific datasets
- [ ] 🟠 API endpoint tests
- [ ] 🟠 WebSocket event tests
- [ ] 🟡 Performance benchmarks (100K row dataset)
- [ ] 🟡 Security tests (path traversal, injection)

### Documentation
- [ ] 🟠 README v2 (installation, usage, screenshots, architecture overview)
- [ ] 🟠 API documentation (OpenAPI + examples)
- [ ] 🟡 Migration guide (v1 → v2)
- [ ] 🟡 Sample output gallery (5 domains)

### Release
- [ ] 🟠 Changelog
- [ ] 🟠 Git tag v2.0.0
- [ ] 🟡 GitHub release with release notes
- [ ] 🟡 Update pyproject.toml version to 2.0.0
