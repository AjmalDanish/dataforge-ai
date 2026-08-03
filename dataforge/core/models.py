"""Core domain models for DataForge AI v2."""

from enum import Enum, IntEnum
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "ExecutionPhase",
    "RetryPolicy",
    "FailurePolicy",
    "AgentHistoryEntry",
    "LogEntry",
]


class ExecutionPhase(IntEnum):
    """Execution phases for the analysis workflow.

    Phases provide ordered guarantees while allowing dynamic routing within phases.
    """

    DATA_INTAKE = 1
    DATA_PREPARATION = 2
    DATA_UNDERSTANDING = 3
    DEEP_ANALYSIS = 4
    STATISTICAL_ANALYSIS = 5
    SYNTHESIS = 6
    OUTPUT = 7

    def __str__(self) -> str:
        """Return human-readable phase name."""
        return self.name.replace("_", " ").title()


class FailurePolicy(Enum):
    """Policy for handling agent failures."""

    HALT = "halt"  # Stop the entire workflow
    SKIP = "skip"  # Skip this agent and continue


class RetryPolicy(BaseModel):
    """Retry configuration for an agent.

    Attributes:
        max_retries: Maximum number of retry attempts.
        backoff_strategy: Backoff strategy ("exponential" or "linear").
        initial_backoff: Initial backoff in seconds.
    """

    max_retries: int = Field(default=2, ge=0, le=5, description="Maximum retry attempts")
    backoff_strategy: str = Field(
        default="exponential",
        description="Backoff strategy: 'exponential' or 'linear'",
    )
    initial_backoff: float = Field(
        default=1.0,
        ge=0.1,
        description="Initial backoff in seconds",
    )

    model_config = {"frozen": True}


class AgentHistoryEntry(BaseModel):
    """Entry in the agent execution history.

    Attributes:
        agent_name: Name of the agent that executed.
        timestamp: ISO timestamp of execution.
        duration_seconds: Execution duration in seconds.
        decision: Agent decision (continue, skip, retry, error).
        message: Agent message.
        quality_score: Quality score (0.0-1.0) if available.
        data_keys_produced: List of state keys produced by this agent.
        metadata: Additional metadata.
    """

    agent_name: str = Field(..., description="Name of the agent")
    timestamp: str = Field(..., description="ISO timestamp of execution")
    duration_seconds: float = Field(..., ge=0, description="Execution duration in seconds")
    decision: str = Field(..., description="Agent decision: continue, skip, retry, error")
    message: str = Field(..., description="Agent message")
    quality_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Quality score (0.0-1.0)"
    )
    data_keys_produced: list[str] = Field(
        default_factory=list, description="State keys produced by this agent"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {"frozen": True}


class LogEntry(BaseModel):
    """Structured log entry.

    Attributes:
        timestamp: ISO timestamp.
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        agent: Agent name that generated the log.
        message: Log message.
        metadata: Additional metadata.
    """

    timestamp: str = Field(..., description="ISO timestamp")
    level: str = Field(..., description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    agent: str = Field(..., description="Agent name")
    message: str = Field(..., description="Log message")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {"frozen": True}