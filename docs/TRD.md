# DataForge AI v2.0 — Technical Requirement Document (TRD)

> Companion to `docs/PRD.md`. Engine: `dataforge/` (LangGraph). Serving: `backend/` (FastAPI on HF Spaces). UI: `frontend/` (Next.js on Netlify). DB: Postgres (Neon/Supabase) via SQLAlchemy+Alembic.

## 1. Architecture
```
[Next.js/Tailwind @ Netlify] --HTTPS--> [FastAPI @ HF Spaces] --invoke--> [LangGraph 13 agents]
        |                                      |                              |
  upload/status/WS/graph                 SessionManager                  GraphState v2
  NEXT_PUBLIC_API_URL                    EventBus (WS fan-out)           checkpointer (PostgresSaver)
        |                                      |                              |
        +-------------- Postgres (runs, events, kpis, insights, reports) <----+
```
CLI (`dataforge/presentation/cli.py`, `run.py`, `execute.py`) stays as local runner; API reuses same `create_graph()`.

## 2. API contracts (`backend/`)
- `POST /api/analyze` multipart(file, domain_hint?) → `201 {run_id, status_url, ws_url}`. Validates ext/size, stores file, creates `runs` row (queued), enqueues background task.
- `GET /api/status/{run_id}` → `{status, phase, steps_completed, steps_skipped, quality_errors}`.
- `GET /api/results/{run_id}` → `{kpis, insights, dashboard, report_urls, trace}`.
- `GET /api/download/{run_id}/{html|pdf|json}` → file stream.
- `WS /ws/{run_id}` → events `{agent, decision, quality_score, ts}` from `application/events.py` EventBus.
- Errors: RFC7807 `{type, title, detail, run_id}`; CORS allowlist = Netlify URL only; body cap 10MB; per-agent `asyncio.wait_for(timeout_seconds)`.

## 3. Engine wiring (remaining work)
- Missing agents: `KPIDiscoveryAgent`, `FeatureEngineeringAgent` (new files), `PlannerAgent` v2 rewrite (phase plan 1-7, quality gates, `global_step_count` loop guard, `asyncio.gather` parallel), Graph v2 (`graph/workflow.py` + `graph/router.py` + `graph/checkpointer.py`, langgraph `^0.0.20 → ^0.2.0`).
- Enhance: `VisualizationAgent` (dashboard+KPI cards via ChartEngine), `ReportingAgent` → ExecutiveReport (Jinja2 + WeasyPrint PDF).
- Done (do not regress): validation, cleaning, schema, domain, objective, profiling (`dataforge/agents/`).

## 4. Config / env
`NEXT_PUBLIC_API_URL`, `DATABASE_URL` (Neon pooled), `LLM_PROVIDER/MODEL`, `OPENAI/ANTHROPIC_API_KEY` (server only), `MAX_FILE_SIZE_MB=100`, `MAX_ROWS=1000000`, `EXECUTION_TIMEOUT=300`. `.env.example` updated; never commit secrets.

## 5. Testing / quality
`pytest` unit per agent (≥85% new code), `tests/integration/test_graph_v2.py`, `test_full_pipeline.py` (5 domains), API tests (httpx), WS test, security tests (traversal, bad ext, oversized). CI: `.github/workflows/ci.yml` (lint ruff/black/isort, mypy, pytest+cov gate).

## 6. Deploy
- Netlify: base `frontend/`, build `npm run build`, publish `.next`, `netlify.toml` redirects + `NEXT_PUBLIC_API_URL`.
- HF Spaces: `backend/` Dockerfile (`uvicorn app:app`), secrets via Space settings, healthcheck `/healthz`.
- DB: Neon project + Alembic migrations run on deploy; local dev uses SQLite file (same SQLAlchemy models).
