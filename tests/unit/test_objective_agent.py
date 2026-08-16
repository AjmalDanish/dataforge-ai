"""Unit tests for BusinessObjectiveDetectionAgent."""

import json
import os
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from dataforge.agents.objective import BusinessObjectiveDetectionAgent
from dataforge.core.models import (
    BusinessDomain,
    BusinessObjective,
    ExecutionPhase,
    FailurePolicy,
    RetryPolicy,
)
from dataforge.core.llm import LLMResponse, LLMMessage
from dataforge.core.state import GraphState


@pytest.fixture
def agent():
    """Create a BusinessObjectiveDetectionAgent instance."""
    return BusinessObjectiveDetectionAgent()


@pytest.fixture
def retail_dataframe():
    """Create a retail dataset."""
    return pd.DataFrame({
        "product_id": [1, 2, 3, 4, 5],
        "product_name": ["Widget A", "Widget B", "Widget C", "Widget D", "Widget E"],
        "price": [19.99, 29.99, 39.99, 49.99, 59.99],
        "quantity": [10, 20, 30, 40, 50],
        "revenue": [179.91, 509.83, 959.76, 1499.85, 2096.65],
        "inventory": [100, 200, 300, 400, 500],
        "category": ["Electronics", "Electronics", "Home", "Home", "Office"],
    })


@pytest.fixture
def finance_dataframe():
    """Create a finance dataset."""
    return pd.DataFrame({
        "account_id": ["ACC001", "ACC002", "ACC003", "ACC004", "ACC005"],
        "balance": [1000.00, 2500.00, 5000.00, 7500.00, 10000.00],
        "transaction_id": ["TXN001", "TXN002", "TXN003", "TXN004", "TXN005"],
        "interest_rate": [0.05, 0.06, 0.07, 0.08, 0.09],
        "loan_amount": [5000.00, 10000.00, 15000.00, 20000.00, 25000.00],
        "credit_score": [700, 720, 740, 760, 780],
        "debit": [100.00, 200.00, 300.00, 400.00, 500.00],
        "payment": [150.00, 250.00, 350.00, 450.00, 550.00],
        "portfolio_value": [5000.00, 10000.00, 15000.00, 20000.00, 25000.00],
    })


@pytest.fixture
def hr_dataframe():
    """Create an HR dataset."""
    return pd.DataFrame({
        "employee_id": ["EMP001", "EMP002", "EMP003", "EMP004", "EMP005"],
        "employee_name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"],
        "salary": [50000.00, 60000.00, 70000.00, 80000.00, 90000.00],
        "department": ["Engineering", "Marketing", "Sales", "HR", "Finance"],
        "hire_date": pd.to_datetime(["2020-01-01", "2019-06-15", "2018-03-20", "2017-09-10", "2016-12-01"]),
        "performance_score": [85, 90, 95, 88, 92],
        "attendance_rate": [0.95, 0.92, 0.98, 0.90, 0.96],
        "training_hours": [40, 50, 60, 45, 55],
    })


@pytest.fixture
def marketing_dataframe():
    """Create a marketing dataset."""
    return pd.DataFrame({
        "campaign_id": ["CMP001", "CMP002", "CMP003", "CMP004", "CMP005"],
        "campaign_name": ["Summer Sale", "Back to School", "Holiday", "Spring", "Fall"],
        "impressions": [10000, 20000, 30000, 40000, 50000],
        "clicks": [500, 1000, 1500, 2000, 2500],
        "conversions": [50, 100, 150, 200, 250],
        "roi": [5.0, 5.0, 5.0, 5.0, 5.0],
        "channel": ["Email", "Social", "Search", "Display", "Video"],
        "customer_id": ["CUST001", "CUST002", "CUST003", "CUST004", "CUST005"],
        "acquisition_cost": [50.00, 100.00, 150.00, 200.00, 250.00],
        "churn_rate": [0.2, 0.15, 0.1, 0.12, 0.08],
        "ad_spend": [500.00, 1000.00, 1500.00, 2000.00, 2500.00],
    })


@pytest.fixture
def saas_dataframe():
    """Create a SaaS dataset."""
    return pd.DataFrame({
        "subscription_id": ["SUB001", "SUB002", "SUB003", "SUB004", "SUB005"],
        "customer_id": ["CUST001", "CUST002", "CUST003", "CUST004", "CUST005"],
        "mrr": [100.00, 200.00, 300.00, 400.00, 500.00],
        "arr": [1200.00, 2400.00, 3600.00, 4800.00, 6000.00],
        "churn": [False, False, True, False, False],
        "feature_usage": [10, 20, 30, 40, 50],
        "onboarding_time": [5, 3, 7, 4, 6],
        "pricing_plan": ["Basic", "Pro", "Enterprise", "Pro", "Basic"],
        "activation_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]),
    })


