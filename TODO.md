# DataForge AI — TODO

> Priority: 🔴 Critical Blocker | 🟠 High | 🟡 Medium | 🟢 Low / Enhancement

---

## CRITICAL BLOCKERS (Must fix before any user can run the system)

- [x] 🔴 **`config.py`**: Add `from typing import Optional` (or replace `Optional[str]` with `str | None`) — currently causes `NameError` on import, breaking the entire application
- [x] 🔴 **`cli.py` `analyze` command**: Wrap `await workflow.ainvoke()` in `asyncio.run()` — the `await` in a synchronous Click handler is invalid and crashes at runtime
- [x] 🔴 **`execute.py`**: Define `verbose` variable before the try-except block on line 97 — currently raises `NameError`
- [x] 🔴 **`run.py`**: Remove broken `from dataforge.presentation.cli import analyze_sync` import — that symbol does not exist
- [x] 🔴 **`run.py`**: Fix undefined `verbose` and `output` references inside the inner `analyze_sync` closure — or replace `run.py` with a clean `asyncio.run(workflow.ainvoke(...))` wrapper

---

## ARCHITECTURE

- [ ] 🟠 **Make hardcoded thresholds configurable**: Move these from agent source code into `Settings`:
  - Categorical detection threshold (<=10 unique or <20% ratio) — `profiling.py`
  - Correlation significance threshold (`|r| > 0.5`) — `statistics.py`
  - Minimum insight count for evaluation (`3`) — `evaluator.py`
  - Minimum agent depth count (`3`) — `evaluator.py`
  - Max visualizations (`6`) — `visualization.py` / `config.py`
- [ ] 🟡 **Caching layer**: Cache computed profile and statistics results keyed by file hash to avoid re-computation on retry
- [ ] 🟡 **Parallel agent execution**: Where agents are independent, use `asyncio.gather()`
- [ ] 🟡 **Checkpoint / state persistence**: Serialize `GraphState` to disk after each agent completes so a crash is recoverable
- [ ] 🟡 **Deadlock detection**: Add a step counter or watchdog to detect if the planner loops on the same agent more than `max_retries` times
- [ ] 🟢 **Circuit breaker**: If an agent raises more than N exceptions, mark it as permanently failed and skip it

---

## CORE INFRASTRUCTURE

- [ ] 🟠 **Remove dual logging**: Agents currently log to both `state.logs` (via `state.add_log()`) and a separate `StructuredLogger` instance — pick one canonical path and remove the other
- [ ] 🟠 **`GraphState` input validation**: Validate `input_dataset_path` at construction time — check file extension, existence, and that it is non-empty
- [ ] 🟡 **`GraphState` typed data accessors**: Add typed properties or methods for well-known keys (`raw_data`, `profile`, `statistics`, etc.) to eliminate dict string-key access errors
- [ ] 🟡 **`StructuredLogger` file handler**: Write logs to file in real-time rather than only on explicit `export_logs()` call
- [ ] 🟢 **mypy compliance**: Fix all type errors flagged by `mypy --strict` and set up pre-commit hook

---

## AGENTS

### PlannerAgent
- [ ] 🟠 **LLM-assisted routing**: Replace hardcoded `if/elif` decision tree with an LLM prompt that reasons about `steps_completed` and `state.data` to determine next action
- [ ] 🟡 **Infinite loop guard**: Detect if `next_agent_suggestion` points to an already-completed agent and handle gracefully
- [ ] 🟡 **Decision confidence**: Return a confidence score with each routing decision for observability

### EvaluatorAgent
- [ ] 🟠 **Configurable thresholds**: Read validation thresholds from `Settings` not magic numbers
- [ ] 🟡 **Severity tiers**: Distinguish between critical failures (must retry) and warnings (proceed with degraded output)
- [ ] 🟡 **Remediation hints**: When returning `REPLAN`, include which specific agent to re-run and why

