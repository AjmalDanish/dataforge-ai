# DataForge AI v2.0 — VISION

> **Subtitle:** Autonomous Business Intelligence Engineer
>
> **Status:** FROZEN after approval — no feature may be added unless it serves this vision.

---

## Mission Statement

Build an AI system that **thinks like a Senior Business Analyst**.

The user uploads a dataset. The system automatically:

1. **Understands** it — schema, semantics, business domain
2. **Cleans** it — with explained, auditable decisions
3. **Profiles** it — deep statistical and semantic profiling
4. **Discovers** — KPIs, patterns, anomalies, business signals
5. **Generates** — executive dashboards, business insights, actionable reports

No manual analysis. No configuration wizards. No prompt engineering.

---

## What This IS

| ✅ This IS | Why |
|---|---|
| Autonomous Business Intelligence Engineer | It does the analyst's job end-to-end |
| Graph-Orchestrated Agent System | True DAG with conditional routing, not a pipeline |
| Business Domain-Aware System | It detects retail vs. finance vs. healthcare, etc. |
| Executive-Grade Report Generator | Output looks like it came from McKinsey, not matplotlib |
| Auditable Decision Engine | Every cleaning decision, every skipped step is logged and explained |

## What This is NOT

| ❌ This is NOT | Why Not |
|---|---|
| AutoML | We don't train models. We discover business intelligence. |
| Dashboard Builder | The dashboard is an output, not the product. |
| BI Tool (Tableau/PowerBI) | No drag-and-drop. No manual configuration. Fully autonomous. |
| Visualization Library | Charts serve insights, not the other way around. |
| Statistical Notebook | No cells. No manual execution. No REPL. |
| Chatbot / Q&A System | We don't answer questions. We answer *every* question, unprompted. |

---

## Core Philosophy

### 1. Business Value Over Technical Novelty
Every feature must answer: *"What should management do?"* — not *"What's the p-value?"*

### 2. Autonomous Over Interactive
The user uploads data and walks away. When they return, the analysis is complete.

### 3. Explainable Over Black-Box
Every decision (cleaning, skipping, retrying) is logged, explained, and auditable.

### 4. Graph Over Pipeline
The execution path is dynamic. Agents are conditionally routed, skipped, or repeated based on data characteristics, not a hardcoded sequence.

### 5. Quality Over Quantity
One brilliant insight is worth more than fifty trivial observations.

### 6. Recruiter-Grade Engineering
Every architectural decision is interview-defensible. The codebase itself is a portfolio piece.

---

## Target Users

### Primary
| User | Need |
|---|---|
| C-Suite Executives | "What's happening in my business?" |
| Business Analysts | "Give me the insights without the SQL" |
| Product Managers | "How are my metrics trending?" |
| Startup Founders | "I have data but no data team" |
| Consultants | "I need a polished analysis in 30 minutes" |

### Secondary
| User | Need |
|---|---|
| Data Scientists | "Automate my initial exploration" |
| Engineering Managers | "Show me the portfolio-quality AI project" |

### Explicitly NOT For
- Real-time streaming analytics
- Production ML model deployment
- Database administration
- Unstructured data (NLP, CV)
- Manual exploratory notebooks

---

## Success Criteria

### Technical
| Metric | Target |
|---|---|
| End-to-end completion rate | ≥ 95% |
| Analysis latency (≤100K rows) | < 90 seconds |
| Cleaning accuracy (vs. manual) | ≥ 85% agreement |
| Domain detection accuracy | ≥ 80% on common domains |
| Test coverage | ≥ 85% |

### Business Value
| Metric | Target |
|---|---|
| Time-to-insight vs. manual analyst | 10x faster |
| Reports requiring zero edits | ≥ 60% |
| KPIs discovered vs. domain expert | ≥ 70% recall |

### Portfolio / Recruiter Impact
| Signal | Evidence |
|---|---|
| Graph Engineering | LangGraph with conditional routing, retry, parallel branches |
| Agent Architecture | 12 specialized agents with clear SRP |
| State Management | Immutable state transitions with full audit trail |
| Clean Architecture | DDD-aligned layers, dependency injection, repository pattern |
| Production Quality | CI/CD, 85%+ coverage, structured logging, error boundaries |

---

## The Autonomous Promise

DataForge AI v2 delivers autonomy through:

1. **Intelligent Planning** — The Planner Agent reasons about what to execute, skip, or repeat
2. **Self-Healing** — Failed agents trigger remediation, not crashes
3. **Domain Awareness** — The system detects whether data is retail, finance, HR, etc.
4. **Business Framing** — Insights are framed in business language, not statistical jargon
5. **Executive Output** — Reports answer "What should management do?" not "Here are some numbers"

---

## Version Scope Boundary

### v2.0 Delivers
- 12 specialized agents (up from 7 in v1)
- Business domain detection
- Business objective detection
- KPI discovery
- Data cleaning with audit trail
- Feature engineering
- Executive dashboards (HTML, interactive)
- Executive reports (HTML, PDF, JSON)
- Graph visualization (workflow status UI)
- CSV, Excel, Parquet, JSON input support
- FastAPI + Web UI

### v2.0 Does NOT Deliver
- Database connectors (PostgreSQL, MySQL, SQLite → v2.5)
- Multi-user / auth (→ v3.0)
- Real-time streaming (→ v3.0)
- Custom agent plugins (→ v2.5)
- ML model training (→ v3.0)
- Natural language Q&A (→ v3.0)

---

## The Constitution Rule

After this architecture is approved:

> **The architecture is FROZEN.**
>
> No feature may be added unless it supports the original vision.
>
> Every proposed change must be evaluated against this document.
>
> If it doesn't serve the mission, it doesn't ship.

---

*"The goal is not to build a tool. The goal is to build an intelligence that makes tools unnecessary."*
