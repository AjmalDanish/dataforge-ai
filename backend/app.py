"""DataForge AI backend — FastAPI serving the LangGraph engine.

Endpoints (see /docs for the OpenAPI schema):

    POST   /api/analyze                 upload a dataset, start a run
    GET    /api/status/{run_id}         progress (phase, completed agents, events)
    GET    /api/results/{run_id}        KPIs, insights, narrative, report links
    GET    /api/download/{run_id}/{fmt} report as html | json | pdf
    GET    /api/runs/{run_id}/files/... report assets (charts, plotly.min.js)
    GET    /api/history                 recent runs
    DELETE /api/runs/{run_id}           delete a run (admin token if configured)
    WS     /ws/{run_id}                 live per-agent events

Runs execute in a worker thread (the agents are CPU-bound pandas code), so the
event loop stays free to serve polling and WebSocket traffic. Run metadata is
kept in memory and mirrored to ``<OUTPUT_DIR>/<run_id>/run.json`` so history
survives restarts.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))  # make the `dataforge` package importable
load_dotenv(BASE_DIR.parent / ".env")  # repo-root .env, if present (real env vars win)

from dataforge import __version__ as APP_VERSION  # noqa: E402
from dataforge.core.state import GraphState  # noqa: E402
from dataforge.graph.workflow import run_workflow  # noqa: E402
from dataforge.infrastructure.llm_providers import llm_from_env  # noqa: E402

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_CONCURRENT_RUNS = int(os.getenv("MAX_CONCURRENT_RUNS", "2"))
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet", ".pq", ".json"}
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("FRONTEND_URL", "*").split(",") if o.strip()]
ADMIN_TOKEN = os.getenv("DATAFORGE_ADMIN_TOKEN", "").strip()

UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))).resolve()
OUTPUT_ROOT = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs"))).resolve()

RUN_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
REPORT_FILES = {"html": "report.html", "json": "report.json", "pdf": "report.pdf"}
MEDIA_TYPES = {"html": "text/html", "json": "application/json", "pdf": "application/pdf"}
# Fields persisted to run.json and returned by /api/status.
PUBLIC_FIELDS = (
    "run_id",
    "filename",
    "format",
    "size_bytes",
    "status",
    "current_phase",
    "steps_completed",
    "steps_skipped",
    "business_domain",
    "created_at",
    "started_at",
    "finished_at",
    "duration_s",
    "error",
    "llm",
)

RUNS: dict[str, dict[str, Any]] = {}
WS_CONNECTIONS: dict[str, list[WebSocket]] = {}
RUNS_LOCK = asyncio.Lock()
RUN_SLOTS = asyncio.Semaphore(MAX_CONCURRENT_RUNS)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error(status: int, kind: str, title: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"type": kind, "title": title, "detail": detail})


def _check_run_id(run_id: str) -> str:
    # Run ids become path segments; only accept our own UUID4 format.
    if not RUN_ID_RE.match(run_id):
        raise _error(404, "not_found", "Run not found", f"No run {run_id}")
    return run_id


def _persist(rec: dict[str, Any]) -> None:
    out = OUTPUT_ROOT / rec["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    payload = {k: rec.get(k) for k in PUBLIC_FIELDS}
    (out / "run.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _load_runs_from_disk() -> None:
    """Rehydrate run metadata after a restart; interrupted runs become failed."""
    for path in OUTPUT_ROOT.glob("*/run.json"):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not RUN_ID_RE.match(str(rec.get("run_id", ""))):
            continue
        if rec.get("status") in ("queued", "running"):
            rec.update(status="failed", error="Server restarted before the run finished")
        rec["events"] = []
        RUNS[rec["run_id"]] = rec


@asynccontextmanager
async def lifespan(_: FastAPI):
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _load_runs_from_disk()
    yield


app = FastAPI(
    title="DataForge AI API",
    version=APP_VERSION,
    description="Autonomous BI engine — 13 LangGraph agents behind a REST + WebSocket API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)


async def _get_run(run_id: str) -> dict[str, Any]:
    _check_run_id(run_id)
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
    if rec is None:
        raise _error(404, "not_found", "Run not found", f"No run {run_id}")
    return rec


async def _broadcast(run_id: str, payload: dict[str, Any]) -> None:
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
        if rec is not None:
            rec["events"].append(payload)
            if payload.get("type") == "agent":
                rec["current_phase"] = payload.get("phase", rec["current_phase"])
                if payload.get("success"):
                    rec["steps_completed"].append(payload["agent"])
    for ws in list(WS_CONNECTIONS.get(run_id, [])):
        try:
            await ws.send_json(payload)
        except Exception:
            conns = WS_CONNECTIONS.get(run_id, [])
            if ws in conns:
                conns.remove(ws)


def _snapshot(final: GraphState, duration_s: float) -> dict[str, Any]:
    """JSON-safe results payload written to results.json."""
    report = final.get("report") or {}
    return {
        "business_domain": str(final.get("business_domain") or "general"),
        "domain_confidence": final.get("business_domain_confidence"),
        "discovered_kpis": final.get("discovered_kpis") or [],
        "business_insights": final.get("business_insights") or [],
        "executive_narrative": final.get("executive_narrative"),
        "business_objectives": final.get("business_objectives") or [],
        "evaluation": final.get("evaluation"),
        "dashboard": final.get("dashboard") or {},
        "steps_completed": [s for s in final.steps_completed if s != "PlannerAgent"],
        "steps_skipped": list(final.steps_skipped),
        "quality_warnings": list(final.quality_warnings),
        "pdf_available": bool(report.get("pdf_available")),
        "duration_s": duration_s,
    }


async def _run_analysis(run_id: str, upload_path: Path, output_dir: Path) -> None:
    loop = asyncio.get_running_loop()

    async def on_event(event: dict[str, Any]) -> None:
        # Called inside the worker thread's loop; hop back to the server loop.
        asyncio.run_coroutine_threadsafe(_broadcast(run_id, {**event, "ts": _now_iso()}), loop)

    async with RUN_SLOTS:
        started = datetime.now(timezone.utc)
        async with RUNS_LOCK:
            rec = RUNS[run_id]
            rec.update(status="running", started_at=started.isoformat())
        await _broadcast(run_id, {"type": "status", "status": "running", "ts": _now_iso()})

        try:
            llm = llm_from_env()
            async with RUNS_LOCK:
                rec["llm"] = f"{llm.provider_name}/{llm.config.model}" if llm else None
            state = GraphState(
                input_dataset_path=str(upload_path),
                output_dir=str(output_dir),
                execution_id=run_id,
            )
            final = await asyncio.to_thread(
                asyncio.run, run_workflow(state, llm_provider=llm, on_event=on_event)
            )
            duration_s = (datetime.now(timezone.utc) - started).total_seconds()
            snapshot = _snapshot(final, duration_s)
            (output_dir / "results.json").write_text(
                json.dumps(snapshot, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
            )
            done = "ReportingAgent" in snapshot["steps_completed"]
            async with RUNS_LOCK:
                rec.update(
                    status="done" if done else "failed",
                    error=None if done else "Analysis ended before a report was produced",
                    finished_at=_now_iso(),
                    duration_s=duration_s,
                    current_phase=final.current_phase,
                    steps_completed=snapshot["steps_completed"],
                    steps_skipped=snapshot["steps_skipped"],
                    business_domain=snapshot["business_domain"],
                )
            await _broadcast(
                run_id, {"type": "done" if done else "error", "status": rec["status"], "error": rec["error"], "duration_s": duration_s, "ts": _now_iso()}
            )
        except Exception as e:
            async with RUNS_LOCK:
                rec.update(
                    status="failed",
                    error=f"{type(e).__name__}: {e}",
                    finished_at=_now_iso(),
                    duration_s=(datetime.now(timezone.utc) - started).total_seconds(),
                )
            await _broadcast(run_id, {"type": "error", "status": "failed", "error": rec["error"], "ts": _now_iso()})
        finally:
            async with RUNS_LOCK:
                _persist(rec)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"status": "ok", "service": "dataforge-api", "version": APP_VERSION, "llm": llm_from_env() is not None}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "dataforge-api", "version": APP_VERSION, "docs": "/docs"}


@app.post("/api/analyze", status_code=201)
async def analyze(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = Path(file.filename or "upload.csv").name
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise _error(
            400, "unsupported_format", "Unsupported file format",
            f"Extension {ext or '(none)'} not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    run_id = str(uuid.uuid4())
    upload_dir = UPLOAD_ROOT / run_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / filename
    size = 0
    with upload_path.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE_BYTES:
                out.close()
                shutil.rmtree(upload_dir, ignore_errors=True)
                raise _error(413, "file_too_large", "File too large", f"Limit is {MAX_FILE_SIZE_MB} MB")
            out.write(chunk)
    if size == 0:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise _error(400, "empty_file", "Empty file", "The uploaded file is empty")

    output_dir = OUTPUT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {
        "run_id": run_id,
        "filename": filename,
        "format": ext.lstrip("."),
        "size_bytes": size,
        "status": "queued",
        "current_phase": 1,
        "steps_completed": [],
        "steps_skipped": [],
        "business_domain": None,
        "created_at": _now_iso(),
        "started_at": None,
        "finished_at": None,
        "duration_s": None,
        "error": None,
        "llm": None,
        "events": [],
    }
    async with RUNS_LOCK:
        RUNS[run_id] = rec
        _persist(rec)
    asyncio.create_task(_run_analysis(run_id, upload_path, output_dir))
    return {
        "run_id": run_id,
        "status": "queued",
        "status_url": f"/api/status/{run_id}",
        "results_url": f"/api/results/{run_id}",
        "ws_url": f"/ws/{run_id}",
    }


@app.get("/api/status/{run_id}")
async def get_status(run_id: str) -> dict[str, Any]:
    rec = await _get_run(run_id)
    async with RUNS_LOCK:
        payload = {k: rec.get(k) for k in PUBLIC_FIELDS}
        payload["events"] = rec["events"][-50:]
    return payload


@app.get("/api/results/{run_id}")
async def get_results(run_id: str) -> dict[str, Any]:
    rec = await _get_run(run_id)
    if rec["status"] in ("queued", "running"):
        return {"run_id": run_id, "status": rec["status"], "message": "Results not ready — poll /api/status"}
    if rec["status"] == "failed":
        return {"run_id": run_id, "status": "failed", "error": rec.get("error"), "finished_at": rec.get("finished_at")}

    output_dir = OUTPUT_ROOT / run_id
    try:
        snapshot = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        snapshot = {}
    reports = {
        fmt: f"/api/download/{run_id}/{fmt}" if (output_dir / name).exists() else None
        for fmt, name in REPORT_FILES.items()
    }
    viz_dir = output_dir / "visualizations"
    charts = sorted(p.name for p in viz_dir.glob("*.html")) if viz_dir.exists() else []
    kpis = snapshot.get("discovered_kpis") or []
    insights = snapshot.get("business_insights") or []
    return {
        "run_id": run_id,
        "status": "done",
        "filename": rec.get("filename"),
        "business_domain": snapshot.get("business_domain") or rec.get("business_domain"),
        "domain_confidence": snapshot.get("domain_confidence"),
        "duration_s": rec.get("duration_s"),
        "finished_at": rec.get("finished_at"),
        "llm": rec.get("llm"),
        "kpis": kpis,
        "insights": insights,
        "narrative": snapshot.get("executive_narrative"),
        "objectives": snapshot.get("business_objectives") or [],
        "evaluation": snapshot.get("evaluation"),
        "dashboard": snapshot.get("dashboard") or {},
        "report_urls": reports,
        "report_view_url": f"/api/runs/{run_id}/files/report.html" if reports["html"] else None,
        "charts": [{"name": c, "url": f"/api/runs/{run_id}/files/visualizations/{c}"} for c in charts],
        "counts": {"kpis": len(kpis), "insights": len(insights), "visualizations": len(charts)},
        "trace": {
            "steps_completed": snapshot.get("steps_completed") or rec.get("steps_completed", []),
            "steps_skipped": snapshot.get("steps_skipped") or [],
            "events": rec.get("events", [])[-100:],
        },
    }


@app.get("/api/download/{run_id}/{fmt}")
async def download(run_id: str, fmt: str) -> FileResponse:
    if fmt not in REPORT_FILES:
        raise _error(400, "bad_format", "Bad format", "fmt must be html, json, or pdf")
    rec = await _get_run(run_id)
    if rec["status"] != "done":
        raise _error(409, "not_ready", "Not ready", "Run not done yet")
    path = OUTPUT_ROOT / run_id / REPORT_FILES[fmt]
    if not path.exists():
        raise _error(404, "artifact_missing", "Artifact not found", f"{fmt} report not generated")
    return FileResponse(str(path), media_type=MEDIA_TYPES[fmt], filename=f"dataforge-{run_id}.{fmt}")


@app.get("/api/runs/{run_id}/files/{file_path:path}")
async def run_file(run_id: str, file_path: str) -> FileResponse:
    """Serve a report asset so report.html's relative chart links work."""
    await _get_run(run_id)
    root = (OUTPUT_ROOT / run_id).resolve()
    target = (root / file_path).resolve()
    allowed = target.suffix in (".html", ".js", ".json", ".pdf", ".png")
    if not allowed or not target.is_relative_to(root) or not target.is_file():
        raise _error(404, "artifact_missing", "Artifact not found", file_path)
    return FileResponse(str(target))


