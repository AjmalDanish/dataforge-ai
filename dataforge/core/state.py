"""Core domain models and state management."""

from typing import Any

from pydantic import BaseModel, Field

from dataforge.shared.utils import generate_execution_id, get_timestamp

__all__ = ["GraphState"]


class GraphState(BaseModel):
    """Central, unified state model shared by all agents.

    This single state object flows through the entire graph,
    carrying all data, context, and execution information.
    """

    # === Immutable Input ===
    input_dataset_path: str = Field(..., description="Path to input dataset")
    input_query: str | None = Field(None, description="User query if provided")
    output_dir: str = Field("./output", description="Output directory")

    # === Mutable Data (single source of truth) ===
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="All analysis data stored as key-value pairs",
    )

    # === Execution Context ===
    execution_id: str = Field(
        default_factory=generate_execution_id, description="Unique execution identifier"
    )
    current_step: str = Field("start", description="Current execution step")
    steps_completed: list[str] = Field(
        default_factory=list, description="List of completed agent names"
    )
    agent_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Agent execution history"
    )

    # === Validation & Retry ===
    validation_status: str = Field(
        "pending", description="Validation status: pending, passed, failed"
    )
    validation_errors: list[str] = Field(
        default_factory=list, description="Validation error messages"
    )
    retry_count: int = Field(0, description="Number of retries performed")
    max_retries: int = Field(3, description="Maximum retry attempts")

    # === Observability ===
    logs: list[dict[str, Any]] = Field(default_factory=list, description="Structured log entries")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Execution metrics")

    # === Timing ===
    start_time: str = Field(default_factory=get_timestamp, description="Analysis start time")
    end_time: str | None = Field(None, description="Analysis end time")

    model_config = {
        "arbitrary_types_allowed": True,  # Allow pandas DataFrames in data dict
        "validate_assignment": True,
    }

    # === Convenience Methods ===
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
        log_entry = {
            "timestamp": get_timestamp(),
            "level": level,
            "agent": agent,
            "message": message,
            **kwargs,
        }
        return self.model_copy(update={"logs": self.logs + [log_entry]})

    def add_agent_result(self, agent_name: str, result: dict[str, Any]) -> "GraphState":
        """Record agent execution result.

        Args:
            agent_name: Name of the agent.
            result: Agent execution result dictionary.

        Returns:
            New GraphState with added agent result.
        """
        history_entry = {
            "agent": agent_name,
            "timestamp": get_timestamp(),
            "result": result,
            "duration_seconds": result.get("duration_seconds", 0.0),
        }
        return self.model_copy(
            update={
                "agent_history": self.agent_history + [history_entry],
                "steps_completed": self.steps_completed + [agent_name],
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

    def increment_retry(self) -> "GraphState":
        """Increment retry count.

        Returns:
            New GraphState with incremented retry count.
        """
        return self.model_copy(update={"retry_count": self.retry_count + 1})

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
