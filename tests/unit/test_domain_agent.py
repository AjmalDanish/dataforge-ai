"""Unit tests for BusinessDomainDetectionAgent."""

import pytest
import pandas as pd
from pathlib import Path

from dataforge.agents.domain import BusinessDomainDetectionAgent
from dataforge.core.models import (
    BusinessDomain,
    ExecutionPhase,
    SchemaInfo,
    ColumnProfile,
    DatasetProfile,
)
from dataforge.core.state import GraphState


@pytest.fixture
def agent():
    """Create a BusinessDomainDetectionAgent instance."""
    return BusinessDomainDetectionAgent()


@pytest.fixture
def retail_dataframe():
    """Create a retail dataset."""
    return pd.DataFrame({
        "product_id": [1, 2, 3, 4, 5],
        "product_name": ["Widget A", "Widget B", "Widget C", "Widget D", "Widget E"],
        "sku": ["SKU001", "SKU002", "SKU003", "SKU004", "SKU005"],
        "price": [19.99, 29.99, 39.99, 49.99, 59.99],
        "quantity": [10, 20, 30, 40, 50],
        "order_id": ["ORD001", "ORD002", "ORD003", "ORD004", "ORD005"],
        "customer_id": ["CUST001", "CUST002", "CUST003", "CUST004", "CUST005"],
        "discount": [0.1, 0.15, 0.2, 0.25, 0.3],
        "revenue": [179.91, 509.83, 959.76, 1499.85, 2096.65],
        "inventory": [100, 200, 300, 400, 500],
        "category": ["Electronics", "Electronics", "Home", "Home", "Office"],
        "brand": ["BrandA", "BrandA", "BrandB", "BrandB", "BrandC"],
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
        "deposit": [200.00, 300.00, 400.00, 500.00, 600.00],
        "withdrawal": [50.00, 100.00, 150.00, 200.00, 250.00],
        "investment": [1000.00, 2000.00, 3000.00, 4000.00, 5000.00],
        "portfolio_value": [5000.00, 10000.00, 15000.00, 20000.00, 25000.00],
    })


@pytest.fixture
def hr_dataframe():
    """Create an HR dataset."""
    return pd.DataFrame({
        "employee_id": ["EMP001", "EMP002", "EMP003", "EMP004", "EMP005"],
        "employee_name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"],
        "salary": [50000.00, 60000.00, 70000.00, 80000.00, 90000.00],
        "wage": [25.00, 30.00, 35.00, 40.00, 45.00],
        "department": ["Engineering", "Marketing", "Sales", "HR", "Finance"],
        "hire_date": pd.to_datetime(["2020-01-01", "2019-06-15", "2018-03-20", "2017-09-10", "2016-12-01"]),
        "termination_date": [None, None, None, None, None],
        "performance_score": [85, 90, 95, 88, 92],
        "review_date": pd.to_datetime(["2024-01-01", "2024-06-15", "2024-03-20", "2024-09-10", "2024-12-01"]),
        "promotion_date": [None, pd.to_datetime("2022-06-15"), pd.to_datetime("2021-03-20"), None, pd.to_datetime("2020-12-01")],
        "benefit_cost": [5000.00, 6000.00, 7000.00, 8000.00, 9000.00],
        "leave_balance": [10, 15, 20, 25, 30],
        "absence_days": [2, 3, 1, 4, 2],
        "attendance_rate": [0.95, 0.92, 0.98, 0.90, 0.96],
        "training_hours": [40, 50, 60, 45, 55],
        "skill_level": ["Senior", "Senior", "Lead", "Mid", "Lead"],
        "position": ["Engineer", "Manager", "Lead", "Specialist", "Director"],
        "title": ["Software Engineer", "Marketing Manager", "Sales Lead", "HR Specialist", "Finance Director"],
        "manager_id": ["MGR001", "MGR002", "MGR003", "MGR004", "MGR005"],
        "team": ["Team A", "Team B", "Team C", "Team D", "Team E"],
        "division": ["Tech", "Marketing", "Sales", "HR", "Finance"],
    })


@pytest.fixture
def healthcare_dataframe():
    """Create a healthcare dataset."""
    return pd.DataFrame({
        "patient_id": ["PAT001", "PAT002", "PAT003", "PAT004", "PAT005"],
        "patient_name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"],
        "diagnosis": ["Diabetes", "Hypertension", "Asthma", "Arthritis", "Depression"],
        "treatment": ["Insulin", "ACE inhibitors", "Inhalers", "NSAIDs", "Therapy"],
        "dosage": ["10mg", "5mg", "2 puffs", "200mg", "1 session"],
        "medication": ["Metformin", "Lisinopril", "Albuterol", "Ibuprofen", "Sertraline"],
        "symptom": ["Thirst", "Headache", "Wheezing", "Pain", "Fatigue"],
        "condition": ["Type 2", "High BP", "Chronic", "Osteo", "MDD"],
        "disease_code": ["E11", "I10", "J45", "M15", "F32"],
        "procedure_id": ["PROC001", "PROC002", "PROC003", "PROC004", "PROC005"],
        "provider_id": ["PROV001", "PROV002", "PROV003", "PROV004", "PROV005"],
        "physician": ["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown", "Dr. Davis"],
        "nurse": ["Nurse A", "Nurse B", "Nurse C", "Nurse D", "Nurse E"],
        "hospital": ["Hospital A", "Hospital B", "Hospital C", "Hospital D", "Hospital E"],
        "clinic": ["Clinic A", "Clinic B", "Clinic C", "Clinic D", "Clinic E"],
        "admission_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]),
        "discharge_date": pd.to_datetime(["2024-01-05", "2024-02-05", "2024-03-05", "2024-04-05", "2024-05-05"]),
        "vital_signs": ["Normal", "Elevated", "Low", "Normal", "Elevated"],
        "lab_result": ["High glucose", "High BP", "Low O2", "Inflammation", "Normal"],
        "prescription": ["Rx001", "Rx002", "Rx003", "Rx004", "Rx005"],
        "therapy_type": ["Insulin therapy", "Lifestyle", "Respiratory", "Physical", "CBT"],
        "recovery_status": ["Improving", "Stable", "Improving", "Stable", "Improving"],
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
        "ctr": [0.05, 0.05, 0.05, 0.05, 0.05],
        "cpa": [10.00, 20.00, 30.00, 40.00, 50.00],
        "cpc": [2.00, 2.00, 2.00, 2.00, 2.00],
        "cpm": [1.00, 1.00, 1.00, 1.00, 1.00],
        "roi": [5.0, 5.0, 5.0, 5.0, 5.0],
        "roas": [10.0, 10.0, 10.0, 10.0, 10.0],
        "channel": ["Email", "Social", "Search", "Display", "Video"],
        "segment": ["New", "Returning", "VIP", "New", "Returning"],
        "audience": ["Age 25-34", "Age 35-44", "Age 45-54", "Age 25-34", "Age 35-44"],
        "lead_id": ["LEAD001", "LEAD002", "LEAD003", "LEAD004", "LEAD005"],
        "prospect_id": ["PROS001", "PROS002", "PROS003", "PROS004", "PROS005"],
        "customer_id": ["CUST001", "CUST002", "CUST003", "CUST004", "CUST005"],
        "acquisition_cost": [50.00, 100.00, 150.00, 200.00, 250.00],
        "retention_rate": [0.8, 0.85, 0.9, 0.88, 0.92],
        "churn_rate": [0.2, 0.15, 0.1, 0.12, 0.08],
        "ad_spend": [500.00, 1000.00, 1500.00, 2000.00, 2500.00],
        "advertisement": ["Banner", "Video", "Text", "Image", "Carousel"],
        "promotion": ["Discount", "Bundle", "Free shipping", "BOGO", "Loyalty"],
        "brand_awareness": [0.6, 0.7, 0.8, 0.75, 0.85],
        "engagement_rate": [0.1, 0.12, 0.15, 0.13, 0.16],
    })


