# BusinessObjectiveDetectionAgent — The Strategist

## 1. Purpose

The BusinessObjectiveDetectionAgent answers a single question:

> **"What analytical questions should the system ask about this dataset?"**

Given a cleaned dataset and its detected business domain, the agent produces two things:

1. `business_objectives` — a structured list of [`BusinessObjective`](../core/models.md) objects (each with a `category`, `priority`, `confidence`, and `keywords`).
2. `answerable_questions` — a deduplicated list of plain-text questions the data can actually answer (capped at 10).

### Boundary: Objective vs KPI vs Insight

| Concept | Owned by | Meaning |
|---|---|---|
| **Business objective** (analytical) | BusinessObjectiveDetectionAgent | A *question to ask* (e.g. "Revenue trend analysis", "Employee retention analysis") |
| **KPI / metric** | KPIDiscoveryAgent | A *measurable value* with a computed trend (e.g. "Monthly revenue = $1.2M, MoM +4.3%") |
| **Insight** | InsightGenerationAgent | A *finding* with evidence and an actionable recommendation (e.g. "Revenue dropped 12% in Q3 because of a supply-chain delay") |

An objective is the *analytical intent*; a KPI is the *measure*; an insight is the *conclusion*.

### User-supplied objectives vs detected objectives

An objective supplied directly by a user (e.g. "I want to know why churn increased") is a **strategic** directive that belongs to the Planner/query layer. The BusinessObjectiveDetectionAgent generates **analytical** objectives that are *derived from the data itself* — the questions the available columns make answerable — so the pipeline has a sensible framing even when the user provides none.

---

## 2. Position in Pipeline

The agent sits in **Phase 3 — Data Understanding**, immediately after business domain detection and before deep profiling:

```
Data Ingestion
      ↓
Validation
      ↓
Cleaning
      ↓
Schema Detection          (Phase 3)
      ↓
Business Domain Detection (Phase 3)
      ↓
Business Objective Detection (Phase 3)   ← this agent
      ↓
Profiling                 (Phase 4)
      ↓
Feature Engineering       (Phase 4)
      ↓
KPI Discovery             (Phase 4)
      ↓
Statistical Analysis      (Phase 5)
      ↓
Insight Generation        (Phase 6)
      ↓
Visualization             (Phase 7)
      ↓
Executive Report          (Phase 7)
```

It consumes `cleaned_data` (from the cleaning phase) and `business_domain` (from the domain agent), and it produces the framing that downstream agents use to focus profiling, KPI discovery, and insight generation.

---

## 3. Agent Contract

Verified against [`dataforge/agents/objective.py`](../../dataforge/agents/objective.py):

| Property | Value |
|---|---|
| Phase | `ExecutionPhase.DATA_UNDERSTANDING` (Phase 3) |
| Inputs (`required_inputs`) | `cleaned_data`, `business_domain` |
| Outputs (`produced_outputs`) | `business_objectives`, `answerable_questions` |
| Retry policy | `RetryPolicy(max_retries=2)` |
| Failure policy | `FailurePolicy.SKIP` |
| Timeout | `30` seconds (default) |
| LLM | **Primary** method |
| Fallback | Deterministic domain templates |

---

## 4. Detection Strategy

### LLM-primary architecture

The agent follows the project's **LLM-assisted, not LLM-dependent** principle (DD-3). When an LLM provider is available, it is the primary path; the deterministic template path is the safety net.

### Bounded LLM context

The agent does **not** send the full DataFrame to the LLM. [`_prepare_llm_context()`](../../dataforge/agents/objective.py) builds a compact prompt payload:

- business domain name
- dataset shape (`rows × columns`)
- the full column list
- each column's dtype
- **at most 5 sample rows**, each truncated to 200 characters

This keeps the token cost bounded regardless of dataset size.

### Structured JSON parsing

[`_create_llm_prompt()`](../../dataforge/agents/objective.py) instructs the LLM to return a JSON object with an `objectives` array (`objective`, `category`, `priority`, `keywords`) and an `answerable_questions` array.

[`_parse_llm_response()`](../../dataforge/agents/objective.py) then:

