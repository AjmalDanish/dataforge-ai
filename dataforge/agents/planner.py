"""Planner Agent - Central decision maker for the analysis workflow."""

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


class PlannerAgent(Agent):
    """Central planning agent that determines execution flow.

    The Planner Agent runs after each agent and decides what to do next:
    - Determine which agent should run next
    - Skip irrelevant agents based on data characteristics
    - Decide when analysis is complete
    - Handle error recovery and re-planning

    Decision Logic:
    1. Initial state (empty steps_completed) → Start with Ingestion Agent
    2. After DataIngestionAgent → Validate, then Profiling Agent
    3. After DataProfilingAgent → Statistics (if numeric) or Visualization (if no numeric)
    4. After StatisticalAnalysisAgent → Visualization Agent
    5. After VisualizationAgent → Evaluator Agent
    6. After EvaluatorAgent → Reporting (if passed) or Re-plan (if failed)
    7. After ReportingAgent → Complete

    Uses `steps_completed` list to detect current stage.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        logger: StructuredLogger | None = None,
    ):
        """Initialize the Planner Agent.

        Args:
            llm_provider: LLM provider instance.
            logger: Structured logger instance.
        """
        super().__init__(llm_provider, logger)
        self.name = "PlannerAgent"

    async def execute(self, state: GraphState) -> AgentResult:
        """Decide next action based on current state and history.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with decision, message, and next agent suggestion.
        """
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