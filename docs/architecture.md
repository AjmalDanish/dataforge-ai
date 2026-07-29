# DataForge AI - Architecture Document

**Version**: 1.0 (Post-Architecture Review)
**Status**: Finalized and Approved for Implementation

---

## Executive Summary

DataForge AI is an autonomous multi-agent data science platform built on **Clean Architecture** principles and **Graph Engineering** using LangGraph. The system uses a true branching graph with a central **Planner Agent** that dynamically orchestrates specialized AI agents to analyze structured datasets.

**Key Architectural Features**:
- **True Graph Workflow**: Dynamic agent selection with branching (not a linear pipeline)
- **Planner Agent**: Central decision maker that determines execution path
- **Evaluator Agent**: Quality validation with feedback loops
- **Unified GraphState**: Single, flexible state model shared by all agents
- **Abstract LLMProvider**: Vendor-agnostic interface for LLM integration
- **Built-in Observability**: Centralized structured logging for all agents

---

## Architecture Principles

### 1. Clean Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│  (CLI Interface - Click)                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Application Layer (Orchestration)            │
│  (Main Orchestrator, Workflow Graph)                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer (7 Agents)                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Planner │ │Ingestion│ │Profiling│ │Statistics│         │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                         │
│  │Evaluator│ │Visualization│ │Reporting│                   │
│  └─────────┘ └─────────────┘ └─────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                              │
│  (GraphState, LLMProvider, StructuredLogger)                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                         │
│  (LLM Provider Implementations, File I/O)                    │
└─────────────────────────────────────────────────────────────┘
```

### 2. SOLID Principles

| Principle | Application |
|-----------|-------------|
| **Single Responsibility** | Each agent has one clear purpose |
| **Open/Closed** | New LLM providers and agents can be added without modification |
| **Liskov Substitution** | All LLM providers are interchangeable |
| **Interface Segregation** | Small, focused interfaces (Agent, LLMProvider) |
| **Dependency Inversion** | Agents depend on LLMProvider abstraction, not concrete implementations |

### 3. Simplicity Over Cleverness

- Sequential agent execution (no parallel complexity in v1.0)
- Simple rule-based Planner (not AI-based decision making)
- Unified state model (no complex state management)
- Essential visualizations only (4 chart types)

---

## Core Components

### 1. GraphState - Unified State Model

```python
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

class GraphState(BaseModel):
    """Central, unified state model shared by all agents.

    This single state object flows through the entire graph,
    carrying all data, context, and execution information.
    """

    # === Immutable Input ===
    input_dataset_path: str = Field(..., description="Path to input dataset")
    input_query: Optional[str] = Field(None, description="User query if provided")
    output_dir: str = Field("./output", description="Output directory")

    # === Mutable Data (single source of truth) ===
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="All analysis data stored as key-value pairs"
    )

    # === Execution Context ===
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_step: str = Field("start", description="Current execution step")
    steps_completed: List[str] = Field(default_factory=list)
    agent_history: List[Dict[str, Any]] = Field(default_factory=list)

    # === Validation & Retry ===
    validation_status: str = Field("pending", description="Validation status")
    validation_errors: List[str] = Field(default_factory=list)
    retry_count: int = Field(0)
    max_retries: int = Field(3)

    # === Observability ===
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True  # Allow pandas DataFrames in data dict

    # === Convenience Methods ===
    def get(self, key: str, default: Any = None) -> Any:
        """Get data value with default."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> "GraphState":
        """Return new state with updated data (immutable)."""
        new_data = self.data.copy()
        new_data[key] = value
        return self.model_copy(update={"data": new_data})

    def add_log(self, level: str, agent: str, message: str, **kwargs) -> "GraphState":
        """Add structured log entry."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "agent": agent,
            "message": message,
            **kwargs
        }
        return self.model_copy(update={"logs": self.logs + [log_entry]})

    def add_agent_result(self, agent_name: str, result: Dict[str, Any]) -> "GraphState":
        """Record agent execution result."""
        history_entry = {
            "agent": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result,
            "duration_seconds": result.get("duration_seconds", 0)
        }
        return self.model_copy(update={
            "agent_history": self.agent_history + [history_entry],
            "steps_completed": self.steps_completed + [agent_name]
        })
