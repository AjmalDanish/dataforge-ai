# DataForge AI v2.0 — INTERVIEW GUIDE

> Defense Guide & Architecture QA for System Design & Coding Interviews

---

## 1. High-Level Architecture Overview (The 2-Minute Elevator Pitch)

When asked *"Walk me through the system architecture of your project"*:

> "DataForge AI v2.0 is a graph-orchestrated, multi-agent business intelligence system designed under Clean Architecture principles.
> 
> The core system consists of 13 specialized agents coordinated by a central Planner node using **LangGraph**. The workflow follows a hub-and-spoke topology: every agent executes its specialized task on an immutable state object (`GraphState`) and returns control to the Planner, which dynamically evaluates state metadata to decide whether to advance to the next phase, execute parallel agents, retry on failure, or degrade gracefully.
> 
> The system processes raw datasets through 7 execution phases: Data Intake, Preparation (Cleaning), Data Understanding (Domain & Objectives), Deep Analysis (Profiling, Feature Engineering, KPIs), Statistical Analysis, Insight Synthesis, and Executive Output (Interactive Dashboards & PDF/HTML Reports). All infrastructure components—such as LLM providers, file readers, chart engines, and template renderers—are decoupled behind abstract interfaces using Dependency Injection."

---

## 2. Technical System Design QA (Deep Dives)

### Q1: Why did you choose LangGraph over traditional DAG schedulers like Airflow or Prefect?
**Answer:**
- **Agentic Decision Making:** Airflow and Prefect are static DAG schedulers meant for deterministic ETL. DataForge AI requires dynamic, conditional runtime routing where execution paths adapt based on intermediate data characteristics (e.g., skipping statistical tests for non-numeric data, or re-cleaning if domain detection uncovers semantic types).
- **Stateful Execution:** LangGraph provides native state management and checkpointing across graph iterations without requiring heavy database backends or external worker agents.
- **Lightweight Concurrency:** LangGraph integrates seamlessly with Python's native `asyncio` loop, allowing independent agents (like Schema, Domain, and Objective detection) to run concurrently via `asyncio.gather()`.

---

### Q2: How do you prevent infinite execution loops in a dynamic hub-and-spoke graph?
**Answer:**
We enforce a multi-layered guardrail strategy within the Planner node:
1. **Global Step Limit:** A hard counter tracks total graph transitions. If `global_step_count > 35`, the Planner forces terminal transition to the Output Phase using available state.
2. **Per-Agent Visit Counter:** Each agent has a maximum visit threshold (typically 2-3 attempts). If an agent exceeds its retry budget, the Planner marks it as permanently skipped and routes forward.
3. **Phase Monotonicity:** Execution follows 7 strictly ordered phases. The Planner is only allowed to step backward by **one phase** (e.g., Phase 3 back to Phase 2 for re-cleaning). Backward steps beyond one phase are blocked by guard policies.

---

### Q3: How does state management work, and how do you handle memory overhead with large datasets?
**Answer:**
- **Immutable Transitions:** `GraphState` is built using Pydantic v2. Agents do not mutate state in place; they return updated state copies via `model_copy(update={...})`.
- **Copy-on-Write & Data References:** Large objects like Pandas DataFrames are stored as dictionary references within `GraphState.data`. Standard shallow dictionary updates preserve DataFrame pointers without deep-copying underlying data blocks.
- **Checkpointing:** For state checkpointing and recovery, metadata is serialized to JSON while heavy DataFrames are written to optimized Parquet files on disk.

---

### Q4: How do you handle LLM unreliability, rate limits, and latency?
**Answer:**
- **Rule-Based Fallbacks:** Every LLM-assisted agent (Domain Detection, Objective Detection, KPI Discovery, Insight Synthesis) has a fully deterministic rule-based fallback (e.g., keyword dictionary matching, pre-defined KPI templates). The system completes successfully even if `OPENAI_API_KEY` is absent or rate-limited.
- **Exponential Backoff & Retry:** The `LLMProvider` infrastructure layer wraps calls with exponential backoff for transient HTTP 429/5xx errors.
- **Parallel Dispatch:** Independent LLM calls are batched across concurrent async tasks, reducing total pipeline latency.

---

### Q5: How do you enforce Clean Architecture and prevent framework lock-in?
**Answer:**
- **Dependency Rule:** Core domain models (`GraphState`, `BusinessDomain`, `KPI`, `InsightModel`) have zero external framework imports.
- **Abstract Interfaces (Ports):** Infrastructure tools implement pure abstract base classes (`FileReader`, `ChartEngine`, `ReportRenderer`, `LLMProvider`).
- **Dependency Injection:** Agents accept interface abstractions via constructor injection rather than instantiating third-party libraries directly. Swapping Plotly for Matplotlib or OpenAI for Anthropic requires zero changes inside agent logic.

---

## 3. Live Coding & Refactoring Scenarios

### Scenario A: "Add a new Business Vertical to Domain Detection"
**How to answer/code:**
1. Open `dataforge/core/domain.py` and add the new domain enum (e.g., `LOGISTICS`).
2. Add domain signal keyword mappings in `DomainRegistry`.
3. Add domain KPI templates in `dataforge/agents/kpi_discovery.py`.
4. Run existing unit tests (`pytest tests/unit/agents/test_domain.py`).

### Scenario B: "Replace Plotly with a custom Matplotlib chart renderer"
**How to answer/code:**
1. Implement `MatplotlibChartEngine` inheriting from `ChartEngine` in `dataforge/infrastructure/charts/matplotlib_engine.py`.
2. Register the implementation in the DI Container (`dataforge/shared/container.py`).
3. No changes required in `VisualizationAgent` or `GraphState`.

---

## 4. Key Metrics to Memorize for Interviews

- **Graph Topology:** 13 Agents (1 Planner Hub + 12 Specialized Spoke Nodes) across 7 Execution Phases.
- **Test Suite:** 85%+ Test Coverage with `pytest` (Unit, Integration, and API test suites).
- **Supported Inputs:** CSV, Excel (`.xlsx`), Parquet (`.parquet`), JSON (`.json` / `.jsonl`).
- **Supported Formats:** HTML (Interactive), PDF (Print-Ready), JSON (Machine-Readable).
- **Execution Limits:** Max file size: 100MB, Max rows: 1,000,000, Max global graph steps: 35.