@pytest.fixture
def real_estate_dataframe():
    """Create a real estate dataset."""
    return pd.DataFrame({
        "property_id": ["PROP001", "PROP002", "PROP003", "PROP004", "PROP005"],
        "address": ["123 Main St", "456 Oak Ave", "789 Pine Rd", "321 Elm Blvd", "654 Maple Ln"],
        "price": [250000, 350000, 450000, 550000, 650000],
        "valuation": [260000, 360000, 440000, 560000, 640000],
        "rental_yield": [0.05, 0.06, 0.07, 0.08, 0.09],
        "location_score": [8.5, 7.5, 9.0, 8.0, 7.0],
        "investment_amount": [50000, 70000, 90000, 110000, 130000],
        "portfolio_risk": [0.3, 0.4, 0.2, 0.3, 0.4],
    })


@pytest.fixture
def education_dataframe():
    """Create an education dataset."""
    return pd.DataFrame({
        "student_id": ["STU001", "STU002", "STU003", "STU004", "STU005"],
        "student_name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"],
        "grade": [85, 90, 95, 88, 92],
        "completion_rate": [0.95, 0.92, 0.98, 0.90, 0.96],
        "learning_outcome": ["Excellent", "Excellent", "Excellent", "Good", "Excellent"],
        "resource_allocation": [1000, 1200, 1500, 1100, 1300],
        "instructor_id": ["INS001", "INS002", "INS003", "INS004", "INS005"],
        "instructor_effectiveness": [0.9, 0.85, 0.95, 0.88, 0.92],
    })


@pytest.fixture
def logistics_dataframe():
    """Create a logistics dataset."""
    return pd.DataFrame({
        "shipment_id": ["SHP001", "SHP002", "SHP003", "SHP004", "SHP005"],
        "delivery_time": [5, 3, 7, 4, 6],
        "route_efficiency": [0.85, 0.92, 0.78, 0.88, 0.90],
        "supply_chain_bottleneck": [False, False, True, False, False],
        "inventory_turnover": [10, 15, 8, 12, 14],
        "carrier_id": ["CAR001", "CAR002", "CAR003", "CAR004", "CAR005"],
        "carrier_performance": [0.9, 0.85, 0.78, 0.92, 0.88],
    })


@pytest.fixture
def healthcare_dataframe():
    """Create a healthcare dataset."""
    return pd.DataFrame({
        "patient_id": ["PAT001", "PAT002", "PAT003", "PAT004", "PAT005"],
        "patient_name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"],
        "diagnosis": ["Diabetes", "Hypertension", "Asthma", "Arthritis", "Depression"],
        "treatment": ["Insulin", "ACE inhibitors", "Inhalers", "NSAIDs", "Therapy"],
        "symptom": ["Thirst", "Headache", "Wheezing", "Pain", "Fatigue"],
        "vital_signs": ["Normal", "Elevated", "Low", "Normal", "Elevated"],
    })


