# DataForge AI v2.0 — SPRINT PLAN

> Detailed Sprint Breakdown — What Ships When

---

## Sprint Overview

| Sprint | Weeks | Focus | Deliverable | Status |
|---|---|---|---|---|
| **Sprint 0** | Pre-work | v1.1 Stabilization | Stable v1 base | OPTIONAL |
| **Sprint 1** | Week 1-2 | Foundation | GraphState v2, BaseAgent v2, Core models | 🟢 IN PROGRESS |
| **Sprint 2** | Week 3-4 | Data Agents | Validation, Cleaning, Schema + File Readers | ⏸️ Pending |
| **Sprint 3** | Week 5-6 | BI Agents | Domain, Objective, KPI, Features, Planner v2, Graph | ⏸️ Pending |
| **Sprint 4** | Week 7-8 | Insights + Viz | Insight Gen, Enhanced Viz, Report Templates | ⏸️ Pending |
| **Sprint 5** | Week 9-10 | Web Layer | FastAPI, WebSocket, Web UI | ⏸️ Pending |
| **Sprint 6** | Week 11-12 | Polish + Ship | Testing, Docs, Performance, Release | ⏸️ Pending |

**Branch Strategy:**
- `main`: v1.0.0 (Released, Frozen) — Only critical bug fixes allowed
- `v2-development`: Active v2 development — All engineering work happens here

**Current Status:**
- **Active Branch:** v2-development
- **Current Sprint:** Sprint 1 - Foundation
- **Sprint 1 Progress:** GraphState v2 foundation complete (6/8 tasks)
- **Next Task:** Checkpoint serialization (Sprint 1 Task 2)

---

## Sprint 0: v1.1 Stabilization (OPTIONAL)

**Goal:** Stable foundation before v2 divergence.

**Status:** OPTIONAL — These tasks are NOT blockers for DataForge AI v2 development.

**Entry Criteria:** v1.0 codebase
**Exit Criteria:** All critical v1 blockers resolved. 80% coverage. LLM wired into Planner.

**Branch:** `main` (v1.0.0 frozen)

| Day | Task | Done |
|---|---|---|
| D1 | Wire LLMProvider into PlannerAgent | ☐ |
| D2 | Enforce max_file_size_mb and max_rows | ☐ |
| D3-4 | Upgrade langgraph to stable version, fix API changes | ☐ |
| D5 | Add asyncio.wait_for() timeout wrappers | ☐ |
| D6-7 | Fix remaining critical TODOs | ☐ |
| D8-9 | Unit tests for VisualizationAgent and ReportingAgent | ☐ |
| D10-11 | Coverage push to 80% | ☐ |

---

## Sprint 1: Foundation (Week 1-2)

**Goal:** Build the v2 core — no agents yet, just the skeleton.

**Entry Criteria:** v1.1 complete
**Exit Criteria:** GraphState v2 passes all tests. BaseAgent v2 contract finalized. All core domain models defined. DI Container wires agents with dependencies.

### Week 1

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon | GraphState v2: typed accessors, phase tracking, visit counts | `core/state.py` | `tests/unit/core/test_state.py` |
| Tue | GraphState v2: checkpoint serialization (JSON + Parquet) | `core/state.py`, `graph/checkpointer.py` | `tests/unit/core/test_checkpoint.py` |
| Wed | BaseAgent v2: retry_policy, failure_policy, can_execute | `agents/base.py` | `tests/unit/agents/test_base.py` |
| Thu | Core domain models: BusinessDomain, KPI, InsightModel | `core/domain.py`, `core/insights.py` | `tests/unit/core/test_domain.py` |
| Fri | Core domain models: CleaningRule, SchemaInfo, value objects | `core/cleaning.py`, `core/models.py` | `tests/unit/core/test_models.py` |

### Week 2

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon | Infrastructure interfaces: FileReader, ChartEngine, ReportRenderer | `core/interfaces.py` | — (abstract, tested via implementations) |
| Tue | DI Container: agent assembly with injected dependencies | `shared/container.py` | `tests/unit/shared/test_container.py` |
| Wed | Infrastructure: PlotlyChartEngine implementation | `infrastructure/charts/plotly_engine.py` | `tests/unit/infra/test_plotly_engine.py` |
| Thu | Infrastructure: Jinja2 ReportRenderer implementation | `infrastructure/renderers/html_renderer.py` | `tests/unit/infra/test_html_renderer.py` |
| Fri | Sprint 1 review, integration tests, refactor | — | `tests/integration/test_foundation.py` |

---

## Sprint 2: Data Agents (Week 3-4)

**Goal:** Build the first 3 processing agents (validation, cleaning, schema).

**Entry Criteria:** Sprint 1 complete
**Exit Criteria:** Upload a CSV → get validated, cleaned, schema-detected data. Cleaning report generated.

### Week 3

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon | DataValidationAgent: file validation, format detection | `agents/validation.py` | `tests/unit/agents/test_validation.py` |
| Tue | DataValidationAgent: encoding fallback, size/row limits | `agents/validation.py` | (extend above) |
| Wed | File readers: CSVReader, ExcelReader, ParquetReader, JSONReader | `infrastructure/readers/*.py` | `tests/unit/infra/test_readers.py` |
| Thu-Fri | DataCleaningAgent: missing values, duplicates, type coercion | `agents/cleaning.py` | `tests/unit/agents/test_cleaning.py` |

### Week 4

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon | DataCleaningAgent: outliers, currency, encoding, column naming | `agents/cleaning.py` | (extend above) |
| Tue | DataCleaningAgent: cleaning report generation | `agents/cleaning.py` | (extend above) |
| Wed-Thu | SchemaDetectionAgent: semantic types, keys, relationships | `agents/schema.py` | `tests/unit/agents/test_schema.py` |
| Fri | Integration test: CSV → Validation → Cleaning → Schema | — | `tests/integration/test_data_pipeline.py` |

