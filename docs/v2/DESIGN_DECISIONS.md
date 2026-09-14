# DataForge AI v2.0 — DESIGN DECISIONS

> Every Decision Challenged — Every Choice Defended

---

## DD-1: Why 13 Agents, Not 16?

**Proposed:** 16 agents (including Evaluator, Visualization Planner, Memory/Audit)
**Decided:** 13 agents (1 Planner + 12 Specialized)

### Agents Removed/Merged

| Agent | Decision | Rationale |
|---|---|---|
| **EvaluatorAgent** | **Merged into Planner** | In v1, the Evaluator ran once after Visualization. This is the wrong granularity. Quality validation should happen after *every* agent, not just one. The Planner already runs after every agent — adding quality gates to the Planner eliminates a redundant node and makes quality pervasive. |
| **Visualization Planning Agent** | **Merged into VisualizationAgent** | Separating chart selection from chart generation adds a full graph cycle (Planner → VizPlanner → Planner → VizGenerator) with no proportional value. The VisualizationAgent can select and generate in one step. |
| **Memory / Audit Agent** | **Removed entirely** | Audit logging is a cross-cutting concern, not an agent's job. `GraphState` tracks agent_history, logs, and metrics. `BaseAgent.execute_with_logging()` handles per-agent audit. Making this an agent would mean it runs at a specific point in the graph — but audit must happen at every point. |

### Why Not Fewer?
- Merging Schema + Domain + Objective into one "Understanding Agent" would violate SRP and create a god-agent
- Merging Cleaning + Validation would make error handling ambiguous (is it a file problem or a data quality problem?)
- Each agent is independently testable, replaceable, and skippable

---

## DD-2: Why Hub-and-Spoke Topology?

**Alternative A:** Linear pipeline (v1 approach — each agent knows its successor)
**Alternative B:** Direct agent-to-agent edges (Schema → Domain → Objective)
**Alternative C:** Hub-and-spoke (all agents return to Planner)

**Decided: C — Hub-and-Spoke**

| Criteria | Linear (A) | Direct Edges (B) | Hub-and-Spoke (C) |
|---|---|---|---|
| Dynamic routing | ❌ Hardcoded | ⚠️ Partially | ✅ Fully dynamic |
| Skip logic | ❌ Each agent checks | ⚠️ Edge conditions | ✅ Planner decides |
| Retry logic | ❌ Distributed | ⚠️ Distributed | ✅ Centralized |
| Agent coupling | 🟡 Each knows next | 🔴 Tight coupling | ✅ Zero coupling |
| Observability | ⚠️ Scattered | ⚠️ Complex | ✅ Single decision point |
| Complexity | ✅ Simple | 🔴 Complex | 🟡 Moderate |
| Scalability | ❌ Hard to add agents | ⚠️ Edge explosion | ✅ Add node + Planner rule |

**Trade-off accepted:** Hub-and-spoke adds ~12 extra Planner invocations per run (one per agent). At <10ms per Planner decision, this adds <120ms total overhead. Acceptable.

---

## DD-3: Why LLM-Assisted, Not LLM-Dependent?

**Alternative A:** Pure LLM (send data to LLM, ask for everything)
**Alternative B:** Pure rules (no LLM at all)
**Alternative C:** LLM-assisted with rule-based fallback

**Decided: C — LLM-Assisted**

| Agent | LLM Usage | Fallback |
|---|---|---|
| DataValidationAgent | None | Fully rule-based |
| DataCleaningAgent | Optional (explain decisions) | Rule-based cleaning |
| SchemaDetectionAgent | Optional (semantic types) | Heuristic type detection |
| BusinessDomainDetectionAgent | Primary | Keyword matching dictionaries |
| BusinessObjectiveDetectionAgent | Primary | Domain-specific question templates |
| ProfilingAgent | None | Fully rule-based (Pandas/NumPy) |
| FeatureEngineeringAgent | Optional | Template-based feature generation |
| KPIDiscoveryAgent | Primary | Domain-specific KPI templates |
| StatisticalAnalysisAgent | None | Fully rule-based (SciPy) |
| InsightGenerationAgent | Primary | Template-based insight generation |
| VisualizationAgent | Optional (chart selection) | Rule-based chart type mapping |
| ExecutiveReportAgent | Primary (executive summary) | Template-based summary |

**Rule:** The system MUST produce useful output even with `OPENAI_API_KEY=""`. LLM makes it better, not possible.

---

## DD-4: Why Immutable State?

**Alternative A:** Mutable state (agents modify GraphState in place)
**Alternative B:** Immutable state (agents return new state via model_copy)

**Decided: B — Immutable**

**Rationale:**
1. **Auditability:** Every state transition is a new snapshot. You can replay the full history.
2. **Debuggability:** If agent N produces wrong output, compare state[N-1] vs state[N].
3. **Concurrency safety:** Parallel agents can't corrupt shared mutable state.
4. **LangGraph alignment:** LangGraph's StateGraph expects state update dicts, not mutations.

**Trade-off accepted:** Memory usage is higher (each state is a new object). Mitigated by Python's copy-on-write semantics for large objects and by DataFrames being referenced, not deep-copied.

---

## DD-5: Why FastAPI Over Flask/Django?

**Decided: FastAPI**