@pytest.fixture
def generic_dataframe():
    """Create a generic dataset."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Item A", "Item B", "Item C", "Item D", "Item E"],
        "value": [10, 20, 30, 40, 50],
        "amount": [100.00, 200.00, 300.00, 400.00, 500.00],
        "count": [5, 10, 15, 20, 25],
    })


@pytest.fixture
def state(retail_dataframe):
    """Create a GraphState with retail data."""
    return GraphState(
        input_dataset_path="/test/data.csv",
        data={
            "cleaned_data": retail_dataframe,
            "business_domain": BusinessDomain.RETAIL,
        },
        current_phase=ExecutionPhase.DATA_UNDERSTANDING,
    )


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.generate_with_retry = AsyncMock()
    return provider


# ============================================================================
# TEST CLASS 1: Agent Initialization and Properties
# ============================================================================

class TestBusinessObjectiveDetectionAgentInit:
    """Tests for BusinessObjectiveDetectionAgent initialization."""

    def test_agent_properties(self, agent):
        """Test agent has correct properties."""
        assert agent.name == "BusinessObjectiveDetectionAgent"
        assert agent.phase == ExecutionPhase.DATA_UNDERSTANDING
        assert "cleaned_data" in agent.required_inputs
        assert "business_domain" in agent.required_inputs
        assert "business_objectives" in agent.produced_outputs
        assert "answerable_questions" in agent.produced_outputs

    def test_agent_retry_policy(self, agent):
        """Test agent has correct retry policy."""
        assert agent.retry_policy.max_retries == 2
        assert agent.retry_policy.backoff_strategy == "exponential"
        assert agent.retry_policy.initial_backoff == 1.0

    def test_agent_failure_policy(self, agent):
        """Test agent has correct failure policy."""
        assert agent.failure_policy == FailurePolicy.SKIP

    def test_agent_timeout(self, agent):
        """Test agent has correct timeout."""
        assert agent.timeout_seconds == 30

    def test_domain_templates_exist(self, agent):
        """Test domain templates exist for all domains."""
        for domain in BusinessDomain:
            assert domain in agent.DOMAIN_QUESTION_TEMPLATES
            templates = agent.DOMAIN_QUESTION_TEMPLATES[domain]
            assert isinstance(templates, list)
            assert len(templates) > 0
            for template in templates:
                assert "objective" in template
                assert "category" in template
                assert "priority" in template
                assert "keywords" in template

    def test_llm_availability_check(self, agent):
        """Test LLM availability check."""
        # Should return False when no API key is set
        result = agent._check_llm_availability()
        assert isinstance(result, bool)

    def test_llm_availability_with_key(self, monkeypatch):
        """Test LLM availability check with API key."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        agent = BusinessObjectiveDetectionAgent()
        assert agent._llm_available is True

    def test_llm_availability_without_key(self, monkeypatch):
        """Test LLM availability check without API key."""
        monkeypatch.setenv("OPENAI_API_KEY", "")
        agent = BusinessObjectiveDetectionAgent()
        assert agent._llm_available is False

    def test_llm_available_with_injected_provider_no_key(self, monkeypatch):
        """Test injected provider is usable without an API key on the env."""
        monkeypatch.setenv("OPENAI_API_KEY", "")
        provider = MagicMock()
        agent = BusinessObjectiveDetectionAgent(llm_provider=provider)
        assert agent.llm is provider
        assert agent._llm_available is True

    @pytest.mark.asyncio
    async def test_injected_provider_is_used(self, monkeypatch, retail_dataframe):
        """Test an injected provider is actually used for detection."""
        monkeypatch.setenv("OPENAI_API_KEY", "")
        provider = MagicMock()
        provider.generate_with_retry = AsyncMock(
            return_value=LLMResponse(
                content=json.dumps({
                    "objectives": [
                        {
                            "objective": "Injected provider objective",
                            "category": "performance",
                            "priority": "high",
                            "keywords": ["injected"],
                        }
                    ],
                    "answerable_questions": ["Injected question?"],
                }),
                model="gpt-4",
                tokens_used=100,
                finish_reason="stop",
                provider="openai",
            )
        )
        agent = BusinessObjectiveDetectionAgent(llm_provider=provider)

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        provider.generate_with_retry.assert_called_once()
        assert result.metrics["detection_method"] == "llm"
        assert result.quality_score == 0.9
        objectives = result.data_updates["business_objectives"]
        assert objectives[0].objective == "Injected provider objective"


# ============================================================================
# TEST CLASS 2: Agent Execution - Success Cases
# ============================================================================

