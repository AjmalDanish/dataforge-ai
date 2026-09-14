# DataForge AI v2.0 — Database Design (Postgres via Neon/Supabase)

> SQLAlchemy 2.0 models in `dataforge/db/` (shared by CLI + API), Alembic migrations in `backend/alembic/`. Local dev: SQLite file. Prod: Neon pooled `DATABASE_URL`.

## 1. Tables
- `datasets(id UUID PK, filename, format, size_bytes, rows, cols, sha256, storage_path, created_at)` — dedupe by sha256.
- `runs(id UUID PK, dataset_id FK, business_domain, domain_confidence, status[queued|running|failed|done], current_phase INT 1-7, steps_completed JSONB, steps_skipped JSONB, quality_warnings JSONB, quality_errors JSONB, started_at, finished_at, duration_s, report_html_url, report_pdf_url, share_token NULL)`.
- `agent_events(id BIGSERIAL PK, run_id FK, agent, decision, quality_score FLOAT, duration_s, message, metadata JSONB, created_at)` — one row per `add_agent_result`; powers WS replay + history.
- `kpis(id BIGSERIAL PK, run_id FK, name, abbreviation, formula, value FLOAT, trend, benchmark_context, interpretation)`.
- `insights(id BIGSERIAL PK, run_id FK, category, title, summary, supporting_data JSONB, severity, business_action, confidence FLOAT, rank INT)`.
- `cleaning_decisions(id BIGSERIAL PK, run_id FK, issue, action, rationale, rows_affected INT)`.
- `checkpoints(run_id FK UNIQUE, state_json JSONB, parquet_refs JSONB, updated_at)` — LangGraph `PostgresSaver` backing (crash resume).

## 2. Conventions
UUID PKs for shareable ids; `created_at TIMESTAMPTZ DEFAULT now()`; JSONB for agent payloads (queryable); indexes on `runs(status, created_at)`, `agent_events(run_id, created_at)`, `insights(run_id, rank)`. Share links = `share_token` (secrets.token_urlsafe 32), nullable until user shares.

## 3. Migrations / ops
Alembic autogenerate reviewed by hand; `alembic upgrade head` runs in HF Spaces startup; Neon branching for PR previews; nightly `VACUUM ANALYZE` not needed at this scale. Retention: raw uploads 30d, reports indefinite (free-tier caps monitored).

## 4. Limits / safety
Enforced in `DataValidationAgent` before insert: ext allowlist, ≤100MB, ≤1M rows, ≤1000 cols. PII: never store file bytes in DB (path refs only); logs redact cell values (aggregates only).
