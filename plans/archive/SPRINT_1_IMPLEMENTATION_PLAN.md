# DataForge AI v2.0 — Sprint 1 Implementation Plan

> **Sprint Goal:** Build the v2 core foundation — no agents yet, just the skeleton.

---

## Sprint Overview

| Attribute | Value |
|-----------|-------|
| **Sprint Number** | 1 |
| **Duration** | 2 weeks (10 working days) |
| **Focus** | Foundation |
| **Entry Criteria** | v1.1 complete |
| **Exit Criteria** | GraphState v2 passes all tests. BaseAgent v2 contract finalized. All core domain models defined. DI Container wires agents with dependencies. |

---

## 1. Sprint Goal

Build the v2 core foundation without implementing any agents yet. This sprint establishes the architectural skeleton that all subsequent sprints will build upon.

**Success Criteria:**
- GraphState v2 with typed accessors and phase tracking
- BaseAgent v2 with enhanced contract (retry_policy, failure_policy, timeout)
- Core domain models (BusinessDomain, KPI, InsightModel, etc.)
- Infrastructure interfaces (FileReader, ChartEngine, ReportRenderer)
- DI Container for dependency injection
- PlotlyChartEngine implementation
- HTMLRenderer implementation
- All components have unit tests
- Integration test validates foundation components work together

---

## 2. Task Order

### Week 1: Core Models and State

**Monday - Day 1: GraphState v2 - Part 1**
- Implement GraphState v2 with immutable state fields
- Add typed accessors for well-known state keys
- Add current_phase tracking (ExecutionPhase IntEnum 1-7)
- Add agent_visit_count dict
- Add global_step_count with max_global_steps limit
- Add steps_skipped list
- Add quality_warnings and quality_errors lists
- Remove v1 fields: validation_status, validation_errors, retry_count, max_retries
- Write unit tests for GraphState v2

**Files to Create:**
- `dataforge/core/models.py` - ExecutionPhase, RetryPolicy, FailurePolicy, AgentHistoryEntry, LogEntry

**Files to Modify:**
- `dataforge/core/state.py` - Complete restructure

**Tests to Create:**
- `tests/unit/core/test_state.py`
- `tests/unit/core/test_models.py`

**Tuesday - Day 2: GraphState v2 - Part 2**
- Implement checkpoint serialization (JSON for metadata)
- Implement checkpoint serialization (Parquet for DataFrames)
- Implement checkpoint restoration
- Add checkpoint methods to GraphState
- Write unit tests for checkpointing

**Files to Create:**
- `dataforge/graph/checkpointer.py` - Checkpointer class

**Files to Modify:**
- `dataforge/core/state.py` - Add checkpoint methods

**Tests to Create:**
- `tests/unit/core/test_checkpoint.py`

**Wednesday - Day 3: BaseAgent v2**
- Add phase attribute (ExecutionPhase)
- Add required_inputs declaration
- Add produced_outputs declaration
- Add retry_policy (RetryPolicy model)
- Add failure_policy (FailurePolicy enum)
- Add timeout_seconds
- Add can_execute(state) precondition checking
- Add quality_score to AgentResult
- Add execution_notes to AgentResult
- Write unit tests for BaseAgent v2

**Files to Modify:**
- `dataforge/agents/base.py` - Enhance BaseAgent class

**Tests to Modify:**
- `tests/unit/agents/test_base.py` - Update for v2 contract

**Thursday - Day 4: Core Domain Models - Part 1**
- Implement BusinessDomain enum
- Implement DomainRegistry with keyword dictionaries
- Implement KPI model
- Implement KPITemplates with domain-specific templates
- Write unit tests for domain models

**Files to Create:**
- `dataforge/core/domain.py` - BusinessDomain, DomainRegistry, KPI, KPITemplates

**Tests to Create:**
- `tests/unit/core/test_domain.py`

**Friday - Day 5: Core Domain Models - Part 2**
- Implement BusinessInsight model
- Implement InsightCategory enum
- Implement InsightSeverity enum
- Implement CleaningRule model
- Implement CleaningDecision model
- Implement SchemaInfo model
- Implement FileMetadata model
- Implement ValidationReport model
- Write unit tests for all models

