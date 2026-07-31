"""LangGraph workflow for DataForge AI."""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from dataforge.agents import (
    DataIngestionAgent,
    DataProfilingAgent,
    EvaluatorAgent,
    PlannerAgent,
    ReportingAgent,
    StatisticalAnalysisAgent,
    VisualizationAgent,
)
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState

__all__ = ["create_graph", "route_from_planner"]


def route_from_planner(state: GraphState) -> str:
    """Route to next agent based on planner's decision.

    Args:
        state: Current graph state.

    Returns:
        Next node name.
    """
    # Mapping from agent names to node names
    agent_to_node = {
        "DataIngestionAgent": "ingestion",
        "DataProfilingAgent": "profiling",
        "StatisticalAnalysisAgent": "statistics",
        "VisualizationAgent": "visualization",
        "EvaluatorAgent": "evaluator",
        "ReportingAgent": "reporting",
    }

    # Get the most recent agent result
    if state.agent_history:
        last_result = state.agent_history[-1]["result"]
        decision = last_result.get("decision")

        if decision == "complete":
            return END

        next_agent = last_result.get("next_agent_suggestion")
        if next_agent:
            return agent_to_node.get(next_agent, END)

    # Default fallback
    return END


def create_graph() -> CompiledStateGraph:
    """Create the analysis workflow graph.

    Returns:
        Compiled StateGraph (CompiledStateGraph with ainvoke/invoke/stream support).
    """
    workflow = StateGraph(GraphState)

    # Create agent instances
    logger = StructuredLogger("workflow", "./output")
    planner = PlannerAgent(logger=logger)
    evaluator = EvaluatorAgent(logger=logger)
    ingestion = DataIngestionAgent(logger=logger)
    profiling = DataProfilingAgent(logger=logger)
    statistics = StatisticalAnalysisAgent(logger=logger)
    visualization = VisualizationAgent(logger=logger)
    reporting = ReportingAgent(logger=logger)

    # Define node functions that call agents
    async def planner_node(state: GraphState) -> GraphState:
        """Planner node."""
        result, new_state = await planner.execute_with_logging(state)
        return new_state

    async def evaluator_node(state: GraphState) -> GraphState:
        """Evaluator node."""
        result, new_state = await evaluator.execute_with_logging(state)
        return new_state

    async def ingestion_node(state: GraphState) -> GraphState:
        """Ingestion node."""
        result, new_state = await ingestion.execute_with_logging(state)
        return new_state

    async def profiling_node(state: GraphState) -> GraphState:
        """Profiling node."""
        result, new_state = await profiling.execute_with_logging(state)
        return new_state

    async def statistics_node(state: GraphState) -> GraphState:
        """Statistics node."""
        result, new_state = await statistics.execute_with_logging(state)
        return new_state

    async def visualization_node(state: GraphState) -> GraphState:
        """Visualization node."""
        result, new_state = await visualization.execute_with_logging(state)
        return new_state

    async def reporting_node(state: GraphState) -> GraphState:
        """Reporting node."""
        result, new_state = await reporting.execute_with_logging(state)
        return new_state

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("ingestion", ingestion_node)
    workflow.add_node("profiling", profiling_node)
    workflow.add_node("statistics", statistics_node)
    workflow.add_node("visualization", visualization_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("reporting", reporting_node)

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