@pytest.fixture
def saas_dataframe():
    """Create a SaaS dataset."""
    return pd.DataFrame({
        "user_id": ["USR001", "USR002", "USR003", "USR004", "USR005"],
        "subscription_id": ["SUB001", "SUB002", "SUB003", "SUB004", "SUB005"],
        "churn": [False, False, True, False, False],
        "mrr": [1000.00, 2000.00, 3000.00, 4000.00, 5000.00],
        "arr": [12000.00, 24000.00, 36000.00, 48000.00, 60000.00],
        "dau": [100, 200, 300, 400, 500],
        "mau": [500, 1000, 1500, 2000, 2500],
        "arpu": [2.00, 2.00, 2.00, 2.00, 2.00],
        "ltv": [240.00, 480.00, 720.00, 960.00, 1200.00],
        "cac": [50.00, 100.00, 150.00, 200.00, 250.00],
        "trial": [True, False, False, True, False],
        "upgrade": [False, True, False, False, True],
        "downgrade": [False, False, True, False, False],
        "feature_usage": [0.8, 0.9, 0.7, 0.85, 0.95],
        "usage_hours": [10, 20, 30, 40, 50],
        "engagement_score": [80, 90, 70, 85, 95],
        "activation_rate": [0.8, 0.9, 0.7, 0.85, 0.95],
        "retention_rate": [0.9, 0.92, 0.88, 0.94, 0.96],
        "revenue": [1000.00, 2000.00, 3000.00, 4000.00, 5000.00],
        "plan": ["Basic", "Pro", "Enterprise", "Pro", "Enterprise"],
        "tier": ["Free", "Paid", "Premium", "Paid", "Premium"],
        "seat_count": [1, 5, 10, 5, 10],
        "license_type": ["Individual", "Team", "Enterprise", "Team", "Enterprise"],
        "renewal_date": pd.to_datetime(["2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01", "2024-06-01"]),
        "cancellation_date": [None, None, pd.to_datetime("2024-03-15"), None, None],
    })


@pytest.fixture
def real_estate_dataframe():
    """Create a real estate dataset."""
    return pd.DataFrame({
        "property_id": ["PROP001", "PROP002", "PROP003", "PROP004", "PROP005"],
        "listing_id": ["LST001", "LST002", "LST003", "LST004", "LST005"],
        "sqft": [1000, 1500, 2000, 2500, 3000],
        "bedrooms": [2, 3, 4, 5, 6],
        "bathrooms": [1, 2, 3, 4, 5],
        "price": [200000.00, 300000.00, 400000.00, 500000.00, 600000.00],
        "rent": [1500.00, 2000.00, 2500.00, 3000.00, 3500.00],
        "lease_term": [12, 12, 24, 24, 36],
        "tenant_id": ["TEN001", "TEN002", "TEN003", "TEN004", "TEN005"],
        "landlord_id": ["LND001", "LND002", "LND003", "LND004", "LND005"],
        "address": ["123 Main St", "456 Oak Ave", "789 Pine Rd", "321 Elm Blvd", "654 Maple Dr"],
        "location": ["Downtown", "Suburb", "Suburb", "Rural", "Downtown"],
        "neighborhood": ["Financial District", "Residential", "Residential", "Country", "Financial District"],
        "zip_code": ["10001", "10002", "10003", "10004", "10005"],
        "market": ["Buyer", "Seller", "Buyer", "Seller", "Buyer"],
        "appraisal_value": [210000.00, 310000.00, 410000.00, 510000.00, 610000.00],
        "mortgage_amount": [150000.00, 225000.00, 300000.00, 375000.00, 450000.00],
        "agent_id": ["AGT001", "AGT002", "AGT003", "AGT004", "AGT005"],
        "broker_id": ["BRK001", "BRK002", "BRK003", "BRK004", "BRK005"],
        "commission": [6000.00, 9000.00, 12000.00, 15000.00, 18000.00],
        "sale_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]),
        "purchase_date": pd.to_datetime(["2020-01-01", "2019-02-01", "2018-03-01", "2017-04-01", "2016-05-01"]),
        "investment_return": [0.1, 0.12, 0.15, 0.18, 0.2],
    })


@pytest.fixture
def education_dataframe():
    """Create an education dataset."""
    return pd.DataFrame({
        "student_id": ["STU001", "STU002", "STU003", "STU004", "STU005"],
        "student_name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"],
        "grade": ["A", "B", "A", "B", "A"],
        "gpa": [3.8, 3.2, 3.9, 3.5, 4.0],
        "enrollment_date": pd.to_datetime(["2020-08-15", "2019-08-15", "2018-08-15", "2017-08-15", "2016-08-15"]),
        "course_id": ["CRS001", "CRS002", "CRS003", "CRS004", "CRS005"],
        "semester": ["Fall 2024", "Spring 2024", "Fall 2023", "Spring 2023", "Fall 2022"],
        "term": ["Fall", "Spring", "Fall", "Spring", "Fall"],
        "class_id": ["CLS001", "CLS002", "CLS003", "CLS004", "CLS005"],
        "subject": ["Math", "Science", "English", "History", "Art"],
        "teacher_id": ["TCH001", "TCH002", "TCH003", "TCH004", "TCH005"],
        "instructor": ["Prof. Smith", "Prof. Johnson", "Prof. Williams", "Prof. Brown", "Prof. Davis"],
        "school": ["School A", "School B", "School C", "School D", "School E"],
        "university": ["University A", "University B", "University C", "University D", "University E"],
        "college": ["College A", "College B", "College C", "College D", "College E"],
        "degree": ["BS", "BA", "BS", "BA", "PhD"],
        "major": ["Computer Science", "Biology", "English", "History", "Art"],
        "credit_hours": [3, 4, 3, 4, 3],
        "attendance_rate": [0.95, 0.92, 0.98, 0.90, 0.96],
        "exam_score": [95, 85, 98, 88, 99],
        "assignment_score": [90, 80, 95, 85, 97],
        "graduation_date": [pd.to_datetime("2024-05-15"), None, None, None, None],
        "transcript_id": ["TRN001", "TRN002", "TRN003", "TRN004", "TRN005"],
        "curriculum": ["STEM", "Science", "Humanities", "Humanities", "Arts"],
    })


