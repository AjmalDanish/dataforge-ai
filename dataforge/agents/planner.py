"""Planner Agent - Central decision maker for the analysis workflow.

Supports two pipelines:
- v1 (default, ``pipeline_version`` unset): legacy chain
  ingestion → profiling → statistics → visualization → evaluator → reporting.
  Preserved for backward compatibility (CLI, existing tests).
- v2 (``state.data["pipeline_version"] == "v2"``): phase-ordered chain
  validation → cleaning → schema → domain → objective → profiling →
  features → kpi → statistics → visualization → reporting, with per-agent
  quality gates (retry on failure within budget, else skip) and a global
  step-count loop guard.
"""

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase, FailurePolicy, RetryPolicy
from dataforge.core.state import GraphState


class PlannerAgent(Agent):
    """Central planning agent that determines execution flow.

    The Planner Agent runs after each agent and decides what to do next:
    - Determine which agent should run next
    - Skip irrelevant agents based on data characteristics
    - Decide when analysis is complete
    - Handle error recovery and re-planning

    Decision Logic (v1):
    1. Initial state (empty steps_completed) → Start with Ingestion Agent
    2. After DataIngestionAgent → Validate, then Profiling Agent
    3. After DataProfilingAgent → Statistics (if numeric) or Visualization (if no numeric)
    4. After StatisticalAnalysisAgent → Visualization Agent
    5. After VisualizationAgent → Evaluator Agent
    6. After EvaluatorAgent → Reporting (if passed) or Re-plan (if failed)
    7. After ReportingAgent → Complete

    Uses `steps_completed` list to detect current stage.
    """

    # v2 contract attributes (planner spans all phases; intake is nominal)
    phase: ExecutionPhase = ExecutionPhase.DATA_INTAKE
    required_inputs: list[str] = []
    produced_outputs: list[str] = []
    retry_policy: RetryPolicy = RetryPolicy(max_retries=1)
    failure_policy: FailurePolicy = FailurePolicy.HALT
    timeout_seconds: int = 30

    # v2 pipeline: (agent name, state keys that must be present)
    V2_PIPELINE: list[tuple[str, list[str]]] = [
        ("DataValidationAgent", []),
        ("DataCleaningAgent", ["raw_data"]),
        ("SchemaDetectionAgent", ["cleaned_data"]),
        ("BusinessDomainDetectionAgent", ["cleaned_data"]),
        ("BusinessObjectiveDetectionAgent", ["business_domain"]),
        ("DataProfilingAgent", ["cleaned_data"]),
        ("FeatureEngineeringAgent", ["cleaned_data"]),
        ("KPIDiscoveryAgent", ["cleaned_data"]),
        ("StatisticalAnalysisAgent", ["profile"]),
        ("VisualizationAgent", ["cleaned_data"]),
        ("ReportingAgent", ["cleaned_data"]),
    ]
    V2_MAX_AGENT_VISITS: int = 2

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize the Planner Agent.

        Args:
            llm_provider: LLM provider instance.
            logger: Structured logger instance.
            retry_policy: Retry policy override (optional).
            failure_policy: Failure policy override (optional).
            timeout_seconds: Timeout override in seconds (optional).
        """
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)
        self.name = "PlannerAgent"

    async def execute(self, state: GraphState) -> AgentResult:
        """Decide next action based on current state and history.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with decision, message, and next agent suggestion.
        """
        # Global loop guard (v2 state).
        try:
            if not state.should_continue():
                return AgentResult(
                    decision=AgentDecision.COMPLETE,
                    message="Max global steps reached, ending analysis",
                    metadata={"reason": "max_global_steps"},
                )
        except AttributeError:
            pass

        # v2 pipeline when explicitly selected.
        try:
            pipeline = state.get("pipeline_version")
        except Exception:
            pipeline = None
        if pipeline == "v2":
            return self._route_v2(state)

        # Use steps_completed to detect where we are in the workflow
        steps = state.steps_completed

        # Empty steps_completed → Start with ingestion
        if not steps:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Starting analysis with data ingestion",
                next_agent_suggestion="DataIngestionAgent",
                metadata={"reason": "initial_state"},
            )

        # After DataIngestionAgent in steps → Check for profiling
        if "DataIngestionAgent" in steps and "DataProfilingAgent" not in steps:
            return self._after_ingestion(state)

        # After DataProfilingAgent in steps → Check for statistics or visualization
        if "DataProfilingAgent" in steps and "StatisticalAnalysisAgent" not in steps:
            return self._after_profiling(state)

        # After StatisticalAnalysisAgent in steps → Check for visualization
        if "StatisticalAnalysisAgent" in steps and "VisualizationAgent" not in steps:
            return self._after_statistics(state)

        # After VisualizationAgent in steps → Check for evaluator
        if "VisualizationAgent" in steps and "EvaluatorAgent" not in steps:
            return self._after_visualization(state)

        # After EvaluatorAgent in steps → Check for reporting
        if "EvaluatorAgent" in steps and "ReportingAgent" not in steps:
            return self._after_evaluator(state)

        # After ReportingAgent in steps → Complete
        if "ReportingAgent" in steps:
            return AgentResult(
                decision=AgentDecision.COMPLETE,
                message="Analysis complete, report generated",
                metadata={"reason": "report_generated"},
            )

        # Fallback
        self.logger.warning(
            "Planner reached unexpected state",
            agent=self.name,
            steps=steps,
            input_dataset_path=state.input_dataset_path,
        )
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Proceeding with next agent (fallback)",
            metadata={"reason": "fallback"},
        )

    # -- v2 routing ------------------------------------------------------
    def _route_v2(self, state: GraphState) -> AgentResult:
        """Phase-ordered routing with per-agent quality gates."""
        steps = state.steps_completed

        # Quality gate: retry the last agent on failure within budget.
        last_agent, last_success = self._last_agent_status(state)
        if last_agent is not None and not last_success:
            visits = self._visit_count(state, last_agent)
            if visits <= self.V2_MAX_AGENT_VISITS:
                return AgentResult(
                    decision=AgentDecision.RETRY,
                    message=f"Retrying {last_agent} (attempt {visits + 1})",
                    next_agent_suggestion=last_agent,
                    metadata={"reason": "quality_gate_retry", "agent": last_agent},
                )
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"{last_agent} failed twice, skipping",
                next_agent_suggestion=self._next_viable(state, skip=last_agent),
                data_updates={"steps_skipped": self._skipped_plus(state, last_agent)},
                metadata={"reason": "quality_gate_skip", "agent": last_agent},
            )

        # Reporting done → complete.
        if "ReportingAgent" in steps:
            return AgentResult(
                decision=AgentDecision.COMPLETE,
                message="Analysis complete, report generated",
                metadata={"reason": "report_generated", "pipeline": "v2"},
            )

        suggestion = self._next_viable(state)
        if suggestion is None:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No viable next agent (missing preconditions)",
                metadata={"reason": "v2_blocked", "steps": steps},
            )
        if not steps:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Starting v2 analysis with data validation",
                next_agent_suggestion=suggestion,
                metadata={"reason": "initial_state", "pipeline": "v2"},
            )
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Proceeding to {suggestion}",
            next_agent_suggestion=suggestion,
            metadata={"reason": "v2_plan", "pipeline": "v2"},
        )

    def _next_viable(self, state: GraphState, skip: str | None = None) -> str | None:
        """First pipeline agent not completed (and not skipped) with met preconditions."""
        steps = set(state.steps_completed)
        skipped = set(self._skipped(state))
        if skip is not None:
            skipped.add(skip)
        for agent_name, preconditions in self.V2_PIPELINE:
            if agent_name in steps or agent_name in skipped:
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

    def _visit_count(self, state: GraphState, agent_name: str) -> int:
        try:
            return state.get_agent_visit_count(agent_name)
        except AttributeError:
            return sum(1 for s in state.steps_completed if s == agent_name)

    def _skipped(self, state: GraphState) -> list[str]:
        try:
            return list(state.steps_skipped)
        except AttributeError:
            return []

    def _skipped_plus(self, state: GraphState, agent_name: str) -> list[str]:
        return self._skipped(state) + [agent_name]

    def _after_ingestion(self, state: GraphState) -> AgentResult:
        """Determine next action after data ingestion."""
        raw_data = state.get("raw_data")
        if raw_data is None:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No data loaded, cannot continue",
                metadata={"reason": "no_data_loaded"},
            )

        import pandas as pd

        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Data loaded ({len(raw_data)} rows, {len(raw_data.columns)} columns), proceeding to profiling",
            next_agent_suggestion="DataProfilingAgent",
            metadata={
                "reason": "data_loaded_successfully",
                "rows": len(raw_data),
                "columns": len(raw_data.columns),
            },
        )

    def _after_profiling(self, state: GraphState) -> AgentResult:
        """Determine next action after profiling."""
        profile = state.get("profile", {})

        if not profile:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No profile available",
                metadata={"reason": "no_profile_available"},
            )

        has_numeric = profile.get("has_numeric_columns", False)
        has_categorical = profile.get("has_categorical_columns", False)

        if not has_numeric and not has_categorical:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No analyzable columns found (no numeric or categorical columns)",
                metadata={"reason": "no_analyzable_columns"},
            )

        if not has_numeric:
            self.logger.info("No numeric columns, skipping statistical analysis", agent=self.name)
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="No numeric data, skipping statistics, proceeding to visualization",
                next_agent_suggestion="VisualizationAgent",
                metadata={"reason": "no_numeric_columns"},
            )

        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Numeric data found, running statistical analysis",
            next_agent_suggestion="StatisticalAnalysisAgent",
            metadata={
                "reason": "numeric_data_available",
                "numeric_column_count": profile.get("numeric_column_count", 0),
            },
        )

    def _after_statistics(self, state: GraphState) -> AgentResult:
        """Determine next action after statistics."""
        stats = state.get("statistics", {})

        if stats:
            corr_count = stats.get("correlations_count", 0)
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Statistical analysis complete ({corr_count} correlations found), generating visualizations",
                next_agent_suggestion="VisualizationAgent",
                metadata={"reason": "statistics_complete", "correlations_count": corr_count},
            )
        else:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Proceeding to visualization",
                next_agent_suggestion="VisualizationAgent",
                metadata={"reason": "statistics_produced_no_results"},
            )

    def _after_visualization(self, state: GraphState) -> AgentResult:
        """Determine next action after visualization."""
        viz_count = len(state.get("visualizations", []))
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Generated {viz_count} visualizations, validating results",
            next_agent_suggestion="EvaluatorAgent",
            metadata={"reason": "visualization_complete", "visualization_count": viz_count},
        )

    def _after_evaluator(self, state: GraphState) -> AgentResult:
        """Determine next action after evaluator."""
        if state.validation_status == "failed":
            failed_checks = state.get("failed_checks", [])
            retry_count = state.retry_count

            # Limit replan attempts
            if retry_count >= state.max_retries:
                self.logger.warning(
                    "Max retries reached, proceeding to report anyway",
                    agent=self.name,
                    retry_count=retry_count,
                )
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Max validation retries reached, generating report with available results",
                    next_agent_suggestion="ReportingAgent",
                    metadata={"reason": "max_retries_exceeded", "retry_count": retry_count},
                )

            # Suggest remediation
            suggestion = self._suggest_remediation(failed_checks, state)
            return AgentResult(
                decision=AgentDecision.REPLAN,
                message=f"Validation failed: {', '.join(failed_checks)}. Re-planning.",
                next_agent_suggestion=suggestion,
                data_updates={"retry_count": retry_count + 1},
                metadata={
                    "reason": "validation_failed",
                    "failed_checks": failed_checks,
                    "retry_count": retry_count + 1,
                },
            )
        else:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Validation passed, generating final report",
                next_agent_suggestion="ReportingAgent",
                metadata={"reason": "validation_passed"},
            )

    def _suggest_remediation(self, failed_checks: list[str], state: GraphState) -> str:
        """Suggest which agent to run for remediation.

        Args:
            failed_checks: List of failed validation check names.
            state: Current graph state.

        Returns:
            Agent name to run for remediation.
        """
        suggestions = {
            "has_data": "DataIngestionAgent",
            "has_insights": "StatisticalAnalysisAgent",
            "data_quality": "DataProfilingAgent",
            "sufficient_depth": "StatisticalAnalysisAgent",
        }

        for check in failed_checks:
            if check in suggestions:
                return suggestions[check]

        # Default: try profiling again
        return "DataProfilingAgent"