---

## Sprint 3: Business Intelligence Agents (Week 5-6)

**Goal:** The differentiators — domain detection, objective detection, KPI discovery.

**Entry Criteria:** Sprint 2 complete
**Exit Criteria:** Full v2 graph executes end-to-end. Planner v2 routes correctly. All 13 agents functional.

### Week 5

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon-Tue | BusinessDomainDetectionAgent: keyword matching + LLM classification | `agents/domain_detection.py` | `tests/unit/agents/test_domain.py` |
| Wed | BusinessObjectiveDetectionAgent: LLM-powered question generation | `agents/objective_detection.py` | `tests/unit/agents/test_objective.py` |
| Thu-Fri | KPIDiscoveryAgent: domain templates + LLM enhancement | `agents/kpi_discovery.py` | `tests/unit/agents/test_kpi.py` |

### Week 6

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon-Tue | FeatureEngineeringAgent: temporal extraction, ratios, binning | `agents/feature_engineering.py` | `tests/unit/agents/test_features.py` |
| Wed-Thu | PlannerAgent v2: phase-based routing, quality gates, parallel dispatch | `agents/planner.py` | `tests/unit/agents/test_planner_v2.py` |
| Fri | Build v2 graph: all 13 agents wired in LangGraph, routing tested | `graph/workflow.py`, `graph/router.py` | `tests/integration/test_graph_v2.py` |

---

## Sprint 4: Insights + Visualization (Week 7-8)

**Goal:** Transform raw analysis into executive-grade output.

**Entry Criteria:** Sprint 3 complete
**Exit Criteria:** Insight generation produces business-grade insights. Dashboard looks professional. Reports are executive-ready.

### Week 7

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon-Tue | InsightGenerationAgent: category detection, LLM synthesis | `agents/insight_generation.py` | `tests/unit/agents/test_insights.py` |
| Wed | InsightGenerationAgent: ranking, confidence scoring | `agents/insight_generation.py` | (extend above) |
| Thu-Fri | VisualizationAgent: chart selection logic, dashboard layout | `agents/visualization.py` | `tests/unit/agents/test_viz_v2.py` |

### Week 8

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon | VisualizationAgent: KPI cards, executive styling | `agents/visualization.py` | (extend above) |
| Tue | Jinja2 templates: report.html, dashboard.html, executive_summary.html | `infrastructure/templates/*.jinja2` | — (tested via integration) |
| Wed-Thu | ExecutiveReportAgent: HTML + PDF + JSON generation | `agents/reporting.py` | `tests/unit/agents/test_report_v2.py` |
| Fri | Full pipeline integration test on 5 sample datasets | — | `tests/integration/test_full_pipeline.py` |

---

## Sprint 5: Web Interface (Week 9-10)

**Goal:** Browser-based upload, real-time graph visualization, report viewing.

**Entry Criteria:** Sprint 4 complete
**Exit Criteria:** User can upload via browser, see graph executing in real-time, and view/download reports.

### Week 9

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon | FastAPI app: project structure, CORS, error handlers | `presentation/api/app.py` | `tests/unit/api/test_app.py` |
| Tue | API routes: POST /analyze (upload), GET /status/{id} | `presentation/api/routes/analysis.py` | `tests/unit/api/test_routes.py` |
| Wed | API routes: GET /results/{id}, GET /download/{id}/{format} | `presentation/api/routes/results.py` | (extend above) |
| Thu | WebSocket: real-time agent status events | `presentation/api/websocket.py` | `tests/unit/api/test_websocket.py` |
| Fri | API integration tests | — | `tests/integration/test_api.py` |

### Week 10

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon | Web UI: upload page (drag-and-drop, file validation) | `presentation/web/index.html`, `js/upload.js` | — (manual test) |
| Tue-Wed | Web UI: graph visualization (SVG nodes, WebSocket updates) | `presentation/web/js/graph.js`, `css/graph.css` | — (manual test) |
| Thu | Web UI: results page (report viewer, download buttons) | `presentation/web/js/results.js` | — (manual test) |
| Fri | End-to-end web test: upload → graph → report | — | Manual QA |

---

## Sprint 6: Polish & Release (Week 11-12)

**Goal:** Production quality. Documentation. Release.

**Entry Criteria:** Sprint 5 complete
**Exit Criteria:** 85% coverage. README v2 complete. Sample outputs committed. v2.0.0 tagged.

### Week 11

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon-Tue | Push test coverage to 85% (fill gaps) | `tests/**/*.py` | — |
| Wed | Performance profiling and optimization | — | — |
| Thu | Security review: path traversal, injection, API key handling | — | `tests/unit/test_security.py` |
| Fri | Sample dataset gallery: run on 5 domains, commit outputs | `datasets/`, `docs/examples/` | — |

### Week 12

| Day | Task | Files | Tests |
|---|---|---|---|
| Mon | README v2: installation, usage, screenshots | `README.md` | — |
| Tue | API documentation: OpenAPI examples, usage guide | `docs/v2/API.md` | — |
| Wed | Changelog, migration guide from v1 | `CHANGELOG.md`, `docs/v2/MIGRATION.md` | — |
| Thu | Final QA: full test suite, manual web test, report review | — | Full suite |
| Fri | Tag v2.0.0, create GitHub release, write release notes | — | — |

---

## Risk Buffers

Each sprint includes 1 buffer day (Friday review) for:
- Unexpected complexity
- Bug fixes from prior sprints
- Integration issues

**Total buffer: 6 days across 12 weeks.**