1. Extracts the first `{...}` JSON block (tolerating markdown code fences).
2. Parses each objective into a [`BusinessObjective`](../../dataforge/core/models.py) with `confidence=0.9`; any individual objective that fails model validation is **skipped** (not fatal).
3. **Sanitizes** `answerable_questions`: a non-list payload is coerced to `[]`, and non-string / blank entries are dropped, so a malformed LLM response cannot leak a non-`list[str]` value into GraphState.
4. If **no** valid objectives survive, it **raises `ValueError`**.

### Unusable LLM response

Because the parser raises instead of silently fabricating output, an empty, malformed, or otherwise unusable LLM response flows back up to [`execute()`](../../dataforge/agents/objective.py), which logs a warning and **falls back to templates with full dataset context**. This guarantees the result is never mislabeled: `detection_method` and `quality_score` always reflect the path that actually produced the objectives.

---

## 5. Deterministic Fallback

[`_detect_with_templates()`](../../dataforge/agents/objective.py) provides a deterministic fallback that never requires a network call.

### Supported domains

All 10 [`BusinessDomain`](../../dataforge/core/models.py) values have dedicated templates, each with 5 entries:

`RETAIL`, `FINANCE`, `HR`, `HEALTHCARE`, `MARKETING`, `SAAS`, `REAL_ESTATE`, `EDUCATION`, `LOGISTICS`, `GENERAL`.

### Keyword filtering

Each template declares `keywords`. Templates are kept only if one of their keywords is a substring of a (lowercased) column name. Templates with no keywords are always kept. If **no** template matches the available columns, the full domain template set is used — the agent degrades gracefully rather than returning nothing.

### GENERAL fallback

An unknown or invalid domain string is coerced to `BusinessDomain.GENERAL`, which has its own template set. [`_detect_with_templates()`](../../dataforge/agents/objective.py) also falls back to `GENERAL` templates when a domain key is absent.

### Question generation, dedup, and cap

[`_generate_answerable_questions()`](../../dataforge/agents/objective.py):

- emits "What is the {objective}?" for each objective;
- adds domain-specific variations for `RETAIL`, `FINANCE`, `HR`, and `SAAS`;
- adds a trend question when numeric-looking columns exist;
- **deduplicates** while preserving order;
- **caps the result at 10 questions**.

### Confidence behavior

| Path | Objective confidence | Quality score | `detection_method` |
|---|---|---|---|
| LLM success | `0.9` | `0.9` | `llm` |
| Template fallback | `0.7` | `0.7` | `templates` |

---

## 6. Failure Handling

| Condition | Behavior |
|---|---|
| Missing/invalid `cleaned_data` | `AgentDecision.ERROR`, `quality_score=0.0`, message "Cleaned data not found or invalid" |
| Empty `cleaned_data` | `AgentDecision.ERROR`, `quality_score=0.0`, message "Cleaned data is empty" |
| Invalid domain string | Coerced to `BusinessDomain.GENERAL` (no crash) |
| Unavailable LLM (no key, no provider) | Skips LLM → template fallback |
| Malformed LLM JSON | `ValueError` → warning logged → template fallback |
| Empty LLM response | `ValueError` → warning logged → template fallback |
| LLM exception | Warning logged → template fallback |
| LLM timeout | `asyncio.TimeoutError` → re-raised as exception → template fallback |
| Unexpected exception | `AgentDecision.ERROR`, `quality_score=0.0`, message "Objective detection failed: {e}" |

**Key guarantee:** LLM failure does **not** fail the whole analysis — the deterministic templates keep the pipeline moving (`FailurePolicy.SKIP` semantics).

---

## 7. GraphState Interaction

The agent does **not** mutate `GraphState` directly. It returns an `AgentResult` whose `data_updates` contain exactly two keys it owns:

- `business_objectives` — `list[BusinessObjective]`
- `answerable_questions` — `list[str]`

The base class [`execute_with_logging()`](../../dataforge/agents/base.py) applies those updates immutably via [`GraphState.set()`](../../dataforge/core/state.py), and records metrics (`detection_method`, `objectives_count`, `questions_count`) via `add_metric`.

---