**Files to Create:**
- `dataforge/core/insights.py` - BusinessInsight, InsightCategory, InsightSeverity
- `dataforge/core/cleaning.py` - CleaningRule, CleaningDecision
- `dataforge/core/models.py` - SchemaInfo, FileMetadata, ValidationReport (extend from Day 1)

**Tests to Create:**
- `tests/unit/core/test_insights.py`
- `tests/unit/core/test_cleaning.py`
- `tests/unit/core/test_models.py` (extend)

### Week 2: Infrastructure and DI

**Monday - Day 6: Infrastructure Interfaces**
- Implement FileReader ABC
- Implement ChartEngine ABC
- Implement ReportRenderer ABC
- Document all interface methods
- Write integration tests (via implementations)

**Files to Create:**
- `dataforge/core/interfaces.py` - FileReader, ChartEngine, ReportRenderer ABCs

**Tests to Create:**
- `tests/unit/core/test_interfaces.py` (abstract, tested via implementations)

**Tuesday - Day 7: DI Container**
- Implement DIContainer class
- Implement get_llm_provider() method
- Implement get_logger() method
- Implement get_chart_engine() method
- Implement get_report_renderer() method
- Implement get_file_reader() method
- Implement create_agent() method with dependency injection
- Implement create_all_agents() method
- Write unit tests for DIContainer

**Files to Create:**
- `dataforge/shared/container.py` - DIContainer class

**Tests to Create:**
- `tests/unit/shared/test_container.py`

**Wednesday - Day 8: PlotlyChartEngine**
- Implement PlotlyChartEngine class
- Implement create_bar_chart() method
- Implement create_line_chart() method
- Implement create_scatter_plot() method
- Implement create_histogram() method
- Implement create_box_plot() method
- Implement create_heatmap() method
- Implement create_kpi_card() method
- Write unit tests for PlotlyChartEngine

**Files to Create:**
- `dataforge/infrastructure/charts/__init__.py`
- `dataforge/infrastructure/charts/plotly_engine.py`

**Tests to Create:**
- `tests/unit/infra/test_plotly_engine.py`

**Thursday - Day 9: HTMLRenderer**
- Implement HTMLRenderer class
- Implement render_html() method using Jinja2
- Create basic report.html.jinja2 template
- Create basic dashboard.html.jinja2 template
- Create basic executive_summary.html.jinja2 template
- Write unit tests for HTMLRenderer

**Files to Create:**
- `dataforge/infrastructure/renderers/__init__.py`
- `dataforge/infrastructure/renderers/html_renderer.py`
- `dataforge/infrastructure/templates/report.html.jinja2`
- `dataforge/infrastructure/templates/dashboard.html.jinja2`
- `dataforge/infrastructure/templates/executive_summary.html.jinja2`

**Tests to Create:**
- `tests/unit/infra/test_html_renderer.py`

**Friday - Day 10: Sprint Review and Integration**
- Review all implemented components
- Write integration test for foundation
- Fix any bugs discovered
- Refactor as needed
- Document any deviations from plan
- Prepare Sprint 1 summary

**Files to Create:**
- `tests/integration/test_foundation.py`

**Files to Modify:**
- Any files requiring bug fixes or refactoring

---

## 3. Dependencies

### Internal Dependencies

```
ExecutionPhase (models.py)
    ↓
RetryPolicy, FailurePolicy (models.py)
    ↓
AgentHistoryEntry, LogEntry (models.py)
    ↓
GraphState v2 (state.py)
    ↓
BaseAgent v2 (agents/base.py)
    ↓
BusinessDomain, KPI (domain.py)
    ↓
InsightCategory, InsightSeverity (insights.py)
    ↓
CleaningRule, CleaningDecision (cleaning.py)
    ↓
FileReader, ChartEngine, ReportRenderer (interfaces.py)
    ↓
DIContainer (shared/container.py)
    ↓
PlotlyChartEngine (infrastructure/charts/plotly_engine.py)
    ↓
HTMLRenderer (infrastructure/renderers/html_renderer.py)
```