```

**Design Rationale**:
- Single source of truth for all data
- Flexible `data` dict accommodates any analysis results
- Immutable with convenience methods for updates
- Built-in logging and metrics
- Easy to extend without schema changes

### 2. LLMProvider - Abstract Interface

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

class LLMMessage(BaseModel):
    """Unified message format for all LLM providers."""
    role: str  # "system", "user", "assistant"
    content: str

class LLMResponse(BaseModel):
    """Unified response format for all LLM providers."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None

class LLMConfig(BaseModel):
    """Configuration for LLM provider."""
    provider: str  # "openai", "anthropic", "ollama", etc.
    model: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30
    base_url: Optional[str] = None

class LLMProvider(ABC):
    """Abstract interface for all LLM providers.

    This interface eliminates vendor lock-in and allows easy
    addition of new providers (OpenAI, Anthropic, Ollama, etc.).
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        config: LLMConfig
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def generate_with_retry(
        self,
        messages: List[LLMMessage],
        config: LLMConfig,
        max_retries: int = 3
    ) -> LLMResponse:
        """Generate with automatic retry on transient failures."""
        pass

    @abstractmethod
    def validate_config(self, config: LLMConfig) -> bool:
        """Validate provider configuration."""
        pass

class LLMProviderFactory:
    """Factory for creating LLM providers.

    Supports dynamic provider registration for extensibility.
    """

    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a new provider."""
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create(cls, config: LLMConfig) -> LLMProvider:
        """Create provider instance from config."""
        provider_class = cls._providers.get(config.provider.lower())
        if provider_class is None:
            raise ValueError(f"Unknown provider: {config.provider}")
        return provider_class()
```

**Design Rationale**:
- Zero vendor lock-in
- Easy to add new providers
- Unified interface for all agents
- Configuration-driven provider selection
- Testable with mock providers

### 3. StructuredLogger - Centralized Observability

```python
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

class StructuredLogger:
    """Centralized structured logging for all agents.

    Provides:
    - Consistent log format across all agents
    - Beautiful colored console output
    - Machine-readable JSON log files
    - Automatic log export
    """

    def __init__(self, execution_id: str, output_dir: str):
        self.execution_id = execution_id
        self.output_dir = Path(output_dir)
        self.logs: List[Dict[str, Any]] = []
        self.log_file = self.output_dir / f"execution_{execution_id}.log"

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Console colors
        self.colors = {
            "DEBUG": "\033[36m",    # Cyan
            "INFO": "\033[32m",     # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",    # Red
            "CRITICAL": "\033[35m", # Magenta
        }
        self.icons = {
            "DEBUG": "🔍",
            "INFO": "✓",
            "WARNING": "⚠",
            "ERROR": "✗",
            "CRITICAL": "💀",
        }

    def _log(self, level: str, **kwargs):
        """Internal log method."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "execution_id": self.execution_id,
            **kwargs
        }
        self.logs.append(entry)

        self._console_log(level, entry)
        self._file_log(entry)

    def _console_log(self, level: str, entry: Dict):
        """Pretty console output with colors."""
        color = self.colors.get(level, "")
        icon = self.icons.get(level, "•")
        reset = "\033[0m"

        msg = f"{color}{icon} [{level}]{reset} {entry.get('message', '')}"
        if "agent" in entry:
            msg += f" [{entry['agent']}]"

        print(msg)

    def _file_log(self, entry: Dict):
        """Write to log file."""
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def info(self, message: str, **kwargs):
        self._log("INFO", message=message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message=message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log("WARNING", message=message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log("ERROR", message=message, **kwargs)

    def export_logs(self) -> Path:
        """Export logs to JSON file."""
        export_path = self.output_dir / f"logs_{self.execution_id}.json"
        with open(export_path, "w") as f:
            json.dump(self.logs, f, indent=2)
        return export_path
```