class TestBusinessObjectiveDetectionAgentExecute:
    """Tests for BusinessObjectiveDetectionAgent.execute method."""

    @pytest.mark.asyncio
    async def test_execute_retail_domain(self, agent, retail_dataframe):
        """Test execution with retail domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert result.decision.value in ["continue", "error"]
        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        questions = result.data_updates["answerable_questions"]

        assert isinstance(objectives, list)
        assert isinstance(questions, list)
        assert len(objectives) > 0
        assert len(questions) > 0

        for obj in objectives:
            assert isinstance(obj, BusinessObjective)
            assert obj.objective
            assert obj.category
            assert obj.priority
            assert 0.0 <= obj.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_execute_finance_domain(self, agent, finance_dataframe):
        """Test execution with finance domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": finance_dataframe,
                "business_domain": BusinessDomain.FINANCE,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_hr_domain(self, agent, hr_dataframe):
        """Test execution with HR domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": hr_dataframe,
                "business_domain": BusinessDomain.HR,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_marketing_domain(self, agent, marketing_dataframe):
        """Test execution with marketing domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": marketing_dataframe,
                "business_domain": BusinessDomain.MARKETING,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_saas_domain(self, agent, saas_dataframe):
        """Test execution with SaaS domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": saas_dataframe,
                "business_domain": BusinessDomain.SAAS,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_real_estate_domain(self, agent, real_estate_dataframe):
        """Test execution with real estate domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": real_estate_dataframe,
                "business_domain": BusinessDomain.REAL_ESTATE,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_education_domain(self, agent, education_dataframe):
        """Test execution with education domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": education_dataframe,
                "business_domain": BusinessDomain.EDUCATION,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_logistics_domain(self, agent, logistics_dataframe):
        """Test execution with logistics domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": logistics_dataframe,
                "business_domain": BusinessDomain.LOGISTICS,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_healthcare_domain(self, agent, healthcare_dataframe):
        """Test execution with healthcare domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": healthcare_dataframe,
                "business_domain": BusinessDomain.HEALTHCARE,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_general_domain(self, agent, generic_dataframe):
        """Test execution with general domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": generic_dataframe,
                "business_domain": BusinessDomain.GENERAL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_execute_populates_all_outputs(self, agent, retail_dataframe):
        """Test execution populates all required outputs."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        # Check metrics are populated
        assert result.metrics is not None
        assert "detection_method" in result.metrics
        assert "objectives_count" in result.metrics
        assert "questions_count" in result.metrics


# ============================================================================
# TEST CLASS 3: Error Handling and Edge Cases
# ============================================================================

class TestBusinessObjectiveDetectionAgentErrorHandling:
    """Tests for BusinessObjectiveDetectionAgent error handling."""

    @pytest.mark.asyncio
    async def test_execute_missing_cleaned_data(self, agent):
        """Test execution with missing cleaned_data."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert result.decision.value == "error"
        assert "not found" in result.message.lower()
        assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_execute_empty_dataframe(self, agent):
        """Test execution with empty DataFrame."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": pd.DataFrame(),
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert result.decision.value == "error"
        assert "empty" in result.message.lower()
        assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_execute_missing_business_domain(self, agent, retail_dataframe):
        """Test execution with missing business_domain."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Should default to GENERAL domain
        assert "business_objectives" in result.data_updates

    @pytest.mark.asyncio
    async def test_execute_invalid_business_domain_string(self, agent, retail_dataframe):
        """Test execution with invalid business domain string."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": "INVALID_DOMAIN",
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Should default to GENERAL domain
        assert "business_objectives" in result.data_updates

    @pytest.mark.asyncio
    async def test_execute_dataframe_with_only_identifiers(self, agent):
        """Test execution with only identifier columns."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "uuid": ["a", "b", "c", "d", "e"],
            "key": ["x", "y", "z", "w", "v"],
        })

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": df,
                "business_domain": BusinessDomain.GENERAL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Should still produce objectives using GENERAL templates
        assert "business_objectives" in result.data_updates
        assert len(result.data_updates["business_objectives"]) > 0

    @pytest.mark.asyncio
    async def test_execute_dataframe_with_only_numeric_columns(self, agent):
        """Test execution with only numeric columns."""
        df = pd.DataFrame({
            "value1": [1, 2, 3, 4, 5],
            "value2": [10, 20, 30, 40, 50],
            "value3": [100, 200, 300, 400, 500],
        })

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": df,
                "business_domain": BusinessDomain.GENERAL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert len(result.data_updates["business_objectives"]) > 0

    @pytest.mark.asyncio
    async def test_execute_very_small_dataset(self, agent):
        """Test execution with very small dataset."""
        df = pd.DataFrame({
            "id": [1],
            "value": [10],
        })

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": df,
                "business_domain": BusinessDomain.GENERAL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert len(result.data_updates["business_objectives"]) > 0

    @pytest.mark.asyncio
    async def test_execute_large_column_dataset(self, agent):
        """Test execution with dataset having many columns."""
        columns = [f"col_{i}" for i in range(50)]
        df = pd.DataFrame({col: [i for i in range(5)] for col in columns})

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": df,
                "business_domain": BusinessDomain.GENERAL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert len(result.data_updates["business_objectives"]) > 0


# ============================================================================
# TEST CLASS 4: LLM Integration
# ============================================================================

