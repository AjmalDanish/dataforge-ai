# ADR-012: Business Objective Detection Agent Implementation

## Status

**Accepted**

## Context

DataForge AI v2 must not only classify a dataset's domain but also decide **what questions to ask** about it. Without an explicit objective-detection stage, downstream agents (profiling, KPI discovery, insight generation) have no shared analytical framing and each would independently invent questions — producing redundant, inconsistent work.

The system therefore needs a dedicated agent that, after schema and domain detection, produces a structured set of **analytical objectives** and **answerable questions** that the dataset can support.

## Decision

Implement `BusinessObjectiveDetectionAgent` as a **Phase 3 (Data Understanding)** agent using an **LLM-primary + deterministic template-fallback** strategy.

- **Inputs:** `cleaned_data`, `business_domain`
- **Outputs:** `business_objectives` (`list[BusinessObjective]`), `answerable_questions` (`list[str]`)
- **Retry policy:** `max_retries=2`
- **Failure policy:** `SKIP`
- **Timeout:** 30 seconds

## Responsibility Boundary

| Concept | Agent | Definition |
|---|---|---|
| **Business objective** | BusinessObjectiveDetectionAgent | Analytical question to ask (e.g. "Revenue trend analysis") |
| **KPI** | KPIDiscoveryAgent | Measurable value with a computed trend (e.g. "MRR = $1.2M, MoM +4.3%") |
| **Insight** | InsightGenerationAgent | Finding with evidence and a recommendation |

An objective is analytical *intent*, a KPI is a *measure*, and an insight is a *conclusion*. Strategic objectives supplied directly by a user belong to the Planner/query layer and are distinct from objectives the agent derives from the data itself.

## LLM Strategy

LLM is the **primary** method, per the project's "LLM-assisted, not LLM-dependent" principle (DD-3):

1. Context sent to the LLM is **bounded** — shape, column names, column dtypes, and at most 5 sample rows truncated to 200 characters each. The full DataFrame is never sent.
2. The prompt requests a strict JSON contract (`objectives[]` + `answerable_questions[]`).
3. [`_parse_llm_response()`](../../dataforge/agents/objective.py) extracts JSON (tolerating markdown fences), validates each objective (skipping invalid entries), and **sanitizes** `answerable_questions` to a clean `list[str]`.
4. If no valid objective survives, the parser **raises `ValueError`**, forcing the caller to fall back to templates with full context — preventing a malformed LLM response from being mislabeled as a high-confidence LLM result.

## Failure Policy

`FailurePolicy.SKIP` — if the agent cannot produce objectives (no LLM, malformed response, unexpected exception), the pipeline continues with degraded business framing rather than aborting the run. Deterministic templates provide the fallback.

## Alternatives Considered

### Alternative 1: Remove the agent

**Pros:** Fewer moving parts; KPIs and insights can be computed without an explicit objectives stage.

**Cons:** Downstream agents would each re-derive their own questions, producing redundant, inconsistent framing; no single place to expose "what can this dataset answer?" to the user.

**Decision:** Rejected. The frozen architecture keeps objectives as a distinct, observable phase.

### Alternative 2: Merge into KPIDiscoveryAgent

**Pros:** One fewer agent; objectives and KPIs are naturally related.

**Cons:** Conflates a *question* with a *measure*, blurring the output contract and making each stage harder to test and reason about. A KPI can be computed without ever stating the objective it serves.

**Decision:** Rejected. The responsibility boundary (question vs measure) is preserved.

### Alternative 3: User-only objectives

**Pros:** No auto-detection complexity; objectives always reflect explicit user intent.

**Cons:** The pipeline has no analytical framing when the user supplies no objectives — the core "autonomous" promise breaks. The dataset's columns are the ground truth of answerability and should drive defaults.

**Decision:** Rejected. Auto-detected analytical objectives are the default, with user-supplied strategic objectives layered above them.

### Alternative 4: Deterministic-only (no LLM)

**Pros:** Predictable, zero cost, no provider configuration.

**Cons:** Template objectives are generic; they cannot adapt to unusual schemas or surface nuanced questions.

**Decision:** Rejected as the *primary* path, but retained as the *fallback* — LLM-primary with a deterministic safety net gives the best of both.

## Consequences

### Positive

- Shared analytical framing for all downstream agents.
- Graceful degradation: LLM failure yields 0.7-confidence template objectives rather than a failed run.
- Bounded LLM cost (small context sample, not full data).
- High test coverage (100% on the agent) and clear behavior contracts.
- Honest labeling: `detection_method`/`quality_score` always reflect the real source of the output.

### Negative

- Adds one more node to the graph and one more phase transition.
- Template fallback quality is generic for domains with weak column matches.
- LLM introduces cost and latency when available.

### Neutral

- Objective confidence is fixed (0.9 LLM / 0.7 template) because the provider interface exposes no per-token probabilities.

## Risks

- **LLM cost/latency** — mitigated by bounded context and a 20-second LLM call cap within the 30-second budget.
- **Fallback quality** — mitigated by 10 domain template sets, column-aware keyword filtering, and a GENERAL fallback; degraded output is still coherent.
- **LLM schema drift** — mitigated by parser sanitization and the raise-on-empty contract, which routes unusable responses to the deterministic path.

## References

- [BusinessObjectiveDetectionAgent Documentation](../agents/BusinessObjectiveDetectionAgent.md)
- [Agent Catalog (Section 6)](../v2/AGENTS.md)
- [Design Decisions (DD-3)](../v2/DESIGN_DECISIONS.md)
- [Domain Models](../../dataforge/core/models.py)
- [GraphState](../../dataforge/core/state.py)
