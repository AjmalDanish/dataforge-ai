"""Core domain models and state management."""

from typing import Any

from pydantic import BaseModel, Field

from dataforge.core.models import AgentHistoryEntry, ExecutionPhase, LogEntry
from dataforge.shared.utils import generate_execution_id, get_timestamp

__all__ = ["GraphState"]


class GraphState(BaseModel):
    """Central state model flowing through the entire graph.

    This single state object flows through the entire graph,
    carrying all data, context, and execution information.

    Design Principles:
    1. Immutability: State is never mutated in place. Every update returns a new
       GraphState via model_copy(update={...})
    2. Single Source of Truth: All agent outputs live in GraphState.data.
       No agent maintains private state.
    3. Typed Accessors: Well-known keys have typed properties to eliminate
       dict-key typos.
    4. Serializable: Entire state (except DataFrames) serializes to JSON.
       DataFrames serialize to Parquet.
    5. Auditable: Every state transition is recorded in agent_history.
    """

    # ════════════════════════════════════════════════════════════
    # IMMUTABLE INPUT (set once at creation, never modified)
    # ════════════════════════════════════════════════════════════
    input_dataset_path: str = Field(..., description="Path to uploaded file")
    input_query: str | None = Field(None, description="Optional user question")
    output_dir: str = Field("./output", description="Output directory")
    execution_id: str = Field(
        default_factory=generate_execution_id, description="Unique run identifier (UUID)"
    )
    start_time: str = Field(default_factory=get_timestamp, description="ISO timestamp")

    # ════════════════════════════════════════════════════════════
    # MUTABLE DATA (the pipeline's shared memory)
    # ════════════════════════════════════════════════════════════
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="All analysis data stored as key-value pairs",
    )

    # ════════════════════════════════════════════════════════════
    # EXECUTION TRACKING
    # ════════════════════════════════════════════════════════════
    current_phase: int = Field(
        default=ExecutionPhase.DATA_INTAKE,
        description="Current execution phase (1-7)",
    )
    current_step: str = Field("start", description="Current node name")
    steps_completed: list[str] = Field(
        default_factory=list, description="Ordered list of completed agents"
    )
    steps_skipped: list[str] = Field(
        default_factory=list, description="Agents that were skipped"
    )
    agent_history: list[AgentHistoryEntry] = Field(
        default_factory=list, description="Full execution history"
    )

    # ════════════════════════════════════════════════════════════
    # QUALITY & RETRY
    # ════════════════════════════════════════════════════════════
    agent_visit_count: dict[str, int] = Field(
        default_factory=dict, description="Per-agent invocation count"
    )
    global_step_count: int = Field(0, description="Total steps (loop detection)")
    max_global_steps: int = Field(35, description="Hard limit")
    quality_warnings: list[str] = Field(
        default_factory=list, description="Non-fatal quality issues"
    )
    quality_errors: list[str] = Field(
        default_factory=list, description="Fatal quality issues"
    )

    # ════════════════════════════════════════════════════════════
    # OBSERVABILITY
    # ════════════════════════════════════════════════════════════
    logs: list[LogEntry] = Field(
        default_factory=list, description="Structured log entries"
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="Timing, token usage, etc."
    )
    end_time: str | None = Field(None, description="Set on completion")

    model_config = {
        "arbitrary_types_allowed": True,  # Allow pandas DataFrames in data dict
        "validate_assignment": True,
    }

    # ════════════════════════════════════════════════════════════
    # TYPED ACCESSORS (well-known state keys)
    # ════════════════════════════════════════════════════════════

    # Phase 1: Data Intake
    @property
    def raw_data(self) -> Any | None:
        """Get raw_data from state.data."""
        return self.data.get("raw_data")

    @property
    def file_metadata(self) -> dict[str, Any] | None:
        """Get file_metadata from state.data."""
        return self.data.get("file_metadata")

    @property
    def validation_report(self) -> dict[str, Any] | None:
        """Get validation_report from state.data."""
        return self.data.get("validation_report")

    # Phase 2: Data Preparation
    @property
    def cleaned_data(self) -> Any | None:
        """Get cleaned_data from state.data."""
        return self.data.get("cleaned_data")

    @property
    def cleaning_report(self) -> dict[str, Any] | None:
        """Get cleaning_report from state.data."""
        return self.data.get("cleaning_report")

    @property
    def cleaning_decisions(self) -> list[dict[str, Any]] | None:
        """Get cleaning_decisions from state.data."""
        return self.data.get("cleaning_decisions")

    # Phase 3: Data Understanding
    @property
    def schema_info(self) -> dict[str, Any] | None:
        """Get schema_info from state.data."""
        return self.data.get("schema_info")

    @property
    def business_domain(self) -> str | None:
        """Get business_domain from state.data."""
        return self.data.get("business_domain")

    @property
    def domain_confidence(self) -> float | None:
        """Get domain_confidence from state.data."""
        return self.data.get("domain_confidence")

    @property
    def domain_signals(self) -> list[dict[str, Any]] | None:
        """Get domain_signals from state.data."""
        return self.data.get("domain_signals")

    @property
    def business_objectives(self) -> list[dict[str, Any]] | None:
        """Get business_objectives from state.data."""
        return self.data.get("business_objectives")

    @property
    def answerable_questions(self) -> list[str] | None:
        """Get answerable_questions from state.data."""
        return self.data.get("answerable_questions")

    # Phase 4: Deep Analysis
    @property
    def profile(self) -> dict[str, Any] | None:
        """Get profile from state.data."""
        return self.data.get("profile")

    @property
    def engineered_data(self) -> Any | None:
        """Get engineered_data from state.data."""
        return self.data.get("engineered_data")

    @property
    def new_features(self) -> list[dict[str, Any]] | None:
        """Get new_features from state.data."""
        return self.data.get("new_features")

    @property
    def discovered_kpis(self) -> list[dict[str, Any]] | None:
        """Get discovered_kpis from state.data."""
        return self.data.get("discovered_kpis")

    # Phase 5: Statistical Analysis
    @property
    def statistics(self) -> dict[str, Any] | None:
        """Get statistics from state.data."""
        return self.data.get("statistics")

    # Phase 6: Synthesis
    @property
    def business_insights(self) -> list[dict[str, Any]] | None:
        """Get business_insights from state.data."""
        return self.data.get("business_insights")

    # Phase 7: Output
    @property
    def visualizations(self) -> list[dict[str, Any]] | None:
        """Get visualizations from state.data."""
        return self.data.get("visualizations")

    @property
    def dashboard(self) -> dict[str, Any] | None:
        """Get dashboard from state.data."""
        return self.data.get("dashboard")

    @property
    def report_html(self) -> str | None:
        """Get report_html path from state.data."""
        return self.data.get("report_html")

    @property
    def report_pdf(self) -> str | None:
        """Get report_pdf path from state.data."""
        return self.data.get("report_pdf")

    @property
    def report_json(self) -> str | None:
        """Get report_json path from state.data."""
        return self.data.get("report_json")

    @property
    def execution_trace(self) -> dict[str, Any] | None:
        """Get execution_trace from state.data."""
        return self.data.get("execution_trace")

    # ════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS
    # ════════════════════════════════════════════════════════════

    def get(self, key: str, default: Any | None = None) -> Any:
        """Get data value with default.

        Args:
            key: Key to retrieve from data dict.
            default: Default value if key not found.

        Returns:
            Value from data dict or default.
        """
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> "GraphState":
        """Return new state with updated data (immutable).

        Args:
            key: Key to update in data dict.
            value: New value.

        Returns:
            New GraphState with updated data.
        """
        new_data = self.data.copy()
        new_data[key] = value
        return self.model_copy(update={"data": new_data})

    def add_log(
        self,
        level: str,
        agent: str,
        message: str,
        **kwargs: Any,
    ) -> "GraphState":
        """Add structured log entry.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            agent: Agent name.
            message: Log message.
            **kwargs: Additional log fields.

        Returns:
            New GraphState with added log entry.
        """
        log_entry = LogEntry(
            timestamp=get_timestamp(),
            level=level,
            agent=agent,
            message=message,
            metadata=kwargs,
        )
        # Cap logs at 500 entries to prevent unbounded growth
        logs = self.logs[-499:] if len(self.logs) >= 500 else self.logs
        return self.model_copy(update={"logs": logs + [log_entry]})

    def add_agent_result(
        self,
        agent_name: str,
        result: dict[str, Any],
        decision: str = "continue",
        quality_score: float | None = None,
        data_keys_produced: list[str] | None = None,
        **metadata: Any,
    ) -> "GraphState":
        """Record agent execution result.

        Args:
            agent_name: Name of the agent.
            result: Agent execution result dictionary.
            decision: Agent decision (continue, skip, retry, error).
            quality_score: Quality score (0.0-1.0).
            data_keys_produced: List of state keys produced.
            **metadata: Additional metadata.

        Returns:
            New GraphState with added agent result.
        """
        duration_seconds = result.get("duration_seconds", 0.0)
        message = result.get("message", "")

        history_entry = AgentHistoryEntry(
            agent_name=agent_name,
            timestamp=get_timestamp(),
            duration_seconds=duration_seconds,
            decision=decision,
            message=message,
            quality_score=quality_score,
            data_keys_produced=data_keys_produced or [],
            metadata=metadata,
        )

        # Increment agent visit count
        visit_count = self.agent_visit_count.copy()
        visit_count[agent_name] = visit_count.get(agent_name, 0) + 1

        # Increment global step count
        new_global_step_count = self.global_step_count + 1

        return self.model_copy(
            update={
                "agent_history": self.agent_history + [history_entry],
                "steps_completed": self.steps_completed + [agent_name],
                "agent_visit_count": visit_count,
                "global_step_count": new_global_step_count,
            }
        )

    def add_skip(self, agent_name: str, reason: str) -> "GraphState":
        """Record agent skip.

        Args:
            agent_name: Name of the skipped agent.
            reason: Reason for skipping.

        Returns:
            New GraphState with skip recorded.
        """
        return self.model_copy(
            update={
                "steps_skipped": self.steps_skipped + [agent_name],
                "logs": self.logs
                + [
                    LogEntry(
                        timestamp=get_timestamp(),
                        level="INFO",
                        agent="Planner",
                        message=f"Skipped {agent_name}: {reason}",
                        metadata={"skipped_agent": agent_name, "reason": reason},
                    )
                ],
            }
        )

    def update_step(self, step: str) -> "GraphState":
        """Update current execution step.

        Args:
            step: New step name.

        Returns:
            New GraphState with updated step.
        """
        return self.model_copy(update={"current_step": step})

    def update_phase(self, phase: ExecutionPhase | int) -> "GraphState":
        """Update current execution phase.

        Args:
            phase: New phase (ExecutionPhase enum or int 1-7).

        Returns:
            New GraphState with updated phase.
        """
        if isinstance(phase, int):
            phase_int = phase
        else:
            phase_int = phase.value

        if not 1 <= phase_int <= 7:
            raise ValueError(f"Phase must be between 1 and 7, got {phase_int}")

        return self.model_copy(update={"current_phase": phase_int})

    def add_quality_warning(self, warning: str) -> "GraphState":
        """Add quality warning.

        Args:
            warning: Warning message.

        Returns:
            New GraphState with warning added.
        """
        return self.model_copy(
            update={"quality_warnings": self.quality_warnings + [warning]}
        )

    def add_quality_error(self, error: str) -> "GraphState":
        """Add quality error.

        Args:
            error: Error message.

        Returns:
            New GraphState with error added.
        """
        return self.model_copy(update={"quality_errors": self.quality_errors + [error]})

    def add_metric(self, key: str, value: Any) -> "GraphState":
        """Add or update a metric.

        Args:
            key: Metric key.
            value: Metric value.

        Returns:
            New GraphState with updated metrics.
        """
        new_metrics = self.metrics.copy()
        new_metrics[key] = value
        return self.model_copy(update={"metrics": new_metrics})

    def mark_complete(self) -> "GraphState":
        """Mark analysis as complete.

        Returns:
            New GraphState with end time set.
        """
        return self.model_copy(update={"end_time": get_timestamp()})

    def should_continue(self) -> bool:
        """Check if workflow should continue.

        Returns:
            True if global_step_count < max_global_steps.
        """
        return self.global_step_count < self.max_global_steps

    def get_agent_visit_count(self, agent_name: str) -> int:
        """Get visit count for a specific agent.

        Args:
            agent_name: Name of the agent.

        Returns:
            Number of times this agent has been invoked.
        """
        return self.agent_visit_count.get(agent_name, 0)

    def has_exceeded_max_retries(self, agent_name: str, max_retries: int) -> bool:
        """Check if agent has exceeded max retries.

        Args:
            agent_name: Name of the agent.
            max_retries: Maximum allowed retries.

        Returns:
            True if agent has exceeded max retries.
        """
        return self.get_agent_visit_count(agent_name) > max_retries