### External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| pydantic | ^2.7 | Data validation, models |
| pandas | ^2.2 | DataFrame handling (GraphState) |
| pyarrow | ^16.0 | Parquet serialization (checkpointing) |
| jinja2 | ^3.1 | HTML templates |
| plotly | ^5.22 | Chart generation |
| pytest | ^8.2 | Testing |
| pytest-asyncio | ^0.23 | Async testing |

---

## 4. Files to Modify

### Existing Files

| File | Changes |
|------|---------|
| `dataforge/core/state.py` | Complete restructure: add phases, typed accessors, checkpointing, remove v1 fields |
| `dataforge/agents/base.py` | Add phase, retry_policy, failure_policy, timeout_seconds, can_execute(), quality_score, execution_notes |
| `dataforge/core/llm.py` | Add token_budget parameter to LLMConfig (optional, can defer) |
| `dataforge/shared/config.py` | Add new settings for v2 (checkpointing, timeouts, etc.) |
| `tests/unit/agents/test_base.py` | Update tests for v2 BaseAgent contract |
| `pyproject.toml` | Update dependencies (add jinja2, upgrade langgraph) |

---

## 5. Files to Create

### Core Layer

| File | Purpose |
|------|---------|
| `dataforge/core/models.py` | ExecutionPhase, RetryPolicy, FailurePolicy, AgentHistoryEntry, LogEntry, SchemaInfo, FileMetadata, ValidationReport |
| `dataforge/core/domain.py` | BusinessDomain enum, DomainRegistry, KPI model, KPITemplates |
| `dataforge/core/insights.py` | BusinessInsight model, InsightCategory enum, InsightSeverity enum |
| `dataforge/core/cleaning.py` | CleaningRule model, CleaningDecision model |
| `dataforge/core/interfaces.py` | FileReader ABC, ChartEngine ABC, ReportRenderer ABC |

### Graph Layer

| File | Purpose |
|------|---------|
| `dataforge/graph/checkpointer.py` | Checkpointer class for state persistence |

### Infrastructure Layer

| File | Purpose |
|------|---------|
| `dataforge/infrastructure/charts/__init__.py` | Charts module init |
| `dataforge/infrastructure/charts/plotly_engine.py` | PlotlyChartEngine implementation |
| `dataforge/infrastructure/renderers/__init__.py` | Renderers module init |
| `dataforge/infrastructure/renderers/html_renderer.py` | HTMLRenderer implementation |
| `dataforge/infrastructure/templates/report.html.jinja2` | Report template |
| `dataforge/infrastructure/templates/dashboard.html.jinja2` | Dashboard template |
| `dataforge/infrastructure/templates/executive_summary.html.jinja2` | Executive summary template |

### Shared Layer

| File | Purpose |
|------|---------|
| `dataforge/shared/container.py` | DIContainer for dependency injection |

### Tests

| File | Purpose |
|------|---------|
| `tests/unit/core/test_state.py` | GraphState v2 tests |
| `tests/unit/core/test_models.py` | Core models tests |
| `tests/unit/core/test_checkpoint.py` | Checkpointing tests |
| `tests/unit/core/test_domain.py` | Domain models tests |
| `tests/unit/core/test_insights.py` | Insight models tests |
| `tests/unit/core/test_cleaning.py` | Cleaning models tests |
| `tests/unit/core/test_interfaces.py` | Interface tests (via implementations) |
| `tests/unit/shared/test_container.py` | DIContainer tests |
| `tests/unit/infra/test_plotly_engine.py` | PlotlyChartEngine tests |
| `tests/unit/infra/test_html_renderer.py` | HTMLRenderer tests |
| `tests/integration/test_foundation.py` | Foundation integration tests |

---

## 6. Risks

### Technical Risks