@pytest.fixture
def logistics_dataframe():
    """Create a logistics dataset."""
    return pd.DataFrame({
        "shipment_id": ["SHP001", "SHP002", "SHP003", "SHP004", "SHP005"],
        "warehouse_id": ["WH001", "WH002", "WH003", "WH004", "WH005"],
        "delivery_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]),
        "route_id": ["RT001", "RT002", "RT003", "RT004", "RT005"],
        "inventory_count": [100, 200, 300, 400, 500],
        "stock_level": [1000, 2000, 3000, 4000, 5000],
        "carrier_id": ["CAR001", "CAR002", "CAR003", "CAR004", "CAR005"],
        "tracking_number": ["TRK001", "TRK002", "TRK003", "TRK004", "TRK005"],
        "freight_cost": [50.00, 100.00, 150.00, 200.00, 250.00],
        "logistics_cost": [60.00, 110.00, 160.00, 210.00, 260.00],
        "supply_chain": ["Chain A", "Chain B", "Chain C", "Chain D", "Chain E"],
        "distribution_center": ["DC001", "DC002", "DC003", "DC004", "DC005"],
        "fulfillment_date": pd.to_datetime(["2024-01-05", "2024-02-05", "2024-03-05", "2024-04-05", "2024-05-05"]),
        "order_id": ["ORD001", "ORD002", "ORD003", "ORD004", "ORD005"],
        "pickup_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]),
        "destination": ["City A", "City B", "City C", "City D", "City E"],
        "origin": ["Warehouse A", "Warehouse B", "Warehouse C", "Warehouse D", "Warehouse E"],
        "transit_time": [5, 4, 6, 3, 5],
        "vehicle_id": ["VEH001", "VEH002", "VEH003", "VEH004", "VEH005"],
        "driver_id": ["DRV001", "DRV002", "DRV003", "DRV004", "DRV005"],
        "dispatch_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]),
        "weight": [10, 20, 30, 40, 50],
        "volume": [1, 2, 3, 4, 5],
        "distance": [100, 200, 300, 400, 500],
        "duration": [5, 4, 6, 3, 5],
        "quantity": [10, 20, 30, 40, 50],
    })