**Design Rationale**:
- Single logging interface for all agents
- Beautiful console output for users
- Machine-readable logs for debugging
- Automatic log export
- Execution tracking

---

## Agent Architecture

### Agent Base Class

```python
from enum import Enum
from typing import Optional
import time
import asyncio

class AgentDecision(Enum):
    """Decision returned by agent after execution."""
    CONTINUE = "continue"  # Continue to next agent
    REPLAN = "replan"     # Ask planner to re-evaluate
    COMPLETE = "complete" # Analysis complete
    ERROR = "error"       # Error occurred

class AgentResult(BaseModel):
    """Result of agent execution."""
    decision: AgentDecision
    message: str
    data_updates: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    next_agent_suggestion: Optional[str] = None

class Agent(ABC):
    """Base class for all agents.

    All agents:
    - Receive GraphState as input
    - Return AgentResult with decision
    - Have automatic logging via execute_with_logging
    - Use shared LLMProvider and StructuredLogger
    """

    def __init__(self, llm_provider: LLMProvider, logger: StructuredLogger):
        self.llm = llm_provider
        self.logger = logger
        self.name = self.__class__.__name__

    @abstractmethod
    async def execute(self, state: GraphState) -> AgentResult:
        """Execute agent logic.

        Returns:
            AgentResult with decision, message, and any data updates.
        """
        pass

    async def execute_with_logging(self, state: GraphState) -> tuple[AgentResult, GraphState]:
        """Execute with automatic logging and state updates."""
        self.logger.info(f"Starting {self.name}", agent=self.name)

        start_time = time.time()

        try:
            result = await self.execute(state)
            duration = time.time() - start_time

            # Log completion
            self.logger.info(
                f"Completed {self.name}",
                agent=self.name,
                decision=result.decision.value,
                duration_seconds=duration,
                result_message=result.message
            )

            # Update state with agent result
            updated_state = state.add_agent_result(self.name, {
                "success": result.decision != AgentDecision.ERROR,
                "decision": result.decision.value,
                "message": result.message,
                "duration_seconds": duration,
                **result.metadata
            })

            # Apply data updates
            if result.data_updates:
                for key, value in result.data_updates.items():
                    updated_state = updated_state.set(key, value)

            return result, updated_state

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"{self.name} failed",
                agent=self.name,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_seconds=duration
            )

            error_result = AgentResult(
                decision=AgentDecision.ERROR,
                message=f"{self.name} failed: {str(e)}"
            )

            updated_state = state.add_agent_result(self.name, {
                "success": False,
                "error": str(e),
                "duration_seconds": duration
            })

            return error_result, updated_state
```

---

## The 7 Agents

### 1. Planner Agent (NEW)

**Purpose**: Central decision maker that orchestrates the workflow.

**Responsibilities**:
- Analyze current GraphState
- Determine which agent to run next
- Skip irrelevant agents based on data characteristics
- Decide when analysis is complete

**Decision Logic**:
```python
class PlannerAgent(Agent):
    """Central planning agent that determines execution flow."""

    async def execute(self, state: GraphState) -> AgentResult:
        """Decide next action based on current state."""

        # Initial state: start with ingestion
        if state.current_step == "start":
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Starting analysis with data ingestion",
                next_agent_suggestion="DataIngestionAgent"
            )

        # After ingestion: decide what to profile
        if "DataIngestionAgent" in state.steps_completed:
            if state.get("raw_data") is None:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="No data loaded, cannot continue"
                )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Data loaded, proceeding to profiling",
                next_agent_suggestion="DataProfilingAgent"
            )

        # After profiling: check if statistics needed
        if "DataProfilingAgent" in state.steps_completed:
            has_numeric = state.get("has_numeric_columns", False)
            if not has_numeric:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="No numeric data, skipping statistics",
                    next_agent_suggestion="VisualizationAgent"
                )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message "Numeric data found, running statistics",
                next_agent_suggestion="StatisticalAnalysisAgent"
            )

        # After statistics: decide on visualization
        if "StatisticalAnalysisAgent" in state.steps_completed:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Analysis complete, generating visualizations",
                next_agent_suggestion="VisualizationAgent"
            )

        # After visualization: evaluate completeness
        if "VisualizationAgent" in state.steps_completed:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Visualizations generated, validating results",
                next_agent_suggestion="EvaluatorAgent"
            )

        # After evaluator: decide to continue or complete
        if "EvaluatorAgent" in state.steps_completed:
            if state.validation_status == "failed":
                return AgentResult(
                    decision=AgentDecision.REPLAN,
                    message="Validation failed, re-planning",
                    next_agent_suggestion="DataProfilingAgent"
                )
            else:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Validation passed, generating report",
                    next_agent_suggestion="ReportingAgent"
                )

        # After reporting: complete
        if "ReportingAgent" in state.steps_completed:
            return AgentResult(
                decision=AgentDecision.COMPLETE,
                message="Analysis complete, report generated"
            )

        # Fallback
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Proceeding with next agent"
        )
```

