# Changelog

All notable changes to DataForge AI project will be documented in this file.

## [Unreleased]

### Added
- StatisticalAnalysisAgent for statistical analysis
- VisualizationAgent for data visualization
- ReportingAgent for HTML and JSON report generation
- Integrated all 7 agents into LangGraph workflow
- Fixed planner routing with explicit agent-to-node mapping
- Fixed next_agent_suggestion not being saved in agent history
- Fixed logger Unicode encoding issues for Windows console
- Fixed profiling agent categorical column detection (≤10 unique OR <20% ratio)
- Fixed ReportingAgent format string error
- Fixed integration test data access patterns
- Fixed CLI to execute workflow (async/await supported)
- Added execute.py entry point for direct workflow execution
- Created demo datasets (employees.csv, products.csv)
- Increased test coverage to 76% (490/650 lines)
- Fixed all unit tests to pass (67 passed, 2 skipped)
- Integration tests passing (4 passed)
- CLI workflow execution verified
- Generated example outputs

### Changed
- Modified GraphState to use flexible `data` dict instead of individual fields
- Simplified workflow routing with explicit agent-to-node mapping  
- Updated logger icons to ASCII-compatible format
- Improved profiling agent categorical detection threshold
- Fixed CLI to use minimal LLM config (provider="openai", model="gpt-4")

### Fixed
- All unit tests passing (67 passed, 2 skipped)
- Fixed integration test data access patterns
- Fixed CLI TODO comment - now executes actual workflow
- Fixed CLI with async/await support

## [0.1.0] - 2025-01-28

### Added
- Core infrastructure: GraphState, LLMProvider, StructuredLogger, Agent base class
- 4 core agents implemented: Planner, Evaluator, Ingestion, Profiling
- Basic LangGraph workflow skeleton
- Unit tests for core components

### Changed
- Approved simplified architecture from architecture review
- Removed 15+ typed fields from GraphState
- Changed to unified `data` dict for flexibility

## [0.0.1] - 2025-01-28

### Added
- StatisticalAnalysisAgent with statistical analysis capabilities
- VisualizationAgent with visualization generation
- ReportingAgent with HTML/JSON report generation
- LangGraph workflow with conditional routing
- Integration tests for end-to-end workflow execution

### Changed
- CLI analysis command with async workflow execution
- Fixed agent routing with explicit agent-to-node mapping

### Fixed
- Agent routing issues with explicit name mapping
- DataProfilingAgent categorical column detection threshold improved
- ReportingAgent format string error

## [Unreleased]

No releases yet - This is the first release candidate.

---

**Release Date**: January 29, 2025
**Status**: Release Candidate 1 (RC1)

---

## Next Release (v1.1 - Planning)
- Enhanced CLI experience
- GitHub Actions CI/CD
- PyPI package publishing
- Example outputs added to repository
- API documentation (Sphinx/reST)
- Performance testing
- Security testing

---

## Roadmap

### v1.0 (Current)
- ✅ 7 specialized agents with unique responsibilities
- ✅ True graph workflow with dynamic branching
- ✅ CLI with async workflow execution
- ✅ 76% test coverage
- ✅ Demo datasets (employees.csv, products.csv)

### v1.5 (Planned)
- Custom agent plugins
- Enhanced visualizations
- More export formats
- Better CLI interface

### v2.0 (Planned)
- Web interface
- Database connectors
- Analysis history
- Multi-user support

---

**Built with ❤️ for the data science community**