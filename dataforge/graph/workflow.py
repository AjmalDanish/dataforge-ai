"""LangGraph workflow skeleton for DataForge AI."""

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from dataforge.core.llm import LLMConfig
from dataforge.core.state import GraphState

__all__ = ["create_graph", "route_from_planner"]


# Placeholder nodes - these will be implemented in later phases
async def planner_agent(state: GraphState) -> dict[str, Any]:
    """Planner agent placeholder.

    Args:
        state: Current graph state.

    Returns:
        State updates.
    """
    # Placeholder: will be implemented with actual logic
    return {"current_step": "planner"}


async def ingestion_agent(state: GraphState) -> dict[str, Any]:
    """Data ingestion agent placeholder.

    Args:
        state: Current graph state.

    Returns:
        State updates.
    """
    # Placeholder: will be implemented with actual logic
    return {"current_step": "ingestion"}


async def profiling_agent(state: GraphState) -> dict[str, Any]:
    """Data profiling agent placeholder.

    Args:
        state: Current graph state.

    Returns:
        State updates.
    """
    # Placeholder: will be implemented with actual logic
    return {"current_step": "profiling"}


async def statistics_agent(state: GraphState) -> dict[str, Any]:
    """Statistical analysis agent placeholder.

    Args:
        state: Current graph state.

    Returns:
        State updates.
    """
    # Placeholder: will be implemented with actual logic
    return {"current_step": "statistics"}


async def visualization_agent(state: GraphState) -> dict[str, Any]:
    """Visualization agent placeholder.

    Args:
        state: Current graph state.

    Returns:
        State updates.
    """
    # Placeholder: will be implemented with actual logic
    return {"current_step": "visualization"}


async def evaluator_agent(state: GraphState) -> dict[str, Any]:
    """Evaluator agent placeholder.

    Args:
        state: Current graph state.

    Returns:
        State updates.
    """
    # Placeholder: will be implemented with actual logic
    return {"current_step": "evaluator"}


async def reporting_agent(state: GraphState) -> dict[str, Any]:
    """Reporting agent placeholder.

    Args:
        state: Current graph state.

    Returns:
        State updates.
    """
    # Placeholder: will be implemented with actual logic
    return {"current_step": "reporting"}


def route_from_planner(state: GraphState) -> str:
    """Route to next agent based on planner's decision.

    Args:
        state: Current graph state.

    Returns:
        Next node name.
    """
    # Get the most recent agent result
    if state.agent_history:
        last_result = state.agent_history[-1]["result"]

        decision = last_result.get("decision")

        if decision == "complete":
            return END

        next_agent = last_result.get("next_agent_suggestion")

        if next_agent:
            # Convert "DataIngestionAgent" to "ingestion"
            return next_agent.lower().replace("agent", "").replace("data", "")

    # Default fallback
    return END


def create_graph() -> StateGraph:
    """Create the analysis workflow graph.

    Returns:
        Compiled StateGraph.
    """
    workflow = StateGraph(GraphState)

    # Add nodes (placeholders for now)
    workflow.add_node("planner", planner_agent)
    workflow.add_node("ingestion", ingestion_agent)
    workflow.add_node("profiling", profiling_agent)
    workflow.add_node("statistics", statistics_agent)
    workflow.add_node("visualization", visualization_agent)
    workflow.add_node("evaluator", evaluator_agent)
    workflow.add_node("reporting", reporting_agent)

    # Set entry point
    workflow.set_entry_point("planner")

    # Add conditional edges from planner
    workflow.add_conditional_edges(
        "planner",
        route_from_planner,
        {
            "ingestion": "ingestion",
            "profiling": "profiling",
            "statistics": "statistics",
            "visualization": "visualization",
            "evaluator": "evaluator",
            "reporting": "reporting",
            END: END,
        },
    )

    # All agents return to planner (except reporting which goes to END)
    workflow.add_edge("ingestion", "planner")
    workflow.add_edge("profiling", "planner")
    workflow.add_edge("statistics", "planner")
    workflow.add_edge("visualization", "planner")
    workflow.add_edge("evaluator", "planner")
    workflow.add_edge("reporting", END)

    return workflow.compile()
