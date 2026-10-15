"""Planner Agent - Central decision maker for the analysis workflow.

Routes the v2 pipeline in phase order:

    validation → cleaning → schema → domain → objective → profiling →
    features → kpi → statistics → insights → visualization → evaluator →
    reporting

Every agent returns to the planner, which applies:

- **Preconditions**: an agent is only scheduled once the state keys it
  needs exist (e.g. statistics needs ``profile``); agents whose inputs never
  appear are skipped.
- **Quality gate**: a failed agent is retried up to ``MAX_AGENT_VISITS``
  times, then skipped (recorded in ``steps_skipped``).
- **Evaluation loop**: when the EvaluatorAgent fails a check, the planner
  re-runs the agent that owns that check once, then re-evaluates before
  reporting.
- **Loop guard**: when the global step budget is exhausted, the planner goes
  straight to ReportingAgent (best-effort report) and then completes.
"""

from typing import Any

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.state import GraphState


class PlannerAgent(Agent):
    """Central planning agent that determines execution flow."""

    # The planner spans all phases; intake is nominal.
    phase: ExecutionPhase = ExecutionPhase.DATA_INTAKE
    required_inputs: list[str] = []
    produced_outputs: list[str] = []
    retry_policy: RetryPolicy = RetryPolicy(max_retries=1)
    failure_policy: FailurePolicy = FailurePolicy.HALT
    timeout_seconds: int = 30

    # (agent name, state keys that must be present before it can run)
    PIPELINE: list[tuple[str, list[str]]] = [
        ("DataValidationAgent", []),
        ("DataCleaningAgent", ["raw_data"]),
        ("SchemaDetectionAgent", ["cleaned_data"]),
        ("BusinessDomainDetectionAgent", ["cleaned_data"]),
        ("BusinessObjectiveDetectionAgent", ["business_domain"]),
        ("DataProfilingAgent", ["cleaned_data"]),
        ("FeatureEngineeringAgent", ["cleaned_data"]),
        ("KPIDiscoveryAgent", ["cleaned_data"]),
        ("StatisticalAnalysisAgent", ["profile"]),
        ("InsightGenerationAgent", ["cleaned_data"]),
        ("VisualizationAgent", ["cleaned_data"]),
        ("EvaluatorAgent", ["cleaned_data"]),
        ("ReportingAgent", ["cleaned_data"]),
    ]
    # Kept as an alias for code written against the v2 sprint naming.
    V2_PIPELINE = PIPELINE
    MAX_AGENT_VISITS: int = 2
    V2_MAX_AGENT_VISITS = MAX_AGENT_VISITS
    MAX_EVALUATIONS: int = 2

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize the Planner Agent."""
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)
        self.name = "PlannerAgent"

    async def execute(self, state: GraphState) -> AgentResult:
        """Decide the next agent based on the current state and history."""
        steps = state.steps_completed

        if not state.should_continue():
            return self._budget_exhausted(state)

        # Quality gate: retry the last agent on failure within budget, else skip it.
        last_agent, last_success = self._last_agent_status(state)
        if last_agent is not None and not last_success:
            visits = state.get_agent_visit_count(last_agent)
            if visits <= self.MAX_AGENT_VISITS:
                return AgentResult(
                    decision=AgentDecision.RETRY,
                    message=f"Retrying {last_agent} (attempt {visits + 1})",
                    next_agent_suggestion=last_agent,
                    metadata={"reason": "quality_gate_retry", "agent": last_agent},
                )
            return self._proceed(
                state,
                skip=last_agent,
                message=f"{last_agent} failed {visits} times, skipping",
                reason="quality_gate_skip",
                extra_updates={"steps_skipped": list(state.steps_skipped) + [last_agent]},
            )

        if "ReportingAgent" in steps:
            return AgentResult(
                decision=AgentDecision.COMPLETE,
                message="Analysis complete, report generated",
                metadata={"reason": "report_generated"},
            )

        # Evaluation loop: remediate a failed check once, then re-evaluate.
        evaluation = state.get("evaluation") or {}
        if last_agent == "EvaluatorAgent" and not evaluation.get("passed", True):
            remediation = evaluation.get("remediation")
            evaluations = state.get_agent_visit_count("EvaluatorAgent")
            if remediation and evaluations < self.MAX_EVALUATIONS:
                return AgentResult(
                    decision=AgentDecision.REPLAN,
                    message=(
                        f"Evaluation failed ({', '.join(evaluation.get('failed_checks', []))}); "
                        f"re-running {remediation}"
                    ),
                    next_agent_suggestion=remediation,
                    data_updates={"pending_reevaluation": True},
                    metadata={"reason": "evaluation_remediation", "agent": remediation},
                )
        if state.get("pending_reevaluation") and last_agent != "EvaluatorAgent":
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Remediation done, re-evaluating",
                next_agent_suggestion="EvaluatorAgent",
                data_updates={"pending_reevaluation": False},
                metadata={"reason": "reevaluation"},
            )

        return self._proceed(state)

    # -- helpers ---------------------------------------------------------
    def _proceed(
        self,
        state: GraphState,
        skip: str | None = None,
        message: str | None = None,
        reason: str = "plan",
        extra_updates: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Route to the next viable pipeline agent, skipping unrunnable ones."""
        suggestion = self._next_viable(state, skip=skip)
        if suggestion is None:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No viable next agent (missing preconditions)",
                data_updates=extra_updates or {},
                metadata={
                    "reason": reason if reason != "plan" else "blocked",
                    "blocked": True,
                    "steps": state.steps_completed,
                },
            )
        if not state.steps_completed:
            message, reason = "Starting analysis with data validation", "initial_state"
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=message or f"Proceeding to {suggestion}",
            next_agent_suggestion=suggestion,
            data_updates=extra_updates or {},
            metadata={"reason": reason},
        )

    def _budget_exhausted(self, state: GraphState) -> AgentResult:
        """Global step budget used up: produce a best-effort report, then stop."""
        if "ReportingAgent" not in state.steps_completed and state.get("cleaned_data") is not None:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Step budget exhausted, generating report with available results",
                next_agent_suggestion="ReportingAgent",
                metadata={"reason": "max_global_steps_report"},
            )
        return AgentResult(
            decision=AgentDecision.COMPLETE,
            message="Max global steps reached, ending analysis",
            metadata={"reason": "max_global_steps"},
        )

    def _next_viable(self, state: GraphState, skip: str | None = None) -> str | None:
        """First pipeline agent not completed/skipped whose preconditions are met."""
        done = set(state.steps_completed) | set(state.steps_skipped)
        if skip is not None:
            done.add(skip)
        for agent_name, preconditions in self.PIPELINE:
            if agent_name in done:
                continue
            if all(state.get(key) is not None for key in preconditions):
                return agent_name
        return None

    def _last_agent_status(self, state: GraphState) -> tuple[str | None, bool]:
        """Name and success flag of the most recent non-planner agent."""
        for entry in reversed(state.agent_history):
            if isinstance(entry, dict):
                agent_name = entry.get("agent")
                result = entry.get("result", {})
            else:
                agent_name = entry.agent_name
                result = (entry.metadata or {}).get("result", {})
            if agent_name == self.name:
                continue
            return agent_name, bool(result.get("success", True))
        return None, True