class TestBusinessObjectiveDetectionAgentLLM:
    """Tests for BusinessObjectiveDetectionAgent LLM integration."""

    @pytest.mark.asyncio
    async def test_llm_success(self, agent, retail_dataframe, mock_llm_provider):
        """Test successful LLM-based detection."""
        # Mock LLM response
        mock_response = LLMResponse(
            content=json.dumps({
                "objectives": [
                    {
                        "objective": "Product performance analysis",
                        "category": "performance",
                        "priority": "high",
                        "keywords": ["product", "performance"]
                    }
                ],
                "answerable_questions": [
                    "What is the product performance trend?"
                ]
            }),
            model="gpt-4",
            tokens_used=100,
            finish_reason="stop",
            provider="openai"
        )
        mock_llm_provider.generate_with_retry.return_value = mock_response

        agent.llm = mock_llm_provider
        agent._llm_available = True

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

        # Check LLM was called
        mock_llm_provider.generate_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_unavailable(self, agent, retail_dataframe):
        """Test fallback when LLM is unavailable."""
        # Ensure LLM is not available
        agent._llm_available = False
        agent.llm = None

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        # Check metrics show template-based detection
        assert result.metrics["detection_method"] == "templates"

    @pytest.mark.asyncio
    async def test_llm_timeout(self, agent, retail_dataframe, mock_llm_provider):
        """Test fallback when LLM times out."""
        import asyncio

        # Mock timeout
        mock_llm_provider.generate_with_retry.side_effect = asyncio.TimeoutError()

        agent.llm = mock_llm_provider
        agent._llm_available = True

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Should fallback to templates
        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

    @pytest.mark.asyncio
    async def test_llm_malformed_json(self, agent, retail_dataframe, mock_llm_provider):
        """Test fallback when LLM returns malformed JSON."""
        # Mock malformed response
        mock_response = LLMResponse(
            content="This is not valid JSON",
            model="gpt-4",
            tokens_used=100,
            finish_reason="stop",
            provider="openai"
        )
        mock_llm_provider.generate_with_retry.return_value = mock_response

        agent.llm = mock_llm_provider
        agent._llm_available = True

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Should fallback to templates and be labeled as such
        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates
        assert result.metrics["detection_method"] == "templates"
        assert result.quality_score == 0.7

    @pytest.mark.asyncio
    async def test_llm_empty_response(self, agent, retail_dataframe, mock_llm_provider):
        """Test fallback when LLM returns empty response.

        Empty/malformed LLM output must NOT be labeled as LLM output. The
        fallback path through execute() uses full dataset context and is
        reported as template-based with quality 0.7.
        """
        # Mock empty response
        mock_response = LLMResponse(
            content=json.dumps({"objectives": [], "answerable_questions": []}),
            model="gpt-4",
            tokens_used=100,
            finish_reason="stop",
            provider="openai"
        )
        mock_llm_provider.generate_with_retry.return_value = mock_response

        agent.llm = mock_llm_provider
        agent._llm_available = True

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Should fallback to templates and be labeled as such
        assert "business_objectives" in result.data_updates
        assert len(result.data_updates["business_objectives"]) > 0
        assert result.metrics["detection_method"] == "templates"
        assert result.quality_score == 0.7
        for obj in result.data_updates["business_objectives"]:
            assert obj.confidence == 0.7

    @pytest.mark.asyncio
    async def test_llm_exception(self, agent, retail_dataframe, mock_llm_provider):
        """Test fallback when LLM raises exception."""
        # Mock exception
        mock_llm_provider.generate_with_retry.side_effect = Exception("LLM error")

        agent.llm = mock_llm_provider
        agent._llm_available = True

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Should fallback to templates
        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

    @pytest.mark.asyncio
    async def test_llm_failure_logs_warning(self, agent, retail_dataframe, mock_llm_provider):
        """Test LLM failure logs a warning when a logger is configured."""
        mock_llm_provider.generate_with_retry.side_effect = Exception("LLM error")
        agent.llm = mock_llm_provider
        agent._llm_available = True
        agent.logger = MagicMock()

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Warning should be logged, and fallback to templates should occur
        agent.logger.warning.assert_called_once()
        assert "business_objectives" in result.data_updates
        assert result.metrics["detection_method"] == "templates"

    @pytest.mark.asyncio
    async def test_execute_unexpected_exception_returns_error(self, agent, retail_dataframe, monkeypatch):
        """Test unexpected exceptions during execution return ERROR result."""
        def boom(*args, **kwargs):
            raise RuntimeError("Unexpected internal failure")

        monkeypatch.setattr(agent, "_detect_with_templates", boom)

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert result.decision.value == "error"
        assert result.quality_score == 0.0
        assert "Objective detection failed" in result.message


# ============================================================================
# TEST CLASS 5: Template-based Detection
# ============================================================================