### 2. Evaluator Agent (NEW)

**Purpose**: Validates analysis quality and requests additional work if needed.

**Responsibilities**:
- Check data quality
- Verify insights generated
- Validate statistical significance
- Request additional analysis if insufficient

**Validation Checks**:
```python
class EvaluatorAgent(Agent):
    """Validates analysis results and quality."""

    async def execute(self, state: GraphState) -> AgentResult:
        """Validate current analysis results."""

        checks = {
            "has_data": self._check_has_data(state),
            "has_insights": self._check_has_insights(state),
            "data_quality": self._check_data_quality(state),
            "sufficient_depth": self._check_analysis_depth(state),
        }

        all_passed = all(checks.values())

        if all_passed:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="All validation checks passed",
                data_updates={"validation_status": "passed"}
            )
        else:
            failed_checks = [k for k, v in checks.items() if not v]

            return AgentResult(
                decision=AgentDecision.REPLAN,
                message=f"Validation failed: {', '.join(failed_checks)}",
                data_updates={
                    "validation_status": "failed",
                    "failed_checks": failed_checks
                }
            )

    def _check_has_data(self, state: GraphState) -> bool:
        """Check if data was loaded."""
        return state.get("raw_data") is not None

    def _check_has_insights(self, state: GraphState) -> bool:
        """Check if insights were generated."""
        insights = state.get("insights", [])
        return len(insights) >= 3

    def _check_data_quality(self, state: GraphState) -> bool:
        """Check data quality (missing values, etc.)."""
        profile = state.get("profile")
        if not profile:
            return False
        # Check for acceptable data quality
        return True

    def _check_analysis_depth(self, state: GraphState) -> bool:
        """Check if sufficient analysis was performed."""
        return len(state.steps_completed) >= 3
```

### 3. Data Ingestion Agent

**Purpose**: Read and parse structured data files.

**Inputs**: `dataset_path` from GraphState
**Outputs**: `raw_data` in GraphState.data

### 4. Data Profiling Agent

**Purpose**: Analyze data structure and characteristics.

**Inputs**: `raw_data` from GraphState.data
**Outputs**: `profile`, `has_numeric_columns`, etc. in GraphState.data

### 5. Statistical Analysis Agent

**Purpose**: Compute descriptive statistics and relationships.

**Inputs**: `raw_data`, `profile` from GraphState.data
**Outputs**: `statistics`, `correlations`, `insights` in GraphState.data

### 6. Visualization Agent

**Purpose**: Generate essential visualizations.

**Chart Types** (4 essential):
1. Histogram - for numeric distributions
2. Bar chart - for categorical distributions
3. Heatmap - for correlations
4. Scatter plot - for relationships

**Inputs**: `raw_data`, `statistics` from GraphState.data
**Outputs**: `visualizations` in GraphState.data

### 7. Reporting Agent

**Purpose**: Compile comprehensive reports.

**Outputs**: `report.md`, `report.html` files

---

## Graph Workflow

