"""Base agent interface and utilities."""

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel

from dataforge.core.llm import LLMConfig, LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState
from dataforge.shared.errors import AgentExecutionError
from dataforge.shared.utils import get_timestamp

__all__ = ["Agent", "AgentDecision", "AgentResult"]


class AgentDecision(Enum):
    """Decision returned by agent after execution."""

    CONTINUE = "continue"  # Continue to next agent
    REPLAN = "replan"  # Ask planner to re-evaluate
    COMPLETE = "complete"  # Analysis complete
    ERROR = "error"  # Error occurred


class AgentResult(BaseModel):
    """Result of agent execution."""

    decision: AgentDecision
    message: str
    data_updates: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    next_agent_suggestion: str | None = None

    model_config = {"frozen": True}


class Agent(ABC):
    """Base class for all agents.

    All agents:
    - Receive GraphState as input
    - Return AgentResult with decision
    - Have automatic logging via execute_with_logging
    - Use shared LLMProvider and StructuredLogger
    """

    def __init__(
        self, llm_provider: LLMProvider | None = None, logger: StructuredLogger | None = None
    ):
        """Initialize the agent.

        Args:
            llm_provider: LLM provider instance (optional).
            logger: Structured logger instance (optional).
        """
        self.llm = llm_provider
        self.logger = logger
        self.name = self.__class__.__name__

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

    async def execute_with_logging(self, state: GraphState) -> tuple[AgentResult, GraphState]:
        """Execute with automatic logging and state updates.

        Args:
            state: Current graph state.

        Returns:
            Tuple of (AgentResult, updated GraphState).
        """
        if self.logger:
            self.logger.info(f"Starting {self.name}", agent=self.name)

        start_time = time.time()

        try:
            result = await self.execute(state)
            duration = time.time() - start_time

            if self.logger:
                # Log completion
                self.logger.info(
                    f"Completed {self.name}",
                    agent=self.name,
                    decision=result.decision.value,
                    duration_seconds=duration,
                    result_message=result.message,
                )

            # Add log to state
            updated_state = state.add_log(
                level="INFO",
                agent=self.name,
                message=f"Completed {self.name}",
                decision=result.decision.value,
                duration_seconds=duration,
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
                    "next_agent_suggestion": result.next_agent_suggestion,
                    **result.metadata,
                },
            )

            # Apply data updates
            if result.data_updates:
                for key, value in result.data_updates.items():
                    updated_state = updated_state.set(key, value)

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
            )

            updated_state = updated_state.add_agent_result(
                self.name,
                {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration,
                },
            )

            return error_result, updated_state

    def can_handle(self, state: GraphState) -> bool:
        """Check if this agent can process the current state.

        Args:
            state: Current graph state.

        Returns:
            True if agent can handle the state.
        """
        # Default: can handle any state
        return True

    def get_dependencies(self) -> list[str]:
        """Return list of required state keys.

        Returns:
            List of state field names that must be non-None.
        """
        # Default: no dependencies
        return []
