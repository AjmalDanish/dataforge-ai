"""Unit tests for ProfilingAgent (v2 contract).

Covers the frozen AGENTS.md §7 specification:
- Phase 4 (DEEP_ANALYSIS)
- Inputs: cleaned_data
- Outputs: profile
- Retry 2, Failure SKIP, Timeout 60s, LLM No

Per-column profile: type, cardinality, completeness, distribution
(mean/median/std/skewness/kurtosis), top values, range (min/max/IQR),
outlier count (IQR), temporal pattern (granularity/range/gaps).

Dataset-level profile: correlation matrices (Pearson, Spearman),
significant correlations (|r| > 0.5 with p-value), overall missing
ratio, duplicate row count.
"""

import copy
import math

import numpy as np
import pandas as pd
import pytest

from dataforge.agents.base import AgentDecision
from dataforge.agents.profiling import DataProfilingAgent, ProfilingAgent
from dataforge.core.logger import StructuredLogger
from dataforge.core.models import ExecutionPhase, FailurePolicy
from dataforge.core.state import GraphState


@pytest.fixture
def logger(tmp_path):
    """Create a structured logger for testing."""
    return StructuredLogger("test-profiling", tmp_path)


@pytest.fixture
def agent(logger):
    """Create a ProfilingAgent instance."""
    return DataProfilingAgent(logger=logger)


