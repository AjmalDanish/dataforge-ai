"""Executive brief and refinement intent, constrained with DSPy.

Consistency comes from four things, not from sampling settings (current
Claude models reject ``temperature``):

1. Typed DSPy signatures: fixed fields, bounded list lengths, closed vocabularies.
2. Numbers are computed by ``dataforge.analytics.dashboard``; the LLM only explains
   them, and ``is_grounded`` rejects any text citing a number that isn't a fact.
3. ``dspy.Refine`` retries once when the output isn't grounded; after that the
   deterministic rule-based brief is used.
4. A disk cache keyed on (model, prompt version, facts, focus): the same data and
   the same request always return the identical brief.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from pydantic import BaseModel, Field

from dataforge.analytics.dashboard import facts, is_grounded

__all__ = ["generate_brief", "interpret_refinement", "make_lm", "rule_brief", "PROMPT_VERSION"]

PROMPT_VERSION = "brief-v1"


class Finding(BaseModel):
    title: str = Field(max_length=90)
    kpi: str = Field(description="KPI label from facts this finding is about")
    direction: Literal["up", "down", "flat"]
    so_what: str = Field(max_length=240, description="Why an executive should care")


class Recommendation(BaseModel):
    action: str = Field(max_length=140, description="Concrete, specific action")
    rationale: str = Field(max_length=240)
    priority: Literal["high", "medium", "low"]
    kpi: str = Field(description="KPI label this action should move")


class Brief(BaseModel):
    headline: str = Field(max_length=120)
    summary: str = Field(max_length=700, description="At most 4 sentences")
    findings: list[Finding] = Field(max_length=4)
    recommendations: list[Recommendation] = Field(max_length=4)
    risks: list[str] = Field(default_factory=list, max_length=3)


class Intent(BaseModel):
    kpis: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    grain: str | None = None
    filters: dict[str, list[str]] = Field(default_factory=dict)
    focus: str = Field(default="", max_length=200, description="One-line focus for the brief")


def _signatures():
    import dspy

    class ExecutiveBrief(dspy.Signature):
        """You are a senior business analyst writing the brief at the top of an executive dashboard.
        Use ONLY numbers that appear in facts_json; you may round them (817860.05 -> $817.9K) but never
        compute, estimate or invent numbers, causes, benchmarks or data that is not there.
        Compare the current period with the previous one, name the biggest drivers from the breakdowns,
        and give specific, prioritized actions tied to a KPI. If focus is given, center the brief on it."""

        facts_json: str = dspy.InputField(desc="Computed metrics: the only numbers you may cite")
        domain: str = dspy.InputField()
        focus: str = dspy.InputField(desc="User's requested focus; may be empty")
        brief: Brief = dspy.OutputField()

    class RefineIntent(dspy.Signature):
        """Translate the user's request for their dashboard into choices taken ONLY from options_json.
        Leave a field empty to keep the current choice. Filter values must be listed in options_json."""

        request: str = dspy.InputField(desc="What the user wants to see")
        options_json: str = dspy.InputField()
        intent: Intent = dspy.OutputField()

    return ExecutiveBrief, RefineIntent


def _claude_lm_class():
    import anthropic
    import dspy

    class ClaudeLM(dspy.BaseLM):
        """DSPy LM backed by the official Anthropic SDK (no sampling params; refusal fallback)."""

        def __init__(self, model: str, api_key: str, max_tokens: int = 16000):
            super().__init__(model=model, max_tokens=max_tokens, cache=False)
            self._client = anthropic.Anthropic(api_key=api_key, timeout=180, max_retries=2)

        def forward(self, prompt=None, messages=None, **kwargs):
            messages = messages or [{"role": "user", "content": prompt}]
            system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
            conversation = [m for m in messages if m["role"] != "system"]
            r = self._client.beta.messages.create(
                model=self.model,
                max_tokens=self.kwargs.get("max_tokens") or 16000,
                system=system or anthropic.omit,
                messages=conversation,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            if r.stop_reason == "refusal":
                raise RuntimeError("Claude declined the request")
            text = "".join(b.text for b in r.content if b.type == "text")
            usage = {
                "prompt_tokens": r.usage.input_tokens,
                "completion_tokens": r.usage.output_tokens,
                "total_tokens": r.usage.input_tokens + r.usage.output_tokens,
            }
            message = SimpleNamespace(content=text, tool_calls=None, reasoning_content=None)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message, finish_reason="stop", logprobs=None)],
                usage=usage,
                model=r.model,
            )

    return ClaudeLM


def make_lm():
    """DSPy LM from the environment (same settings as ``llm_from_env``), or None."""
    from dataforge.infrastructure.llm_providers import llm_from_env

    provider = llm_from_env()
    if provider is None:
        return None
    cfg = provider.config
    if cfg.provider == "anthropic":
        return _claude_lm_class()(model=cfg.model, api_key=cfg.api_key)
    import dspy

    return dspy.LM(f"{cfg.provider}/{cfg.model}", api_key=cfg.api_key, cache=False)


def _cache_path(*parts: Any) -> Path | None:
    root = os.getenv("DATAFORGE_LLM_CACHE_DIR") or (
        str(Path(os.getenv("OUTPUT_DIR", "output")) / "_llm_cache")
    )
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()
    return Path(root) / f"{digest}.json"


def _fmt(v: Any, unit: str | None = None) -> str:
    if not isinstance(v, (int, float)):
        return str(v)
    text = f"{v:,.0f}" if float(v).is_integer() or abs(v) >= 1000 else f"{v:,.2f}"
    return f"${text}" if unit == "currency" else text


def _period_label(p: str | None) -> str | None:
    """'2015-12' -> 'Dec 2015'; other grains are left as-is."""
    import calendar

    if p and len(p) == 7 and p[4] == "-" and p[:4].isdigit() and p[5:].isdigit():
        return f"{calendar.month_abbr[int(p[5:])]} {p[:4]}"
    return p


def rule_brief(dashboard: dict[str, Any], domain: str = "general") -> dict[str, Any]:
    """Deterministic brief with the same shape as the LLM one (used without a key, or as fallback)."""
    tiles = dashboard["kpis"]
    raw = dashboard.get("period") or {}
    period = {k: _period_label(v) if k in ("current", "previous") else v for k, v in raw.items()}
    lead = tiles[0]
    findings, recs = [], []
    for t in tiles:
        if t.get("change_pct") is None:
            continue
        direction = "up" if t["change_pct"] > 1 else "down" if t["change_pct"] < -1 else "flat"
        findings.append({
            "title": f"{t['label']} {direction} {abs(t['change_pct'])}% ({period.get('current')} vs {period.get('previous')})",
            "kpi": t["label"],
            "direction": direction,
            "so_what": f"{t['label']}: {_fmt(t['current'], t['unit'])} vs {_fmt(t['previous'], t['unit'])}.",
        })
    findings = findings[:2]  # leave room for the drivers below
    for b in dashboard["breakdowns"][:2]:
        if b["rows"]:
            top = b["rows"][0]
            findings.append({
                "title": f"{top['name']} leads {b['dimension']} with {top['share_pct']}% share",
                "kpi": lead["label"],
                "direction": "flat",
                "so_what": f"{top['name']} contributed {_fmt(top['value'], lead['unit'])}.",
            })
    findings = findings[:4]
    down = [t for t in tiles if (t.get("change_pct") or 0) < -1]
    if down:
        recs.append({
            "action": f"Investigate the {abs(down[0]['change_pct'])}% drop in {down[0]['label']} for {period.get('current')}",
            "rationale": "Find whether the decline is seasonal, operational or demand-driven before it persists.",
            "priority": "high",
            "kpi": down[0]["label"],
        })
    if dashboard["breakdowns"] and dashboard["breakdowns"][0]["rows"]:
        b = dashboard["breakdowns"][0]
        recs.append({
            "action": f"Protect and promote the top {b['dimension']} ({b['rows'][0]['name']})",
            "rationale": f"It drives {b['rows'][0]['share_pct']}% of {lead['label']}.",
            "priority": "medium",
            "kpi": lead["label"],
        })
    if dashboard.get("heatmap"):
        peak = max(dashboard["heatmap"]["cells"], key=lambda c: c["value"] or 0)
        recs.append({
            "action": f"Staff and stock for the peak slot ({peak['day']} {peak['hour']}:00)",
            "rationale": "Demand concentrates there; shortfalls cost the most.",
            "priority": "medium",
            "kpi": lead["label"],
        })
    change = lead.get("change_pct")
    headline = (
        f"{lead['label']} {_fmt(lead['value'], lead['unit'])}"
        + (f"; {period.get('current')} {'+' if change > 0 else ''}{change}% vs {period.get('previous')}" if change is not None else "")
    )[:120]
    summary = (
        f"{domain.title()} data from {dashboard['date_range'][0]} to {dashboard['date_range'][1]}. "
        if dashboard.get("date_range") else f"{domain.title()} data. "
    ) + " ".join(f["so_what"] for f in findings[:2])
    return {"headline": headline, "summary": summary[:700], "findings": findings, "recommendations": recs[:4], "risks": [], "source": "rules"}


def _brief_text(brief: dict[str, Any]) -> str:
    parts = [brief["headline"], brief["summary"], *brief.get("risks", [])]
    for f in brief["findings"]:
        parts += [f["title"], f["so_what"]]
    for r in brief["recommendations"]:
        parts += [r["action"], r["rationale"]]
    return "\n".join(parts)


def generate_brief(
    dashboard: dict[str, Any], domain: str = "general", focus: str = "", lm=None
) -> dict[str, Any]:
    """Executive brief for ``dashboard``: cached, grounded, typed; rule-based without an LLM."""
    fact_sheet = facts(dashboard)
    if lm is None:
        return rule_brief(dashboard, domain)

    cache = _cache_path(PROMPT_VERSION, lm.model, fact_sheet, domain, focus)
    if cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    import dspy

    ExecutiveBrief, _ = _signatures()

    def grounded(_args, pred) -> float:
        return 1.0 if is_grounded(_brief_text(pred.brief.model_dump()), fact_sheet) else 0.0

    program = dspy.Refine(dspy.Predict(ExecutiveBrief), N=2, reward_fn=grounded, threshold=1.0)
    try:
        with dspy.context(lm=lm, adapter=dspy.JSONAdapter()):
            pred = program(facts_json=json.dumps(fact_sheet), domain=domain, focus=focus)
        brief = pred.brief.model_dump()
    except Exception:
        return rule_brief(dashboard, domain)
    if not is_grounded(_brief_text(brief), fact_sheet):
        return rule_brief(dashboard, domain)  # never show unverifiable numbers
    brief["source"] = "llm"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(brief, sort_keys=True), encoding="utf-8")
    return brief


def interpret_refinement(instructions: str, opts: dict[str, Any], lm=None) -> dict[str, Any]:
    """User's free-text request -> dashboard spec limited to ``opts``. Empty without an LLM."""
    if lm is None or not instructions.strip():
        return {}
    cache = _cache_path(PROMPT_VERSION, "intent", lm.model, instructions.strip(), opts)
    if cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    import dspy

    _, RefineIntent = _signatures()
    try:
        with dspy.context(lm=lm, adapter=dspy.JSONAdapter()):
            intent = dspy.Predict(RefineIntent)(
                request=instructions.strip(), options_json=json.dumps(opts)
            ).intent
    except Exception:
        return {}
    spec = {
        "kpis": [k for k in intent.kpis if k in opts["kpis"]],
        "dimensions": [d for d in intent.dimensions if d in opts["dimensions"]],
        "grain": intent.grain if intent.grain in opts["grains"] else None,
        "filters": {
            k: [v for v in vals if v in opts["filters"].get(k, [])]
            for k, vals in intent.filters.items()
            if k in opts["filters"]
        },
        "focus": intent.focus.strip(),
    }
    spec = {k: v for k, v in spec.items() if v}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(spec, sort_keys=True), encoding="utf-8")
    return spec