| Criteria | Flask | Django | FastAPI |
|---|---|---|---|
| Async support | ❌ WSGI | ⚠️ ASGI optional | ✅ ASGI native |
| WebSocket | ⚠️ Flask-SocketIO | ⚠️ Django Channels | ✅ Built-in |
| OpenAPI docs | ❌ Manual | ❌ Manual | ✅ Auto-generated |
| Request validation | ❌ Manual | ⚠️ Django Forms | ✅ Pydantic native |
| Learning curve | ✅ Simple | 🔴 Heavy | ✅ Simple |
| Weight | ✅ Light | 🔴 Heavy (ORM, admin, etc.) | ✅ Light |

**Critical factor:** Our agent pipeline is async. FastAPI is async-native. Flask would require an event loop workaround.

---

## DD-6: Why Jinja2 for Reports, Not f-strings?

**v1 Problem:** Report HTML is generated by string concatenation in Python — 400+ lines of `html.append(f"<div>...")`. This is:
- Untestable (can't test template independently)
- Unmaintainable (HTML mixed with Python logic)
- Unstyled (CSS is embedded in Python strings)

**v2 Decision:** Jinja2 templates

**Benefits:**
- Designers can edit `report.html.jinja2` without touching Python
- CSS is in proper CSS files
- Template inheritance for consistent layout
- Conditional sections (show stats only if available)
- Testable (render template with mock data)

---

## DD-7: Why Not React/Vue for the Web UI?

**Decided: Vanilla HTML + CSS + JavaScript**

**Rationale:**
The Web UI has exactly three screens:
1. Upload page (file picker + drag-and-drop)
2. Graph visualization (SVG nodes + WebSocket updates)
3. Results page (report viewer + download links)

This does NOT need:
- Virtual DOM
- Component lifecycle management
- NPM build tools
- 500KB of JavaScript framework

**What it DOES need:**
- WebSocket client (native browser API)
- SVG manipulation (native browser API)
- Fetch API for uploads (native browser API)

**Trade-off:** If v3 adds multi-user dashboards, collaborative editing, or complex state management, a framework becomes justified. For v2, vanilla JS is correct.

---

## DD-8: Why Remove the v1 Evaluator Agent?

**v1 Pattern:**
```
Ingestion → Profiling → Statistics → Visualization → Evaluator → Reporting
```

**Problem:** The Evaluator only runs once, late in the pipeline. By the time it detects "no insights generated," the workflow has already wasted time on visualization.

**v2 Pattern:**
```
Every agent → Planner (with built-in quality gate) → Next agent or retry
```

**Benefits:**
- Quality checks happen after **every** agent, not just one
- Early detection: if Cleaning fails, we catch it immediately
- No wasted computation on downstream agents
- Planner has full context for remediation decisions

---

## DD-9: Why Phase-Based Execution, Not Free-Form?

**Alternative A:** Free-form — Planner decides completely dynamically (any agent at any time)
**Alternative B:** Phase-based — agents are grouped into ordered phases, but routing within phases is dynamic

**Decided: B — Phase-Based**

**Rationale:**
- Free-form creates a debugging nightmare: "Why did it run Statistics before Cleaning?"
- Phases provide guarantees: "Cleaning always happens before Statistics"
- Within phases, order can be dynamic (e.g., Domain and Objective can run in any order)
- Phase-based is more predictable for users watching the graph visualization

**Phases:**
1. Data Intake → 2. Data Preparation → 3. Data Understanding → 4. Deep Analysis → 5. Statistical Analysis → 6. Synthesis → 7. Output

**Constraint:** The Planner can move backward one phase (e.g., re-clean after domain detection reveals something) but never more than one. This prevents infinite phase regression.

---

## DD-10: Why Not Separate Planning and Execution Steps?

**Alternative:** Plan the entire execution upfront, then execute it linearly.

**Decided: Interleaved planning and execution**

**Rationale:**
- The optimal plan depends on data characteristics discovered during execution
- Example: "Should we run Feature Engineering?" depends on domain detection results, which aren't available at planning time
- Interleaved planning allows the system to adapt as it learns about the data
- This is how a real Senior Business Analyst works: discover, adapt, iterate

---

## Decision Summary

| # | Decision | Key Trade-off |
|---|---|---|
| DD-1 | 13 agents (not 16) | Less modularity for 3 removed agents, but eliminates redundancy |
| DD-2 | Hub-and-spoke topology | ~120ms routing overhead, but fully dynamic and zero agent coupling |
| DD-3 | LLM-assisted, not LLM-dependent | Two code paths to maintain, but system works without API keys |
| DD-4 | Immutable state | Higher memory usage, but full auditability and concurrency safety |
| DD-5 | FastAPI | Tied to Python async, but perfect fit for our async agents |
| DD-6 | Jinja2 templates | Extra dependency, but proper separation of concerns |
| DD-7 | Vanilla JS UI | No framework ecosystem, but minimal complexity for minimal UI |
| DD-8 | No separate Evaluator | Quality logic in Planner, but more Planner complexity |
| DD-9 | Phase-based execution | Less flexibility than free-form, but predictable and debuggable |
| DD-10 | Interleaved planning | Plan may change mid-execution, but adapts to discovered data characteristics |
