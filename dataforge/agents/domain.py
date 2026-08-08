"""BusinessDomainDetectionAgent — The Industry Expert.

Determines the business domain represented by the dataset.
Uses deterministic heuristics with confidence scoring.
"""

import re
from collections import defaultdict
from datetime import datetime
from typing import Any

import pandas as pd

from dataforge.core.models import (
    BusinessDomain,
    ColumnProfile,
    DatasetProfile,
    ExecutionPhase,
    FailurePolicy,
    RetryPolicy,
)
from dataforge.core.state import GraphState

from .base import Agent, AgentDecision, AgentResult


class BusinessDomainDetectionAgent(Agent):
    """Detects the business domain of the dataset.

    Responsibilities:
    - Analyze column names for domain-specific keywords
    - Analyze semantic types for domain patterns
    - Analyze value patterns for domain characteristics
    - Analyze identifiers for domain hints
    - Analyze measures for domain hints
    - Calculate confidence scores for each domain
    - Generate evidence and reasoning for classification
    - Provide domain summary

    Phase: 3 — Data Understanding
    Inputs: cleaned_data, schema_info, column_profiles, dataset_profile,
            semantic_column_types, measure_columns, dimension_columns,
            identifier_columns
    Outputs: business_domain, business_domain_confidence,
             business_domain_candidates, business_domain_evidence,
             business_domain_summary, domain_keywords_detected,
             domain_features_detected, domain_reasoning
    """

    # Agent properties
    phase: ExecutionPhase = ExecutionPhase.DATA_UNDERSTANDING
    required_inputs: list[str] = [
        "cleaned_data",
        "schema_info",
        "column_profiles",
        "dataset_profile",
        "semantic_column_types",
        "measure_columns",
        "dimension_columns",
        "identifier_columns",
    ]
    produced_outputs: list[str] = [
        "business_domain",
        "business_domain_confidence",
        "business_domain_candidates",
        "business_domain_evidence",
        "business_domain_summary",
        "domain_keywords_detected",
        "domain_features_detected",
        "domain_reasoning",
    ]
    retry_policy: RetryPolicy = RetryPolicy(max_retries=2)
    failure_policy: FailurePolicy = FailurePolicy.SKIP
    timeout_seconds: int = 30

    # Domain keyword dictionaries
    DOMAIN_KEYWORDS = {
        BusinessDomain.RETAIL: [
            "product", "sku", "item", "price", "cost", "quantity", "order",
            "invoice", "transaction", "cart", "checkout", "customer", "discount",
            "revenue", "sales", "inventory", "stock", "shipment", "category",
            "brand", "merchant", "store", "shop", "purchase", "refund",
        ],
        BusinessDomain.FINANCE: [
            "account", "balance", "transaction", "interest", "loan", "credit",
            "debit", "payment", "deposit", "withdrawal", "investment", "portfolio",
            "asset", "liability", "equity", "dividend", "yield", "rate",
            "bank", "banking", "mortgage", "insurance", "premium", "claim",
        ],
        BusinessDomain.HR: [
            "employee", "staff", "worker", "salary", "wage", "department",
            "hire_date", "termination_date", "performance", "review", "promotion",
            "benefit", "leave", "absence", "attendance", "training", "skill",
            "position", "title", "manager", "supervisor", "team", "division",
        ],
        BusinessDomain.HEALTHCARE: [
            "patient", "diagnosis", "treatment", "dosage", "medication", "drug",
            "symptom", "condition", "disease", "icd", "procedure", "provider",
            "physician", "nurse", "hospital", "clinic", "admission", "discharge",
            "vital", "lab", "result", "prescription", "therapy", "recovery",
        ],
        BusinessDomain.MARKETING: [
            "campaign", "impression", "click", "conversion", "ctr", "cpa",
            "cpc", "cpm", "roi", "roas", "channel", "segment", "audience",
            "lead", "prospect", "customer", "acquisition", "retention", "churn",
            "ad", "advertisement", "promotion", "brand", "awareness", "engagement",
        ],
        BusinessDomain.SAAS: [
            "user", "subscription", "churn", "mrr", "arr", "dau", "mau",
            "arpu", "ltv", "cac", "trial", "upgrade", "downgrade", "feature",
            "usage", "engagement", "activation", "retention", "revenue",
            "plan", "tier", "seat", "license", "renewal", "cancellation",
        ],
        BusinessDomain.REAL_ESTATE: [
            "property", "listing", "sqft", "bedrooms", "bathrooms", "price",
            "rent", "lease", "tenant", "landlord", "address", "location",
            "neighborhood", "zip", "market", "appraisal", "value", "mortgage",
            "agent", "broker", "commission", "sale", "purchase", "investment",
        ],
        BusinessDomain.EDUCATION: [
            "student", "grade", "enrollment", "course", "gpa", "semester",
            "term", "class", "subject", "teacher", "instructor", "school",
            "university", "college", "degree", "major", "credit", "attendance",
            "exam", "assignment", "score", "graduation", "transcript", "curriculum",
        ],
        BusinessDomain.LOGISTICS: [
            "shipment", "warehouse", "delivery", "route", "inventory", "stock",
            "carrier", "tracking", "freight", "logistics", "supply", "chain",
            "distribution", "fulfillment", "order", "pickup", "destination",
            "origin", "transit", "carrier", "vehicle", "driver", "dispatch",
        ],
    }

    # Domain-specific patterns
    DOMAIN_PATTERNS = {
        BusinessDomain.RETAIL: {
            "identifiers": [r"^(product|sku|item)_id", r"^(order|invoice|transaction)_id", r"^customer_id"],
            "measures": [r"^(price|cost|quantity|revenue|sales|discount|profit|margin)"],
        },
        BusinessDomain.FINANCE: {
            "identifiers": [r"^account_id", r"^(transaction|payment|deposit|withdrawal)_id"],
            "measures": [r"^(balance|amount|interest|rate|principal|payment|fee|charge)"],
        },
        BusinessDomain.HR: {
            "identifiers": [r"^employee_id", r"^(staff|worker)_id"],
            "measures": [r"^(salary|wage|bonus|commission|hours|overtime|benefit_cost)"],
        },
        BusinessDomain.HEALTHCARE: {
            "identifiers": [r"^patient_id", r"^(diagnosis|treatment|procedure)_id"],
            "measures": [r"^(dosage|vital|lab_result|cost|charge|duration|length_of_stay)"],
        },
        BusinessDomain.MARKETING: {
            "identifiers": [r"^(campaign|ad|lead)_id", r"^customer_id"],
            "measures": [r"^(impression|click|conversion|ctr|cpa|cpc|cpm|roi|roas|spend|budget)"],
        },
        BusinessDomain.SAAS: {
            "identifiers": [r"^user_id", r"^(subscription|account)_id"],
            "measures": [r"^(mrr|arr|arpu|ltv|cac|dau|mau|churn|retention|revenue)"],
        },
        BusinessDomain.REAL_ESTATE: {
            "identifiers": [r"^(property|listing)_id", r"^address"],
            "measures": [r"^(price|rent|sqft|bedrooms|bathrooms|lot_size|year_built|value)"],
        },
        BusinessDomain.EDUCATION: {
            "identifiers": [r"^student_id", r"^(course|class)_id"],
            "measures": [r"^(grade|gpa|credit|score|attendance|hours|enrollment)"],
        },
        BusinessDomain.LOGISTICS: {
            "identifiers": [r"^(shipment|order|delivery)_id", r"^tracking"],
            "measures": [r"^(weight|volume|distance|duration|cost|freight|quantity)"],
        },
    }

    # Confidence thresholds
    MIN_CONFIDENCE_THRESHOLD: float = 0.3
    HIGH_CONFIDENCE_THRESHOLD: float = 0.7

    def __init__(
        self,
        llm_provider=None,
        logger=None,
        retry_policy: RetryPolicy | None = None,
        failure_policy: FailurePolicy | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize BusinessDomainDetectionAgent.

        Args:
            llm_provider: LLM provider instance (not used by this agent).
            logger: Structured logger instance.
            retry_policy: Retry policy override.
            failure_policy: Failure policy override.
            timeout_seconds: Timeout override in seconds.
        """
        super().__init__(llm_provider, logger, retry_policy, failure_policy, timeout_seconds)

    async def execute(self, state: GraphState) -> AgentResult:
        """Execute domain detection logic.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with domain information and confidence score.
        """
        try:
            # Get required inputs from state
            cleaned_data = state.data.get("cleaned_data")
            schema_info = state.data.get("schema_info")
            column_profiles = state.data.get("column_profiles", {})
            dataset_profile = state.data.get("dataset_profile")
            semantic_types = state.data.get("semantic_column_types", {})
            measure_columns = state.data.get("measure_columns", [])
            dimension_columns = state.data.get("dimension_columns", [])
            identifier_columns = state.data.get("identifier_columns", [])

            # Validate inputs
            if cleaned_data is None or not isinstance(cleaned_data, pd.DataFrame):
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data not found or invalid",
                    quality_score=0.0,
                    execution_notes=["No cleaned data available for domain detection"],
                )

            if cleaned_data.empty:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="Cleaned data is empty",
                    quality_score=0.0,
                    execution_notes=["Empty dataset cannot be analyzed"],
                )

            # Stage 1: Analyze column names
            keyword_scores = self._analyze_column_names(cleaned_data)

            # Stage 2: Analyze semantic types
            semantic_scores = self._analyze_semantic_types(semantic_types)

            # Stage 3: Analyze value patterns
            pattern_scores = self._analyze_value_patterns(cleaned_data)

            # Stage 4: Analyze identifiers
            identifier_scores = self._analyze_identifiers(identifier_columns)

            # Stage 5: Analyze measures
            measure_scores = self._analyze_measures(measure_columns)

            # Stage 6: Calculate overall confidence for each domain
            domain_confidences = {}
            for domain in BusinessDomain:
                keyword_score = keyword_scores.get(domain, 0.0)
                semantic_score = semantic_scores.get(domain, 0.0)
                pattern_score = pattern_scores.get(domain, 0.0)
                identifier_score = identifier_scores.get(domain, 0.0)
                measure_score = measure_scores.get(domain, 0.0)

                confidence = self._calculate_domain_confidence(
                    keyword_score,
                    semantic_score,
                    pattern_score,
                    identifier_score,
                    measure_score,
                )

                domain_confidences[domain] = confidence

            # Stage 7: Select domain with highest confidence
            selected_domain = max(domain_confidences.items(), key=lambda x: x[1])[0]
            selected_confidence = domain_confidences[selected_domain]

            # Fallback to GENERAL if confidence is too low
            if selected_confidence < self.MIN_CONFIDENCE_THRESHOLD:
                selected_domain = BusinessDomain.GENERAL
                selected_confidence = 0.0

            # Stage 8: Generate evidence
            evidence = self._generate_evidence(
                cleaned_data,
                semantic_types,
                identifier_columns,
                measure_columns,
                selected_domain,
            )

            # Stage 9: Generate keywords detected
            keywords_detected = self._generate_keywords_detected(
                cleaned_data,
                selected_domain,
            )

            # Stage 10: Generate features detected
            features_detected = self._generate_features_detected(
                semantic_types,
                identifier_columns,
                measure_columns,
                selected_domain,
            )

            # Stage 11: Generate summary and reasoning
            summary = self._generate_domain_summary(selected_domain, selected_confidence, evidence)
            reasoning = self._generate_domain_reasoning(selected_domain, domain_confidences, evidence)

            # Prepare candidates (exclude GENERAL if not selected)
            candidates = {
                domain.value: confidence
                for domain, confidence in domain_confidences.items()
                if domain != BusinessDomain.GENERAL or domain == selected_domain
            }

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Detected domain: {selected_domain.value} (confidence: {selected_confidence:.2f})",
                quality_score=selected_confidence,
                execution_notes=[reasoning],
                data_updates={
                    "business_domain": selected_domain,
                    "business_domain_confidence": selected_confidence,
                    "business_domain_candidates": candidates,
                    "business_domain_evidence": evidence,
                    "business_domain_summary": summary,
                    "domain_keywords_detected": keywords_detected,
                    "domain_features_detected": features_detected,
                    "domain_reasoning": reasoning,
                },
            )

        except Exception as e:
            # Fallback to GENERAL domain on error
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Error during domain detection, using GENERAL domain: {str(e)}",
                quality_score=0.0,
                execution_notes=[f"Error: {str(e)}"],
                data_updates={
                    "business_domain": BusinessDomain.GENERAL,
                    "business_domain_confidence": 0.0,
                    "business_domain_candidates": {},
                    "business_domain_evidence": [f"Error during detection: {str(e)}"],
                    "business_domain_summary": "Fallback to GENERAL domain due to error",
                    "domain_keywords_detected": {},
                    "domain_features_detected": {},
                    "domain_reasoning": "Fallback to GENERAL domain due to error",
                },
            )

    def _analyze_column_names(self, df: pd.DataFrame) -> dict[BusinessDomain, float]:
        """Analyze column names for domain keywords.

        Args:
            df: Input dataframe.

        Returns:
            Dictionary mapping domains to keyword match scores (0.0-1.0).
        """
        scores = defaultdict(float)
        total_columns = len(df.columns)

        if total_columns == 0:
            return dict(scores)

        for col in df.columns:
            col_lower = str(col).lower()

            for domain, keywords in self.DOMAIN_KEYWORDS.items():
                # Check if column name contains any domain keyword
                matches = [kw for kw in keywords if kw in col_lower]
                if matches:
                    # Score based on number of matches
                    scores[domain] += len(matches) * 0.1

        # Normalize scores to 0.0-1.0 range
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {domain: score / max_score for domain, score in scores.items()}

        return dict(scores)

    def _analyze_semantic_types(self, semantic_types: dict[str, str]) -> dict[BusinessDomain, float]:
        """Analyze semantic types for domain patterns.

        Args:
            semantic_types: Dictionary mapping column names to semantic types.

        Returns:
            Dictionary mapping domains to semantic type scores (0.0-1.0).
        """
        scores = defaultdict(float)

        # Domain-specific semantic type patterns
        domain_semantic_patterns = {
            BusinessDomain.RETAIL: ["currency", "percentage", "identifier"],
            BusinessDomain.FINANCE: ["currency", "percentage", "identifier"],
            BusinessDomain.HR: ["datetime", "identifier"],
            BusinessDomain.HEALTHCARE: ["datetime", "identifier", "text"],
            BusinessDomain.MARKETING: ["percentage", "identifier"],
            BusinessDomain.SAAS: ["datetime", "identifier", "percentage"],
            BusinessDomain.REAL_ESTATE: ["currency", "identifier"],
            BusinessDomain.EDUCATION: ["datetime", "identifier", "percentage"],
            BusinessDomain.LOGISTICS: ["datetime", "identifier", "currency"],
        }

        total_columns = len(semantic_types)
        if total_columns == 0:
            return dict(scores)

        for semantic_type in semantic_types.values():
            for domain, patterns in domain_semantic_patterns.items():
                if semantic_type in patterns:
                    scores[domain] += 0.2

        # Normalize scores to 0.0-1.0 range
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {domain: score / max_score for domain, score in scores.items()}

        return dict(scores)

    def _analyze_value_patterns(self, df: pd.DataFrame) -> dict[BusinessDomain, float]:
        """Analyze value patterns for domain characteristics.

        Args:
            df: Input dataframe.

        Returns:
            Dictionary mapping domains to pattern match scores (0.0-1.0).
        """
        scores = defaultdict(float)

        # Domain-specific value patterns
        domain_value_patterns = {
            BusinessDomain.RETAIL: {
                "currency": r"^[\$€£¥₹]\s*[\d,]+\.?\d*",
                "percentage": r"^[\d,]+\.?\d*\s*%$",
            },
            BusinessDomain.FINANCE: {
                "currency": r"^[\$€£¥₹]\s*[\d,]+\.?\d*",
                "percentage": r"^[\d,]+\.?\d*\s*%$",
            },
            BusinessDomain.MARKETING: {
                "percentage": r"^[\d,]+\.?\d*\s*%$",
            },
            BusinessDomain.SAAS: {
                "percentage": r"^[\d,]+\.?\d*\s*%$",
            },
        }

        # Sample up to 100 values per column
        sample_size = min(100, len(df))

        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            # Sample values
            sample_values = series.sample(min(sample_size, len(series)), random_state=42)

            for domain, patterns in domain_value_patterns.items():
                for pattern_name, pattern in patterns.items():
                    # Compile pattern
                    regex = re.compile(pattern)

                    # Count matches
                    matches = sum(1 for val in sample_values.astype(str) if regex.match(val))
                    match_ratio = matches / len(sample_values)

                    # Boost score if match ratio > 0.5
                    if match_ratio > 0.5:
                        scores[domain] += 0.1

        # Normalize scores to 0.0-1.0 range
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {domain: score / max_score for domain, score in scores.items()}

        return dict(scores)

    def _analyze_identifiers(self, identifier_columns: list[str]) -> dict[BusinessDomain, float]:
        """Analyze identifier columns for domain hints.

        Args:
            identifier_columns: List of identifier column names.

        Returns:
            Dictionary mapping domains to identifier pattern scores (0.0-1.0).
        """
        scores = defaultdict(float)

        if not identifier_columns:
            return dict(scores)

        for col in identifier_columns:
            col_lower = str(col).lower()

            for domain, patterns in self.DOMAIN_PATTERNS.items():
                # Check identifier patterns
                identifier_patterns = patterns.get("identifiers", [])
                for pattern in identifier_patterns:
                    if re.match(pattern, col_lower):
                        scores[domain] += 0.2

        # Normalize scores to 0.0-1.0 range
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {domain: score / max_score for domain, score in scores.items()}

        return dict(scores)

    def _analyze_measures(self, measure_columns: list[str]) -> dict[BusinessDomain, float]:
        """Analyze measure columns for domain hints.

        Args:
            measure_columns: List of measure column names.

        Returns:
            Dictionary mapping domains to measure pattern scores (0.0-1.0).
        """
        scores = defaultdict(float)

        if not measure_columns:
            return dict(scores)

        for col in measure_columns:
            col_lower = str(col).lower()

            for domain, patterns in self.DOMAIN_PATTERNS.items():
                # Check measure patterns
                measure_patterns = patterns.get("measures", [])
                for pattern in measure_patterns:
                    if re.match(pattern, col_lower):
                        scores[domain] += 0.2

        # Normalize scores to 0.0-1.0 range
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {domain: score / max_score for domain, score in scores.items()}

        return dict(scores)

    def _calculate_domain_confidence(
        self,
        keyword_score: float,
        semantic_score: float,
        pattern_score: float,
        identifier_score: float,
        measure_score: float,
    ) -> float:
        """Calculate overall domain confidence using weighted scoring.

        Args:
            keyword_score: Column name keyword match score (0.0-1.0).
            semantic_score: Semantic type match score (0.0-1.0).
            pattern_score: Value pattern match score (0.0-1.0).
            identifier_score: Identifier pattern match score (0.0-1.0).
            measure_score: Measure pattern match score (0.0-1.0).

        Returns:
            Overall confidence score (0.0-1.0).
        """
        weights = {
            "keyword": 0.40,
            "semantic": 0.20,
            "pattern": 0.20,
            "identifier": 0.10,
            "measure": 0.10,
        }

        confidence = (
            keyword_score * weights["keyword"] +
            semantic_score * weights["semantic"] +
            pattern_score * weights["pattern"] +
            identifier_score * weights["identifier"] +
            measure_score * weights["measure"]
        )

        return min(1.0, max(0.0, confidence))

    def _generate_evidence(
        self,
        df: pd.DataFrame,
        semantic_types: dict[str, str],
        identifier_columns: list[str],
        measure_columns: list[str],
        domain: BusinessDomain,
    ) -> list[str]:
        """Generate evidence for domain selection.

        Args:
            df: Input dataframe.
            semantic_types: Semantic types mapping.
            identifier_columns: Identifier column names.
            measure_columns: Measure column names.
            domain: Selected domain.

        Returns:
            List of evidence items.
        """
        evidence = []

        # Check for matching keywords
        domain_keywords = self.DOMAIN_KEYWORDS.get(domain, [])
        for col in df.columns:
            col_lower = str(col).lower()
            for keyword in domain_keywords:
                if keyword in col_lower:
                    evidence.append(f"Column '{col}' contains keyword '{keyword}'")
                    break

        # Check for matching semantic types
        for col, semantic_type in semantic_types.items():
            if semantic_type in ["currency", "percentage", "datetime"]:
                evidence.append(f"Column '{col}' has semantic type '{semantic_type}'")

        # Check for matching identifiers
        for col in identifier_columns:
            evidence.append(f"Column '{col}' identified as identifier")

        # Check for matching measures
        for col in measure_columns:
            evidence.append(f"Column '{col}' identified as measure")

        return evidence[:10]  # Limit to top 10 evidence items

    def _generate_keywords_detected(
        self,
        df: pd.DataFrame,
        domain: BusinessDomain,
    ) -> dict[str, list[str]]:
        """Generate keywords detected for each domain.

        Args:
            df: Input dataframe.
            domain: Selected domain.

        Returns:
            Dictionary mapping domain names to detected keywords.
        """
        keywords_detected = {}

        for candidate_domain in BusinessDomain:
            domain_keywords = self.DOMAIN_KEYWORDS.get(candidate_domain, [])
            detected = []

            for col in df.columns:
                col_lower = str(col).lower()
                for keyword in domain_keywords:
                    if keyword in col_lower:
                        detected.append(keyword)
                        break

            if detected:
                keywords_detected[candidate_domain.value] = list(set(detected))

        return keywords_detected

    def _generate_features_detected(
        self,
        semantic_types: dict[str, str],
        identifier_columns: list[str],
        measure_columns: list[str],
        domain: BusinessDomain,
    ) -> dict[str, list[str]]:
        """Generate features detected for each domain.

        Args:
            semantic_types: Semantic types mapping.
            identifier_columns: Identifier column names.
            measure_columns: Measure column names.
            domain: Selected domain.

        Returns:
            Dictionary mapping domain names to detected features.
        """
        features_detected = {}

        for candidate_domain in BusinessDomain:
            features = []

            # Add semantic type features
            for col, semantic_type in semantic_types.items():
                features.append(f"{semantic_type}: {col}")

            # Add identifier features
            for col in identifier_columns:
                features.append(f"identifier: {col}")

            # Add measure features
            for col in measure_columns:
                features.append(f"measure: {col}")

            if features:
                features_detected[candidate_domain.value] = features

        return features_detected

    def _generate_domain_summary(
        self,
        domain: BusinessDomain,
        confidence: float,
        evidence: list[str],
    ) -> str:
        """Generate human-readable domain summary.

        Args:
            domain: Detected business domain.
            confidence: Confidence score (0.0-1.0).
            evidence: List of evidence items.

        Returns:
            Human-readable domain summary.
        """
        confidence_percent = confidence * 100

        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence_level = "high"
        elif confidence >= self.MIN_CONFIDENCE_THRESHOLD:
            confidence_level = "moderate"
        else:
            confidence_level = "low"

        summary = (
            f"Dataset classified as {domain.get_display_name()} domain "
            f"with {confidence_level} confidence ({confidence_percent:.1f}%). "
        )

        if evidence:
            summary += f"Key evidence: {', '.join(evidence[:3])}"

        return summary

    def _generate_domain_reasoning(
        self,
        domain: BusinessDomain,
        candidates: dict[BusinessDomain, float],
        evidence: list[str],
    ) -> str:
        """Generate detailed reasoning for domain selection.

        Args:
            domain: Selected business domain.
            candidates: All domain candidates with scores.
            evidence: List of evidence items.

        Returns:
            Detailed reasoning for domain selection.
        """
        reasoning = f"Selected {domain.get_display_name()} as the primary domain.\n\n"

        # Add candidate rankings
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        reasoning += "Domain candidates ranked by confidence:\n"
        for i, (candidate_domain, score) in enumerate(sorted_candidates[:5], 1):
            score_percent = score * 100
            reasoning += f"{i}. {candidate_domain.get_display_name()}: {score_percent:.1f}%\n"

        reasoning += "\n"

        # Add evidence
        if evidence:
            reasoning += "Supporting evidence:\n"
            for i, item in enumerate(evidence[:5], 1):
                reasoning += f"{i}. {item}\n"

        return reasoning