| Risk | Probability | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| Immutable state increases memory usage | Medium | Medium | 🟡 Medium | Use copy-on-write, DataFrame references, shallow dict copies |
| Typed accessors add boilerplate | Low | Low | 🟢 Low | Acceptable trade-off for type safety and IDE support |
| Checkpointing adds complexity | Medium | Medium | 🟡 Medium | Keep simple: JSON + Parquet, test thoroughly |
| DI Container adds complexity | Medium | Low | 🟢 Low | Keep simple: manual wiring, clear documentation |
| Jinja2 template learning curve | Low | Low | 🟢 Low | Simple templates, use existing examples |

### Project Risks

| Risk | Probability | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| Sprint 1 scope creep | Medium | Medium | 🟡 Medium | Strict task list, no agents in Sprint 1 |
| Underestimating GraphState complexity | Medium | Medium | 🟡 Medium | Buffer day on Friday, prioritize core features |
| Test coverage drops | Medium | Medium | 🟡 Medium | Write tests in same day as implementation |

---

## 7. Expected Test Changes

### New Test Files

1. **`tests/unit/core/test_state.py`**
   - Test GraphState creation
   - Test typed accessors
   - Test phase tracking
   - Test agent_visit_count
   - Test global_step_count
   - Test steps_skipped
   - Test quality_warnings and quality_errors
   - Test immutability (model_copy)

2. **`tests/unit/core/test_models.py`**
   - Test ExecutionPhase enum
   - Test RetryPolicy model
   - Test FailurePolicy enum
   - Test AgentHistoryEntry model
   - Test LogEntry model
   - Test SchemaInfo model
   - Test FileMetadata model
   - Test ValidationReport model

3. **`tests/unit/core/test_checkpoint.py`**
   - Test checkpoint serialization (JSON)
   - Test checkpoint serialization (Parquet)
   - Test checkpoint restoration
   - Test checkpoint with large DataFrames

4. **`tests/unit/core/test_domain.py`**
   - Test BusinessDomain enum values
   - Test DomainRegistry keyword matching
   - Test DomainRegistry column classification
   - Test KPI model
   - Test KPITemplates for each domain

5. **`tests/unit/core/test_insights.py`**
   - Test BusinessInsight model
   - Test InsightCategory enum
   - Test InsightSeverity enum

6. **`tests/unit/core/test_cleaning.py`**
   - Test CleaningRule model
   - Test CleaningDecision model

7. **`tests/unit/core/test_interfaces.py`**
   - Test FileReader ABC (via mock)
   - Test ChartEngine ABC (via mock)
   - Test ReportRenderer ABC (via mock)

8. **`tests/unit/shared/test_container.py`**
   - Test DIContainer creation
   - Test get_llm_provider()
   - Test get_logger()
   - Test get_chart_engine()
   - Test get_report_renderer()
   - Test get_file_reader()
   - Test create_agent() with dependencies
   - Test create_all_agents()

9. **`tests/unit/infra/test_plotly_engine.py`**
   - Test create_bar_chart()
   - Test create_line_chart()
   - Test create_scatter_plot()
   - Test create_histogram()
   - Test create_box_plot()
   - Test create_heatmap()
   - Test create_kpi_card()

10. **`tests/unit/infra/test_html_renderer.py`**
    - Test render_html()
    - Test template rendering
    - Test template context passing

11. **`tests/integration/test_foundation.py`**
    - Test GraphState + BaseAgent integration
    - Test DIContainer + agents integration
    - Test PlotlyChartEngine + VisualizationAgent integration (mock)
    - Test HTMLRenderer + ReportingAgent integration (mock)
    - Test checkpointing end-to-end

### Modified Test Files

1. **`tests/unit/agents/test_base.py`**
   - Update for BaseAgent v2 contract
   - Test phase attribute
   - Test required_inputs
   - Test produced_outputs
   - Test retry_policy
   - Test failure_policy
   - Test timeout_seconds
   - Test can_execute()
   - Test quality_score in AgentResult
   - Test execution_notes in AgentResult

---

## 8. Expected Commit Strategy

### Commit Pattern

Each logical unit of work should be committed with a clear, descriptive message following conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Maintenance tasks

### Planned Commits

**Week 1:**