@app.get("/api/history")
async def history(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    async with RUNS_LOCK:
        items = sorted(RUNS.values(), key=lambda r: r.get("created_at") or "", reverse=True)[:limit]
        runs = [{k: r.get(k) for k in PUBLIC_FIELDS} for r in items]
    return {"runs": runs, "count": len(runs)}


@app.websocket("/ws/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    async with RUNS_LOCK:
        rec = RUNS.get(run_id) if RUN_ID_RE.match(run_id) else None
        backlog = list(rec["events"]) if rec else []
    if rec is None:
        await websocket.send_json({"type": "error", "detail": "Run not found", "run_id": run_id})
        await websocket.close()
        return
    for event in backlog:
        await websocket.send_json(event)
    WS_CONNECTIONS.setdefault(run_id, []).append(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping", "ts": _now_iso()})
    except WebSocketDisconnect:
        pass
    finally:
        conns = WS_CONNECTIONS.get(run_id, [])
        if websocket in conns:
            conns.remove(websocket)


@app.delete("/api/runs/{run_id}")
async def delete_run(run_id: str, x_admin_token: str | None = Header(default=None)) -> dict[str, str]:
    if ADMIN_TOKEN and x_admin_token != ADMIN_TOKEN:
        raise _error(403, "forbidden", "Forbidden", "A valid X-Admin-Token header is required")
    rec = await _get_run(run_id)
    if rec["status"] in ("queued", "running"):
        raise _error(409, "running", "Run in progress", "Wait for the run to finish before deleting it")
    async with RUNS_LOCK:
        RUNS.pop(run_id, None)
    shutil.rmtree(UPLOAD_ROOT / run_id, ignore_errors=True)
    shutil.rmtree(OUTPUT_ROOT / run_id, ignore_errors=True)
    WS_CONNECTIONS.pop(run_id, None)
    return {"status": "deleted", "run_id": run_id}
