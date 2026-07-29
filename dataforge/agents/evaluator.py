"""Evaluator Agent - Quality validation for analysis results."""

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


class EvaluatorAgent(Agent):
    """Validates analysis results and quality.

    The Evaluator Agent runs after visualization and validates:
    - Whether data was successfully loaded
    - Whether insights were generated
    - Data quality (missing values, etc.)
    - Whether sufficient analysis depth was achieved

    If validation passes, the workflow proceeds to reporting.
    If validation fails, the workflow re-plans with remediation suggestions.
    """

    def __init__(
        self, llm_provider: LLMProvider | None = None, logger: StructuredLogger | None = None
    ):
        """Initialize the Evaluator Agent.

        Args:
            llm_provider: LLM provider instance.
            logger: Structured logger instance.
        """
        super().__init__(llm_provider, logger)

    async def execute(self, state: GraphState) -> AgentResult:
        """Validate current analysis results against quality gates.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with validation decision and results.
        """
        checks = {
            "has_data": self._check_has_data(state),
            "has_insights": self._check_has_insights(state),
            "data_quality": self._check_data_quality(state),
            "sufficient_depth": self._check_analysis_depth(state),
        }

        all_passed = all(checks.values())

        self.logger.info(
            "Validation checks performed",
            agent=self.name,
            checks=checks,
            all_passed=all_passed,
        )

        if all_passed:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="All validation checks passed",
                data_updates={"validation_status": "passed"},
                metadata={"validation_results": checks, "all_checks_passed": True},
            )
        else:
            failed_checks = [k for k, v in checks.items() if not v]

            # Increment retry count
            new_retry_count = state.retry_count + 1

            return AgentResult(
                decision=AgentDecision.REPLAN,
                message=f"Validation failed: {', '.join(failed_checks)}",
                data_updates={
                    "validation_status": "failed",
                    "failed_checks": failed_checks,
                    "retry_count": new_retry_count,
                },
                metadata={
                    "validation_results": checks,
                    "failed_checks": failed_checks,
                    "retry_count": new_retry_count,
                },
            )

    def _check_has_data(self, state: GraphState) -> bool:
        """Check if data was loaded.

        Args:
            state: Current graph state.

        Returns:
            True if data exists and is not empty.
        """
        raw_data = state.get("raw_data")
        if raw_data is None:
            return False
        return len(raw_data) > 0

    def _check_has_insights(self, state: GraphState) -> bool:
        """Check if insights were generated.

        Args:
            state: Current graph state.

        Returns:
            True if at least 3 insights were generated.
        """
        insights = state.get("insights", [])
        return len(insights) >= 3

    def _check_data_quality(self, state: GraphState) -> bool:
        """Check data quality (missing values, etc.).

        Args:
            state: Current graph state.

        Returns:
            True if data quality is acceptable.
        """
        profile = state.get("profile")
        if profile is None:
            # No profile yet, skip this check
            return True

        # Check overall missing value percentage
        missing_ratio = profile.get("overall_missing_ratio", 0)
        return missing_ratio < 0.5  # Less than 50% missing

    def _check_analysis_depth(self, state: GraphState) -> bool:
        """Check if sufficient analysis was performed.

        Args:
            state: Current graph state.

        Returns:
            True if sufficient depth was achieved.
        """
        # Require at least: ingestion + profiling + (stats OR viz)
        required = {"DataIngestionAgent", "DataProfilingAgent"}
        optional = {"StatisticalAnalysisAgent", "VisualizationAgent"}

        completed = set(state.steps_completed)
        has_required = required.issubset(completed)
        has_optional = len(completed.intersection(optional)) > 0

        return has_required and has_optional
