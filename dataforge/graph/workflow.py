"""LangGraph workflow for DataForge AI.

The graph is a hub-and-spoke DAG: every agent node returns to the planner,
and the planner's ``next_agent_suggestion`` picks the next node through a
conditional edge (see ``PlannerAgent`` for the routing rules).

Use :func:`run_workflow` to execute an analysis; it owns the recursion limit
and streams one event per agent step to an optional callback (the API uses
this for live WebSocket progress).
"""

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from dataforge.agents import (
    BusinessDomainDetectionAgent,
    BusinessObjectiveDetectionAgent,
    DataCleaningAgent,
    DataProfilingAgent,
    DataValidationAgent,
    EvaluatorAgent,
    FeatureEngineeringAgent,
    InsightGenerationAgent,
    KPIDiscoveryAgent,
    PlannerAgent,
    ReportingAgent,
    SchemaDetectionAgent,
    StatisticalAnalysisAgent,
    VisualizationAgent,
)
from dataforge.agents.base import Agent
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState

__all__ = [
    "AGENT_NODES",
    "RECURSION_LIMIT",
    "create_graph",
    "route_from_planner",
    "run_workflow",
]

# Agent class name → graph node name.
AGENT_NODES: dict[str, str] = {
    "DataValidationAgent": "validation",
    "DataCleaningAgent": "cleaning",
    "SchemaDetectionAgent": "schema",
    "BusinessDomainDetectionAgent": "domain",
    "BusinessObjectiveDetectionAgent": "objective",
    "DataProfilingAgent": "profiling",
    "FeatureEngineeringAgent": "features",
    "KPIDiscoveryAgent": "kpi",
    "StatisticalAnalysisAgent": "statistics",
    "InsightGenerationAgent": "insights",
    "VisualizationAgent": "visualization",
    "EvaluatorAgent": "evaluator",
    "ReportingAgent": "reporting",
}

# LangGraph counts every node visit (planner included). The planner's own
# ``max_global_steps`` budget (80) ends the run well before this limit.
RECURSION_LIMIT = 200

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


def route_from_planner(state: GraphState) -> str:
    """Route to the node the planner suggested (or END)."""
    if not state.agent_history:
        return END
    last = state.agent_history[-1]
    if isinstance(last, dict):
        result = last.get("result", {})
    else:
        result = (last.metadata or {}).get("result", {})
        if not result and last.decision:
            result = {"decision": last.decision}
    if result.get("decision") == "complete":
        return END
    next_agent = result.get("next_agent_suggestion")
    return AGENT_NODES.get(next_agent, END) if next_agent else END


def _agent_node(agent: Agent) -> Callable[[GraphState], Awaitable[GraphState]]:
    async def node(state: GraphState) -> GraphState:
        _, new_state = await agent.execute_with_logging(state)
        return new_state

    node.__name__ = f"{agent.name}_node"
    return node


def create_graph(
    llm_provider: LLMProvider | None = None,
    logger: StructuredLogger | None = None,
) -> CompiledStateGraph:
    """Create the analysis workflow graph.

    Args:
        llm_provider: Optional LLM provider for the LLM-assisted agents
            (domain tie-breaking, objectives, executive narrative). Without it
            every agent runs its deterministic rule-based path.
        logger: Optional structured logger shared by all agents.

    Returns:
        Compiled StateGraph (supports ``ainvoke`` / ``astream``).
    """
    logger = logger or StructuredLogger("workflow", "./output")
    agents: list[Agent] = [
        DataValidationAgent(logger=logger),
        DataCleaningAgent(logger=logger),
        SchemaDetectionAgent(logger=logger),
        BusinessDomainDetectionAgent(llm_provider=llm_provider, logger=logger),
        BusinessObjectiveDetectionAgent(llm_provider=llm_provider, logger=logger),
        DataProfilingAgent(logger=logger),
        FeatureEngineeringAgent(logger=logger),
        KPIDiscoveryAgent(logger=logger),
        StatisticalAnalysisAgent(logger=logger),
        InsightGenerationAgent(llm_provider=llm_provider, logger=logger),
        VisualizationAgent(logger=logger),
        EvaluatorAgent(logger=logger),
        ReportingAgent(logger=logger),
    ]
    phases = {agent.name: int(agent.phase) for agent in agents}
    planner = PlannerAgent(logger=logger)

    async def planner_node(state: GraphState) -> GraphState:
        result, new_state = await planner.execute_with_logging(state)
        # Track the phase of the agent about to run (drives UI progress).
        phase = phases.get(result.next_agent_suggestion or "")
        if phase is not None and phase != new_state.current_phase:
            new_state = new_state.update_phase(phase)
        return new_state

    workflow = StateGraph(GraphState)
    workflow.add_node("planner", planner_node)
    for agent in agents:
        workflow.add_node(AGENT_NODES[agent.name], _agent_node(agent))
        workflow.add_edge(AGENT_NODES[agent.name], "planner")

    workflow.set_entry_point("planner")
    workflow.add_conditional_edges(
        "planner",
        route_from_planner,
        {**{node: node for node in AGENT_NODES.values()}, END: END},
    )
    return workflow.compile()


def _as_state(value: Any) -> GraphState:
    return value if isinstance(value, GraphState) else GraphState.model_validate(value)


async def run_workflow(
    state: GraphState,
    llm_provider: LLMProvider | None = None,
    on_event: EventCallback | None = None,
    logger: StructuredLogger | None = None,
) -> GraphState:
    """Run a full analysis and return the final state.

    Args:
        state: Initial state (``input_dataset_path`` and ``output_dir`` set).
        llm_provider: Optional LLM provider (see :func:`create_graph`).
        on_event: Optional async callback, called once per agent step with
            ``{"type": "agent", "agent", "decision", "success", "message",
            "duration_s", "phase", "step"}``. Planner steps are not reported.
        logger: Optional structured logger.
    """
    logger = logger or StructuredLogger(state.execution_id, state.output_dir)
    graph = create_graph(llm_provider=llm_provider, logger=logger)
    final = state
    seen = len(state.agent_history)
    async for value in graph.astream(
        state, {"recursion_limit": RECURSION_LIMIT}, stream_mode="values"
    ):
        final = _as_state(value)
        new_entries = final.agent_history[seen:]
        seen = len(final.agent_history)
        if on_event is None:
            continue
        for entry in new_entries:
            if entry.agent_name == "PlannerAgent":
                continue
            result = (entry.metadata or {}).get("result", {})
            await on_event(
                {
                    "type": "agent",
                    "agent": entry.agent_name,
                    "decision": entry.decision,
                    "success": bool(result.get("success", True)),
                    "message": entry.message or result.get("error", ""),
                    "duration_s": round(entry.duration_seconds or 0.0, 3),
                    "phase": final.current_phase,
                    "step": final.global_step_count,
                }
            )
    return final.mark_complete()
