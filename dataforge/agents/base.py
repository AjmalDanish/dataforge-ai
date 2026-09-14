"""Base agent interface and utilities."""

import time
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState
from dataforge.shared.errors import AgentExecutionError
from dataforge.shared.utils import get_timestamp

__all__ = ["Agent", "AgentDecision", "AgentResult"]


class AgentDecision(Enum):
    """Decision returned by agent after execution."""

    CONTINUE = "continue"  # Continue to next agent
    SKIP = "skip"  # Skip this agent
    RETRY = "retry"  # Retry this agent
    ERROR = "error"  # Error occurred
    COMPLETE = "complete"  # Analysis complete


class AgentResult(BaseModel):
    """Result of agent execution."""

    decision: AgentDecision
    message: str
    data_updates: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    next_agent_suggestion: str | None = None
    
    # v2 enhancements
    quality_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Quality score (0.0-1.0)"
    )
    execution_notes: list[str] = Field(
        default_factory=list, description="Notes about execution"
    )
    execution_duration: float | None = Field(
        default=None, description="Execution duration in seconds"
    )
    warnings: list[str] = Field(default_factory=list, description="Warnings during execution")
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="Structured execution metrics"
    )

    model_config = {"frozen": True}


class Agent(ABC):
    """Base class for all agents.

    All agents:
    - Receive GraphState as input
    - Return AgentResult with decision
    - Have automatic logging via execute_with_logging
    - Use shared LLMProvider and StructuredLogger
    - Support v2 features: phase tracking, retry policy, quality scoring
    """

    # v2 agent properties (can be overridden by subclasses)
    # Note: These are class attributes, not Pydantic fields
    phase: ExecutionPhase = ExecutionPhase.DATA_INTAKE
    required_inputs: list[str] = []
    produced_outputs: list[str] = []
    retry_policy: RetryPolicy = RetryPolicy()
    failure_policy: FailurePolicy = FailurePolicy.HALT
    timeout_seconds: int = 300  # 5 minutes default

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize the agent.

        Args:
            llm_provider: LLM provider instance (optional).
            logger: Structured logger instance (optional).
            retry_policy: Retry policy override (optional).
            failure_policy: Failure policy override (optional).
            timeout_seconds: Timeout override in seconds (optional).
        """
        self.llm = llm_provider
        self.logger = logger
        self.name = self.__class__.__name__
        
        # Allow runtime overrides of v2 properties
        if retry_policy is not None:
            self.retry_policy = retry_policy
        if failure_policy is not None:
            self.failure_policy = failure_policy
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def execute(self, state: GraphState) -> AgentResult:
        """Execute agent logic.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with decision, message, and any data updates.

        Raises:
            AgentExecutionError: On execution errors.
        """
        pass

    def can_execute(self, state: GraphState) -> bool:
        """Check if this agent can execute on the current state.

        Validates:
        1. Current phase matches agent's phase
        2. All required inputs are present
        3. Agent hasn't exceeded retry limit

        Args:
            state: Current graph state.

        Returns:
            True if agent can execute.
        """
        # Check phase compatibility
        if state.current_phase != self.phase:
            return False

        # Check required inputs
        for input_key in self.required_inputs:
            if input_key not in state.data or state.data[input_key] is None:
                return False

        # Check retry limit
        visit_count = state.get_agent_visit_count(self.name)
        if visit_count > self.retry_policy.max_retries:
            return False

        return True

    def validate_input(self, state: GraphState) -> tuple[bool, list[str]]:
        """Validate input state before execution.

        Args:
            state: Current graph state.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        # Validate required inputs
        for input_key in self.required_inputs:
            if input_key not in state.data:
                errors.append(f"Missing required input: {input_key}")
            elif state.data[input_key] is None:
                errors.append(f"Required input is None: {input_key}")

        return len(errors) == 0, errors

    def validate_output(self, result: AgentResult) -> tuple[bool, list[str]]:
        """Validate agent output before returning.

        Args:
            result: Agent result to validate.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        # Validate quality score if provided
        if result.quality_score is not None:
            if not 0.0 <= result.quality_score <= 1.0:
                errors.append(f"Quality score out of range: {result.quality_score}")

        # Validate produced outputs are in data_updates
        for output_key in self.produced_outputs:
            if output_key not in result.data_updates:
                errors.append(f"Missing expected output: {output_key}")

        return len(errors) == 0, errors

    def before_execute(self, state: GraphState) -> GraphState:
        """Hook called before agent execution.

        Can be overridden by subclasses to:
        - Update state before execution
        - Log pre-execution information
        - Perform validation

        Args:
            state: Current graph state.

        Returns:
            Possibly modified state.
        """
        # Default: no changes
        return state

    def after_execute(
        self, state: GraphState, result: AgentResult
    ) -> tuple[GraphState, AgentResult]:
        """Hook called after agent execution.

        Can be overridden by subclasses to:
        - Post-process results
        - Add additional metadata
        - Perform cleanup

        Args:
            state: Current graph state.
            result: Agent execution result.

        Returns:
            Tuple of (possibly modified state, possibly modified result).
        """
        # Default: no changes
        return state, result

    async def execute_with_logging(self, state: GraphState) -> tuple[AgentResult, GraphState]:
        """Execute with automatic logging and state updates.

        Args:
            state: Current graph state.

        Returns:
            Tuple of (AgentResult, updated GraphState).
        """
        # Pre-execution hook
        state = self.before_execute(state)

        # Validate input
        is_valid, errors = self.validate_input(state)
        if not is_valid:
            error_msg = f"Input validation failed: {', '.join(errors)}"
            error_result = AgentResult(
                decision=AgentDecision.ERROR,
                message=error_msg,
                execution_notes=errors,
            )
            return error_result, state.add_log(
                level="ERROR", agent=self.name, message=error_msg
            )

        if self.logger:
            self.logger.info(f"Starting {self.name}", agent=self.name)

        start_time = time.time()

        try:
            result = await self.execute(state)
            duration = time.time() - start_time

            # Add execution duration to result
            result = result.model_copy(update={"execution_duration": duration})

            # Validate output
            is_valid, errors = self.validate_output(result)
            if not is_valid:
                warning_msg = f"Output validation warnings: {', '.join(errors)}"
                result = result.model_copy(
                    update={"warnings": result.warnings + [warning_msg]}
                )

            # Post-execution hook
            state, result = self.after_execute(state, result)

            if self.logger:
                # Log completion
                self.logger.info(
                    f"Completed {self.name}",
                    agent=self.name,
                    decision=result.decision.value,
                    duration_seconds=duration,
                    quality_score=result.quality_score,
                    result_message=result.message,
                )

            # Add log to state
            updated_state = state.add_log(
                level="INFO",
                agent=self.name,
                message=f"Completed {self.name}",
                decision=result.decision.value,
                duration_seconds=duration,
                quality_score=result.quality_score,
                result_message=result.message,
            )

            # Update state with agent result
            updated_state = updated_state.add_agent_result(
                self.name,
                {
                    "success": result.decision != AgentDecision.ERROR,
                    "decision": result.decision.value,
                    "message": result.message,
                    "duration_seconds": duration,
                    "quality_score": result.quality_score,
                    "next_agent_suggestion": result.next_agent_suggestion,
                    "warnings": result.warnings,
                    "execution_notes": result.execution_notes,
                    **result.metadata,
                },
                data_keys_produced=list(result.data_updates.keys()),
                quality_score=result.quality_score,
            )

            # Apply data updates
            if result.data_updates:
                for key, value in result.data_updates.items():
                    updated_state = updated_state.set(key, value)

            # Add metrics to state
            if result.metrics:
                for key, value in result.metrics.items():
                    updated_state = updated_state.add_metric(key, value)

            return result, updated_state

        except Exception as e:
            duration = time.time() - start_time

            if self.logger:
                self.logger.error(
                    f"{self.name} failed",
                    agent=self.name,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    duration_seconds=duration,
                )

            # Add error log to state
            updated_state = state.add_log(
                level="ERROR",
                agent=self.name,
                message=f"{self.name} failed",
                error_type=type(e).__name__,
                error_message=str(e),
                duration_seconds=duration,
            )

            error_result = AgentResult(
                decision=AgentDecision.ERROR,
                message=f"{self.name} failed: {str(e)}",
                execution_duration=duration,
                execution_notes=[f"Error: {type(e).__name__}"],
            )

            updated_state = updated_state.add_agent_result(
                self.name,
                {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration,
                },
                decision=error_result.decision.value,
            )

            return error_result, updated_state

    def can_handle(self, state: GraphState) -> bool:
        """Check if this agent can process the current state.

        Deprecated: Use can_execute() instead. This method is kept for
        backward compatibility with v1 agents.

        Args:
            state: Current graph state.

        Returns:
            True if agent can handle the state.
        """
        return self.can_execute(state)

    def get_dependencies(self) -> list[str]:
        """Return list of required state keys.

        Deprecated: Use required_inputs property instead. This method is kept
        for backward compatibility with v1 agents.

        Returns:
            List of state field names that must be non-None.
        """
        return self.required_inputs

    def should_save_checkpoint(self, state: GraphState) -> bool:
        """Determine if a checkpoint should be saved after this agent.

        Args:
            state: Current graph state.

        Returns:
            True if checkpoint should be saved.
        """
        # Default: save checkpoint after every agent
        # Subclasses can override for more granular control
        return True

    def save_checkpoint_if_needed(self, state: GraphState) -> GraphState:
        """Save checkpoint if needed.

        Args:
            state: Current graph state.

        Returns:
            Unmodified state (checkpoint is saved to disk).
        """
        if self.should_save_checkpoint(state):
            try:
                checkpoint_dir = state.save_checkpoint()
                if self.logger:
                    self.logger.info(
                        f"Checkpoint saved",
                        agent=self.name,
                        checkpoint_dir=str(checkpoint_dir),
                    )
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Failed to save checkpoint: {str(e)}",
                        agent=self.name,
                    )

        return state
