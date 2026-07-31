# DataForge AI - Architecture Diagram

```mermaid
graph TB
    subgraph "Presentation Layer"
        CLI[dataforge/presentation/cli.py<br/>Command-Line Interface]
        ENTRY[dataforge/__main__.py<br/>Entry Point]
    end

    subgraph "Graph Orchestration Layer"
        WORKFLOW[dataforge/graph/workflow.py<br/>LangGraph StateGraph]
        ROUTER[Conditional Router<br/>route_from_planner]
    end

    subgraph "Agent Layer"
        PLANNER[PlannerAgent<br/>Analysis Planning]
        EVALUATOR[EvaluatorAgent<br/>Validation & Retry]
        INGESTION[DataIngestionAgent<br/>Data Loading]
        PROFILING[DataProfilingAgent<br/>Schema & Types]
        STATISTICS[StatisticalAnalysisAgent<br/>Descriptive Stats]
        VISUALIZATION[VisualizationAgent<br/>Chart Generation]
        REPORTING[ReportingAgent<br/>Report Creation]
    end

    subgraph "Core Layer"
        STATE[GraphState<br/>Central State Model]
        LOGGER[StructuredLogger<br/>Logging System]
        LLM[LLMProvider<br/>OpenAI/Anthropic]
    end

    subgraph "Infrastructure Layer"
        CONFIG[Settings<br/>Configuration]
        ERRORS[Custom Errors<br/>Error Handling]
        UTILS[Utilities<br/>Helper Functions]
    end

    subgraph "Data Layer"
        CSV[CSV Files]
        OUTPUT[Output Directory<br/>HTML/JSON/Visualizations]
    end

    ENTRY --> CLI
    CLI --> WORKFLOW
    WORKFLOW --> ROUTER
    ROUTER --> PLANNER
    PLANNER --> EVALUATOR
    EVALUATOR --> INGESTION
    INGESTION --> PROFILING
    PROFILING --> STATISTICS
    STATISTICS --> VISUALIZATION
    VISUALIZATION --> REPORTING
    REPORTING --> WORKFLOW

    WORKFLOW --> STATE
    WORKFLOW --> LOGGER
    WORKFLOW --> LLM

    PLANNER --> STATE
    EVALUATOR --> STATE
    INGESTION --> STATE
    PROFILING --> STATE
    STATISTICS --> STATE
    VISUALIZATION --> STATE
    REPORTING --> STATE

    PLANNER --> LOGGER
    EVALUATOR --> LOGGER
    INGESTION --> LOGGER
    PROFILING --> LOGGER
    STATISTICS --> LOGGER
    VISUALIZATION --> LOGGER
    REPORTING --> LOGGER

    PLANNER --> LLM
    EVALUATOR --> LLM
    STATISTICS --> LLM

    CLI --> CONFIG
    WORKFLOW --> CONFIG
    LLM --> CONFIG

    INGESTION --> CSV
    REPORTING --> OUTPUT
    VISUALIZATION --> OUTPUT

    style CLI fill:#e1f5ff
    style WORKFLOW fill:#fff4e1
    style STATE fill:#ffe1f5
    style LLM fill:#e1ffe1
    style CSV fill:#f5f5f5
    style OUTPUT fill:#f5f5f5
```

## Architecture Overview

### Layer Responsibilities

1. **Presentation Layer**: User-facing CLI interface and entry points
2. **Graph Orchestration Layer**: LangGraph workflow management and routing
3. **Agent Layer**: Seven specialized AI agents for different analysis tasks
4. **Core Layer**: Central state management, logging, and LLM integration
5. **Infrastructure Layer**: Configuration, error handling, and utilities
6. **Data Layer**: Input data sources and output artifacts

### Key Design Principles

- **Single Source of Truth**: GraphState is the only mutable state object
- **Agent Independence**: Each agent operates independently through the state
- **Async-First**: All agents execute asynchronously for performance
- **Type Safety**: Pydantic models enforce data validation
- **Observability**: Structured logging at every step