@pytest.fixture
def mixed_domain_dataframe():
    """Create a mixed domain dataset."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "value": [100, 200, 300, 400, 500],
        "date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]),
        "status": ["Active", "Inactive", "Active", "Inactive", "Active"],
    })


@pytest.fixture
def state(retail_dataframe):
    """Create a GraphState with retail data."""
    schema_info = SchemaInfo(
        columns={
            "product_id": {"type": "identifier", "semantic_type": "identifier"},
            "product_name": {"type": "text", "semantic_type": "text"},
            "price": {"type": "numeric", "semantic_type": "currency"},
            "quantity": {"type": "numeric", "semantic_type": "measure"},
            "discount": {"type": "numeric", "semantic_type": "percentage"},
        },
        primary_keys=["product_id"],
        foreign_keys={},
        semantic_types={
            "product_id": "identifier",
            "price": "currency",
            "discount": "percentage",
        },
    )
    
    column_profiles = {
        "product_id": ColumnProfile(
            name="product_id",
            dtype="int64",
            non_null_count=5,
            null_count=0,
            null_percentage=0.0,
            unique_count=5,
            cardinality="low",
        ),
        "price": ColumnProfile(
            name="price",
            dtype="float64",
            non_null_count=5,
            null_count=0,
            null_percentage=0.0,
            unique_count=5,
            cardinality="low",
        ),
    }
    
    dataset_profile = DatasetProfile(
        row_count=5,
        column_count=12,
        memory_usage_mb=0.1,
        numeric_columns=["price", "quantity", "discount", "revenue", "inventory"],
        text_columns=["product_name", "category", "brand"],
        datetime_columns=[],
        boolean_columns=[],
        categorical_columns=["category", "brand"],
        identifier_columns=["product_id", "order_id", "customer_id", "sku"],
        measure_columns=["price", "quantity", "discount", "revenue", "inventory"],
        dimension_columns=["product_name", "category", "brand"],
    )
    
    return GraphState(
        input_dataset_path="/test/data.csv",
        current_phase=ExecutionPhase.DATA_UNDERSTANDING,
        data={
            "cleaned_data": retail_dataframe,
            "schema_info": schema_info,
            "column_profiles": column_profiles,
            "dataset_profile": dataset_profile,
            "semantic_column_types": {
                "product_id": "identifier",
                "price": "currency",
                "discount": "percentage",
            },
            "measure_columns": ["price", "quantity", "discount", "revenue", "inventory"],
            "dimension_columns": ["product_name", "category", "brand"],
            "identifier_columns": ["product_id", "order_id", "customer_id", "sku"],
        },
    )


class TestBusinessDomainDetectionAgentInit:
    """Tests for BusinessDomainDetectionAgent initialization."""
    
    def test_agent_properties(self, agent):
        """Test agent has correct properties."""
        assert agent.phase == ExecutionPhase.DATA_UNDERSTANDING
        assert "cleaned_data" in agent.required_inputs
        assert "schema_info" in agent.required_inputs
        assert "business_domain" in agent.produced_outputs
        assert "business_domain_confidence" in agent.produced_outputs
    
    def test_agent_thresholds(self, agent):
        """Test agent has correct thresholds."""
        assert agent.MIN_CONFIDENCE_THRESHOLD == 0.3
        assert agent.HIGH_CONFIDENCE_THRESHOLD == 0.7
    
    def test_domain_keywords(self, agent):
        """Test domain keywords are defined."""
        assert BusinessDomain.RETAIL in agent.DOMAIN_KEYWORDS
        assert BusinessDomain.FINANCE in agent.DOMAIN_KEYWORDS
        assert BusinessDomain.HR in agent.DOMAIN_KEYWORDS
        assert BusinessDomain.HEALTHCARE in agent.DOMAIN_KEYWORDS
        assert BusinessDomain.MARKETING in agent.DOMAIN_KEYWORDS
        assert BusinessDomain.SAAS in agent.DOMAIN_KEYWORDS
        assert BusinessDomain.REAL_ESTATE in agent.DOMAIN_KEYWORDS
        assert BusinessDomain.EDUCATION in agent.DOMAIN_KEYWORDS
        assert BusinessDomain.LOGISTICS in agent.DOMAIN_KEYWORDS
    
    def test_domain_patterns(self, agent):
        """Test domain patterns are defined."""
        assert BusinessDomain.RETAIL in agent.DOMAIN_PATTERNS
        assert BusinessDomain.FINANCE in agent.DOMAIN_PATTERNS
        assert "identifiers" in agent.DOMAIN_PATTERNS[BusinessDomain.RETAIL]
        assert "measures" in agent.DOMAIN_PATTERNS[BusinessDomain.RETAIL]


class TestBusinessDomainDetectionAgentExecute:
    """Tests for BusinessDomainDetectionAgent.execute method."""
    
    @pytest.mark.asyncio
    async def test_execute_retail_domain(self, agent, retail_dataframe):
        """Test execution with retail dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=12,
            memory_usage_mb=0.1,
            numeric_columns=["price", "quantity", "discount", "revenue", "inventory"],
            text_columns=["product_name", "category", "brand"],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=["category", "brand"],
            identifier_columns=["product_id", "order_id", "customer_id", "sku"],
            measure_columns=["price", "quantity", "discount", "revenue", "inventory"],
            dimension_columns=["product_name", "category", "brand"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": retail_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"price": "currency", "discount": "percentage"},
                "measure_columns": ["price", "quantity", "discount", "revenue", "inventory"],
                "dimension_columns": ["product_name", "category", "brand"],
                "identifier_columns": ["product_id", "order_id", "customer_id", "sku"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        assert result.quality_score >= 0.0
        assert result.quality_score <= 1.0
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
            assert "business_domain_confidence" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_finance_domain(self, agent, finance_dataframe):
        """Test execution with finance dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=12,
            memory_usage_mb=0.1,
            numeric_columns=["balance", "interest_rate", "loan_amount", "credit_score"],
            text_columns=[],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=[],
            identifier_columns=["account_id", "transaction_id"],
            measure_columns=["balance", "interest_rate", "loan_amount", "credit_score"],
            dimension_columns=[],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": finance_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"balance": "currency", "interest_rate": "percentage"},
                "measure_columns": ["balance", "interest_rate", "loan_amount", "credit_score"],
                "dimension_columns": [],
                "identifier_columns": ["account_id", "transaction_id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_hr_domain(self, agent, hr_dataframe):
        """Test execution with HR dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=20,
            memory_usage_mb=0.1,
            numeric_columns=["salary", "wage", "performance_score", "benefit_cost"],
            text_columns=["employee_name", "department", "position", "title"],
            datetime_columns=["hire_date", "review_date", "promotion_date"],
            boolean_columns=[],
            categorical_columns=["department", "position", "title"],
            identifier_columns=["employee_id", "manager_id"],
            measure_columns=["salary", "wage", "performance_score", "benefit_cost"],
            dimension_columns=["employee_name", "department", "position", "title"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": hr_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"hire_date": "datetime", "review_date": "datetime"},
                "measure_columns": ["salary", "wage", "performance_score", "benefit_cost"],
                "dimension_columns": ["employee_name", "department", "position", "title"],
                "identifier_columns": ["employee_id", "manager_id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_healthcare_domain(self, agent, healthcare_dataframe):
        """Test execution with healthcare dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=20,
            memory_usage_mb=0.1,
            numeric_columns=[],
            text_columns=["patient_name", "diagnosis", "treatment", "medication"],
            datetime_columns=["admission_date", "discharge_date"],
            boolean_columns=[],
            categorical_columns=["diagnosis", "treatment", "medication"],
            identifier_columns=["patient_id", "procedure_id", "provider_id"],
            measure_columns=[],
            dimension_columns=["patient_name", "diagnosis", "treatment", "medication"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": healthcare_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"admission_date": "datetime", "discharge_date": "datetime"},
                "measure_columns": [],
                "dimension_columns": ["patient_name", "diagnosis", "treatment", "medication"],
                "identifier_columns": ["patient_id", "procedure_id", "provider_id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_marketing_domain(self, agent, marketing_dataframe):
        """Test execution with marketing dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=20,
            memory_usage_mb=0.1,
            numeric_columns=["impressions", "clicks", "conversions", "ctr", "cpa"],
            text_columns=["campaign_name", "channel", "segment"],
            datetime_columns=[],
            boolean_columns=["churn"],
            categorical_columns=["channel", "segment"],
            identifier_columns=["campaign_id", "lead_id", "prospect_id", "customer_id"],
            measure_columns=["impressions", "clicks", "conversions", "ctr", "cpa"],
            dimension_columns=["campaign_name", "channel", "segment"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": marketing_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"ctr": "percentage", "cpa": "currency"},
                "measure_columns": ["impressions", "clicks", "conversions", "ctr", "cpa"],
                "dimension_columns": ["campaign_name", "channel", "segment"],
                "identifier_columns": ["campaign_id", "lead_id", "prospect_id", "customer_id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_saas_domain(self, agent, saas_dataframe):
        """Test execution with SaaS dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=20,
            memory_usage_mb=0.1,
            numeric_columns=["mrr", "arr", "dau", "mau", "arpu"],
            text_columns=["plan", "tier", "license_type"],
            datetime_columns=["renewal_date", "cancellation_date"],
            boolean_columns=["churn", "trial", "upgrade", "downgrade"],
            categorical_columns=["plan", "tier", "license_type"],
            identifier_columns=["user_id", "subscription_id"],
            measure_columns=["mrr", "arr", "dau", "mau", "arpu"],
            dimension_columns=["plan", "tier", "license_type"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": saas_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"renewal_date": "datetime", "churn": "boolean"},
                "measure_columns": ["mrr", "arr", "dau", "mau", "arpu"],
                "dimension_columns": ["plan", "tier", "license_type"],
                "identifier_columns": ["user_id", "subscription_id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_real_estate_domain(self, agent, real_estate_dataframe):
        """Test execution with real estate dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=20,
            memory_usage_mb=0.1,
            numeric_columns=["sqft", "bedrooms", "bathrooms", "price", "rent"],
            text_columns=["address", "location", "neighborhood"],
            datetime_columns=["sale_date", "purchase_date"],
            boolean_columns=[],
            categorical_columns=["location", "neighborhood", "market"],
            identifier_columns=["property_id", "listing_id", "address"],
            measure_columns=["sqft", "bedrooms", "bathrooms", "price", "rent"],
            dimension_columns=["address", "location", "neighborhood"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": real_estate_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"price": "currency", "rent": "currency"},
                "measure_columns": ["sqft", "bedrooms", "bathrooms", "price", "rent"],
                "dimension_columns": ["address", "location", "neighborhood"],
                "identifier_columns": ["property_id", "listing_id", "address"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_education_domain(self, agent, education_dataframe):
        """Test execution with education dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=20,
            memory_usage_mb=0.1,
            numeric_columns=["gpa", "credit_hours", "exam_score", "assignment_score"],
            text_columns=["student_name", "subject", "major"],
            datetime_columns=["enrollment_date", "graduation_date"],
            boolean_columns=[],
            categorical_columns=["grade", "subject", "major"],
            identifier_columns=["student_id", "course_id", "class_id"],
            measure_columns=["gpa", "credit_hours", "exam_score", "assignment_score"],
            dimension_columns=["student_name", "subject", "major"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": education_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"enrollment_date": "datetime", "graduation_date": "datetime"},
                "measure_columns": ["gpa", "credit_hours", "exam_score", "assignment_score"],
                "dimension_columns": ["student_name", "subject", "major"],
                "identifier_columns": ["student_id", "course_id", "class_id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_logistics_domain(self, agent, logistics_dataframe):
        """Test execution with logistics dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=20,
            memory_usage_mb=0.1,
            numeric_columns=["weight", "volume", "distance", "duration", "quantity"],
            text_columns=["destination", "origin", "supply_chain"],
            datetime_columns=["delivery_date", "pickup_date", "dispatch_date"],
            boolean_columns=[],
            categorical_columns=["destination", "origin", "supply_chain"],
            identifier_columns=["shipment_id", "tracking_number"],
            measure_columns=["weight", "volume", "distance", "duration", "quantity"],
            dimension_columns=["destination", "origin", "supply_chain"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": logistics_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"delivery_date": "datetime", "pickup_date": "datetime"},
                "measure_columns": ["weight", "volume", "distance", "duration", "quantity"],
                "dimension_columns": ["destination", "origin", "supply_chain"],
                "identifier_columns": ["shipment_id", "tracking_number"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_mixed_domain(self, agent, mixed_domain_dataframe):
        """Test execution with mixed domain dataset."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=5,
            memory_usage_mb=0.1,
            numeric_columns=["value"],
            text_columns=["name", "status"],
            datetime_columns=["date"],
            boolean_columns=[],
            categorical_columns=["status"],
            identifier_columns=["id"],
            measure_columns=["value"],
            dimension_columns=["name", "status"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": mixed_domain_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"date": "datetime"},
                "measure_columns": ["value"],
                "dimension_columns": ["name", "status"],
                "identifier_columns": ["id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
        if result.decision.name == "CONTINUE":
            # Should fallback to GENERAL or select a domain with low confidence
            assert "business_domain" in result.data_updates
    
    @pytest.mark.asyncio
    async def test_execute_missing_cleaned_data(self, agent):
        """Test execution with missing cleaned data."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={},
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name == "ERROR"
        assert "not found or invalid" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_empty_dataframe(self, agent):
        """Test execution with empty dataframe."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=0,
            column_count=0,
            memory_usage_mb=0.0,
            numeric_columns=[],
            text_columns=[],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=[],
            identifier_columns=[],
            measure_columns=[],
            dimension_columns=[],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": pd.DataFrame(),
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {},
                "measure_columns": [],
                "dimension_columns": [],
                "identifier_columns": [],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name == "ERROR"
        assert "empty" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_populates_all_outputs(self, agent, retail_dataframe):
        """Test execution populates all required outputs."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=12,
            memory_usage_mb=0.1,
            numeric_columns=["price", "quantity", "discount", "revenue", "inventory"],
            text_columns=["product_name", "category", "brand"],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=["category", "brand"],
            identifier_columns=["product_id", "order_id", "customer_id", "sku"],
            measure_columns=["price", "quantity", "discount", "revenue", "inventory"],
            dimension_columns=["product_name", "category", "brand"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": retail_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"price": "currency", "discount": "percentage"},
                "measure_columns": ["price", "quantity", "discount", "revenue", "inventory"],
                "dimension_columns": ["product_name", "category", "brand"],
                "identifier_columns": ["product_id", "order_id", "customer_id", "sku"],
            },
        )
        
        result = await agent.execute(state)
        
        if result.decision.name == "CONTINUE":
            assert "business_domain" in result.data_updates
            assert "business_domain_confidence" in result.data_updates
            assert "business_domain_candidates" in result.data_updates
            assert "business_domain_evidence" in result.data_updates
            assert "business_domain_summary" in result.data_updates
            assert "domain_keywords_detected" in result.data_updates
            assert "domain_features_detected" in result.data_updates
            assert "domain_reasoning" in result.data_updates


class TestBusinessDomainDetectionColumnAnalysis:
    """Tests for column name analysis methods."""
    
    @pytest.mark.asyncio
    async def test_analyze_column_names_retail(self, agent, retail_dataframe):
        """Test column name analysis for retail dataset."""
        scores = agent._analyze_column_names(retail_dataframe)
        
        assert isinstance(scores, dict)
        assert all(isinstance(domain, BusinessDomain) for domain in scores.keys())
        assert all(isinstance(score, float) for score in scores.values())
        assert all(0.0 <= score <= 1.0 for score in scores.values())
        # Retail should have high score due to many matching keywords
        assert scores.get(BusinessDomain.RETAIL, 0.0) > 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_column_names_finance(self, agent, finance_dataframe):
        """Test column name analysis for finance dataset."""
        scores = agent._analyze_column_names(finance_dataframe)
        
        assert isinstance(scores, dict)
        # Finance should have high score due to many matching keywords
        assert scores.get(BusinessDomain.FINANCE, 0.0) > 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_column_names_empty(self, agent):
        """Test column name analysis with empty dataframe."""
        df = pd.DataFrame()
        scores = agent._analyze_column_names(df)
        
        assert isinstance(scores, dict)
        assert len(scores) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_column_names_no_keywords(self, agent):
        """Test column name analysis with no matching keywords."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
            "col3": [7, 8, 9],
        })
        scores = agent._analyze_column_names(df)
        
        assert isinstance(scores, dict)
        # All scores should be 0 or very low
        assert all(score == 0.0 for score in scores.values())


class TestBusinessDomainDetectionSemanticAnalysis:
    """Tests for semantic type analysis methods."""
    
    @pytest.mark.asyncio
    async def test_analyze_semantic_types_retail(self, agent):
        """Test semantic type analysis for retail dataset."""
        semantic_types = {
            "price": "currency",
            "discount": "percentage",
            "product_id": "identifier",
        }
        scores = agent._analyze_semantic_types(semantic_types)
        
        assert isinstance(scores, dict)
        assert all(isinstance(domain, BusinessDomain) for domain in scores.keys())
        assert all(isinstance(score, float) for score in scores.values())
        assert all(0.0 <= score <= 1.0 for score in scores.values())
    
    @pytest.mark.asyncio
    async def test_analyze_semantic_types_empty(self, agent):
        """Test semantic type analysis with empty dict."""
        semantic_types = {}
        scores = agent._analyze_semantic_types(semantic_types)
        
        assert isinstance(scores, dict)
        assert len(scores) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_semantic_types_no_matches(self, agent):
        """Test semantic type analysis with no matching types."""
        semantic_types = {
            "col1": "unknown",
            "col2": "other",
            "col3": "custom",
        }
        scores = agent._analyze_semantic_types(semantic_types)
        
        assert isinstance(scores, dict)
        # All scores should be 0 or very low
        assert all(score == 0.0 for score in scores.values())


class TestBusinessDomainDetectionPatternAnalysis:
    """Tests for value pattern analysis methods."""
    
    @pytest.mark.asyncio
    async def test_analyze_value_patterns_currency(self, agent):
        """Test value pattern analysis for currency values."""
        df = pd.DataFrame({
            "price": ["$19.99", "$29.99", "$39.99", "$49.99", "$59.99"],
            "cost": ["€100.00", "€200.00", "€300.00", "€400.00", "€500.00"],
        })
        scores = agent._analyze_value_patterns(df)
        
        assert isinstance(scores, dict)
        assert all(isinstance(domain, BusinessDomain) for domain in scores.keys())
        assert all(isinstance(score, float) for score in scores.values())
        assert all(0.0 <= score <= 1.0 for score in scores.values())
    
    @pytest.mark.asyncio
    async def test_analyze_value_patterns_percentage(self, agent):
        """Test value pattern analysis for percentage values."""
        df = pd.DataFrame({
            "discount": ["10%", "15%", "20%", "25%", "30%"],
            "growth": ["5.5%", "6.5%", "7.5%", "8.5%", "9.5%"],
        })
        scores = agent._analyze_value_patterns(df)
        
        assert isinstance(scores, dict)
        assert all(isinstance(score, float) for score in scores.values())
    
    @pytest.mark.asyncio
    async def test_analyze_value_patterns_empty(self, agent):
        """Test value pattern analysis with empty dataframe."""
        df = pd.DataFrame()
        scores = agent._analyze_value_patterns(df)
        
        assert isinstance(scores, dict)
        assert len(scores) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_value_patterns_all_null(self, agent):
        """Test value pattern analysis with all null values."""
        df = pd.DataFrame({
            "col1": [None, None, None, None, None],
            "col2": [None, None, None, None, None],
        })
        scores = agent._analyze_value_patterns(df)
        
        assert isinstance(scores, dict)
        assert len(scores) == 0


class TestBusinessDomainDetectionIdentifierAnalysis:
    """Tests for identifier analysis methods."""
    
    @pytest.mark.asyncio
    async def test_analyze_identifiers_retail(self, agent):
        """Test identifier analysis for retail dataset."""
        identifier_columns = ["product_id", "order_id", "customer_id", "sku"]
        scores = agent._analyze_identifiers(identifier_columns)
        
        assert isinstance(scores, dict)
        assert all(isinstance(domain, BusinessDomain) for domain in scores.keys())
        assert all(isinstance(score, float) for score in scores.values())
        assert all(0.0 <= score <= 1.0 for score in scores.values())
        # Retail should have high score due to matching identifier patterns
        assert scores.get(BusinessDomain.RETAIL, 0.0) > 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_identifiers_empty(self, agent):
        """Test identifier analysis with empty list."""
        identifier_columns = []
        scores = agent._analyze_identifiers(identifier_columns)
        
        assert isinstance(scores, dict)
        assert len(scores) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_identifiers_no_matches(self, agent):
        """Test identifier analysis with no matching patterns."""
        identifier_columns = ["col1", "col2", "col3"]
        scores = agent._analyze_identifiers(identifier_columns)
        
        assert isinstance(scores, dict)
        # All scores should be 0 or very low
        assert all(score == 0.0 for score in scores.values())


class TestBusinessDomainDetectionMeasureAnalysis:
    """Tests for measure analysis methods."""
    
    @pytest.mark.asyncio
    async def test_analyze_measures_retail(self, agent):
        """Test measure analysis for retail dataset."""
        measure_columns = ["price", "quantity", "discount", "revenue", "inventory"]
        scores = agent._analyze_measures(measure_columns)
        
        assert isinstance(scores, dict)
        assert all(isinstance(domain, BusinessDomain) for domain in scores.keys())
        assert all(isinstance(score, float) for score in scores.values())
        assert all(0.0 <= score <= 1.0 for score in scores.values())
        # Retail should have high score due to matching measure patterns
        assert scores.get(BusinessDomain.RETAIL, 0.0) > 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_measures_empty(self, agent):
        """Test measure analysis with empty list."""
        measure_columns = []
        scores = agent._analyze_measures(measure_columns)
        
        assert isinstance(scores, dict)
        assert len(scores) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_measures_no_matches(self, agent):
        """Test measure analysis with no matching patterns."""
        measure_columns = ["col1", "col2", "col3"]
        scores = agent._analyze_measures(measure_columns)
        
        assert isinstance(scores, dict)
        # All scores should be 0 or very low
        assert all(score == 0.0 for score in scores.values())


class TestBusinessDomainDetectionConfidence:
    """Tests for confidence calculation methods."""
    
    def test_calculate_domain_confidence_all_scores(self, agent):
        """Test confidence calculation with all scores."""
        confidence = agent._calculate_domain_confidence(
            keyword_score=1.0,
            semantic_score=1.0,
            pattern_score=1.0,
            identifier_score=1.0,
            measure_score=1.0,
        )
        
        assert confidence == 1.0
    
    def test_calculate_domain_confidence_no_scores(self, agent):
        """Test confidence calculation with no scores."""
        confidence = agent._calculate_domain_confidence(
            keyword_score=0.0,
            semantic_score=0.0,
            pattern_score=0.0,
            identifier_score=0.0,
            measure_score=0.0,
        )
        
        assert confidence == 0.0
    
    def test_calculate_domain_confidence_mixed_scores(self, agent):
        """Test confidence calculation with mixed scores."""
        confidence = agent._calculate_domain_confidence(
            keyword_score=0.5,
            semantic_score=0.5,
            pattern_score=0.5,
            identifier_score=0.5,
            measure_score=0.5,
        )
        
        assert 0.0 <= confidence <= 1.0
        # Weighted average: 0.5 * 0.4 + 0.5 * 0.2 + 0.5 * 0.2 + 0.5 * 0.1 + 0.5 * 0.1 = 0.5
        assert confidence == 0.5
    
    def test_calculate_domain_confidence_keyword_weight(self, agent):
        """Test confidence calculation with keyword weight."""
        confidence = agent._calculate_domain_confidence(
            keyword_score=1.0,
            semantic_score=0.0,
            pattern_score=0.0,
            identifier_score=0.0,
            measure_score=0.0,
        )
        
        # Keyword weight is 0.4
        assert confidence == 0.4
    
    def test_calculate_domain_confidence_clamped(self, agent):
        """Test confidence calculation is clamped to 0.0-1.0."""
        confidence_high = agent._calculate_domain_confidence(
            keyword_score=2.0,
            semantic_score=2.0,
            pattern_score=2.0,
            identifier_score=2.0,
            measure_score=2.0,
        )
        assert confidence_high == 1.0
        
        confidence_low = agent._calculate_domain_confidence(
            keyword_score=-1.0,
            semantic_score=-1.0,
            pattern_score=-1.0,
            identifier_score=-1.0,
            measure_score=-1.0,
        )
        assert confidence_low == 0.0


class TestBusinessDomainDetectionEvidence:
    """Tests for evidence generation methods."""
    
    @pytest.mark.asyncio
    async def test_generate_evidence_retail(self, agent, retail_dataframe):
        """Test evidence generation for retail dataset."""
        semantic_types = {
            "price": "currency",
            "discount": "percentage",
            "product_id": "identifier",
        }
        identifier_columns = ["product_id", "order_id", "customer_id", "sku"]
        measure_columns = ["price", "quantity", "discount", "revenue", "inventory"]
        
        evidence = agent._generate_evidence(
            retail_dataframe,
            semantic_types,
            identifier_columns,
            measure_columns,
            BusinessDomain.RETAIL,
        )
        
        assert isinstance(evidence, list)
        assert all(isinstance(item, str) for item in evidence)
        assert len(evidence) <= 10  # Limited to top 10
        # Should have evidence for retail keywords
        assert any("product" in item.lower() for item in evidence)
    
    @pytest.mark.asyncio
    async def test_generate_evidence_empty(self, agent):
        """Test evidence generation with empty data."""
        df = pd.DataFrame()
        semantic_types = {}
        identifier_columns = []
        measure_columns = []
        
        evidence = agent._generate_evidence(
            df,
            semantic_types,
            identifier_columns,
            measure_columns,
            BusinessDomain.GENERAL,
        )
        
        assert isinstance(evidence, list)
        assert len(evidence) == 0


class TestBusinessDomainDetectionKeywords:
    """Tests for keywords detection methods."""
    
    @pytest.mark.asyncio
    async def test_generate_keywords_detected_retail(self, agent, retail_dataframe):
        """Test keywords detected for retail dataset."""
        keywords_detected = agent._generate_keywords_detected(
            retail_dataframe,
            BusinessDomain.RETAIL,
        )
        
        assert isinstance(keywords_detected, dict)
        assert all(isinstance(domain, str) for domain in keywords_detected.keys())
        assert all(isinstance(keywords, list) for keywords in keywords_detected.values())
        # Retail should have detected keywords
        assert BusinessDomain.RETAIL.value in keywords_detected
        assert len(keywords_detected[BusinessDomain.RETAIL.value]) > 0
    
    @pytest.mark.asyncio
    async def test_generate_keywords_detected_empty(self, agent):
        """Test keywords detected with empty dataframe."""
        df = pd.DataFrame()
        keywords_detected = agent._generate_keywords_detected(df, BusinessDomain.GENERAL)
        
        assert isinstance(keywords_detected, dict)
        assert len(keywords_detected) == 0


class TestBusinessDomainDetectionFeatures:
    """Tests for features detection methods."""
    
    @pytest.mark.asyncio
    async def test_generate_features_detected(self, agent):
        """Test features detected generation."""
        semantic_types = {
            "price": "currency",
            "discount": "percentage",
            "product_id": "identifier",
        }
        identifier_columns = ["product_id", "order_id", "customer_id", "sku"]
        measure_columns = ["price", "quantity", "discount", "revenue", "inventory"]
        
        features_detected = agent._generate_features_detected(
            semantic_types,
            identifier_columns,
            measure_columns,
            BusinessDomain.RETAIL,
        )
        
        assert isinstance(features_detected, dict)
        assert all(isinstance(domain, str) for domain in features_detected.keys())
        assert all(isinstance(features, list) for features in features_detected.values())
        # Should have features for all domains
        assert len(features_detected) > 0
    
    @pytest.mark.asyncio
    async def test_generate_features_detected_empty(self, agent):
        """Test features detected with empty data."""
        semantic_types = {}
        identifier_columns = []
        measure_columns = []
        
        features_detected = agent._generate_features_detected(
            semantic_types,
            identifier_columns,
            measure_columns,
            BusinessDomain.GENERAL,
        )
        
        assert isinstance(features_detected, dict)
        assert len(features_detected) == 0


class TestBusinessDomainDetectionSummary:
    """Tests for summary generation methods."""
    
    @pytest.mark.asyncio
    async def test_generate_domain_summary_high_confidence(self, agent):
        """Test domain summary with high confidence."""
        evidence = ["Column 'product_id' contains keyword 'product'", "Column 'price' has semantic type 'currency'"]
        summary = agent._generate_domain_summary(
            BusinessDomain.RETAIL,
            0.8,
            evidence,
        )
        
        assert isinstance(summary, str)
        assert "Retail" in summary
        assert "high" in summary.lower()
        assert "80.0%" in summary
    
    @pytest.mark.asyncio
    async def test_generate_domain_summary_moderate_confidence(self, agent):
        """Test domain summary with moderate confidence."""
        evidence = ["Column 'id' identified as identifier"]
        summary = agent._generate_domain_summary(
            BusinessDomain.GENERAL,
            0.5,
            evidence,
        )
        
        assert isinstance(summary, str)
        assert "General" in summary
        assert "moderate" in summary.lower()
        assert "50.0%" in summary
    
    @pytest.mark.asyncio
    async def test_generate_domain_summary_low_confidence(self, agent):
        """Test domain summary with low confidence."""
        evidence = []
        summary = agent._generate_domain_summary(
            BusinessDomain.GENERAL,
            0.2,
            evidence,
        )
        
        assert isinstance(summary, str)
        assert "General" in summary
        assert "low" in summary.lower()
        assert "20.0%" in summary
    
    @pytest.mark.asyncio
    async def test_generate_domain_summary_no_evidence(self, agent):
        """Test domain summary with no evidence."""
        evidence = []
        summary = agent._generate_domain_summary(
            BusinessDomain.RETAIL,
            0.7,
            evidence,
        )
        
        assert isinstance(summary, str)
        assert "Retail" in summary


class TestBusinessDomainDetectionReasoning:
    """Tests for reasoning generation methods."""
    
    @pytest.mark.asyncio
    async def test_generate_domain_reasoning(self, agent):
        """Test domain reasoning generation."""
        candidates = {
            BusinessDomain.RETAIL: 0.8,
            BusinessDomain.FINANCE: 0.2,
            BusinessDomain.GENERAL: 0.0,
        }
        evidence = ["Column 'product_id' contains keyword 'product'", "Column 'price' has semantic type 'currency'"]
        
        reasoning = agent._generate_domain_reasoning(
            BusinessDomain.RETAIL,
            candidates,
            evidence,
        )
        
        assert isinstance(reasoning, str)
        assert "Retail" in reasoning
        assert "confidence" in reasoning.lower()
        assert "evidence" in reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_generate_domain_reasoning_no_evidence(self, agent):
        """Test domain reasoning with no evidence."""
        candidates = {
            BusinessDomain.GENERAL: 0.0,
        }
        evidence = []
        
        reasoning = agent._generate_domain_reasoning(
            BusinessDomain.GENERAL,
            candidates,
            evidence,
        )
        
        assert isinstance(reasoning, str)
        assert "General" in reasoning


class TestBusinessDomainDetectionEdgeCases:
    """Tests for edge cases."""
    
    @pytest.mark.asyncio
    async def test_all_null_dataframe(self, agent):
        """Test with all null values."""
        df = pd.DataFrame({
            "col1": [None, None, None, None, None],
            "col2": [None, None, None, None, None],
        })
        
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=2,
            memory_usage_mb=0.1,
            numeric_columns=[],
            text_columns=[],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=[],
            identifier_columns=[],
            measure_columns=[],
            dimension_columns=[],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": df,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {},
                "measure_columns": [],
                "dimension_columns": [],
                "identifier_columns": [],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
    
    @pytest.mark.asyncio
    async def test_all_numeric_dataframe(self, agent):
        """Test with all numeric values."""
        df = pd.DataFrame({
            "col1": [1, 2, 3, 4, 5],
            "col2": [10, 20, 30, 40, 50],
            "col3": [100, 200, 300, 400, 500],
        })
        
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=3,
            memory_usage_mb=0.1,
            numeric_columns=["col1", "col2", "col3"],
            text_columns=[],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=[],
            identifier_columns=[],
            measure_columns=["col1", "col2", "col3"],
            dimension_columns=[],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": df,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {},
                "measure_columns": ["col1", "col2", "col3"],
                "dimension_columns": [],
                "identifier_columns": [],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
    
    @pytest.mark.asyncio
    async def test_all_text_dataframe(self, agent):
        """Test with all text values."""
        df = pd.DataFrame({
            "col1": ["a", "b", "c", "d", "e"],
            "col2": ["f", "g", "h", "i", "j"],
            "col3": ["k", "l", "m", "n", "o"],
        })
        
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=3,
            memory_usage_mb=0.1,
            numeric_columns=[],
            text_columns=["col1", "col2", "col3"],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=["col1", "col2", "col3"],
            identifier_columns=[],
            measure_columns=[],
            dimension_columns=["col1", "col2", "col3"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": df,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {},
                "measure_columns": [],
                "dimension_columns": ["col1", "col2", "col3"],
                "identifier_columns": [],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
    
    @pytest.mark.asyncio
    async def test_large_dataset(self, agent):
        """Test with large dataset (10,000 rows)."""
        df = pd.DataFrame({
            "product_id": [f"PROD{i:05d}" for i in range(10000)],
            "price": [19.99 + i * 0.01 for i in range(10000)],
            "quantity": [10 + i % 100 for i in range(10000)],
            "category": ["Electronics", "Home", "Office"] * 3333 + ["Electronics"],
        })
        
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=10000,
            column_count=4,
            memory_usage_mb=1.0,
            numeric_columns=["price", "quantity"],
            text_columns=["category"],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=["category"],
            identifier_columns=["product_id"],
            measure_columns=["price", "quantity"],
            dimension_columns=["category"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": df,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"price": "currency"},
                "measure_columns": ["price", "quantity"],
                "dimension_columns": ["category"],
                "identifier_columns": ["product_id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
    
    @pytest.mark.asyncio
    async def test_minimal_dataset(self, agent):
        """Test with minimal dataset (10 rows)."""
        df = pd.DataFrame({
            "product_id": [f"PROD{i:05d}" for i in range(10)],
            "price": [1.99 + i * 0.01 for i in range(10)],
            "quantity": [10 + i % 100 for i in range(10)],
            "category": ["Electronics", "Home", "Office"] * 3 + ["Electronics"],
        })
        
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=10,
            column_count=4,
            memory_usage_mb=0.1,
            numeric_columns=["price", "quantity"],
            text_columns=["category"],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=["category"],
            identifier_columns=["product_id"],
            measure_columns=["price", "quantity"],
            dimension_columns=["category"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": df,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {"price": "currency"},
                "measure_columns": ["price", "quantity"],
                "dimension_columns": ["category"],
                "identifier_columns": ["product_id"],
            },
        )
        
        result = await agent.execute(state)
        
        assert result.decision.name in ["CONTINUE", "ERROR"]
    
    @pytest.mark.asyncio
    async def test_error_handling_during_execution(self, agent):
        """Test error handling during execution."""
        # Create a state that will cause an error
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": "not a dataframe",  # Invalid type
                "schema_info": None,
                "column_profiles": {},
                "dataset_profile": None,
                "semantic_column_types": {},
                "measure_columns": [],
                "dimension_columns": [],
                "identifier_columns": [],
            },
        )
        
        result = await agent.execute(state)
        
        # Should return ERROR for invalid cleaned data type
        assert result.decision.name == "ERROR"
        assert "not found or invalid" in result.message.lower()


class TestBusinessDomainDetectionIntegration:
    """Integration tests for BusinessDomainDetectionAgent."""
    
    @pytest.mark.asyncio
    async def test_full_domain_detection_workflow(self, agent, retail_dataframe):
        """Test full domain detection workflow."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=["product_id"],
            foreign_keys={},
            semantic_types={
                "product_id": "identifier",
                "price": "currency",
                "discount": "percentage",
            },
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=12,
            memory_usage_mb=0.1,
            numeric_columns=["price", "quantity", "discount", "revenue", "inventory"],
            text_columns=["product_name", "category", "brand"],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=["category", "brand"],
            identifier_columns=["product_id", "order_id", "customer_id", "sku"],
            measure_columns=["price", "quantity", "discount", "revenue", "inventory"],
            dimension_columns=["product_name", "category", "brand"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": retail_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {
                    "product_id": "identifier",
                    "price": "currency",
                    "discount": "percentage",
                },
                "measure_columns": ["price", "quantity", "discount", "revenue", "inventory"],
                "dimension_columns": ["product_name", "category", "brand"],
                "identifier_columns": ["product_id", "order_id", "customer_id", "sku"],
            },
        )
        
        result = await agent.execute(state)
        
        if result.decision.name == "CONTINUE":
            # Verify all outputs
            assert "business_domain" in result.data_updates
            assert "business_domain_confidence" in result.data_updates
            assert "business_domain_candidates" in result.data_updates
            assert "business_domain_evidence" in result.data_updates
            assert "business_domain_summary" in result.data_updates
            assert "domain_keywords_detected" in result.data_updates
            assert "domain_features_detected" in result.data_updates
            assert "domain_reasoning" in result.data_updates
            
            # Verify types
            assert isinstance(result.data_updates["business_domain"], BusinessDomain)
            assert isinstance(result.data_updates["business_domain_confidence"], float)
            assert isinstance(result.data_updates["business_domain_candidates"], dict)
            assert isinstance(result.data_updates["business_domain_evidence"], list)
            assert isinstance(result.data_updates["business_domain_summary"], str)
            assert isinstance(result.data_updates["domain_keywords_detected"], dict)
            assert isinstance(result.data_updates["domain_features_detected"], dict)
            assert isinstance(result.data_updates["domain_reasoning"], str)
            
            # Verify confidence range
            assert 0.0 <= result.data_updates["business_domain_confidence"] <= 1.0
            
            # Verify evidence is not empty for retail
            assert len(result.data_updates["business_domain_evidence"]) > 0
    
    @pytest.mark.asyncio
    async def test_can_execute(self, agent, retail_dataframe):
        """Test can_execute method."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=12,
            memory_usage_mb=0.1,
            numeric_columns=["price", "quantity", "discount", "revenue", "inventory"],
            text_columns=["product_name", "category", "brand"],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=["category", "brand"],
            identifier_columns=["product_id", "order_id", "customer_id", "sku"],
            measure_columns=["price", "quantity", "discount", "revenue", "inventory"],
            dimension_columns=["product_name", "category", "brand"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={
                "cleaned_data": retail_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {},
                "measure_columns": [],
                "dimension_columns": [],
                "identifier_columns": [],
            },
        )
        
        can_execute = agent.can_execute(state)
        assert can_execute is True
    
    @pytest.mark.asyncio
    async def test_cannot_execute_wrong_phase(self, agent, retail_dataframe):
        """Test can_execute returns False for wrong phase."""
        schema_info = SchemaInfo(
            columns={},
            primary_keys=[],
            foreign_keys={},
            semantic_types={},
        )
        
        dataset_profile = DatasetProfile(
            row_count=5,
            column_count=12,
            memory_usage_mb=0.1,
            numeric_columns=["price", "quantity", "discount", "revenue", "inventory"],
            text_columns=["product_name", "category", "brand"],
            datetime_columns=[],
            boolean_columns=[],
            categorical_columns=["category", "brand"],
            identifier_columns=["product_id", "order_id", "customer_id", "sku"],
            measure_columns=["price", "quantity", "discount", "revenue", "inventory"],
            dimension_columns=["product_name", "category", "brand"],
        )
        
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_INTAKE,  # Wrong phase
            data={
                "cleaned_data": retail_dataframe,
                "schema_info": schema_info,
                "column_profiles": {},
                "dataset_profile": dataset_profile,
                "semantic_column_types": {},
                "measure_columns": [],
                "dimension_columns": [],
                "identifier_columns": [],
            },
        )
        
        can_execute = agent.can_execute(state)
        assert can_execute is False
    
    @pytest.mark.asyncio
    async def test_cannot_execute_missing_input(self, agent):
        """Test can_execute returns False for missing input."""
        state = GraphState(
            input_dataset_path="/test/data.csv",
            current_phase=ExecutionPhase.DATA_UNDERSTANDING,
            data={},
        )
        
        can_execute = agent.can_execute(state)
        assert can_execute is False