### DataIngestionAgent
- [ ] 🟠 **File size enforcement**: Reject files exceeding `settings.max_file_size_mb` before loading
- [ ] 🟠 **Row count enforcement**: Reject datasets exceeding `settings.max_rows` after initial load
- [ ] 🟡 **Corrupted file detection**: Validate CSV structure (consistent column counts) before returning success
- [ ] 🟡 **Progress feedback**: Log progress for large files (e.g., per 100k rows read)
- [ ] 🟢 **Additional formats**: Add support for JSON lines, Excel (`.xlsx`), and TSV

### DataProfilingAgent
- [ ] 🟡 **Temporal detection improvement**: Use `pd.to_datetime` with error catching for more reliable temporal column detection
- [ ] 🟡 **Profile caching**: Cache the profile dict keyed on `(file_path, file_mtime)` to avoid re-profiling on retry
- [ ] 🟢 **Outlier flagging during profiling**: Add IQR-based outlier flags to the profile

### StatisticalAnalysisAgent
- [ ] 🟡 **Shapiro-Wilk guard**: Skip normality test if `n < 3` (currently may fail silently)
- [ ] 🟡 **Correlation statistical significance**: Add p-value alongside r-value for all correlations
- [ ] 🟡 **Configurable correlation threshold**: Read from `Settings.correlation_threshold` instead of hardcoded `0.5`
- [ ] 🟢 **Time-series detection**: If a temporal column is present, add trend/seasonality analysis

### VisualizationAgent
- [ ] 🟡 **Error handling for Plotly failures**: Wrap each `go.Figure` call in try-except and skip failed charts gracefully
- [ ] 🟡 **Visualization caching**: Skip regenerating charts that already exist on disk
- [ ] 🟡 **Configurable max visualizations**: Read from `Settings.max_visualizations` consistently
- [ ] 🟢 **Custom styling**: Allow caller to pass a color theme or branding config

### ReportingAgent
- [ ] 🟡 **Externalize HTML template**: Move the report template to `dataforge/templates/report.html.jinja2`
- [ ] 🟡 **Markdown report**: Add an optional `.md` report alongside HTML and JSON
- [ ] 🟢 **Custom branding**: Accept a logo URL or color palette via settings

---

## GRAPH WORKFLOW

- [ ] 🟠 **Fix routing edge case**: If `agent_history` is empty and `route_from_planner` is called, it falls through to `END` silently — add a log warning
- [ ] 🟡 **Workflow visualization**: Generate a Mermaid diagram of the workflow topology in the report
- [ ] 🟡 **Upgrade `langgraph` API compatibility**: After upgrading the package, audit all StateGraph and `ainvoke` calls for API changes
- [ ] 🟢 **Workflow streaming**: Use `workflow.astream()` for real-time progress events

---

## CLI & ENTRY POINTS

- [ ] 🔴 **Fix `analyze` command async execution** (see Critical Blockers above)
- [ ] 🟠 **End-to-end CLI smoke test**: Add a pytest test that invokes the Click CLI runner against a real CSV and asserts `exit_code == 0`
- [ ] 🟠 **Progress reporting**: Add `click.progressbar` or rich `Progress` display while the workflow runs
- [ ] 🟡 **`--dry-run` flag**: Validate the dataset and print what agents would run without executing
- [ ] 🟡 **`--config` flag**: Accept a YAML/TOML config file to override `Settings` values per-run
- [ ] 🟡 **Clean up `run.py`**: Replace the broken Click-wrapper pattern with a clean `asyncio.run()` wrapper
- [ ] 🟡 **Clean up `execute.py`**: Fix the `verbose` NameError and the unclosed f-string on line 80
- [ ] 🟢 **`dataforge list-datasets` command**: Scan the `datasets/` directory and print available demo files

---

## TESTING

- [ ] 🟠 **Fix failing integration test**: `test_workflow_generates_all_expected_outputs` — investigate and fix data access pattern
- [ ] 🟠 **CLI e2e tests**: Add `CliRunner`-based tests that exercise the full `analyze` command path
- [ ] 🟠 **VisualizationAgent unit tests**: No tests currently exist for `VisualizationAgent` or `StatisticalAnalysisAgent`
- [ ] 🟠 **ReportingAgent unit tests**: Add tests verifying HTML and JSON report structure
- [ ] 🟡 **Performance tests**: Benchmark profiling and statistics on 100k-row and 1M-row datasets
- [ ] 🟡 **Security tests**: Test path traversal attempts in `input_dataset_path`, malformed CSV, encoding injection
- [ ] 🟡 **Failure injection tests**: Mock individual agents to raise exceptions and verify graceful degradation
- [ ] 🟡 **Coverage target**: Reach 85% coverage (currently 76%)
- [ ] 🟢 **Property-based tests**: Use `hypothesis` to generate random CSV structures

