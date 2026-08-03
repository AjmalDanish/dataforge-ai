# DataForge AI v2.0 — TODO

> Master Task List — Track Everything

---

## Legend

- `[ ]` Not started
- `[/]` In progress
- `[x]` Complete
- 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

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

## Phase 1: Core Foundation

### GraphState v2
- [x] 🔴 Add typed accessors for well-known state keys (raw_data, cleaned_data, profile, etc.)
- [x] 🔴 Add current_phase tracking (IntEnum 1-7)
- [x] 🔴 Add agent_visit_count (per-agent invocation counter)
- [x] 🔴 Add global_step_count with max_global_steps limit
- [x] 🔴 Add steps_skipped list
- [x] 🔴 Add quality_warnings and quality_errors lists
- [ ] 🟠 Implement checkpoint serialization (JSON + Parquet)
- [ ] 🟠 Implement checkpoint restoration

### BaseAgent v2
- [ ] 🔴 Add required_inputs and produced_outputs declarations
- [ ] 🔴 Add retry_policy (max_retries, backoff_strategy)
- [ ] 🔴 Add failure_policy (HALT or SKIP)
- [ ] 🔴 Add timeout_seconds
- [ ] 🔴 Add can_execute(state) precondition checking
- [ ] 🔴 Add quality_score to AgentResult
- [ ] 🟠 Add execution_notes to AgentResult

### Core Domain Models
- [ ] 🔴 BusinessDomain enum + DomainRegistry
- [ ] 🔴 KPI model (name, formula, value, trend, benchmark)
- [ ] 🔴 BusinessInsight model (category, title, summary, action, confidence)
- [ ] 🔴 CleaningRule and CleaningDecision models
- [ ] 🔴 SchemaInfo model (semantic types, keys, relationships)
- [ ] 🟠 FileMetadata model
- [ ] 🟠 ValidationReport model
- [ ] 🟠 ExecutionPhase IntEnum

### Infrastructure Interfaces
- [ ] 🟠 FileReader ABC (read, validate_format)
- [ ] 🟠 ChartEngine ABC (create_bar, create_line, create_scatter, etc.)
- [ ] 🟠 ReportRenderer ABC (render_html, render_pdf, render_json)
- [ ] 🟠 DI Container (agent assembly with injected dependencies)

---

## Phase 2: Data Agents

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
- [ ] 🔴 CSVReader implementation
- [ ] 🔴 ExcelReader implementation (openpyxl)
- [ ] 🟠 ParquetReader implementation
- [ ] 🟠 JSONReader implementation (records + lines format)

---

## Phase 3: Business Intelligence Agents

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

## Phase 4: Output Quality

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

## Phase 5: Web Interface

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

## Phase 6: Polish & Release

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
