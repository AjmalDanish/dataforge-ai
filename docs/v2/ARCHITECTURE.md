# DataForge AI v2.0 — ARCHITECTURE

> System Architecture Document — The Blueprint

---

## 1. Architectural Style

**Layered Clean Architecture** with **Graph-Orchestrated Agent Core**.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                          │
│  FastAPI REST API  │  Web UI (HTML/JS)  │  CLI (Click)             │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                     APPLICATION LAYER                               │
│  AnalysisOrchestrator  │  SessionManager  │  EventBus              │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                   GRAPH ORCHESTRATION LAYER                         │
│  LangGraph StateGraph  │  Planner  │  Router  │  Checkpointer      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                        AGENT LAYER                                  │
│  12 Specialized Agents (each with BaseAgent contract)              │
│  Validation │ Cleaning │ Schema │ Domain │ Objective │ Profiling   │
│  Feature Eng │ KPI │ Statistics │ Insight │ Visualization │ Report │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                     DOMAIN / CORE LAYER                             │
│  GraphState  │  AgentResult  │  Domain Models  │  Value Objects    │
│  Business Rules  │  KPI Definitions  │  Domain Registry            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                              │
│  LLM Providers  │  File Readers  │  Report Renderers               │
│  Template Engine │  PDF Generator  │  Chart Engine  │  Logger      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Responsibilities

### 2.1 Presentation Layer
**Purpose:** Entry points for users and external systems.

| Component | Responsibility |
|---|---|
| `FastAPI REST API` | HTTP endpoints: upload, status, results, graph state |
| `Web UI` | Browser-based upload, real-time graph visualization, report viewer |
| `CLI` | Command-line interface for power users and CI/CD integration |

**Rules:**
- No business logic in this layer
- Thin controllers that delegate to Application Layer
- Handles serialization/deserialization
- Manages WebSocket connections for real-time updates

### 2.2 Application Layer
**Purpose:** Use-case orchestration and session management.

| Component | Responsibility |
|---|---|
| `AnalysisOrchestrator` | Coordinates a full analysis run: create state → invoke graph → collect results |
| `SessionManager` | Manages analysis sessions, tracks progress, stores results |
| `EventBus` | Publishes agent completion events for real-time UI updates |

**Rules:**
- No direct agent calls (delegates to Graph Layer)
- No infrastructure concerns (no file I/O, no LLM calls)
- Manages cross-cutting concerns: timing, audit trail assembly

### 2.3 Graph Orchestration Layer
**Purpose:** The intelligent routing engine.

| Component | Responsibility |
|---|---|
| `StateGraph` | LangGraph graph definition with nodes, edges, conditional routing |
| `PlannerNode` | Central decision-maker that runs after every agent |
| `Router` | Maps agent decisions to next nodes |
| `Checkpointer` | Persists state after each node for crash recovery |

**Rules:**
- This is a true DAG, not a linear pipeline
- Every agent returns to the Planner for re-evaluation
- The Planner decides: continue, skip, retry, or complete
- Conditional edges allow dynamic routing

### 2.4 Agent Layer
**Purpose:** 12 specialized agents, each with a single responsibility.

**Rules:**
- Every agent extends `BaseAgent`
- Every agent receives `GraphState`, returns `AgentResult`
- Agents are stateless — all state lives in `GraphState`
- Agents declare their dependencies (required state keys)
- Agents declare their outputs (state keys they produce)
- Agents have retry policies and failure policies

### 2.5 Domain / Core Layer
**Purpose:** The heart of the system. Domain models, business rules, value objects.

| Component | Responsibility |
|---|---|
| `GraphState` | Immutable state model flowing through the graph |
| `AgentResult` | Standardized agent output with decision + data updates |
| `DomainRegistry` | Registry of known business domains (retail, finance, HR, etc.) |
| `KPIDefinition` | Domain-specific KPI templates |
| `CleaningRule` | Data cleaning rule definitions |
| `InsightModel` | Structured business insight representation |

**Rules:**
- No framework dependencies (no LangGraph, no FastAPI, no Pandas imports)
- Pure Python + Pydantic
- This layer is the most testable and most stable

### 2.6 Infrastructure Layer
**Purpose:** Adapters for external systems and libraries.

| Component | Responsibility |
|---|---|
| `LLMProvider` (OpenAI, Anthropic, Ollama) | LLM abstraction with retry and fallback |
| `FileReader` (CSV, Excel, Parquet, JSON) | Format-specific data loading |
| `ReportRenderer` (HTML, PDF, JSON) | Report generation and formatting |
| `TemplateEngine` (Jinja2) | HTML report templates |
| `ChartEngine` (Plotly) | Interactive visualization generation |
| `PDFGenerator` (WeasyPrint or similar) | PDF report generation |
| `StructuredLogger` | Structured logging with structlog |

