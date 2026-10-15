# Changelog

All notable changes to DataForge AI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-10-15

### Added
- **v2 pipeline**: 13 agents across 7 phases — validation, cleaning, schema, business domain, business objectives, profiling, feature engineering, KPI discovery, statistics, insight generation, visualization, evaluation, reporting.
- **Planner v2**: precondition-based scheduling, retry-then-skip quality gate, evaluator remediation loop, step budget with best-effort reporting, phase tracking.
- **LLM integration** (optional): executive narrative + recommendations, domain tie-breaking, objective generation; Anthropic (`claude-opus-5-5`, server-side refusal fallback) or OpenAI, selected from the environment.
- **Executive PDF report** (ReportLab) alongside HTML and JSON.
- **FastAPI backend**: streaming uploads, per-agent WebSocket events, report asset serving, PDF download, persisted run metadata, optional admin token for deletes.
- **Next.js frontend**: live 7-phase agent graph, activity log, narrative, KPI cards, insights, chart viewer, one-click samples.
- `run_workflow()` helper shared by the CLI and API; Dockerfile; GitHub Actions CI (Python 3.11–3.13, frontend build, Docker smoke test).

### Fixed
- CLI, `run.py` and tests used `recursion_limit=25`, so the 24+-step pipeline always failed with `GraphRecursionError`.
- Report HTML embedded column names and values unescaped (stored XSS via a crafted file).
- Text columns were converted to dates when a single value parsed as a date, wiping the other values.
- KPIs fell back to the first numeric column when no column matched (e.g. "Average Salary" computed over `id`); revenue KPIs were computed from `price`.
- Identifier columns were profiled, correlated and charted.
- Agent timeouts were declared but never enforced; an agent failing input validation was rescheduled indefinitely.
- Each chart embedded its own copy of plotly.js (~5 MB per chart, ~100 MB per run); scatter trend lines required the missing `statsmodels`.
- Statistics ran on raw instead of cleaned data; `BusinessDomain` serialized as `BusinessDomain.HR`.
- The API ran analyses on the event loop, freezing status polling and WebSockets during a run.

### Changed
- Anthropic provider updated for current models (no `temperature`, text read from text blocks only, refusals surfaced as errors).
- Removed the v1 linear routing and `execute.py`; `python -m dataforge analyze` and `run.py` are the entry points.
- Dependencies trimmed to what the code imports; `requirements*.txt` added.

## [1.0.0] - 2024-07-31

### Added
- **Complete Autonomous Multi-Agent System**: 7 specialized AI agents orchestrated through LangGraph
- **True Graph Workflow**: Dynamic branching with Planner Agent decision engine
- **Quality Gates**: Evaluator Agent validates results and triggers automatic remediation
- **Comprehensive Analysis**: Data ingestion, profiling, statistics, visualization, and reporting
- **Interactive Reports**: HTML reports with embedded Plotly visualizations
- **Structured Logging**: All operations logged with agent, duration, and decision data
- **CLI Interface**: Command-line interface with multiple entry points
- **Demo Datasets**: Employee and product datasets for immediate testing

### Fixed
- **Critical Blockers Resolved**:
  - Added missing `Optional` import in config.py
  - Fixed async execution in CLI analyze command
  - Fixed undefined `verbose` variable in execute.py
  - Removed broken import and undefined variables in run.py
  - Added logs to GraphState in agent execution
- **Test Suite**: All 72 tests passing (71 unit + integration, 2 skipped)
- **Code Quality**: 73% test coverage across all modules

### Changed
- **Architecture**: Simplified GraphState with flexible `data` dict
- **Workflow**: Explicit agent-to-node mapping for cleaner routing
- **Entry Points**: Simplified run.py and execute.py for direct execution
- **Version**: Upgraded from 0.1.0 to 1.0.0 (production ready)

### Known Limitations
- LLM integration deferred to v1.1 (PlannerAgent uses hardcoded routing)
- No caching mechanism for computed results
- No file size or row count limits
- No timeout enforcement for agent execution
- No parallel execution of independent agents
- Supports only CSV and Parquet formats

### Technical Details
- **Python**: 3.11+ with type hints throughout
- **Dependencies**: LangGraph (^0.0.20), Pandas, Plotly, SciPy, PyArrow, Pydantic
- **Testing**: pytest with asyncio support, 73% coverage
- **Code Quality**: black formatting, mypy type checking (Unix only)

---

## [0.1.0] - 2024-01-28

### Added
- Core infrastructure: GraphState, LLMProvider, StructuredLogger, Agent base class
- 4 core agents implemented: Planner, Evaluator, Ingestion, Profiling
- Basic LangGraph workflow skeleton
- Unit tests for core components

### Changed
- Approved simplified architecture from architecture review
- Removed 15+ typed fields from GraphState

---

## [Unreleased]

### Planned (v1.1)
- LLM Integration: Wire LLMProvider into PlannerAgent for AI-assisted routing
- Resource limits: Enforce max_file_size_mb and max_rows
- Per-agent timeout: Implement asyncio.wait_for() wrappers
- LangGraph upgrade: Upgrade to current stable version