1. `feat(core): add ExecutionPhase, RetryPolicy, FailurePolicy models`
2. `feat(core): add AgentHistoryEntry, LogEntry models`
3. `feat(core): implement GraphState v2 with typed accessors and phase tracking`
4. `feat(core): add checkpoint serialization to GraphState`
5. `feat(graph): implement Checkpointer class`
6. `feat(agents): enhance BaseAgent with phase, retry_policy, failure_policy`
7. `feat(core): implement BusinessDomain enum and DomainRegistry`
8. `feat(core): implement KPI model and KPITemplates`
9. `feat(core): implement BusinessInsight model and enums`
10. `feat(core): implement CleaningRule and CleaningDecision models`
11. `feat(core): implement SchemaInfo, FileMetadata, ValidationReport models`

**Week 2:**

12. `feat(core): add FileReader, ChartEngine, ReportRenderer interfaces`
13. `feat(shared): implement DIContainer for dependency injection`
14. `feat(infrastructure): implement PlotlyChartEngine`
15. `feat(infrastructure): implement HTMLRenderer with Jinja2 templates`
16. `test(core): add comprehensive unit tests for core models`
17. `test(core): add comprehensive unit tests for GraphState`
18. `test(infrastructure): add unit tests for PlotlyChartEngine`
19. `test(infrastructure): add unit tests for HTMLRenderer`
20. `test(integration): add foundation integration tests`
21. `chore(sprint): complete Sprint 1 foundation`

### Branch Protection

- All commits go to `v2-development` branch
- NO commits to `main` branch
- `main` is frozen at v1.0.0

---

## 9. Acceptance Criteria

### Must Have (Blocking)

- [ ] GraphState v2 implements all required fields
- [ ] GraphState v2 has typed accessors for all well-known state keys
- [ ] GraphState v2 supports 7 execution phases
- [ ] GraphState v2 tracks agent_visit_count per agent
- [ ] GraphState v2 has global_step_count with max_global_steps limit
- [ ] GraphState v2 has steps_skipped list
- [ ] GraphState v2 has quality_warnings and quality_errors lists
- [ ] GraphState v2 supports checkpoint serialization (JSON + Parquet)
- [ ] GraphState v2 supports checkpoint restoration
- [ ] BaseAgent v2 has phase attribute
- [ ] BaseAgent v2 has required_inputs declaration
- [ ] BaseAgent v2 has produced_outputs declaration
- [ ] BaseAgent v2 has retry_policy
- [ ] BaseAgent v2 has failure_policy
- [ ] BaseAgent v2 has timeout_seconds
- [ ] BaseAgent v2 has can_execute() method
- [ ] AgentResult has quality_score
- [ ] AgentResult has execution_notes
- [ ] BusinessDomain enum has 10 domains
- [ ] DomainRegistry has keyword dictionaries for all domains
- [ ] KPI model is defined with required fields
- [ ] KPITemplates has templates for all domains
- [ ] BusinessInsight model is defined
- [ ] InsightCategory enum has 8 categories
- [ ] InsightSeverity enum is defined
- [ ] CleaningRule model is defined
- [ ] CleaningDecision model is defined
- [ ] SchemaInfo model is defined
- [ ] FileMetadata model is defined
- [ ] ValidationReport model is defined
- [ ] FileReader ABC is defined with read() and validate_format()
- [ ] ChartEngine ABC is defined with all chart methods
- [ ] ReportRenderer ABC is defined with render_html(), render_pdf(), render_json()
- [ ] DIContainer is implemented
- [ ] DIContainer can create LLMProvider
- [ ] DIContainer can create StructuredLogger
- [ ] DIContainer can create ChartEngine
- [ ] DIContainer can create ReportRenderer
- [ ] DIContainer can create FileReader
- [ ] DIContainer can create agents with dependencies
- [ ] PlotlyChartEngine implements all ChartEngine methods
- [ ] HTMLRenderer implements render_html() with Jinja2
- [ ] HTMLRenderer has basic templates
- [ ] All components have unit tests
- [ ] Unit tests pass (pytest)
- [ ] Integration test passes
- [ ] Test coverage ≥ 80% for foundation components