**Rules:**
- All external library dependencies live here
- Implements interfaces defined in Core/Domain layer
- Swappable: change Plotly to Matplotlib without touching agents

---

## 3. Dependency Rule

Dependencies flow **inward only**:

```
Presentation → Application → Graph → Agent → Core ← Infrastructure
```

- Core layer depends on **nothing**
- Infrastructure layer depends on **Core only** (implements its interfaces)
- Agent layer depends on **Core only**
- Graph layer depends on **Core + Agent**
- Application layer depends on **Core + Graph**
- Presentation layer depends on **Core + Application**

**Violated in v1:** Agents directly imported `pandas`, `plotly`, and `scipy`. In v2, agents call infrastructure interfaces.

---

## 4. Dependency Injection

All cross-cutting dependencies are injected, not instantiated inside agents.

```python
# v1 (anti-pattern):
class VisualizationAgent(Agent):
    async def execute(self, state):
        import plotly.graph_objects as go  # hard dependency
        fig = go.Figure(...)

# v2 (injected):
class VisualizationAgent(BaseAgent):
    def __init__(self, chart_engine: ChartEngine, ...):
        self.chart_engine = chart_engine

    async def execute(self, state):
        chart = self.chart_engine.create_bar_chart(...)
```

**Container:** A lightweight DI container (or manual wiring in a `Container` class) assembles all agents with their dependencies at startup.

---

## 5. State Management

### Immutable State Transitions
`GraphState` is never mutated in place. Every agent returns a new state via `model_copy(update={...})`.

### Single Source of Truth
All data lives in `GraphState.data: dict[str, Any]`. No agent maintains private state.

### Typed Accessors (v2 improvement)
Well-known state keys get typed properties to eliminate string-key errors:

```python
@property
def raw_data(self) -> pd.DataFrame | None:
    return self.data.get("raw_data")

@property
def cleaned_data(self) -> pd.DataFrame | None:
    return self.data.get("cleaned_data")

@property
def business_domain(self) -> BusinessDomain | None:
    return self.data.get("business_domain")
```

### Checkpoint Persistence
After each agent completes, `GraphState` is serialized to disk (JSON + Parquet for DataFrames) for crash recovery.

---

## 6. Error Handling Strategy

### Agent-Level
| Error Type | Strategy |
|---|---|
| Transient (timeout, rate limit) | Retry with exponential backoff (max 3) |
| Data Quality (missing columns) | Log warning, degrade gracefully |
| Fatal (file not found, auth) | Halt immediately, report error |
| Logic Error (unexpected state) | Log error, skip agent, continue |

### Graph-Level
| Scenario | Strategy |
|---|---|
| Agent returns ERROR | Planner evaluates: retry, skip, or halt |
| Agent exceeds timeout | Kill agent, mark as failed, continue |
| Infinite loop detected | Step counter > 30 → force completion |
| All retries exhausted | Proceed with available results + degradation report |

### Application-Level
| Scenario | Strategy |
|---|---|
| Uncaught exception | Global error handler returns structured error response |
| Upload validation failure | Return 400 with specific error messages |
| LLM provider down | Fallback to rule-based decisions (no LLM) |

---

## 7. Observability

### Structured Logging
Every agent logs: `timestamp`, `agent_name`, `action`, `duration_ms`, `decision`, `metadata`.

### Execution Trace
A complete ordered list of every agent execution, decision, and state transition — included in final output.

### Metrics
| Metric | Collected By |
|---|---|
| Agent execution time | `BaseAgent.execute_with_logging()` |
| Total analysis time | `AnalysisOrchestrator` |
| LLM token usage | `LLMProvider` |
| Retry count per agent | `GraphState.retry_count` |
| State size (bytes) | Checkpointer |

### Real-Time Events
WebSocket events emitted for each agent start/complete/error — consumed by Web UI for live graph visualization.

---

## 8. Folder Structure (v2)