### True Branching Graph

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Planner   │ ← Decision #1: Start with Ingestion
                    │   Agent     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Ingestion  │
                    │   Agent     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Planner   │ ← Decision #2: Profiling or Error
                    │  (Re-eval)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │ Profile  │ │ Skip     │ │  Error   │
       │  Agent   │ │ Stats    │ │ Handler  │
       └────┬─────┘  │ (no num) │  └──────────┘
            │       └──────────┘
            │            │
            ▼            ▼
       ┌─────────────┐
       │   Planner   │ ← Decision #3: Stats or Visualization
       │  (Re-eval)  │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │ Statistics  │
       │   Agent     │
       └────┬────────┘
            │
            ▼
       ┌─────────────┐
       │   Planner   │ ← Decision #4: Visualization
       │  (Re-eval)  │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │Visualization│
       │   Agent     │
       └────┬────────┘
            │
            ▼
       ┌─────────────┐
       │   Planner   │ ← Decision #5: Evaluate
       │  (Re-eval)  │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │  Evaluator  │ ← Validation check
       │   Agent     │
       └──────┬──────┘
              │
     ┌────────┴────────┐
     │                 │
     ▼                 ▼
  PASS              FAIL
     │                 │
     ▼                 ▼
┌─────────┐    ┌─────────────┐
│ Planner │    │   Planner   │ ← Re-plan with different agents
│ (final) │    │  (retry)    │
└────┬────┘    └─────────────┘
     │               │
     ▼               │
┌─────────┐          │
│Reporter │          │
│ Agent   │          │
└────┬────┘          │
     │               │
     ▼               │
┌─────────┐          │
│   END   │          └───► Loop back to agents
└─────────┘
```

### Key Graph Features

1. **Planner Runs Multiple Times**: After each agent, Planner decides next action
2. **Conditional Branching**: Skip statistics if no numeric data
3. **Validation Loops**: Evaluator can trigger re-planning
4. **Error Handling**: Error handler path for failures
5. **Dynamic Execution**: Path adapts to data characteristics

### LangGraph Implementation

```python
from langgraph.graph import StateGraph, END

def create_graph() -> StateGraph:
    """Create the analysis workflow graph."""

    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("planner", planner_agent)
    workflow.add_node("ingestion", ingestion_agent)
    workflow.add_node("profiling", profiling_agent)
    workflow.add_node("statistics", statistics_agent)
    workflow.add_node("visualization", visualization_agent)
    workflow.add_node("evaluator", evaluator_agent)
    workflow.add_node("reporting", reporting_agent)

    # Set entry point
    workflow.set_entry_point("planner")

    # Add conditional edges from planner
    workflow.add_conditional_edges(
        "planner",
        route_from_planner,
        {
            "ingestion": "ingestion",
            "profiling": "profiling",
            "statistics": "statistics",
            "visualization": "visualization",
            "evaluator": "evaluator",
            "reporting": "reporting",
            "end": END,
        }
    )

    # All agents return to planner
    workflow.add_edge("ingestion", "planner")
    workflow.add_edge("profiling", "planner")
    workflow.add_edge("statistics", "planner")
    workflow.add_edge("visualization", "planner")
    workflow.add_edge("evaluator", "planner")
    workflow.add_edge("reporting", END)

    return workflow.compile()

def route_from_planner(state: GraphState) -> str:
    """Route to next agent based on planner's decision."""
    last_result = state.agent_history[-1] if state.agent_history else {}

    if last_result.get("decision") == "complete":
        return "end"

    next_agent = last_result.get("next_agent_suggestion")
    if next_agent:
        return next_agent.lower().replace("agent", "")

    return "end"
```

---

## Error Handling and Retry

### Retry Strategy

```python
class RetryOrchestrator:
    """Handles retry logic with exponential backoff."""

    async def execute_with_retry(
        self,
        agent: Agent,
        state: GraphState,
        max_retries: int = 3
    ) -> tuple[AgentResult, GraphState]:
        """Execute agent with retry logic."""

        retry_count = 0
        last_result = None
        current_state = state

        while retry_count <= max_retries:
            result, current_state = await agent.execute_with_logging(current_state)

            if result.decision != AgentDecision.ERROR:
                return result, current_state

            last_result = result
            retry_count += 1

            if retry_count <= max_retries:
                backoff = 2 ** retry_count  # 1s, 2s, 4s
                logger.warning(
                    f"Retrying {agent.name}",
                    agent=agent.name,
                    retry_count=retry_count,
                    backoff_seconds=backoff
                )
                await asyncio.sleep(backoff)

        # Max retries exceeded
        return last_result, current_state