class TestBusinessObjectiveDetectionAgentTemplates:
    """Tests for BusinessObjectiveDetectionAgent template-based detection."""

    @pytest.mark.asyncio
    async def test_deterministic_fallback(self, agent, retail_dataframe):
        """Test deterministic template-based fallback."""
        agent._llm_available = False
        agent.llm = None

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        # Check quality score for template-based detection
        assert result.quality_score == 0.7

    @pytest.mark.asyncio
    async def test_column_aware_template_filtering(self, agent):
        """Test template filtering based on available columns."""
        # Create DataFrame with only product-related columns
        df = pd.DataFrame({
            "product_id": [1, 2, 3],
            "product_name": ["A", "B", "C"],
            "price": [10, 20, 30],
        })

        agent._llm_available = False
        agent.llm = None

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": df,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        objectives = result.data_updates["business_objectives"]
        assert len(objectives) > 0

    @pytest.mark.asyncio
    async def test_template_confidence(self, agent, retail_dataframe):
        """Test confidence values for template-based detection."""
        agent._llm_available = False
        agent.llm = None

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        objectives = result.data_updates["business_objectives"]

        for obj in objectives:
            assert obj.confidence == 0.7  # Template-based confidence

    @pytest.mark.asyncio
    async def test_llm_confidence(self, agent, retail_dataframe, mock_llm_provider):
        """Test confidence values for LLM-based detection."""
        # Mock LLM response
        mock_response = LLMResponse(
            content=json.dumps({
                "objectives": [
                    {
                        "objective": "Test objective",
                        "category": "performance",
                        "priority": "high",
                        "keywords": ["test"]
                    }
                ],
                "answerable_questions": ["Test question?"]
            }),
            model="gpt-4",
            tokens_used=100,
            finish_reason="stop",
            provider="openai"
        )
        mock_llm_provider.generate_with_retry.return_value = mock_response

        agent.llm = mock_llm_provider
        agent._llm_available = True

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        objectives = result.data_updates["business_objectives"]

        for obj in objectives:
            assert obj.confidence == 0.9  # LLM-based confidence


# ============================================================================
# TEST CLASS 6: Answerable Questions Generation
# ============================================================================

class TestBusinessObjectiveDetectionAgentQuestions:
    """Tests for BusinessObjectiveDetectionAgent answerable questions generation."""

    @pytest.mark.asyncio
    async def test_numeric_column_questions(self, agent):
        """Test questions generated from numeric columns."""
        df = pd.DataFrame({
            "amount": [100, 200, 300],
            "price": [10, 20, 30],
            "value": [1, 2, 3],
        })

        agent._llm_available = False
        agent.llm = None

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": df,
                "business_domain": BusinessDomain.GENERAL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        questions = result.data_updates["answerable_questions"]
        assert len(questions) > 0

    @pytest.mark.asyncio
    async def test_question_deduplication(self, agent, retail_dataframe):
        """Test duplicate questions are removed."""
        agent._llm_available = False
        agent.llm = None

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        questions = result.data_updates["answerable_questions"]

        # Check no duplicates
        assert len(questions) == len(set(questions))

    @pytest.mark.asyncio
    async def test_maximum_question_limit(self, agent, retail_dataframe):
        """Test questions are limited to maximum."""
        agent._llm_available = False
        agent.llm = None

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        questions = result.data_updates["answerable_questions"]

        # Should not exceed 10 questions
        assert len(questions) <= 10


# ============================================================================
# TEST CLASS 7: Data Immutability
# ============================================================================

class TestBusinessObjectiveDetectionAgentImmutability:
    """Tests for BusinessObjectiveDetectionAgent data immutability."""

    @pytest.mark.asyncio
    async def test_no_mutation_of_cleaned_data(self, agent, retail_dataframe):
        """Test cleaned_data is not mutated."""
        original_df = retail_dataframe.copy()

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        await agent.execute(state)

        # Check DataFrame was not mutated
        pd.testing.assert_frame_equal(retail_dataframe, original_df)

    @pytest.mark.asyncio
    async def test_no_hidden_state_mutation(self, agent, retail_dataframe):
        """Test no hidden mutations to GraphState."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Check only expected keys were added
        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates

        # Check cleaned_data was not modified
        assert "cleaned_data" not in result.data_updates


# ============================================================================
# TEST CLASS 8: GraphState and AgentResult
# ============================================================================

class TestBusinessObjectiveDetectionAgentOutputs:
    """Tests for BusinessObjectiveDetectionAgent output correctness."""

    @pytest.mark.asyncio
    async def test_agentresult_correctness(self, agent, retail_dataframe):
        """Test AgentResult has correct structure."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        # Check AgentResult structure
        assert hasattr(result, "decision")
        assert hasattr(result, "message")
        assert hasattr(result, "data_updates")
        assert hasattr(result, "quality_score")
        assert hasattr(result, "execution_notes")
        assert hasattr(result, "metrics")

    @pytest.mark.asyncio
    async def test_execution_notes_populated(self, agent, retail_dataframe):
        """Test execution notes are populated."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert result.execution_notes is not None
        assert len(result.execution_notes) > 0

    @pytest.mark.asyncio
    async def test_execution_metrics_populated(self, agent, retail_dataframe):
        """Test execution metrics are populated."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert result.metrics is not None
        assert "detection_method" in result.metrics
        assert "objectives_count" in result.metrics
        assert "questions_count" in result.metrics