### Should Have (Non-blocking but important)

- [ ] GraphState v2 has comprehensive docstrings
- [ ] BaseAgent v2 has comprehensive docstrings
- [ ] All domain models have comprehensive docstrings
- [ ] All interfaces have comprehensive docstrings
- [ ] DIContainer has comprehensive docstrings
- [ ] PlotlyChartEngine has comprehensive docstrings
- [ ] HTMLRenderer has comprehensive docstrings
- [ ] All tests have docstrings
- [ ] Code follows PEP 8 style
- [ ] Code passes mypy type checking
- [ ] Code passes ruff linting

### Nice to Have (Optional)

- [ ] GraphState v2 has performance benchmarks
- [ ] Checkpointing has performance benchmarks
- [ ] DIContainer has example usage in docstrings
- [ ] PlotlyChartEngine has example charts in docstrings
- [ ] HTMLRenderer has example templates in docstrings

---

## 10. Definition of Done

Sprint 1 is considered **DONE** when:

1. **All Must Have acceptance criteria are met**
2. **All unit tests pass** (pytest)
3. **Integration test passes**
4. **Test coverage ≥ 80%** for foundation components
5. **Code is committed** to `v2-development` branch
6. **Code is pushed** to `origin/v2-development`
7. **Sprint 1 summary** is documented
8. **Sprint 2 planning** can begin

---

## 11. Sprint 1 Deliverables

### Code Deliverables

1. **GraphState v2** - Complete restructure with all v2 features
2. **BaseAgent v2** - Enhanced contract with all v2 attributes
3. **Core domain models** - All models defined and tested
4. **Infrastructure interfaces** - All ABCs defined
5. **DIContainer** - Complete implementation with tests
6. **PlotlyChartEngine** - Complete implementation with tests
7. **HTMLRenderer** - Complete implementation with templates and tests
8. **Checkpointer** - Complete implementation with tests

### Documentation Deliverables

1. **Sprint 1 summary** - What was accomplished, what was deferred
2. **Updated architecture** - Any deviations from plan documented
3. **Known issues** - Any bugs or limitations discovered

### Test Deliverables

1. **Unit tests** - All foundation components have unit tests
2. **Integration test** - Foundation components work together
3. **Test coverage report** - ≥ 80% coverage

---

## 12. Sprint 1 Risks and Mitigation

### Risk: GraphState v2 complexity underestimated

**Probability:** Medium  
**Impact:** Medium  
**Mitigation:**
- Prioritize core features first
- Defer advanced features (e.g., complex checkpointing) if needed
- Use Friday buffer day for catch-up

### Risk: Immutable state memory usage

**Probability:** Medium  
**Impact:** Medium  
**Mitigation:**
- Use shallow dict copies
- Use DataFrame references (not deep copies)
- Profile memory usage
- Document memory expectations

### Risk: DI Container complexity

**Probability:** Low  
**Impact:** Low  
**Mitigation:**
- Keep DI Container simple (manual wiring)
- Clear documentation
- Comprehensive tests

### Risk: Jinja2 learning curve

**Probability:** Low  
**Impact:** Low  
**Mitigation:**
- Start with simple templates
- Use Jinja2 documentation
- Basic HTML templates are sufficient for Sprint 1

---

## 13. Sprint 1 Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Tasks completed | 100% (21 tasks) | Task checklist |
| Unit tests passing | 100% | pytest |
| Integration test passing | 100% | pytest |
| Test coverage | ≥ 80% | pytest-cov |
| Code committed | 100% | git log |
| Code pushed | 100% | git log --origin |
| Documentation complete | 100% | Sprint summary |

---

## 14. Next Steps (After Sprint 1)

1. **Sprint 1 review** - Review what was accomplished
2. **Sprint 2 planning** - Plan data pipeline agents
3. **Begin Sprint 2** - Start implementing data agents

---

**Plan Status:** Ready for Approval  
**Generated:** 2026-08-03  
**Author:** Code Mode  
**Version:** 1.0