---

## DOCUMENTATION

- [ ] 🟠 **API documentation**: Set up Sphinx with `autodoc` to generate API reference from docstrings
- [ ] 🟠 **Example outputs**: Run the workflow on demo datasets and commit generated reports/charts to `docs/examples/`
- [ ] 🟡 **Jupyter tutorial notebook**: Create `notebooks/quickstart.ipynb` demonstrating end-to-end usage
- [ ] 🟡 **Fix README installation command**: Line 33 has malformed `pip install -e -r -e .`; correct to `pip install -e .`
- [ ] 🟡 **Architecture decision records (ADRs)**: Document key design decisions in `docs/decisions/`
- [ ] 🟢 **`docs/VISION.md`**: Create the VISION.md file referenced in README.md but currently missing

---

## RELEASE & DEVOPS

- [ ] 🟠 **GitHub Actions CI**: Add `.github/workflows/ci.yml` running `pytest --cov` on push/PR
- [ ] 🟠 **PyPI publishing**: Configure `pyproject.toml` for publishing and add `publish.yml` workflow
- [ ] 🟡 **GitHub issue templates**: Add bug report and feature request templates in `.github/ISSUE_TEMPLATE/`
- [ ] 🟡 **Pre-commit hooks**: Configure `black`, `isort`, `flake8`, and `mypy` as pre-commit hooks
- [ ] 🟡 **Git tags**: Create a `v0.1.0` tag; do not tag as `v1.0.0` until critical blockers are resolved
- [ ] 🟡 **`CONTRIBUTING.md`**: Write contribution guide covering setup, coding standards, and PR process
- [ ] 🟢 **`SECURITY.md`**: Document the security policy and responsible disclosure process
- [ ] 🟢 **Dependabot**: Enable Dependabot for automatic dependency update PRs

---

## VERSION 1.1 FEATURES (Post-Release Enhancements)

- [ ] 🟢 **`langgraph` version**: Upgrade `langgraph` from `^0.0.20` to the current stable version in `pyproject.toml` and verify all LangGraph API calls remain compatible
- [ ] 🟢 **LLM Integration**: Wire `LLMProvider` into at least one agent — `PlannerAgent` is the natural candidate for LLM-assisted routing decisions; without this the "AI-powered" claim is unfounded
- [ ] 🟢 **Resource limits**: Enforce `max_file_size_mb` and `max_rows` in `DataIngestionAgent` (settings values exist but are never checked)
- [ ] 🟢 **Per-agent timeout**: Implement `asyncio.wait_for()` wrappers around each agent's `execute()` call using `settings.execution_timeout`

---

## FUTURE FEATURES (v1.5 / v2.0)

- [ ] 🟢 **LLM-powered natural language insights**: Use `LLMProvider.generate()` in `ReportingAgent` to produce narrative text about the data
- [ ] 🟢 **LLM-assisted anomaly explanation**: Have an LLM explain why a detected outlier is significant
- [ ] 🟢 **Web interface**: FastAPI backend + HTML/JS frontend for drag-and-drop dataset upload
- [ ] 🟢 **Database connectors**: PostgreSQL, SQLite, BigQuery via SQLAlchemy
- [ ] 🟢 **Excel and JSON support**: Add to `DataIngestionAgent` using `openpyxl` / `pandas.read_json`
- [ ] 🟢 **Analysis history**: Store past runs in SQLite and allow comparison across runs
- [ ] 🟢 **Custom agent plugins**: Plugin system for user-defined agents via Python entry points
- [ ] 🟢 **ML agent**: Add a `ModelTrainingAgent` that fits scikit-learn models and reports performance
- [ ] 🟢 **Time-series agent**: Detect and analyze time-series datasets (trend, seasonality, forecasting)