# ============================================================================
# TEST CLASS 9: Helper Methods
# ============================================================================

class TestBusinessObjectiveDetectionAgentHelpers:
    """Tests for BusinessObjectiveDetectionAgent helper methods."""

    def test_prepare_llm_context(self, agent, retail_dataframe):
        """Test LLM context preparation."""
        domain = BusinessDomain.RETAIL
        columns = retail_dataframe.columns.tolist()
        column_types = {col: str(dtype) for col, dtype in retail_dataframe.dtypes.items()}

        context = agent._prepare_llm_context(
            retail_dataframe, domain, columns, column_types
        )

        assert "Business Domain: retail" in context
        assert "Dataset Shape:" in context
        assert "Columns:" in context
        assert "Column Types:" in context

    def test_create_llm_prompt(self, agent):
        """Test LLM prompt creation."""
        domain = BusinessDomain.RETAIL
        context = "Test context"

        prompt = agent._create_llm_prompt(domain, context)

        assert "retail" in prompt
        assert context in prompt
        assert "objectives" in prompt
        assert "answerable_questions" in prompt

    def test_parse_llm_response_valid(self, agent):
        """Test parsing valid LLM response."""
        response = json.dumps({
            "objectives": [
                {
                    "objective": "Test objective",
                    "category": "performance",
                    "priority": "high",
                    "keywords": ["test"]
                }
            ],
            "answerable_questions": ["Test question?"]
        })

        objectives, questions = agent._parse_llm_response(response)

        assert len(objectives) == 1
        assert len(questions) == 1
        assert objectives[0].objective == "Test objective"

    def test_parse_llm_response_malformed(self, agent):
        """Test parsing malformed LLM response raises ValueError.

        The caller (execute/_detect_with_llm) is responsible for falling back
        to templates with full dataset context. Returning template objectives
        from the parser would let execute() mislabel template output as LLM
        output with an inflated quality score.
        """
        response = "Not valid JSON"

        with pytest.raises(ValueError):
            agent._parse_llm_response(response)

    def test_parse_llm_response_non_dict_json_raises(self, agent):
        """Test valid JSON that is not an object raises a wrapped ValueError.

        Covers the defensive path where parsing succeeds but the payload shape
        is unusable (e.g. a JSON array instead of an object with 'objectives').
        """
        response = json.dumps([1, 2, 3])

        with pytest.raises(ValueError, match="Failed to parse LLM response"):
            agent._parse_llm_response(response)

    def test_parse_llm_response_skips_invalid_objective(self, agent):
        """Test parsing skips invalid objectives that fail model validation."""
        response = json.dumps({
            "objectives": [
                {
                    "objective": "Valid objective",
                    "category": "performance",
                    "priority": "high",
                    "keywords": ["valid"]
                },
                {
                    "objective": "Invalid objective",
                    "category": "performance",
                    "priority": "high",
                    "keywords": "not-a-list"
                }
            ],
            "answerable_questions": ["Valid question?"]
        })

        objectives, questions = agent._parse_llm_response(response)

        # Invalid objective skipped, valid one retained
        assert len(objectives) == 1
        assert objectives[0].objective == "Valid objective"
        assert len(questions) == 1

    def test_parse_llm_response_non_list_questions_sanitized(self, agent):
        """Test non-list answerable_questions payload is sanitized to [].

        LLMs can silently violate the JSON contract (e.g. returning a bare
        string or null). state.set() stores Any unvalidated, so a non-list
        would leak into GraphState and break downstream list[str] consumers.
        """
        response = json.dumps({
            "objectives": [
                {
                    "objective": "Valid objective",
                    "category": "performance",
                    "priority": "high",
                    "keywords": ["valid"]
                }
            ],
            "answerable_questions": "What is the trend?"
        })

        objectives, questions = agent._parse_llm_response(response)

        assert len(objectives) == 1
        assert questions == []

    def test_parse_llm_response_mixed_questions_sanitized(self, agent):
        """Test non-string entries inside answerable_questions are dropped."""
        response = json.dumps({
            "objectives": [
                {
                    "objective": "Valid objective",
                    "category": "performance",
                    "priority": "high",
                    "keywords": ["valid"]
                }
            ],
            "answerable_questions": [
                "Keep me",
                "   ",
                {"nested": "object"},
                None,
                42,
                "Also keep me",
            ]
        })

        objectives, questions = agent._parse_llm_response(response)

        assert len(objectives) == 1
        assert questions == ["Keep me", "Also keep me"]

    @pytest.mark.asyncio
    async def test_detect_with_llm_raises_when_llm_none(self, agent, retail_dataframe):
        """Test _detect_with_llm raises when LLM provider is unavailable."""
        agent.llm = None
        domain = BusinessDomain.RETAIL
        columns = retail_dataframe.columns.tolist()
        column_types = {col: str(dtype) for col, dtype in retail_dataframe.dtypes.items()}

        with pytest.raises(Exception, match="LLM provider not available"):
            await agent._detect_with_llm(
                retail_dataframe, domain, columns, column_types
            )

    def test_detect_with_templates(self, agent, retail_dataframe):
        """Test template-based detection."""
        domain = BusinessDomain.RETAIL
        columns = retail_dataframe.columns.tolist()
        column_types = {col: str(dtype) for col, dtype in retail_dataframe.dtypes.items()}

        objectives, questions = agent._detect_with_templates(
            retail_dataframe, domain, columns, column_types
        )

        assert len(objectives) > 0
        assert len(questions) > 0

    def test_generate_answerable_questions(self, agent):
        """Test answerable questions generation."""
        objectives = [
            BusinessObjective(
                objective="Test objective",
                category="performance",
                priority="high",
                confidence=0.7,
                keywords=["test"]
            )
        ]

        questions = agent._generate_answerable_questions(
            objectives, ["amount", "price"], BusinessDomain.RETAIL
        )

        assert len(questions) > 0


