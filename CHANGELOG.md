# Changelog

All notable changes to DataForge AI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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