@pytest.fixture
def sample_dataframe():
    """Rich DataFrame with numeric, categorical, boolean and temporal columns."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "category": ["a", "b", "a", "b", "a"],
            "amount": [10.0, 20.0, 30.0, 40.0, 50.0],
            "amount2": [50.0, 40.0, 30.0, 20.0, 10.0],
            "flag": [True, False, True, False, True],
            "created": pd.to_datetime(
                ["2021-01-01", "2021-01-02", "2021-01-03", "2021-01-04", "2021-01-05"]
            ),
        }
    )


@pytest.fixture
def text_dataframe():
    """DataFrame with a high-cardinality text column."""
    return pd.DataFrame(
        {
            "value": list(range(15)),
            "label": [f"distinct text {i}" for i in range(15)],
        }
    )


@pytest.fixture
def state(sample_dataframe):
    """GraphState carrying cleaned_data."""
    return GraphState(input_dataset_path="test.csv").set("cleaned_data", sample_dataframe)


def _make_state(df) -> GraphState:
    """Build a GraphState from a DataFrame."""
    return GraphState(input_dataset_path="test.csv").set("cleaned_data", df)


# ══════════════════════════════════════════════════════════════════
# 1. v2 Contract
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentContract:
    """Tests for the frozen v2 contract attributes."""

    def test_agent_phase(self, agent):
        assert agent.phase == ExecutionPhase.DEEP_ANALYSIS

    def test_agent_required_inputs(self, agent):
        assert agent.required_inputs == ["cleaned_data"]

    def test_agent_produced_outputs(self, agent):
        assert agent.produced_outputs == ["profile"]

    def test_agent_failure_policy(self, agent):
        assert agent.failure_policy == FailurePolicy.SKIP

    def test_agent_timeout_seconds(self, agent):
        assert agent.timeout_seconds == 60

    def test_agent_retry_policy(self, agent):
        assert agent.retry_policy.max_retries == 2

    def test_agent_name(self, agent):
        assert agent.name == "DataProfilingAgent"

    def test_profiling_agent_alias(self):
        """ProfilingAgent is the frozen spec name and aliases the implementation."""
        assert ProfilingAgent is DataProfilingAgent
        instance = ProfilingAgent()
        assert instance.name == "DataProfilingAgent"

    def test_llm_is_none_by_default(self, agent):
        assert agent.llm is None


# ══════════════════════════════════════════════════════════════════
# 2. Execute — Happy Path
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentExecute:
    """Tests for the execute() happy path."""

    @pytest.mark.asyncio
    async def test_execute_returns_continue(self, agent, state):
        result = await agent.execute(state)
        assert result.decision == AgentDecision.CONTINUE

    @pytest.mark.asyncio
    async def test_execute_produces_profile(self, agent, state):
        result = await agent.execute(state)
        assert "profile" in result.data_updates

    @pytest.mark.asyncio
    async def test_execute_populates_all_outputs(self, agent, state):
        result = await agent.execute(state)
        for output in agent.produced_outputs:
            assert output in result.data_updates

    @pytest.mark.asyncio
    async def test_profile_dataset_level_keys(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        assert profile["n_rows"] == 5
        assert profile["n_columns"] == 6
        assert "columns" in profile
        assert "overall_missing_ratio" in profile
        assert "duplicate_row_count" in profile
        assert "correlations" in profile

    @pytest.mark.asyncio
    async def test_profile_column_type_lists(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        assert profile["numeric_columns"] == ["id", "amount", "amount2"]
        assert profile["categorical_columns"] == ["category"]
        assert profile["boolean_columns"] == ["flag"]
        assert profile["temporal_columns"] == ["created"]
        assert profile["has_numeric_columns"] is True
        assert profile["has_categorical_columns"] is True
        assert profile["numeric_column_count"] == 3
        assert profile["categorical_column_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_quality_score(self, agent, state):
        result = await agent.execute(state)
        assert result.quality_score == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.asyncio
    async def test_execute_notes_populated(self, agent, state):
        result = await agent.execute(state)
        assert len(result.execution_notes) > 0

    @pytest.mark.asyncio
    async def test_execute_metrics_populated(self, agent, state):
        result = await agent.execute(state)
        assert result.metrics.get("n_rows") == 5
        assert result.metrics.get("n_columns") == 6


# ══════════════════════════════════════════════════════════════════
# 3. Input Validation
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentInputValidation:
    """Tests for invalid input handling."""

    @pytest.mark.asyncio
    async def test_missing_cleaned_data(self, agent):
        state = GraphState(input_dataset_path="test.csv")
        result = await agent.execute(state)
        assert result.decision == AgentDecision.ERROR
        assert "not found" in result.message.lower()
        assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_cleaned_data_none(self, agent):
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", None)
        result = await agent.execute(state)
        assert result.decision == AgentDecision.ERROR

    @pytest.mark.asyncio
    async def test_cleaned_data_not_dataframe(self, agent):
        state = GraphState(input_dataset_path="test.csv").set("cleaned_data", [1, 2, 3])
        result = await agent.execute(state)
        assert result.decision == AgentDecision.ERROR

    @pytest.mark.asyncio
    async def test_empty_dataframe(self, agent):
        state = _make_state(pd.DataFrame())
        result = await agent.execute(state)
        assert result.decision == AgentDecision.ERROR
        assert "empty" in result.message.lower()

    @pytest.mark.asyncio
    async def test_zero_column_dataframe(self, agent):
        state = _make_state(pd.DataFrame(index=[0, 1, 2]))
        result = await agent.execute(state)
        assert result.decision == AgentDecision.ERROR


# ══════════════════════════════════════════════════════════════════
# 4. Semantic Type Inference
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentTypeInference:
    """Tests for semantic type classification."""

    def test_infer_numeric(self, agent):
        assert agent._infer_type(pd.Series([1, 2, 3])) == "numeric"

    def test_infer_float(self, agent):
        assert agent._infer_type(pd.Series([1.5, 2.5, 3.5])) == "numeric"

    def test_infer_boolean(self, agent):
        assert agent._infer_type(pd.Series([True, False, True])) == "boolean"

    def test_infer_temporal_datetime(self, agent):
        s = pd.to_datetime(pd.Series(["2021-01-01", "2021-01-02"]))
        assert agent._infer_type(s) == "temporal"

    def test_infer_temporal_object_strings(self, agent):
        assert agent._infer_type(pd.Series(["2021-01-01", "2021-01-02"])) == "temporal"

    def test_infer_categorical_low_cardinality(self, agent):
        assert agent._infer_type(pd.Series(["a", "b", "a", "b"])) == "categorical"

    def test_infer_text_high_cardinality(self, agent):
        s = pd.Series([f"v{i}" for i in range(15)])
        assert agent._infer_type(s) == "text"

    def test_infer_category_dtype(self, agent):
        s = pd.Series(["a", "b", "a"], dtype="category")
        assert agent._infer_type(s) == "categorical"

    def test_infer_all_null_object(self, agent):
        assert agent._infer_type(pd.Series([None, None, None])) == "categorical"

    def test_numeric_strings_not_temporal(self, agent):
        """Object columns of numeric strings must not be misread as temporal."""
        assert agent._infer_type(pd.Series(["1", "2", "3"])) != "temporal"


# ══════════════════════════════════════════════════════════════════
# 5. Numeric Distribution, Range & Outliers
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentNumeric:
    """Tests for numeric column profiling."""

    @pytest.mark.asyncio
    async def test_numeric_distribution_stats(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        dist = profile["columns"]["amount"]["distribution"]
        assert dist["mean"] == pytest.approx(30.0)
        assert dist["median"] == pytest.approx(30.0)
        assert dist["std"] == pytest.approx(15.8113883, abs=1e-4)
        assert dist["skewness"] == pytest.approx(0.0, abs=1e-6)
        assert dist["kurtosis"] is not None
        assert dist["kurtosis"] < 0

    @pytest.mark.asyncio
    async def test_numeric_range(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        rng = profile["columns"]["amount"]["range"]
        assert rng["min"] == 10.0
        assert rng["max"] == 50.0
        assert rng["q1"] == 20.0
        assert rng["q3"] == 40.0
        assert rng["iqr"] == 20.0

    @pytest.mark.asyncio
    async def test_numeric_no_outliers(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        assert profile["columns"]["amount"]["outlier_count"] == 0

    @pytest.mark.asyncio
    async def test_numeric_outlier_count(self, agent):
        df = pd.DataFrame({"v": [1.0, 2.0, 3.0, 4.0, 100.0]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["columns"]["v"]["outlier_count"] == 1

    @pytest.mark.asyncio
    async def test_constant_numeric_column(self, agent):
        df = pd.DataFrame({"const": [5.0, 5.0, 5.0, 5.0]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        col = profile["columns"]["const"]
        dist = col["distribution"]
        assert dist["mean"] == 5.0
        assert dist["std"] == 0.0
        assert dist["skewness"] is None
        assert dist["kurtosis"] is None
        assert col["outlier_count"] == 0
        assert col["range"]["iqr"] == 0.0

    @pytest.mark.asyncio
    async def test_all_null_numeric_column(self, agent):
        df = pd.DataFrame({"v": [np.nan, np.nan, np.nan]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        col = profile["columns"]["v"]
        assert col["distribution"] is None
        assert col["range"] is None
        assert col["outlier_count"] is None

    @pytest.mark.asyncio
    async def test_numeric_with_missing_values(self, agent):
        df = pd.DataFrame({"v": [1.0, np.nan, 3.0, 4.0]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        col = profile["columns"]["v"]
        assert col["completeness"]["non_null_count"] == 3
        assert col["completeness"]["missing_count"] == 1
        assert col["distribution"]["mean"] == pytest.approx(8.0 / 3.0)

    @pytest.mark.asyncio
    async def test_infinite_values_handled(self, agent):
        df = pd.DataFrame({"v": [1.0, np.inf, 3.0, -np.inf]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        col = profile["columns"]["v"]
        assert col["distribution"]["mean"] == pytest.approx(2.0)

    @pytest.mark.asyncio
    async def test_negative_values_range(self, agent):
        df = pd.DataFrame({"v": [-10.0, -5.0, 0.0, 5.0]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        rng = profile["columns"]["v"]["range"]
        assert rng["min"] == -10.0
        assert rng["max"] == 5.0


# ══════════════════════════════════════════════════════════════════
# 6. Categorical Top Values
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentTopValues:
    """Tests for categorical top values."""

    @pytest.mark.asyncio
    async def test_top_values(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        top = profile["columns"]["category"]["top_values"]
        counts = {t["value"]: t["count"] for t in top}
        assert counts == {"a": 3, "b": 2}

    @pytest.mark.asyncio
    async def test_top_values_frequency(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        top = profile["columns"]["category"]["top_values"]
        freqs = {t["value"]: t["frequency"] for t in top}
        assert freqs["a"] == pytest.approx(0.6)
        assert freqs["b"] == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_text_column_no_top_values(self, agent, text_dataframe):
        profile = (await agent.execute(_make_state(text_dataframe))).data_updates["profile"]
        assert profile["columns"]["label"]["top_values"] == []

    @pytest.mark.asyncio
    async def test_numeric_column_no_top_values(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        assert profile["columns"]["amount"]["top_values"] == []


# ══════════════════════════════════════════════════════════════════
# 7. Temporal Patterns
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentTemporal:
    """Tests for temporal column profiling."""

    @pytest.mark.asyncio
    async def test_temporal_pattern_present(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        tp = profile["columns"]["created"]["temporal_pattern"]
        assert tp is not None
        assert tp["granularity"] == "daily"
        assert tp["gap_count"] == 0

    @pytest.mark.asyncio
    async def test_temporal_min_max(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        tp = profile["columns"]["created"]["temporal_pattern"]
        assert tp["min"] == "2021-01-01"
        assert tp["max"] == "2021-01-05"

    @pytest.mark.asyncio
    async def test_temporal_gap_detection(self, agent):
        df = pd.DataFrame(
            {"d": pd.to_datetime(["2021-01-01", "2021-01-02", "2021-01-04"])}
        )
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        tp = profile["columns"]["d"]["temporal_pattern"]
        assert tp["gap_count"] == 1

    @pytest.mark.asyncio
    async def test_temporal_single_value(self, agent):
        df = pd.DataFrame({"d": pd.to_datetime(["2021-01-01", "2021-01-01"])})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        tp = profile["columns"]["d"]["temporal_pattern"]
        assert tp["granularity"] == "single"
        assert tp["gap_count"] == 0

    @pytest.mark.asyncio
    async def test_temporal_object_column(self, agent):
        df = pd.DataFrame({"d": ["2021-01-01", "2021-01-02", "2021-01-03"]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["temporal_columns"] == ["d"]
        assert profile["columns"]["d"]["temporal_pattern"]["granularity"] == "daily"

    def test_granularity_mapping(self, agent):
        assert agent._granularity_from_timedelta(pd.Timedelta(days=400)) == "yearly"
        assert agent._granularity_from_timedelta(pd.Timedelta(days=30)) == "monthly"
        assert agent._granularity_from_timedelta(pd.Timedelta(days=2)) == "daily"
        assert agent._granularity_from_timedelta(pd.Timedelta(hours=3)) == "hourly"
        assert agent._granularity_from_timedelta(pd.Timedelta(minutes=15)) == "minute"
        assert agent._granularity_from_timedelta(pd.Timedelta(seconds=30)) == "second"


# ══════════════════════════════════════════════════════════════════
# 8. Correlations
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentCorrelations:
    """Tests for correlation matrices and significance."""

    @pytest.mark.asyncio
    async def test_pearson_perfect_negative(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        matrix = profile["correlations"]["pearson"]["matrix"]
        assert matrix["amount"]["amount2"] == pytest.approx(-1.0, abs=1e-6)

    @pytest.mark.asyncio
    async def test_spearman_perfect_negative(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        matrix = profile["correlations"]["spearman"]["matrix"]
        assert matrix["amount"]["amount2"] == pytest.approx(-1.0, abs=1e-6)

    @pytest.mark.asyncio
    async def test_diagonal_is_one(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        matrix = profile["correlations"]["pearson"]["matrix"]
        assert matrix["amount"]["amount"] == 1.0

    @pytest.mark.asyncio
    async def test_significant_correlations_have_pvalue(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        sig = profile["correlations"]["pearson"]["significant"]
        assert len(sig) > 0
        for entry in sig:
            assert "p_value" in entry
            assert entry["p_value"] is not None

    @pytest.mark.asyncio
    async def test_significant_flags_strong_negative(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        sig = profile["correlations"]["pearson"]["significant"]
        found = [
            e
            for e in sig
            if {e["column_a"], e["column_b"]} == {"amount", "amount2"}
        ]
        assert found
        entry = found[0]
        assert entry["correlation"] == pytest.approx(-1.0, abs=1e-6)
        assert entry["direction"] == "negative"
        assert entry["strength"] == "strong"

    @pytest.mark.asyncio
    async def test_insufficient_numeric_columns(self, agent):
        df = pd.DataFrame({"a": [1, 2, 3]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["correlations"]["pearson"]["matrix"] == {}
        assert profile["correlations"]["pearson"]["significant"] == []
        assert profile["correlations"]["spearman"]["matrix"] == {}

    @pytest.mark.asyncio
    async def test_constant_column_correlation_is_none(self, agent):
        df = pd.DataFrame({"const": [5.0, 5.0, 5.0, 5.0], "v": [1.0, 2.0, 3.0, 4.0]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        matrix = profile["correlations"]["pearson"]["matrix"]
        assert matrix["const"]["v"] is None
        assert matrix["v"]["const"] is None

    @pytest.mark.asyncio
    async def test_missing_values_pairwise(self, agent):
        df = pd.DataFrame(
            {"a": [1.0, 2.0, np.nan, 4.0], "b": [2.0, 4.0, 6.0, 8.0]}
        )
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        matrix = profile["correlations"]["pearson"]["matrix"]
        assert matrix["a"]["b"] == pytest.approx(1.0, abs=1e-6)


# ══════════════════════════════════════════════════════════════════
# 9. Dataset-Level Profile
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentDatasetLevel:
    """Tests for dataset-level metrics."""

    @pytest.mark.asyncio
    async def test_no_duplicates(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        assert profile["duplicate_row_count"] == 0

    @pytest.mark.asyncio
    async def test_duplicate_rows(self, agent):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [2, 2, 3]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["duplicate_row_count"] == 1

    @pytest.mark.asyncio
    async def test_overall_missing_ratio_zero(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        assert profile["overall_missing_ratio"] == 0.0

    @pytest.mark.asyncio
    async def test_overall_missing_ratio(self, agent):
        df = pd.DataFrame({"a": [1, np.nan, 3], "b": [4, 5, 6]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["overall_missing_ratio"] == pytest.approx(1.0 / 6.0)

    @pytest.mark.asyncio
    async def test_quality_score_reflects_missing(self, agent):
        df = pd.DataFrame({"a": [1, np.nan, 3], "b": [4, 5, 6]})
        result = await agent.execute(_make_state(df))
        assert result.quality_score == pytest.approx(5.0 / 6.0)


# ══════════════════════════════════════════════════════════════════
# 10. Edge Cases
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentEdgeCases:
    """Tests for boundary and edge-case datasets."""

    @pytest.mark.asyncio
    async def test_single_row(self, agent):
        df = pd.DataFrame({"a": [1], "b": ["x"]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["n_rows"] == 1
        assert profile["columns"]["a"]["distribution"]["std"] == 0.0

    @pytest.mark.asyncio
    async def test_all_numeric(self, agent):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["numeric_column_count"] == 2
        assert profile["has_categorical_columns"] is False

    @pytest.mark.asyncio
    async def test_all_text(self, agent, text_dataframe):
        profile = (await agent.execute(_make_state(text_dataframe))).data_updates["profile"]
        assert "label" in profile["text_columns"]
        assert profile["has_numeric_columns"] is True  # "value" is numeric

    @pytest.mark.asyncio
    async def test_all_null_dataframe(self, agent):
        df = pd.DataFrame({"a": [None, None, None], "b": [np.nan, np.nan, np.nan]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["overall_missing_ratio"] == 1.0
        assert profile["has_numeric_columns"] is False

    @pytest.mark.asyncio
    async def test_non_string_column_names(self, agent):
        df = pd.DataFrame({0: [1, 2, 3], 1: ["a", "b", "c"]})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert 0 in profile["columns"]
        assert 1 in profile["columns"]

    @pytest.mark.asyncio
    async def test_many_columns(self, agent):
        df = pd.DataFrame({f"c{i}": [i, i + 1, i + 2] for i in range(50)})
        profile = (await agent.execute(_make_state(df))).data_updates["profile"]
        assert profile["n_columns"] == 50

    @pytest.mark.asyncio
    async def test_boolean_column_profiled(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        assert profile["columns"]["flag"]["type"] == "boolean"
        assert profile["columns"]["flag"]["distribution"] is None

    @pytest.mark.asyncio
    async def test_unique_ratio_cardinality(self, agent, state):
        profile = (await agent.execute(state)).data_updates["profile"]
        card = profile["columns"]["category"]["cardinality"]
        assert card["unique_count"] == 2
        assert card["unique_ratio"] == pytest.approx(0.4)


# ══════════════════════════════════════════════════════════════════
# 11. Data Safety / Immutability
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentImmutability:
    """Tests that cleaned_data is never mutated."""

    @pytest.mark.asyncio
    async def test_no_mutation_of_cleaned_data(self, agent, sample_dataframe):
        before = sample_dataframe.copy(deep=True)
        state = _make_state(sample_dataframe)
        await agent.execute(state)
        pd.testing.assert_frame_equal(sample_dataframe, before)

    @pytest.mark.asyncio
    async def test_no_mutation_with_inf_and_nan(self, agent):
        df = pd.DataFrame({"v": [1.0, np.inf, np.nan]})
        before = df.copy(deep=True)
        await agent.execute(_make_state(df))
        pd.testing.assert_frame_equal(df, before)

    @pytest.mark.asyncio
    async def test_state_data_not_mutated(self, agent, sample_dataframe):
        state = _make_state(sample_dataframe)
        result = await agent.execute(state)
        # execute() returns data_updates but does not write back into state.data
        assert "profile" not in state.data
        assert state.data["cleaned_data"] is sample_dataframe
        assert "profile" in result.data_updates


# ══════════════════════════════════════════════════════════════════
# 12. Error Handling
# ══════════════════════════════════════════════════════════════════


class TestProfilingAgentErrorHandling:
    """Tests for unexpected error handling."""

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_error(self, agent, state, monkeypatch):
        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(agent, "_build_profile", _boom)
        result = await agent.execute(state)
        assert result.decision == AgentDecision.ERROR
        assert "boom" in result.message
        assert result.quality_score == 0.0