# ============================================================================
# TEST CLASS 10: Integration Tests
# ============================================================================

class TestBusinessObjectiveDetectionAgentIntegration:
    """Integration tests for BusinessObjectiveDetectionAgent."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_llm(self, agent, retail_dataframe, mock_llm_provider):
        """Test full workflow with LLM."""
        # Mock LLM response
        mock_response = LLMResponse(
            content=json.dumps({
                "objectives": [
                    {
                        "objective": "Product performance analysis",
                        "category": "performance",
                        "priority": "high",
                        "keywords": ["product", "performance"]
                    }
                ],
                "answerable_questions": [
                    "What is the product performance trend?"
                ]
            }),
            model="gpt-4",
            tokens_used=100,
            finish_reason="stop",
            provider="openai"
        )
        mock_llm_provider.generate_with_retry.return_value = mock_response

        agent.llm = mock_llm_provider
        agent._llm_available = True

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert result.decision.value == "continue"
        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates
        assert result.quality_score == 0.9

    @pytest.mark.asyncio
    async def test_full_workflow_without_llm(self, agent, retail_dataframe):
        """Test full workflow without LLM."""
        agent._llm_available = False
        agent.llm = None

        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        result = await agent.execute(state)

        assert result.decision.value == "continue"
        assert "business_objectives" in result.data_updates
        assert "answerable_questions" in result.data_updates
        assert result.quality_score == 0.7

    @pytest.mark.asyncio
    async def test_can_execute(self, agent, retail_dataframe):
        """Test can_execute method."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        can_execute = agent.can_execute(state)
        assert can_execute is True

    @pytest.mark.asyncio
    async def test_cannot_execute_wrong_phase(self, agent, retail_dataframe):
        """Test can_execute returns False for wrong phase."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "cleaned_data": retail_dataframe,
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_INTAKE,
        )

        can_execute = agent.can_execute(state)
        assert can_execute is False

    @pytest.mark.asyncio
    async def test_cannot_execute_missing_input(self, agent):
        """Test can_execute returns False for missing input."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            data={
                "business_domain": BusinessDomain.RETAIL,
            },
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        )

        can_execute = agent.can_execute(state)
        assert can_execute is False