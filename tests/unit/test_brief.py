"""DSPy brief: typed output, grounding fallback, consistency cache, refinement validation."""

import json

import pandas as pd
import pytest

dspy = pytest.importorskip("dspy")
from dspy.utils import DummyLM  # noqa: E402

from dataforge.analytics.dashboard import build_dashboard, infer_model, options  # noqa: E402
from dataforge.llm.brief import generate_brief, interpret_refinement  # noqa: E402


@pytest.fixture(autouse=True)
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATAFORGE_LLM_CACHE_DIR", str(tmp_path / "cache"))
    return tmp_path / "cache"


@pytest.fixture
def dash():
    df = pd.DataFrame({
        "date": [f"2015-0{m}-1{d}" for m in (1, 2) for d in range(10)] * 3,
        "id": [f"o{i // 2}" for i in range(60)],
        "size": ["S", "M", "L"] * 20,
        "price": [10.0, 15.0, 20.0] * 20,
    })
    return build_dashboard(df, infer_model(df), {"grain": "month"})


def _brief(headline: str, summary: str) -> dict:
    return {"brief": {
        "headline": headline,
        "summary": summary,
        "findings": [{"title": "Sales held steady", "kpi": "Revenue", "direction": "flat",
                      "so_what": "Demand is stable across sizes."}],
        "recommendations": [{"action": "Promote large pizzas", "rationale": "Largest share of revenue.",
                             "priority": "high", "kpi": "Revenue"}],
        "risks": ["Only two months of history."],
    }}


def test_without_lm_uses_rules(dash):
    brief = generate_brief(dash, "retail")
    assert brief["source"] == "rules" and brief["headline"]


def test_grounded_llm_brief_is_cached_and_identical(dash, cache_dir):
    revenue = dash["kpis"][0]["value"]
    lm = DummyLM([_brief(f"Revenue ${revenue:,.0f}", "Steady two months.")], adapter=dspy.JSONAdapter())
    first = generate_brief(dash, "retail", lm=lm)
    assert first["source"] == "llm"
    assert first["headline"] == f"Revenue ${revenue:,.0f}"
    assert len(list(cache_dir.iterdir())) == 1

    # Same facts again: served from the cache — no LLM call, byte-identical.
    exhausted = DummyLM([], adapter=dspy.JSONAdapter())
    assert generate_brief(dash, "retail", lm=exhausted) == first


def test_invented_numbers_fall_back_to_rules(dash):
    made_up = _brief("Revenue jumped 87.3% to $9,999,999", "Record quarter.")
    lm = DummyLM([made_up, made_up], adapter=dspy.JSONAdapter())
    brief = generate_brief(dash, "retail", lm=lm)
    assert brief["source"] == "rules"
    assert "9,999,999" not in json.dumps(brief)


def test_refinement_is_limited_to_real_options(dash):
    opts = dash["options"]
    intent = {"intent": {"kpis": ["revenue", "profit"], "dimensions": ["size", "region"], "grain": "quarter",
                         "filters": {"size": ["L", "XXL"], "store": ["north"]}, "focus": "Large pizzas"}}
    spec = interpret_refinement("focus on large pizzas by size", opts, lm=DummyLM([intent], adapter=dspy.JSONAdapter()))
    assert spec == {"kpis": ["revenue"], "dimensions": ["size"], "filters": {"size": ["L"]}, "focus": "Large pizzas"}
    assert interpret_refinement("anything", opts, lm=None) == {}


def test_claude_lm_adapter_works_with_dspy(dash, monkeypatch):
    """The production path: DSPy -> ClaudeLM -> Anthropic SDK (network call mocked)."""
    from types import SimpleNamespace as NS

    from dataforge.llm.brief import _claude_lm_class

    revenue = dash["kpis"][0]["value"]
    payload = json.dumps(_brief(f"Revenue ${revenue:,.0f}", "Steady."))
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return NS(
            content=[NS(type="thinking", text=""), NS(type="text", text=payload)],
            stop_reason="end_turn",
            usage=NS(input_tokens=100, output_tokens=50),
            model=kwargs["model"],
        )

    lm = _claude_lm_class()(model="claude-opus-5-5", api_key="test-key")
    monkeypatch.setattr(lm._client.beta.messages, "create", fake_create)

    brief = generate_brief(dash, "retail", lm=lm)

    assert brief["source"] == "llm" and brief["headline"] == f"Revenue ${revenue:,.0f}"
    sent = calls[0]
    assert sent["model"] == "claude-opus-5-5"
    assert "temperature" not in sent  # rejected by current Claude models
    assert sent["fallbacks"] == "default"
    assert all(m["role"] in ("user", "assistant") for m in sent["messages"])
