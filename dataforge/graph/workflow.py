"""LangGraph workflow for DataForge AI."""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from dataforge.agents import (
    BusinessDomainDetectionAgent,
    BusinessObjectiveDetectionAgent,
    DataCleaningAgent,
    DataIngestionAgent,
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
        "DataValidationAgent": "validation",
        "DataCleaningAgent": "cleaning",
        "SchemaDetectionAgent": "schema",
        "BusinessDomainDetectionAgent": "domain",
        "BusinessObjectiveDetectionAgent": "objective",
        "DataProfilingAgent": "profiling",
        "ProfilingAgent": "profiling",
        "FeatureEngineeringAgent": "features",
        "KPIDiscoveryAgent": "kpi",
        "InsightGenerationAgent": "insights",
        "StatisticalAnalysisAgent": "statistics",
        "VisualizationAgent": "visualization",
        "EvaluatorAgent": "evaluator",
        "ReportingAgent": "reporting",
    }

    # Get the most recent agent result (v1 dict entries or v2 objects)
    if state.agent_history:
        last = state.agent_history[-1]
        if isinstance(last, dict):
            last_result = last["result"]
        else:
            last_result = (last.metadata or {}).get("result", {})
            if not last_result and last.decision:
                last_result = {"decision": last.decision}
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
    validation = DataValidationAgent(logger=logger)
    cleaning = DataCleaningAgent(logger=logger)
    schema = SchemaDetectionAgent(logger=logger)
    domain = BusinessDomainDetectionAgent(logger=logger)
    objective = BusinessObjectiveDetectionAgent(logger=logger)
    profiling = DataProfilingAgent(logger=logger)
    features = FeatureEngineeringAgent(logger=logger)
    kpi = KPIDiscoveryAgent(logger=logger)
    insights = InsightGenerationAgent(logger=logger)
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

    async def validation_node(state: GraphState) -> GraphState:
        """Validation node (v2 entry)."""
        result, new_state = await validation.execute_with_logging(state)
        return new_state

    async def cleaning_node(state: GraphState) -> GraphState:
        """Cleaning node."""
        result, new_state = await cleaning.execute_with_logging(state)
        return new_state

    async def schema_node(state: GraphState) -> GraphState:
        """Schema detection node."""
        result, new_state = await schema.execute_with_logging(state)
        return new_state

    async def domain_node(state: GraphState) -> GraphState:
        """Business domain detection node."""
        result, new_state = await domain.execute_with_logging(state)
        return new_state

    async def objective_node(state: GraphState) -> GraphState:
        """Business objective detection node."""
        result, new_state = await objective.execute_with_logging(state)
        return new_state

    async def features_node(state: GraphState) -> GraphState:
        """Feature engineering node."""
        result, new_state = await features.execute_with_logging(state)
        return new_state

    async def kpi_node(state: GraphState) -> GraphState:
        """KPI discovery node."""
        result, new_state = await kpi.execute_with_logging(state)
        return new_state

    async def insights_node(state: GraphState) -> GraphState:
        """Insight generation node."""
        result, new_state = await insights.execute_with_logging(state)
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
    workflow.add_node("validation", validation_node)
    workflow.add_node("cleaning", cleaning_node)
    workflow.add_node("schema", schema_node)
    workflow.add_node("domain", domain_node)
    workflow.add_node("objective", objective_node)
    workflow.add_node("profiling", profiling_node)
    workflow.add_node("features", features_node)
    workflow.add_node("kpi", kpi_node)
    workflow.add_node("insights", insights_node)
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
            "validation": "validation",
            "cleaning": "cleaning",
            "schema": "schema",
            "domain": "domain",
            "objective": "objective",
            "profiling": "profiling",
            "features": "features",
            "kpi": "kpi",
            "insights": "insights",
            "statistics": "statistics",
            "visualization": "visualization",
            "evaluator": "evaluator",
            "reporting": "reporting",
            END: END,
        },
    )

    # All agents return to planner (except reporting which goes to END)
    workflow.add_edge("ingestion", "planner")
    workflow.add_edge("validation", "planner")
    workflow.add_edge("cleaning", "planner")
    workflow.add_edge("schema", "planner")
    workflow.add_edge("domain", "planner")
    workflow.add_edge("objective", "planner")
    workflow.add_edge("profiling", "planner")
    workflow.add_edge("features", "planner")
    workflow.add_edge("kpi", "planner")
    workflow.add_edge("insights", "planner")
    workflow.add_edge("statistics", "planner")
    workflow.add_edge("visualization", "planner")
    workflow.add_edge("evaluator", "planner")
    workflow.add_edge("reporting", END)

    return workflow.compile()
