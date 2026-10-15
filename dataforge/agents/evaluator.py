"""Evaluator Agent - Quality gate before the report is written."""

from typing import Any

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.state import GraphState


class EvaluatorAgent(Agent):
    """Validates analysis results before reporting.

    Checks:
    - ``has_data``: cleaned data exists and is non-empty
    - ``has_insights``: at least one business insight was generated
    - ``has_visualizations``: at least one chart was produced
    - ``data_quality``: under 50% of cells are missing

    The verdict is written to ``evaluation`` (``passed``, ``checks``,
    ``failed_checks``, ``remediation``). The agent itself never fails — the
    PlannerAgent reads the verdict and re-runs ``remediation`` once before
    re-evaluating.
    """

    phase: ExecutionPhase = ExecutionPhase.OUTPUT
    required_inputs: list[str] = []
    produced_outputs: list[str] = ["evaluation"]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=1)
    failure_policy: FailurePolicy = FailurePolicy.SKIP
    timeout_seconds: int = 30

    # Which agent owns each check (re-run to remediate a failure).
    REMEDIATION: dict[str, str | None] = {
        "has_data": None,  # nothing downstream can recover missing data
        "has_insights": "InsightGenerationAgent",
        "has_visualizations": "VisualizationAgent",
        "data_quality": None,  # a property of the input, not of the analysis
    }

    def __init__(
        self, llm_provider: LLMProvider | None = None, logger: StructuredLogger | None = None
    ):
        """Initialize the Evaluator Agent."""
        super().__init__(llm_provider, logger)

    async def execute(self, state: GraphState) -> AgentResult:
        """Validate current analysis results against quality gates."""
        checks = {
            "has_data": self._check_has_data(state),
            "has_insights": self._check_has_insights(state),
            "has_visualizations": self._check_has_visualizations(state),
            "data_quality": self._check_data_quality(state),
        }
        failed_checks = [name for name, ok in checks.items() if not ok]
        remediation = next(
            (self.REMEDIATION[c] for c in failed_checks if self.REMEDIATION.get(c)), None
        )
        passed = not failed_checks

        if self.logger:
            self.logger.info(
                "Validation checks performed", agent=self.name, checks=checks, passed=passed
            )

        evaluation: dict[str, Any] = {
            "passed": passed,
            "checks": checks,
            "failed_checks": failed_checks,
            "remediation": remediation,
        }
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=(
                "All quality checks passed"
                if passed
                else f"Quality checks failed: {', '.join(failed_checks)}"
            ),
            data_updates={"evaluation": evaluation},
            metadata={"validation_results": checks, "failed_checks": failed_checks},
            quality_score=round(sum(checks.values()) / len(checks), 3),
        )

    def _check_has_data(self, state: GraphState) -> bool:
        data = state.get("cleaned_data")
        if data is None:
            data = state.get("raw_data")
        return data is not None and len(data) > 0

    def _check_has_insights(self, state: GraphState) -> bool:
        return len(state.get("business_insights") or []) > 0

    def _check_has_visualizations(self, state: GraphState) -> bool:
        return len(state.get("visualizations") or []) > 0

    def _check_data_quality(self, state: GraphState) -> bool:
        profile = state.get("profile")
        if not profile:
            return True  # nothing to judge yet
        return profile.get("overall_missing_ratio", 0) < 0.5