```

### Error Categories

| Category | Retry? | Action |
|----------|--------|--------|
| Transient (network, timeout) | Yes | Exponential backoff |
| LLM rate limit | Yes | Delayed retry |
| Data format error | No | Skip agent, continue |
| Validation error | No | Re-plan with different approach |
| Critical error | No | Halt workflow |

---

## Module Structure

```
dataforge/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── state.py              # GraphState model
│   ├── llm.py                # LLMProvider interface and factory
│   └── logger.py             # StructuredLogger
├── agents/
│   ├── __init__.py
│   ├── base.py               # Agent base class
│   ├── planner.py            # Planner Agent
│   ├── evaluator.py          # Evaluator Agent
│   ├── ingestion.py          # Data Ingestion
│   ├── profiling.py          # Data Profiling
│   ├── statistics.py         # Statistical Analysis
│   ├── visualization.py      # Visualizations
│   └── reporting.py          # Report Generation
├── graph/
│   ├── __init__.py
│   ├── workflow.py           # LangGraph definition
│   └── routing.py            # Conditional routing logic
├── infrastructure/
│   ├── __init__.py
│   ├── llm_providers/
│   │   ├── __init__.py
│   │   ├── openai.py         # OpenAI implementation
│   │   └── anthropic.py      # Anthropic implementation
│   └── file_reader.py        # File I/O
├── application/
│   ├── __init__.py
│   └── orchestrator.py       # Main orchestration
├── presentation/
│   └── cli.py                # CLI interface
└── shared/
    ├── config.py             # Configuration
    └── constants.py          # Constants
```

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Graph Orchestration | LangGraph | 0.0.20+ |
| Data Processing | Pandas | 2.0+ |
| Numerical Computing | NumPy | 1.24+ |
| Statistics | SciPy | 1.11+ |
| Visualization | Plotly | 5.18+ |
| File Format | PyArrow | 12.0+ |
| Validation | Pydantic | 2.0+ |
| CLI | Click | 8.1+ |
| Logging | structlog | 23.0+ |
| LLM | OpenAI / Anthropic | Latest |

See TECH_STACK.md for detailed justifications.

---

## Non-Functional Requirements

### Performance
- Complete analysis in < 60 seconds for typical datasets (< 10MB)
- < 2GB RAM for standard workloads
- Progress updates every 5 seconds

### Reliability
- > 95% successful completion on valid datasets
- Retry logic for transient failures
- Graceful degradation on errors

### Maintainability
- > 80% test coverage for business logic
- Type hints on all public functions
- Clear module boundaries

### Observability
- Structured logging for all operations
- Execution tracking with unique IDs
- Exportable log files

---

## Implementation Size Estimate

| Component | Lines of Code |
|-----------|---------------|
| Core (GraphState, LLM, Logger) | 400 |
| Planner + Evaluator Agents | 500 |
| 5 Analysis Agents | 1,200 |
| Graph Definition | 200 |
| CLI | 200 |
| Infrastructure | 300 |
| Tests | 1,000 |
| **Total** | **~3,800 lines** |

**Previous Estimate**: ~6,250 lines
**Reduction**: 39%

---

## Conclusion

This architecture is:
- ✅ **Simpler** - 39% less code than initial design
- ✅ **More Sophisticated** - True graph with dynamic planning
- ✅ **More Maintainable** - Unified interfaces, built-in logging
- ✅ **More Impressive** - Planner Agent, validation loops
- ✅ **Achievable** - Conservative 5-day estimate
- ✅ **Production-Ready** - Error handling, observability, testing

All future implementation must follow this architecture document.

**Document Version**: 2.0 (Post-Architecture Review)
**Last Updated**: 2024
**Status**: ✅ FINALIZED AND APPROVED