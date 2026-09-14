# DataForge AI v2.0 — TECH STACK

> Technology Choices — Every Decision Justified

---

## Selection Criteria

Every technology was selected against these criteria:
1. **Maturity** — Is it production-stable?
2. **Fit** — Does it solve the specific problem well?
3. **Maintainability** — Will it be easy to debug and upgrade?
4. **Community** — Is there active community support?
5. **Interview Signal** — Does it demonstrate engineering depth?
6. **Necessity** — Is it actually needed? (If not, don't add it.)

---

## Core Runtime

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **Python** | 3.12+ | Primary language | Ecosystem dominance in data/AI, async support, type hints |
| **Pydantic** | ^2.7 | Data validation, settings, models | The standard for Python data validation. Used in FastAPI, LangChain. |
| **asyncio** | stdlib | Async execution | Native Python concurrency for parallel agents |

---

## Graph Orchestration

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **LangGraph** | ^0.2.0 | Graph workflow engine | True conditional routing, state management, checkpointing. Upgraded from ^0.0.20 (v1). |

**Why LangGraph over alternatives:**
- **vs. Prefect/Airflow:** LangGraph is designed for agent workflows, not ETL. Lighter weight, Python-native.
- **vs. Custom graph:** LangGraph provides checkpointing, conditional edges, and streaming out of the box.
- **vs. LangChain:** LangGraph is the graph-orchestration component. We use it without the LangChain chain abstraction.

**Upgrade Note:** v1 used `langgraph ^0.0.20` (pre-stable). v2 targets `^0.2.0` (stable API with `StateGraph`, `CompiledGraph`, and `MemorySaver`).

---

## Data Processing

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **Pandas** | ^2.2 | Data manipulation | Industry standard. 100% of our data fits in memory (max 1M rows). |
| **NumPy** | ^1.26 | Numerical operations | Required by Pandas, SciPy. Mature. |
| **SciPy** | ^1.13 | Statistical tests | Shapiro-Wilk, Pearson, Spearman, ANOVA. No reinventing the wheel. |
| **PyArrow** | ^16.0 | Parquet I/O | Required for Parquet support. Also used for state checkpointing. |
| **openpyxl** | ^3.1 | Excel (.xlsx) reading | Standard library for Excel format. New in v2. |

**What we DON'T use and why:**
- **Polars:** Faster than Pandas, but Pandas ecosystem compatibility matters more. Polars could be a v3 optimization.
- **Dask:** Not needed. Our max dataset is 1M rows (fits in memory).
- **Spark:** Massive overkill. We're not processing terabytes.

---

## AI / LLM

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **OpenAI SDK** | ^1.30 | GPT-4o / GPT-4o-mini access | Primary LLM provider |
| **Anthropic SDK** | ^0.30 | Claude access | Secondary LLM provider |

**LLM Strategy:**
- LLM is used for: domain detection, objective detection, KPI discovery, insight generation, executive summaries
- LLM is NOT used for: data loading, cleaning, profiling, statistics, visualization
- **Fallback:** Every LLM-dependent agent has a rule-based fallback for when LLM is unavailable or too expensive
- **Token Budget:** Configurable per-agent token limits to control costs

**What we DON'T use:**
- **LangChain chains/agents:** We use LangGraph for orchestration but make direct LLM calls. LangChain's chain abstraction adds complexity without value for our use case.
- **Ollama (local models):** Supported via `base_url` configuration in OpenAI SDK (OpenAI-compatible API). No separate dependency needed.

---

## Visualization

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **Plotly** | ^5.22 | Interactive charts | Interactive HTML charts, publication quality, no server needed |

**What we DON'T use:**
- **Matplotlib:** Not interactive. Output is static PNG. Poor for dashboards.
- **Seaborn:** Built on Matplotlib. Same limitations.
- **Altair/Vega:** Good, but Plotly has broader adoption and Plotly Express is simpler.
- **D3.js:** We're a Python backend, not a JS frontend.

---

## Report Generation

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **Jinja2** | ^3.1 | HTML templating | Separates content from presentation. Industry standard. |
| **WeasyPrint** | ^62.0 | HTML → PDF conversion | CSS-based PDF generation. Better quality than reportlab. |

**Alternative considered:** Playwright PDF generation. WeasyPrint is lighter and doesn't require a browser binary.

---

## Web Layer

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **FastAPI** | ^0.111 | REST API + WebSocket | Async-native, auto-generated OpenAPI docs, WebSocket for real-time events |
| **Uvicorn** | ^0.30 | ASGI server | Production-grade server for FastAPI |

**Frontend (Web UI):**
- **Vanilla HTML + CSS + JavaScript** — No React, no Vue, no build tools
- **Why:** The UI is a workflow visualization + report viewer. It doesn't need a SPA framework.
- **WebSocket:** For real-time graph node status updates

**What we DON'T use:**
- **Flask:** Synchronous. FastAPI is async-native which matters for our concurrent agents.
- **Django:** Too heavy. We don't need ORM, admin panel, or template engine for views.
- **Streamlit:** Proprietary rendering model. We need control over the report layout.

---

## Logging & Observability

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **structlog** | ^24.1 | Structured logging | JSON-structured logs for machine parsing. Context injection. |

**What we DON'T add:**
- **OpenTelemetry:** Overkill for a single-process application. Can be added in v3.
- **Prometheus:** No long-running server to monitor in v2 MVP.

---

## Configuration

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **pydantic-settings** | ^2.3 | Settings management | Environment variable parsing, validation, type safety |
| **python-dotenv** | ^1.0 | .env file loading | Developer convenience for local API keys |

---

## Testing

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **pytest** | ^8.2 | Test framework | Industry standard. Fixtures, parametrize, async support. |
| **pytest-cov** | ^5.0 | Coverage reporting | Target: 85% |
| **pytest-asyncio** | ^0.23 | Async test support | Required for testing async agents |
| **pytest-mock** | ^3.14 | Mocking | Clean mock fixtures |
| **httpx** | ^0.27 | API test client | AsyncClient for testing FastAPI endpoints |

---

## Code Quality

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **ruff** | ^0.5 | Linter + formatter | Replaces black + isort + flake8. 10-100x faster. Single tool. |
| **mypy** | ^1.10 | Static type checking | Catches type errors before runtime |
| **pre-commit** | ^3.7 | Git hooks | Enforces quality checks before commit |

**v1 → v2 Change:** Replaced `black` + `isort` + `flake8` (three tools) with `ruff` (one tool, faster).

---

## Build & Package

| Technology | Version | Purpose | Justification |
|---|---|---|---|
| **Poetry** | ^1.8 | Dependency management | Reproducible builds, lock file, dev/prod separation |
| **Makefile** | — | Task runner | Common commands: `make test`, `make lint`, `make run` |

---

## Dependency Summary

### Production Dependencies (14)

```toml
[tool.poetry.dependencies]
python = "^3.12"
pydantic = "^2.7"
pydantic-settings = "^2.3"
langgraph = "^0.2.0"
pandas = "^2.2"
numpy = "^1.26"
scipy = "^1.13"
pyarrow = "^16.0"
openpyxl = "^3.1"
plotly = "^5.22"
jinja2 = "^3.1"
weasyprint = "^62.0"
fastapi = "^0.111"
uvicorn = "^0.30"
openai = "^1.30"
anthropic = "^0.30"
structlog = "^24.1"
python-dotenv = "^1.0"
```

### Development Dependencies (7)

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.2"
pytest-cov = "^5.0"
pytest-asyncio = "^0.23"
pytest-mock = "^3.14"
httpx = "^0.27"
ruff = "^0.5"
mypy = "^1.10"
pre-commit = "^3.7"
```

### Total: 21 dependencies (14 prod + 7 dev)

**v1 had 19 dependencies.** v2 adds 5 (openpyxl, weasyprint, fastapi, uvicorn, pydantic-settings) and removes 3 (black, isort, flake8 → ruff). Net +2 is acceptable for the significant capability increase.

---

## Technology Radar

| Technology | Status | Notes |
|---|---|---|
| Polars | **Watch** | Consider for v3 if performance becomes an issue |
| DuckDB | **Watch** | Could replace Pandas for analytical queries in v3 |
| Ollama | **Supported** | Via OpenAI-compatible API, no separate dep |
| LiteLLM | **Watch** | Unified LLM proxy — consider if we add 3+ providers |
| Streamlit | **Rejected** | Too opinionated for our report/dashboard needs |
| Docker | **v2.5** | Containerization for deployment |
| SQLAlchemy | **v2.5** | Database connectors (PostgreSQL, MySQL, SQLite) |
