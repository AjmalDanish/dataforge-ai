"""BusinessObjectiveDetectionAgent — The Strategist.

This agent determines what business questions the dataset can answer.
It uses LLM as the primary method with deterministic domain-specific
question templates as fallback.

Role: "What questions should we ask?"
Phase: 3 — Data Understanding
"""

import asyncio
import os
import time
from typing import Any

import pandas as pd

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMConfig, LLMMessage, LLMProviderFactory
from dataforge.core.models import (
    BusinessDomain,
    BusinessObjective,
    ExecutionPhase,
    FailurePolicy,
    RetryPolicy,
)
from dataforge.core.state import GraphState


class BusinessObjectiveDetectionAgent(Agent):
    """Detects business objectives and answerable questions from the dataset.

    This agent analyzes the cleaned data and business domain to identify
    strategic business questions that the dataset can help answer. It uses
    LLM as the primary method with deterministic domain-specific question
    templates as fallback.

    The agent produces:
    - business_objectives: List of structured BusinessObjective objects
    - answerable_questions: List of plain-text questions the data can answer

    Example outputs:
    - HR data: "Employee retention analysis", "Salary equity audit"
    - Retail data: "Product performance ranking", "Revenue trend analysis"
    - Finance data: "Transaction anomaly detection", "Portfolio risk assessment"
    """

    # Agent properties
    phase: ExecutionPhase = ExecutionPhase.DATA_UNDERSTANDING
    required_inputs: list[str] = [
        "cleaned_data",
        "business_domain",
    ]
    produced_outputs: list[str] = [
        "business_objectives",
        "answerable_questions",
    ]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=2)
    failure_policy: FailurePolicy = FailurePolicy.SKIP
    timeout_seconds: int = 30

    # Domain-specific question templates for fallback
    DOMAIN_QUESTION_TEMPLATES: dict[BusinessDomain, list[dict[str, Any]]] = {
        BusinessDomain.RETAIL: [
            {
                "objective": "Product performance ranking",
                "category": "performance",
                "priority": "high",
                "keywords": ["product", "sales", "ranking", "performance"],
            },
            {
                "objective": "Revenue trend analysis",
                "category": "growth",
                "priority": "high",
                "keywords": ["revenue", "trend", "growth", "sales"],
            },
            {
                "objective": "Customer segmentation analysis",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["customer", "segmentation", "grouping"],
            },
            {
                "objective": "Inventory optimization",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["inventory", "stock", "optimization"],
            },
            {
                "objective": "Seasonal demand forecasting",
                "category": "growth",
                "priority": "medium",
                "keywords": ["seasonal", "demand", "forecast"],
            },
        ],
        BusinessDomain.FINANCE: [
            {
                "objective": "Transaction anomaly detection",
                "category": "risk",
                "priority": "critical",
                "keywords": ["transaction", "anomaly", "fraud", "detection"],
            },
            {
                "objective": "Portfolio risk assessment",
                "category": "risk",
                "priority": "high",
                "keywords": ["portfolio", "risk", "assessment"],
            },
            {
                "objective": "Cash flow forecasting",
                "category": "growth",
                "priority": "high",
                "keywords": ["cash", "flow", "forecasting"],
            },
            {
                "objective": "Expense pattern analysis",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["expense", "pattern", "analysis"],
            },
            {
                "objective": "Revenue diversification analysis",
                "category": "growth",
                "priority": "medium",
                "keywords": ["revenue", "diversification", "sources"],
            },
        ],
        BusinessDomain.HR: [
            {
                "objective": "Employee retention analysis",
                "category": "performance",
                "priority": "high",
                "keywords": ["employee", "retention", "turnover", "churn"],
            },
            {
                "objective": "Salary equity audit",
                "category": "risk",
                "priority": "critical",
                "keywords": ["salary", "equity", "pay", "gap"],
            },
            {
                "objective": "Department performance comparison",
                "category": "performance",
                "priority": "medium",
                "keywords": ["department", "performance", "comparison"],
            },
            {
                "objective": "Workforce diversity analysis",
                "category": "risk",
                "priority": "medium",
                "keywords": ["diversity", "workforce", "inclusion"],
            },
            {
                "objective": "Training effectiveness evaluation",
                "category": "efficiency",
                "priority": "low",
                "keywords": ["training", "effectiveness", "evaluation"],
            },
        ],
        BusinessDomain.MARKETING: [
            {
                "objective": "Campaign performance analysis",
                "category": "performance",
                "priority": "high",
                "keywords": ["campaign", "performance", "roi", "conversion"],
            },
            {
                "objective": "Customer lifetime value analysis",
                "category": "growth",
                "priority": "high",
                "keywords": ["customer", "lifetime", "value", "clv"],
            },
            {
                "objective": "Channel effectiveness comparison",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["channel", "effectiveness", "comparison"],
            },
            {
                "objective": "Brand sentiment tracking",
                "category": "performance",
                "priority": "medium",
                "keywords": ["brand", "sentiment", "tracking"],
            },
            {
                "objective": "Lead conversion optimization",
                "category": "growth",
                "priority": "medium",
                "keywords": ["lead", "conversion", "optimization"],
            },
        ],
        BusinessDomain.SAAS: [
            {
                "objective": "Churn prediction and analysis",
                "category": "risk",
                "priority": "critical",
                "keywords": ["churn", "retention", "cancellation"],
            },
            {
                "objective": "Monthly recurring revenue analysis",
                "category": "growth",
                "priority": "high",
                "keywords": ["mrr", "recurring", "revenue"],
            },
            {
                "objective": "Feature adoption tracking",
                "category": "performance",
                "priority": "medium",
                "keywords": ["feature", "adoption", "usage"],
            },
            {
                "objective": "Customer onboarding optimization",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["onboarding", "activation", "time-to-value"],
            },
            {
                "objective": "Pricing strategy evaluation",
                "category": "growth",
                "priority": "medium",
                "keywords": ["pricing", "strategy", "evaluation"],
            },
        ],
        BusinessDomain.REAL_ESTATE: [
            {
                "objective": "Property valuation analysis",
                "category": "performance",
                "priority": "high",
                "keywords": ["property", "valuation", "price", "assessment"],
            },
            {
                "objective": "Market trend forecasting",
                "category": "growth",
                "priority": "high",
                "keywords": ["market", "trend", "forecasting"],
            },
            {
                "objective": "Rental yield optimization",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["rental", "yield", "optimization"],
            },
            {
                "objective": "Location attractiveness scoring",
                "category": "performance",
                "priority": "medium",
                "keywords": ["location", "attractiveness", "scoring"],
            },
            {
                "objective": "Investment portfolio analysis",
                "category": "risk",
                "priority": "medium",
                "keywords": ["investment", "portfolio", "risk"],
            },
        ],
        BusinessDomain.EDUCATION: [
            {
                "objective": "Student performance analysis",
                "category": "performance",
                "priority": "high",
                "keywords": ["student", "performance", "grades", "achievement"],
            },
            {
                "objective": "Course completion rate analysis",
                "category": "efficiency",
                "priority": "high",
                "keywords": ["completion", "rate", "dropout"],
            },
            {
                "objective": "Learning outcome assessment",
                "category": "performance",
                "priority": "medium",
                "keywords": ["learning", "outcome", "assessment"],
            },
            {
                "objective": "Resource allocation optimization",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["resource", "allocation", "optimization"],
            },
            {
                "objective": "Instructor effectiveness evaluation",
                "category": "performance",
                "priority": "medium",
                "keywords": ["instructor", "effectiveness", "evaluation"],
            },
        ],
        BusinessDomain.LOGISTICS: [
            {
                "objective": "Delivery time optimization",
                "category": "efficiency",
                "priority": "high",
                "keywords": ["delivery", "time", "optimization"],
            },
            {
                "objective": "Route efficiency analysis",
                "category": "efficiency",
                "priority": "high",
                "keywords": ["route", "efficiency", "optimization"],
            },
            {
                "objective": "Supply chain bottleneck identification",
                "category": "risk",
                "priority": "critical",
                "keywords": ["supply", "chain", "bottleneck"],
            },
            {
                "objective": "Inventory turnover analysis",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["inventory", "turnover", "analysis"],
            },
            {
                "objective": "Carrier performance comparison",
                "category": "performance",
                "priority": "medium",
                "keywords": ["carrier", "performance", "comparison"],
            },
        ],
        BusinessDomain.HEALTHCARE: [
            {
                "objective": "Patient outcome analysis",
                "category": "performance",
                "priority": "high",
                "keywords": ["patient", "outcome", "recovery"],
            },
            {
                "objective": "Treatment effectiveness evaluation",
                "category": "performance",
                "priority": "high",
                "keywords": ["treatment", "effectiveness", "evaluation"],
            },
            {
                "objective": "Resource utilization optimization",
                "category": "efficiency",
                "priority": "medium",
                "keywords": ["resource", "utilization", "optimization"],
            },
            {
                "objective": "Readmission rate analysis",
                "category": "risk",
                "priority": "high",
                "keywords": ["readmission", "rate", "analysis"],
            },
            {
                "objective": "Diagnostic accuracy assessment",
                "category": "performance",
                "priority": "medium",
                "keywords": ["diagnostic", "accuracy", "assessment"],
            },
        ],
        BusinessDomain.GENERAL: [
            {
                "objective": "Data quality assessment",
                "category": "performance",
                "priority": "high",
                "keywords": ["data", "quality", "assessment"],
            },
            {
                "objective": "Trend analysis",
                "category": "growth",
                "priority": "medium",
                "keywords": ["trend", "analysis", "patterns"],
            },
            {
                "objective": "Outlier detection",
                "category": "risk",
                "priority": "medium",
                "keywords": ["outlier", "anomaly", "detection"],
            },
            {
                "objective": "Correlation analysis",
                "category": "performance",
                "priority": "medium",
                "keywords": ["correlation", "relationship", "analysis"],
            },
            {
                "objective": "Summary statistics generation",
                "category": "performance",
                "priority": "low",
                "keywords": ["summary", "statistics", "descriptive"],
            },
        ],
    }

    def __init__(
        self,
        llm_provider: Any | None = None,
        logger: Any | None = None,
        retry_policy: Any | None = None,
        failure_policy: Any | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize the BusinessObjectiveDetectionAgent.

        Args:
            llm_provider: Optional LLM provider instance.
            logger: Optional logger instance.
            retry_policy: Retry policy configuration.
            failure_policy: Failure policy configuration.
            timeout_seconds: Execution timeout in seconds (default: 30).
        """
        super().__init__(
            llm_provider=llm_provider,
            logger=logger,
            retry_policy=retry_policy,
            failure_policy=failure_policy,
            timeout_seconds=timeout_seconds,
        )
        # An injected provider is usable even without an API key on the env
        self._llm_available = self._check_llm_availability() or self.llm is not None

    def _check_llm_availability(self) -> bool:
        """Check if LLM is available for use.

        Returns:
            True if LLM is available, False otherwise.
        """
        api_key = os.getenv("OPENAI_API_KEY", "")
        return bool(api_key and api_key.strip())

    async def execute(self, state: GraphState) -> AgentResult:
        """Execute objective detection logic.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with business objectives and answerable questions.
        """
        try:
            # Get required inputs from state
            cleaned_data = state.data.get("cleaned_data")
            business_domain = state.data.get("business_domain")

            # Validate inputs
            if cleaned_data is None or not isinstance(cleaned_data, pd.DataFrame):
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data not found or invalid",
                    quality_score=0.0,
                    execution_notes=["No cleaned data available for objective detection"],
                )

            if cleaned_data.empty:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data is empty",
                    quality_score=0.0,
                    execution_notes=["Empty dataset cannot be analyzed"],
                )

            if business_domain is None:
                business_domain = BusinessDomain.GENERAL

            # Ensure business_domain is a BusinessDomain enum
            if isinstance(business_domain, str):
                try:
                    business_domain = BusinessDomain(business_domain)
                except ValueError:
                    business_domain = BusinessDomain.GENERAL

            # Extract column information for context
            columns = cleaned_data.columns.tolist()
            column_types = {
                col: str(dtype) for col, dtype in cleaned_data.dtypes.items()
            }

            # Try LLM-based detection if available
            if self._llm_available and self.llm:
                try:
                    start_time = time.time()
                    business_objectives, answerable_questions = await self._detect_with_llm(
                        cleaned_data, business_domain, columns, column_types
                    )
                    duration = time.time() - start_time

                    if business_objectives:
                        return AgentResult(
                            decision=AgentDecision.CONTINUE,
                            message=f"Detected {len(business_objectives)} business objectives using LLM",
                            quality_score=0.9,
                            execution_duration=duration,
                            execution_notes=[
                                f"LLM-based detection completed in {duration:.2f}s",
                                f"Domain: {business_domain.value}",
                            ],
                            data_updates={
                                "business_objectives": business_objectives,
                                "answerable_questions": answerable_questions,
                            },
                            metrics={
                                "detection_method": "llm",
                                "objectives_count": len(business_objectives),
                                "questions_count": len(answerable_questions),
                            },
                        )
                except Exception as e:
                    if self.logger:
                        self.logger.warning(
                            f"LLM detection failed, using fallback: {str(e)}",
                            agent=self.name,
                        )

            # Fallback to domain-specific templates
            business_objectives, answerable_questions = self._detect_with_templates(
                cleaned_data, business_domain, columns, column_types
            )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Detected {len(business_objectives)} business objectives using templates",
                quality_score=0.7,
                execution_notes=[
                    f"Template-based detection completed",
                    f"Domain: {business_domain.value}",
                    "LLM not available or failed, using domain templates",
                ],
                data_updates={
                    "business_objectives": business_objectives,
                    "answerable_questions": answerable_questions,
                },
                metrics={
                    "detection_method": "templates",
                    "objectives_count": len(business_objectives),
                    "questions_count": len(answerable_questions),
                },
            )

        except Exception as e:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Objective detection failed: {str(e)}",
                quality_score=0.0,
                execution_notes=[f"Error: {str(e)}"],
            )

    async def _detect_with_llm(
        self,
        df: pd.DataFrame,
        domain: BusinessDomain,
        columns: list[str],
        column_types: dict[Any, str],
    ) -> tuple[list[BusinessObjective], list[str]]:
        """Detect objectives using LLM.

        Args:
            df: The cleaned DataFrame.
            domain: Detected business domain.
            columns: List of column names.
            column_types: Dictionary of column types.

        Returns:
            Tuple of (business_objectives, answerable_questions).
        """
        # Prepare context for LLM
        context = self._prepare_llm_context(df, domain, columns, column_types)

        # Create LLM prompt
        prompt = self._create_llm_prompt(domain, context)

        # Call LLM with timeout
        try:
            if self.llm is None:
                raise Exception("LLM provider not available")
            response = await asyncio.wait_for(
                self.llm.generate_with_retry(
                    messages=[
                        LLMMessage(
                            role="system",
                            content=(
                                "You are a business intelligence expert. "
                                "Analyze the dataset and identify strategic business "
                                "questions that can be answered. Return results in JSON format."
                            ),
                        ),
                        LLMMessage(role="user", content=prompt),
                    ],
                    max_retries=1,
                ),
                # Respect the configured overall timeout while leaving a buffer
                # for template fallback and result construction.
                timeout=max(min(self.timeout_seconds - 5.0, 20.0), 1.0),
            )

            # Parse LLM response
            return self._parse_llm_response(response.content)

        except asyncio.TimeoutError:
            raise Exception("LLM request timed out")
        except Exception as e:
            raise Exception(f"LLM request failed: {str(e)}")

    def _prepare_llm_context(
        self,
        df: pd.DataFrame,
        domain: BusinessDomain,
        columns: list[str],
        column_types: dict[Any, str],
    ) -> str:
        """Prepare context description for LLM.

        Args:
            df: The cleaned DataFrame.
            domain: Detected business domain.
            columns: List of column names.
            column_types: Dictionary of column types.

        Returns:
            Context description string.
        """
        context_parts = [
            f"Business Domain: {domain.value}",
            f"Dataset Shape: {df.shape[0]} rows, {df.shape[1]} columns",
            f"Columns: {', '.join(columns)}",
            "\nColumn Types:",
        ]

        for col, dtype in column_types.items():
            context_parts.append(f"  - {col}: {dtype}")

        # Add sample data for first few rows (avoid full DataFrame scan)
        sample_size = min(5, len(df))
        if sample_size > 0:
            context_parts.append(f"\nSample Data (first {sample_size} rows):")
            for idx, row in df.head(sample_size).iterrows():
                row_str = ", ".join([f"{k}={v}" for k, v in row.items() if pd.notna(v)])
                context_parts.append(f"  Row {idx}: {row_str[:200]}")  # Limit length

        return "\n".join(context_parts)

    def _create_llm_prompt(self, domain: BusinessDomain, context: str) -> str:
        """Create LLM prompt for objective detection.

        Args:
            domain: Detected business domain.
            context: Dataset context description.

        Returns:
            LLM prompt string.
        """
        return f"""Based on the following {domain.value} dataset, identify 3-5 strategic business questions that can be answered.

{context}

Return a JSON object with this structure:
{{
  "objectives": [
    {{
      "objective": "Business question or objective",
      "category": "performance|growth|efficiency|risk",
      "priority": "low|medium|high|critical",
      "keywords": ["keyword1", "keyword2"]
    }}
  ],
  "answerable_questions": [
    "What is the X trend over time?",
    "How does Y compare across Z?",
    "What are the top N items by metric M?"
  ]
}}

Focus on questions that:
1. Can be answered with the available data
2. Provide strategic business value
3. Are specific and actionable
4. Cover different aspects (performance, growth, efficiency, risk)
"""

    def _parse_llm_response(
        self,
        response: str,
    ) -> tuple[list[BusinessObjective], list[str]]:
        """Parse LLM response into structured objectives.

        Args:
            response: LLM response string.

        Returns:
            Tuple of (business_objectives, answerable_questions).

        Raises:
            ValueError: If the response is not valid JSON or contains no
                usable objectives, so the caller can fall back to templates
                with full dataset context.
        """
        import json
        import re

        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                response = json_match.group(0)

            data = json.loads(response)

            # Parse objectives
            business_objectives = []
            for obj_data in data.get("objectives", []):
                try:
                    business_objectives.append(
                        BusinessObjective(
                            objective=obj_data.get("objective", ""),
                            category=obj_data.get("category", "general"),
                            priority=obj_data.get("priority", "medium"),
                            confidence=0.9,  # High confidence for LLM-generated
                            keywords=obj_data.get("keywords", []),
                        )
                    )
                except Exception:
                    continue

            # Parse answerable questions, defending against schema drift.
            # LLMs do not reliably honor the JSON contract, so a non-list
            # payload must never leak into GraphState (state.set stores Any
            # unvalidated, and the downstream typed accessor is advisory only).
            raw_questions = data.get("answerable_questions", [])
            if not isinstance(raw_questions, list):
                raw_questions = []
            answerable_questions = [
                q for q in raw_questions if isinstance(q, str) and q.strip()
            ]

            # Nothing usable: let the caller fall back to templates with full
            # dataset context. Never silently label template output as LLM output.
            if not business_objectives:
                raise ValueError("LLM response contained no valid objectives")

            return business_objectives, answerable_questions

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse LLM response: {str(e)}")

    def _detect_with_templates(
        self,
        df: pd.DataFrame,
        domain: BusinessDomain,
        columns: list[str],
        column_types: dict[Any, str],
    ) -> tuple[list[BusinessObjective], list[str]]:
        """Detect objectives using domain-specific templates.

        Args:
            df: The cleaned DataFrame.
            domain: Detected business domain.
            columns: List of column names.
            column_types: Dictionary of column types.

        Returns:
            Tuple of (business_objectives, answerable_questions).
        """
        # Get domain-specific templates
        templates = self.DOMAIN_QUESTION_TEMPLATES.get(
            domain, self.DOMAIN_QUESTION_TEMPLATES[BusinessDomain.GENERAL]
        )

        # Filter templates based on available columns
        filtered_templates = []
        column_names_lower = [col.lower() for col in columns]

        for template in templates:
            # Check if any keywords match available columns
            keywords = template.get("keywords", [])
            has_match = any(
                any(keyword in col_name for col_name in column_names_lower)
                for keyword in keywords
            )

            if has_match or not keywords:
                filtered_templates.append(template)

        # If no matches, use all templates for the domain
        if not filtered_templates:
            filtered_templates = templates

        # Create BusinessObjective objects
        business_objectives = []
        answerable_questions = []

        for template in filtered_templates:
            business_objectives.append(
                BusinessObjective(
                    objective=template["objective"],
                    category=template.get("category", "general"),
                    priority=template.get("priority", "medium"),
                    confidence=0.7,  # Medium confidence for template-based
                    keywords=template.get("keywords", []),
                )
            )

        # Generate answerable questions from objectives
        answerable_questions = self._generate_answerable_questions(
            business_objectives, columns, domain
        )

        return business_objectives, answerable_questions

    def _generate_answerable_questions(
        self,
        objectives: list[BusinessObjective],
        columns: list[str],
        domain: BusinessDomain,
    ) -> list[str]:
        """Generate answerable questions from objectives and columns.

        Args:
            objectives: List of business objectives.
            columns: List of column names.
            domain: Detected business domain.

        Returns:
            List of answerable questions.
        """
        questions = []

        # Generate questions based on objectives and available columns
        for obj in objectives:
            questions.append(f"What is the {obj.objective.lower()}?")

            # Add domain-specific question variations
            if domain == BusinessDomain.RETAIL:
                questions.append("What are the top products by sales?")
                questions.append("How does revenue vary over time?")
            elif domain == BusinessDomain.FINANCE:
                questions.append("What are the trends in transaction amounts?")
                questions.append("How is risk distributed across the portfolio?")
            elif domain == BusinessDomain.HR:
                questions.append("What factors influence employee retention?")
                questions.append("How do salaries compare across departments?")
            elif domain == BusinessDomain.SAAS:
                questions.append("What are the key drivers of customer churn?")
                questions.append("How is MRR trending over time?")

        # Generate generic questions based on column types
        numeric_columns = [
            col for col in columns if any(
                keyword in col.lower() for keyword in
                ["amount", "price", "cost", "value", "count", "quantity", "score", "rate"]
            )
        ]

        if numeric_columns:
            questions.append(f"What are the trends in {', '.join(numeric_columns[:3])}?")

        # Remove duplicates while preserving order
        seen = set()
        unique_questions = []
        for q in questions:
            if q not in seen:
                seen.add(q)
                unique_questions.append(q)

        return unique_questions[:10]  # Limit to 10 questions