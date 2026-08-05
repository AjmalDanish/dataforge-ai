# DataForge AI v2.0 — ROADMAP

> From v1.0 to v2.0 — The Evolutionary Path

---

## Version Strategy

```
main (v1.0.0)       →  v2-development     →  v2.0-alpha  →  v2.0-beta  →  v2.0 (Release)
  Frozen                  Active                Core agents    Web UI         Production
  CLI only                Sprint 1              Graph v2       Dashboard      Full docs
  CSV/Parquet             Foundation            Cleaning       Reports        85% coverage
```

**Branch Strategy:**
- `main`: v1.0.0 (Released, Frozen) — Only critical bug fixes allowed
- `v2-development`: Active v2 development — All engineering work happens here

---

## v1.1 — Stabilization (OPTIONAL)

**Goal:** Fix critical issues in v1 before starting v2 work. Do not add features.

**Status:** OPTIONAL — These tasks are NOT blockers for DataForge AI v2 development.

**Branch:** `main` (v1.0.0 frozen)

| # | Item | Priority | Est. |
|---|---|---|---|
| 1.1.1 | Wire LLMProvider into PlannerAgent (rule-based → LLM-assisted routing) | 🔴 High | 2d |
| 1.1.2 | Enforce max_file_size_mb and max_rows in DataIngestionAgent | 🔴 High | 1d |
| 1.1.3 | Upgrade langgraph from ^0.0.20 to latest stable | 🟠 Medium | 2d |
| 1.1.4 | Add per-agent timeout via asyncio.wait_for() | 🟠 Medium | 1d |
| 1.1.5 | Fix all critical TODO items from v1 TODO.md | 🟠 Medium | 2d |
| 1.1.6 | Add unit tests for VisualizationAgent and ReportingAgent | 🟠 Medium | 2d |
| 1.1.7 | Reach 80% test coverage | 🟡 Low | 1d |

**Subtotal: ~11 days**

---

## v2.0-alpha — Core Engine (6 weeks)

**Goal:** Build the v2 graph engine, new agents, and GraphState v2. CLI-only. No web UI.

### Sprint 1: Foundation (Week 1-2)

| # | Item | Priority | Est. |
|---|---|---|---|
| 2.1.1 | Implement GraphState v2 (typed accessors, phase tracking, per-agent visit counts) | 🔴 | 3d |
| 2.1.2 | Implement BaseAgent v2 (retry_policy, failure_policy, required_inputs, produced_outputs) | 🔴 | 2d |
| 2.1.3 | Implement Core domain models (BusinessDomain, KPI, CleaningRule, InsightModel) | 🔴 | 2d |
| 2.1.4 | Implement DI Container (agent assembly with injected dependencies) | 🟠 | 1d |
| 2.1.5 | Implement Infrastructure interfaces (FileReader, ChartEngine, ReportRenderer) | 🟠 | 2d |

### Sprint 2: Data Agents (Week 3-4)

| # | Item | Priority | Est. |
|---|---|---|---|
| 2.2.1 | Implement DataValidationAgent (expand from v1 IngestionAgent) | 🔴 | 2d |
| 2.2.2 | Implement DataCleaningAgent (entirely new) | 🔴 | 4d |
| 2.2.3 | Implement SchemaDetectionAgent (semantic types, keys, relationships) | 🔴 | 3d |
| 2.2.4 | Implement CSV, Excel, Parquet, JSON file readers | 🟠 | 2d |
| 2.2.5 | Unit tests for all Sprint 2 agents | 🟠 | 2d |

### Sprint 3: Business Intelligence Agents (Week 5-6)

| # | Item | Priority | Est. |
|---|---|---|---|
| 2.3.1 | Implement BusinessDomainDetectionAgent (LLM + rule-based) | 🔴 | 3d |
| 2.3.2 | Implement BusinessObjectiveDetectionAgent (LLM-powered) | 🔴 | 2d |
| 2.3.3 | Implement KPIDiscoveryAgent (domain templates + LLM) | 🔴 | 3d |
| 2.3.4 | Implement FeatureEngineeringAgent | 🟠 | 3d |
| 2.3.5 | Update PlannerAgent for v2 (phase-based, quality gates, parallel dispatch) | 🔴 | 3d |
| 2.3.6 | Build v2 graph (all 13 agents wired into LangGraph) | 🔴 | 2d |
| 2.3.7 | Unit tests for all Sprint 3 agents | 🟠 | 2d |