```
dataforge-ai/
├── dataforge/
│   ├── __init__.py
│   ├── __main__.py
│   │
│   ├── core/                          # Domain Layer (zero dependencies)
│   │   ├── __init__.py
│   │   ├── state.py                   # GraphState model
│   │   ├── models.py                  # AgentResult, AgentDecision, value objects
│   │   ├── domain.py                  # BusinessDomain, KPIDefinition, DomainRegistry
│   │   ├── insights.py                # InsightModel, InsightSeverity
│   │   ├── cleaning.py                # CleaningRule, CleaningDecision
│   │   └── interfaces.py             # Abstract interfaces (ports)
│   │
│   ├── agents/                        # Agent Layer
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseAgent ABC
│   │   ├── planner.py                 # PlannerAgent (graph router)
│   │   ├── validation.py             # DataValidationAgent
│   │   ├── cleaning.py               # DataCleaningAgent
│   │   ├── schema.py                  # SchemaDetectionAgent
│   │   ├── domain_detection.py       # BusinessDomainDetectionAgent
│   │   ├── objective_detection.py    # BusinessObjectiveDetectionAgent
│   │   ├── profiling.py              # ProfilingAgent
│   │   ├── feature_engineering.py    # FeatureEngineeringAgent
│   │   ├── kpi_discovery.py          # KPIDiscoveryAgent
│   │   ├── statistics.py             # StatisticalAnalysisAgent
│   │   ├── insight_generation.py     # InsightGenerationAgent
│   │   ├── visualization.py          # VisualizationAgent
│   │   └── reporting.py              # ExecutiveReportAgent
│   │
│   ├── graph/                         # Graph Orchestration Layer
│   │   ├── __init__.py
│   │   ├── workflow.py                # LangGraph StateGraph definition
│   │   ├── router.py                  # Routing logic
│   │   └── checkpointer.py           # State persistence
│   │
│   ├── application/                   # Application Layer
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # AnalysisOrchestrator
│   │   ├── session.py                # SessionManager
│   │   └── events.py                 # EventBus
│   │
│   ├── infrastructure/                # Infrastructure Layer
│   │   ├── __init__.py
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── provider.py           # LLMProvider ABC
│   │   │   ├── openai_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   └── factory.py            # LLMProviderFactory
│   │   ├── readers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # FileReader ABC
│   │   │   ├── csv_reader.py
│   │   │   ├── excel_reader.py
│   │   │   ├── parquet_reader.py
│   │   │   └── json_reader.py
│   │   ├── renderers/
│   │   │   ├── __init__.py
│   │   │   ├── html_renderer.py
│   │   │   ├── pdf_renderer.py
│   │   │   └── json_renderer.py
│   │   ├── charts/
│   │   │   ├── __init__.py
│   │   │   └── plotly_engine.py
│   │   ├── templates/
│   │   │   ├── report.html.jinja2
│   │   │   ├── dashboard.html.jinja2
│   │   │   └── executive_summary.html.jinja2
│   │   └── logging/
│   │       ├── __init__.py
│   │       └── structured_logger.py
│   │
│   ├── presentation/                  # Presentation Layer
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── app.py                # FastAPI application
│   │   │   ├── routes/
│   │   │   │   ├── analysis.py       # /analyze endpoints
│   │   │   │   ├── status.py         # /status, /graph-state endpoints
│   │   │   │   └── results.py        # /results, /download endpoints
│   │   │   ├── schemas.py            # Request/Response Pydantic models
│   │   │   └── websocket.py          # WebSocket for real-time events
│   │   ├── cli/
│   │   │   └── cli.py                # Click CLI
│   │   └── web/
│   │       ├── index.html
│   │       ├── css/
│   │       └── js/
│   │
│   └── shared/                        # Cross-cutting utilities
│       ├── __init__.py
│       ├── config.py                  # Settings (Pydantic BaseSettings)
│       ├── errors.py                  # Custom exception hierarchy
│       └── utils.py                   # Pure utility functions
│
├── tests/
│   ├── unit/
│   │   ├── agents/
│   │   ├── core/
│   │   ├── infrastructure/
│   │   └── application/
│   ├── integration/
│   │   ├── test_full_workflow.py
│   │   ├── test_api_endpoints.py
│   │   └── test_graph_routing.py
│   └── conftest.py
│
├── datasets/
├── docs/
│   └── v2/                           # This architecture
├── pyproject.toml
├── README.md
└── Makefile
```

---

## 9. Key Architecture Decisions (Summary)

| # | Decision | Rationale |
|---|---|---|
| AD-1 | LangGraph for orchestration | True graph with conditional routing, state management, checkpointing |
| AD-2 | Pydantic for all models | Validation, serialization, type safety |
| AD-3 | Immutable state transitions | Auditability, reproducibility, debuggability |
| AD-4 | LLM-assisted (not LLM-dependent) | Rule-based fallback when LLM is unavailable |
| AD-5 | Infrastructure behind interfaces | Swap Plotly/WeasyPrint/OpenAI without touching agents |
| AD-6 | FastAPI for web layer | Async-native, OpenAPI docs, WebSocket support |
| AD-7 | Jinja2 for report templates | Separation of content and presentation |
| AD-8 | No ORM, no database in v2.0 | File-based I/O keeps deployment simple |
| AD-9 | Planner-as-hub topology | Every agent returns to Planner for re-evaluation |
| AD-10 | Evaluator removed as separate agent | Quality gates integrated into Planner's post-agent validation |

> **AD-10 Rationale:** In v1, the Evaluator was a separate agent that ran once after Visualization. In v2, quality validation is a concern of the Planner — it validates after *every* agent, not just one. This eliminates a redundant graph node and makes quality gates pervasive.
