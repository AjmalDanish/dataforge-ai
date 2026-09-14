# DataForge AI v2.0 — Product Requirement Document (PRD)

> Status: Draft v1 | Owner: AjmalDanish | Target role: Data Scientist / ML
> Stack lock: Next.js+Tailwind (Netlify) + FastAPI (HuggingFace Spaces) + Postgres (Neon/Supabase)
> Source vision: `docs/v2/VISION.md` — autonomous BI engineer, not AutoML, not a chatbot.

## 1. Problem
Small teams have CSV/Excel/Parquet/JSON data but no analyst. Manual exploration takes hours and reports look amateur. DataForge AI uploads a file and returns an executive-grade dashboard + report with zero configuration.

## 2. Users
| User | Need | Priority |
|---|---|---|
| Founder / PM (primary) | "What's happening in my data, what should I do?" | P0 |
| Recruiter / hiring manager | Live demo + clean code proving DS/ML + AI engineering skill | P0 |
| Analyst (secondary) | Auditable cleaning log, stats appendix, downloadable artifacts | P1 |

## 3. Goals / Non-goals
Goals: 13-agent autonomous analysis; KPI discovery per business domain; ranked business insights with confidence; interactive dashboard + HTML/PDF/JSON reports; run history with shareable links; live progress over WebSocket.
Non-goals (v2.0): model training, streaming data, multi-user auth/teams, DB connectors, NL chat Q&A. These are v2.5/v3.0.

## 4. User stories (MVP must)
1. Upload CSV/XLSX/Parquet/JSON (≤100MB, ≤1M rows) via drag-drop, get validation feedback in <5s.
2. Watch live agent graph (13 nodes, status badges) via WebSocket while analysis runs.
3. View KPI cards + trend chart + distributions + heatmap dashboard.
4. Read Top/Bottom performers, trends, anomalies, risks, recommendations with confidence scores.
5. Download HTML/PDF/JSON report; open past runs from history; share read-only link.
6. Every cleaning decision is listed with rationale; skipped agents are explained.

## 5. Functional requirements
- FR1 File intake: format detection, encoding fallback (utf-8→latin-1→cp1252), size/row/column enforcement, `ValidationReport` + `FileMetadata`.
- FR2 Cleaning: missing/duplicates/type/invalid-date/currency/column-normalize fixes, `cleaning_report` + per-decision log, original never mutated.
- FR3 Understanding: schema (semantic types, keys, relations), domain (10 domains + general fallback), objectives/questions.
- FR4 Analysis: profile, engineered features, domain KPIs with values+trends, stats (descriptive, Pearson+Spearman+p-values, outliers IQR+Z, normality guard n≥8, group tests).
- FR5 Synthesis: categorized insights (top/bottom, trend, anomaly, risk, opportunity, correlation, recommendation), ranked by impact, LLM-written with rule fallback.
- FR6 Output: dashboard (KPI row + trend + grid + heatmap), reports HTML+PDF+JSON + execution trace.
- FR7 Platform: async runs, status polling + WebSocket events, history list/detail, download endpoints, share tokens.

## 6. NFRs
- Analysis ≤90s for ≤100K rows; end-to-end completion ≥95%; domain accuracy ≥80% common domains.
- Test coverage ≥85%; no `Any`-leak in new contracts; mypy clean on `dataforge/db`, `backend/`.
- Free-tier deployable: Netlify static + HF Spaces CPU + Neon free Postgres; cold-start message on UI.
- Security: path traversal blocked, upload allowlist, API key via env only, PII never logged, 10MB JSON body cap.

## 7. Success metrics
Recruiter opens Netlify URL → uploads `datasets/employees.csv` → sees live graph → gets report in <2min. 5 domain galleries committed. v2.0.0 tagged with release notes.

## 8. Milestones
M1 Docs (PRD→TRD→UI/UX→DB) → M2 DB+API skeleton → M3 agents close-out → M4 reports → M5 web → M6 hardening/release.