**Alpha Milestone:** All 13 agents functional. Graph routes correctly. CLI produces results.

---

## v2.0-beta — Output Quality (4 weeks)

**Goal:** Executive-grade reports, dashboards, and web UI.

### Sprint 4: Insight & Visualization (Week 7-8)

| # | Item | Priority | Est. |
|---|---|---|---|
| 2.4.1 | Implement InsightGenerationAgent (LLM synthesis of all prior analysis) | 🔴 | 3d |
| 2.4.2 | Enhance VisualizationAgent (dashboard layout, KPI cards, chart selection) | 🔴 | 3d |
| 2.4.3 | Implement Jinja2 report templates (HTML + dashboard) | 🟠 | 2d |
| 2.4.4 | Implement ExecutiveReportAgent (HTML + PDF + JSON) | 🔴 | 3d |
| 2.4.5 | Integration test: full pipeline on 5+ sample datasets | 🟠 | 2d |

### Sprint 5: Web Interface (Week 9-10)

| # | Item | Priority | Est. |
|---|---|---|---|
| 2.5.1 | Implement FastAPI application (upload, status, results endpoints) | 🔴 | 2d |
| 2.5.2 | Implement WebSocket for real-time graph node updates | 🟠 | 2d |
| 2.5.3 | Build Web UI: upload page | 🟠 | 1d |
| 2.5.4 | Build Web UI: graph visualization (node status, execution flow) | 🔴 | 3d |
| 2.5.5 | Build Web UI: results/report viewer | 🟠 | 2d |
| 2.5.6 | API tests with httpx AsyncClient | 🟠 | 1d |

**Beta Milestone:** Web UI functional. Reports are executive-grade. Dashboard is interactive.

---

## v2.0 — Release (2 weeks)

**Goal:** Polish, documentation, testing, release.

### Sprint 6: Polish & Release (Week 11-12)

| # | Item | Priority | Est. |
|---|---|---|---|
| 2.6.1 | Reach 85% test coverage | 🔴 | 2d |
| 2.6.2 | Complete README v2 | 🟠 | 1d |
| 2.6.3 | API documentation (OpenAPI auto-generated + examples) | 🟠 | 1d |
| 2.6.4 | Sample dataset gallery (5 domains, with expected outputs) | 🟠 | 2d |
| 2.6.5 | Performance optimization (profile bottlenecks, optimize hot paths) | 🟠 | 2d |
| 2.6.6 | Security review (path traversal, injection, API key exposure) | 🟠 | 1d |
| 2.6.7 | GitHub release (tag, changelog, release notes) | 🟡 | 1d |

**Release Milestone:** v2.0.0 tagged. Production-ready. Documentation complete.

---

## Post-v2.0 Roadmap

### v2.5 (3 months post-release)
- Database connectors (PostgreSQL, MySQL, SQLite via SQLAlchemy)
- Docker container + docker-compose
- Custom agent plugin system
- Analysis history (SQLite-backed)
- Comparison mode (compare two datasets)

### v3.0 (6 months post-release)
- Multi-user support with authentication
- Real-time streaming data support
- Natural language Q&A ("Ask your data")
- Advanced ML integration (scikit-learn models)
- Collaborative analysis (shared workspaces)

---

## Effort Summary

| Phase | Duration | Effort (person-days) |
|---|---|---|
| v1.1 Stabilization | 2 weeks | 11 days |
| v2.0-alpha (Core Engine) | 6 weeks | ~36 days |
| v2.0-beta (Output + Web) | 4 weeks | ~24 days |
| v2.0 Release | 2 weeks | ~10 days |
| **Total** | **14 weeks** | **~81 person-days** |

**Solo developer pace:** ~14 weeks (3.5 months)
**Two-developer pace:** ~8 weeks (2 months)
