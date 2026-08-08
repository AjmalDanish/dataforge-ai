"""Agent implementations."""

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.agents.cleaning import DataCleaningAgent
from dataforge.agents.domain import BusinessDomainDetectionAgent
from dataforge.agents.evaluator import EvaluatorAgent
from dataforge.agents.ingestion import DataIngestionAgent
from dataforge.agents.planner import PlannerAgent
from dataforge.agents.profiling import DataProfilingAgent
from dataforge.agents.reporting import ReportingAgent
from dataforge.agents.schema import SchemaDetectionAgent
from dataforge.agents.statistics import StatisticalAnalysisAgent
from dataforge.agents.validation import DataValidationAgent
from dataforge.agents.visualization import VisualizationAgent

__all__ = [
    "Agent",
    "AgentDecision",
    "AgentResult",
    "PlannerAgent",
    "EvaluatorAgent",
    "DataIngestionAgent",
    "DataValidationAgent",
    "DataCleaningAgent",
    "SchemaDetectionAgent",
    "BusinessDomainDetectionAgent",
    "DataProfilingAgent",
    "StatisticalAnalysisAgent",
    "VisualizationAgent",
    "ReportingAgent",
]