## 8. Performance

- **Template path**: O(columns × templates) substring checks; it never iterates DataFrame cell values, so runtime is insensitive to row count (1K vs 1M rows).
- **LLM path**: context is bounded to 5 sample rows × 200 chars plus the column list, so token cost is O(columns), not O(rows).
- **Question generation**: O(objectives + columns), capped at 10 outputs.
- **LLM call timeout**: `max(min(timeout_seconds - 5.0, 20.0), 1.0)` seconds — leaves a buffer for fallback and result construction while respecting the configured 30-second budget.

---

## 9. Testing

Verified test results (re-run during Task 6.4/6.5):

| Scope | Result |
|---|---|
| `tests/unit/test_objective_agent.py` | **65 tests — 65 passed, 0 failed, 0 errors** |
| Objective statement coverage | **100%** (`objective.py` 147 statements, 0 missed) |
| Objective + domain (`test_domain_agent.py`) | **126 passed, 0 failed** |
| Full repository | **548 passed, 14 failed, 16 skipped** |

The 14 repository failures are **pre-existing v1/v2 migration issues outside this task** (see Section 10).

The objective test suite (10 classes) covers: initialization and availability checks (including injected-provider-without-key), all 10 domain execution paths, LLM success/timeout/malformed/empty/exception, template fallback, question dedup/limit, data immutability, output correctness, and integration workflows.

---

## 10. Known Repository Issues

These failures exist at the repository level and are **not** caused by, and are **not** fixed by, this agent:

1. **workflow `AgentHistoryEntry`/v1-v2 mismatch** — [`route_from_planner()`](../../dataforge/graph/workflow.py) subscripts `state.agent_history[-1]["result"]`, but history entries are now Pydantic objects → `TypeError: 'AgentHistoryEntry' object is not subscriptable`.
2. **PlannerAgent v1 GraphState fields** — references `validation_status`, `max_retries`, `retry_count` which no longer exist on v2 `GraphState`.
3. **EvaluatorAgent v1 GraphState fields** — references `retry_count` which no longer exists on v2 `GraphState`.
4. **MockFileReader missing `peek_metadata`** — abstract method not implemented in the test mock.

These belong to their own Sprint 3 PlannerAgent v2 / Graph v2 / reader tasks.

---

## 11. Interview Explanation

> "DataForge v2 breaks analysis into 13 single-purpose agents. The BusinessObjectiveDetectionAgent is **The Strategist**: its job is to turn a raw dataset into the set of *analytical questions* that are actually answerable. That's the key word — *answerable*. A user might hand us a vague goal, but the columns are the ground truth of what we can compute, so we derive objectives from the data.
>
> We keep objectives separate from KPIs and insights because they're different phases of reasoning: an objective is a *question*, a KPI is a *number with a trend*, and an insight is a *conclusion with evidence*. Conflating them would make each stage's output ambiguous to downstream agents.
>
> It's **LLM-primary** because an LLM is good at open-ended question synthesis, but it's **not LLM-dependent**: we feed it a tightly bounded context (shape + columns + a few sample rows, never the whole table) and parse a strict JSON contract, with sanitization so a schema-drift response can't corrupt state. If the LLM fails, times out, or returns garbage, we have deterministic, column-aware templates for all ten business domains — so analysis quality degrades gracefully to a 0.7-confidence fallback instead of failing.
>
> It's **Phase 3** because you can't frame questions until you know the schema and the business domain — but you want framing *before* deep profiling so downstream work is focused.
>
> I drove coverage to **100%** on this agent — 65 tests — by testing behavior, not implementation: every LLM failure mode, every domain, the fallback labeling, and the immutability guarantee. The suite caught real defects during review, like a mislabeling bug where a malformed LLM response was silently relabeled as a high-confidence LLM result."

---

## Related Components

- **BusinessDomainDetectionAgent** — supplies `business_domain` upstream.
- **KPIDiscoveryAgent** — turns the detected objectives into computable metrics downstream.
- **InsightGenerationAgent** — turns metrics into findings with recommendations.
- **[Architecture Decision Record: ADR-012](../adr/012-business-objective-detection-agent.md)**
