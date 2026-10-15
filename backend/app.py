"""DataForge AI backend — FastAPI serving the LangGraph engine.

Endpoints (see /docs for the OpenAPI schema):

    POST   /api/analyze                       upload a dataset (sign-in required)
    POST   /api/samples/{name}                analyze a bundled sample (anonymous OK)
    GET    /api/status/{run_id}               progress (phase, completed agents, events)
    GET    /api/results/{run_id}              KPIs, insights, narrative, report links
    GET    /api/download/{run_id}/{fmt}?t=    report as html | json | pdf
    GET    /api/runs/{run_id}/{t}/files/...   report assets (charts, plotly.min.js)
    GET    /api/history                       the signed-in user's runs
    DELETE /api/runs/{run_id}                 delete a run (owner or admin token)
    WS     /ws/{run_id}?t=                    live per-agent events

Access control (see security.py): a run is readable by its owner (Clerk
session token) or by anyone holding its share token ``t``. Analyses are rate
limited per user, and anonymous sample runs per client IP.

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

from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
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
from security import (  # noqa: E402
    RateLimiter,
    User,
    auth_mode,
    can_read,
    client_ip,
    limit_from_env,
    new_share_token,
    optional_user,
    require_user,
)

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_CONCURRENT_RUNS = int(os.getenv("MAX_CONCURRENT_RUNS", "2"))
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet", ".pq", ".json"}
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("FRONTEND_URL", "*").split(",") if o.strip()]
ADMIN_TOKEN = os.getenv("DATAFORGE_ADMIN_TOKEN", "").strip()

UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))).resolve()
OUTPUT_ROOT = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs"))).resolve()
SAMPLES_DIR = Path(os.getenv("SAMPLES_DIR", str(BASE_DIR.parent / "datasets"))).resolve()
SAMPLE_FILES = ("employees.csv", "products.csv")
USER_RUNS_PER_HOUR = limit_from_env("USER_RUNS_PER_HOUR", 10)
ANON_RUNS_PER_HOUR = limit_from_env("ANON_RUNS_PER_HOUR", 5)
LIMITER = RateLimiter()

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
# Also persisted, never listed publicly: who owns the run and its share token.
PERSISTED_FIELDS = PUBLIC_FIELDS + ("owner", "share_token")

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
    payload = {k: rec.get(k) for k in PERSISTED_FIELDS}
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
        if not rec.get("share_token"):
            continue  # pre-auth run with no access control; never expose it
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


async def _readable_run(run_id: str, user: User | None, token: str | None) -> dict[str, Any]:
    """The run if the caller may read it; 404 otherwise (don't reveal it exists)."""
    rec = await _get_run(run_id)
    if not can_read(rec, user, token):
        raise _error(404, "not_found", "Run not found", f"No run {run_id}")
    return rec


def _links(rec: dict[str, Any]) -> dict[str, str]:
    run_id, token = rec["run_id"], rec["share_token"]
    return {
        "run_page": f"/runs/{run_id}?t={token}",
        "files": f"/api/runs/{run_id}/{token}/files",
        "ws": f"/ws/{run_id}?t={token}",
    }


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
    return {
        "status": "ok",
        "service": "dataforge-api",
        "version": APP_VERSION,
        "llm": llm_from_env() is not None,
        "auth": auth_mode(),
    }


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "dataforge-api", "version": APP_VERSION, "docs": "/docs"}


async def _start_run(
    run_id: str, filename: str, ext: str, size: int, upload_path: Path, owner: str | None
) -> dict[str, Any]:
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
        "owner": owner,
        "share_token": new_share_token(),
        "events": [],
    }
    async with RUNS_LOCK:
        RUNS[run_id] = rec
        _persist(rec)
    asyncio.create_task(_run_analysis(run_id, upload_path, output_dir))
    return {
        "run_id": run_id,
        "status": "queued",
        "share_token": rec["share_token"],
        "status_url": f"/api/status/{run_id}",
        "results_url": f"/api/results/{run_id}",
        **_links(rec),
    }


@app.post("/api/analyze", status_code=201)
async def analyze(file: UploadFile = File(...), user: User = Depends(require_user)) -> dict[str, Any]:
    LIMITER.check(f"user:{user.id}", USER_RUNS_PER_HOUR)
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

    return await _start_run(run_id, filename, ext, size, upload_path, user.id)


@app.get("/api/samples")
async def list_samples() -> dict[str, Any]:
    return {"samples": [name for name in SAMPLE_FILES if (SAMPLES_DIR / name).is_file()]}


@app.post("/api/samples/{name}", status_code=201)
async def analyze_sample(
    name: str, request: Request, user: User | None = Depends(optional_user)
) -> dict[str, Any]:
    """Analyze a bundled sample dataset. Works signed out (rate limited per IP)."""
    source = SAMPLES_DIR / name
    if name not in SAMPLE_FILES or not source.is_file():
        raise _error(404, "not_found", "Sample not found", f"Available: {list(SAMPLE_FILES)}")
    if user is not None:
        LIMITER.check(f"user:{user.id}", USER_RUNS_PER_HOUR)
    else:
        LIMITER.check(f"ip:{client_ip(request)}", ANON_RUNS_PER_HOUR)
    run_id = str(uuid.uuid4())
    upload_dir = UPLOAD_ROOT / run_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / name
    shutil.copyfile(source, upload_path)
    owner = user.id if user else None
    return await _start_run(run_id, name, source.suffix, upload_path.stat().st_size, upload_path, owner)


@app.get("/api/status/{run_id}")
async def get_status(
    run_id: str, t: str | None = None, user: User | None = Depends(optional_user)
) -> dict[str, Any]:
    rec = await _readable_run(run_id, user, t)
    async with RUNS_LOCK:
        payload = {k: rec.get(k) for k in PUBLIC_FIELDS}
        payload["events"] = rec["events"][-50:]
        payload["share_token"] = rec["share_token"]
        payload["links"] = _links(rec)
        payload["is_owner"] = user is not None and user.id == rec.get("owner")
    return payload


@app.get("/api/results/{run_id}")
async def get_results(
    run_id: str, t: str | None = None, user: User | None = Depends(optional_user)
) -> dict[str, Any]:
    rec = await _readable_run(run_id, user, t)
    token = rec["share_token"]
    files = _links(rec)["files"]
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
        fmt: f"/api/download/{run_id}/{fmt}?t={token}" if (output_dir / name).exists() else None
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
        "report_view_url": f"{files}/report.html" if reports["html"] else None,
        "charts": [{"name": c, "url": f"{files}/visualizations/{c}"} for c in charts],
        "counts": {"kpis": len(kpis), "insights": len(insights), "visualizations": len(charts)},
        "trace": {
            "steps_completed": snapshot.get("steps_completed") or rec.get("steps_completed", []),
            "steps_skipped": snapshot.get("steps_skipped") or [],
            "events": rec.get("events", [])[-100:],
        },
    }


@app.get("/api/download/{run_id}/{fmt}")
async def download(
    run_id: str, fmt: str, t: str | None = None, user: User | None = Depends(optional_user)
) -> FileResponse:
    if fmt not in REPORT_FILES:
        raise _error(400, "bad_format", "Bad format", "fmt must be html, json, or pdf")
    rec = await _readable_run(run_id, user, t)
    if rec["status"] != "done":
        raise _error(409, "not_ready", "Not ready", "Run not done yet")
    path = OUTPUT_ROOT / run_id / REPORT_FILES[fmt]
    if not path.exists():
        raise _error(404, "artifact_missing", "Artifact not found", f"{fmt} report not generated")
    return FileResponse(str(path), media_type=MEDIA_TYPES[fmt], filename=f"dataforge-{run_id}.{fmt}")


@app.get("/api/runs/{run_id}/{t}/files/{file_path:path}")
async def run_file(run_id: str, t: str, file_path: str) -> FileResponse:
    """Serve a report asset. The share token sits in the path (not the query) so
    report.html's relative chart links resolve with the same access."""
    await _readable_run(run_id, None, t)
    root = (OUTPUT_ROOT / run_id).resolve()
    target = (root / file_path).resolve()
    allowed = target.suffix in (".html", ".js", ".json", ".pdf", ".png")
    if not allowed or not target.is_relative_to(root) or not target.is_file():
        raise _error(404, "artifact_missing", "Artifact not found", file_path)
    return FileResponse(str(target))


@app.get("/api/history")
async def history(limit: int = 20, user: User = Depends(require_user)) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    async with RUNS_LOCK:
        mine = [r for r in RUNS.values() if r.get("owner") == user.id]
        items = sorted(mine, key=lambda r: r.get("created_at") or "", reverse=True)[:limit]
        runs = [
            {**{k: r.get(k) for k in PUBLIC_FIELDS}, "share_token": r["share_token"]}
            for r in items
        ]
    return {"runs": runs, "count": len(runs)}


@app.websocket("/ws/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str, t: str | None = None) -> None:
    await websocket.accept()
    async with RUNS_LOCK:
        rec = RUNS.get(run_id) if RUN_ID_RE.match(run_id) else None
        if rec is not None and not can_read(rec, None, t):
            rec = None
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
async def delete_run(
    run_id: str,
    x_admin_token: str | None = Header(default=None),
    user: User | None = Depends(optional_user),
) -> dict[str, str]:
    rec = await _get_run(run_id)
    is_admin = bool(ADMIN_TOKEN) and x_admin_token == ADMIN_TOKEN
    is_owner = user is not None and rec.get("owner") is not None and user.id == rec["owner"]
    if not (is_admin or is_owner):
        raise _error(403, "forbidden", "Forbidden", "Only the run's owner can delete it")
    if rec["status"] in ("queued", "running"):
        raise _error(409, "running", "Run in progress", "Wait for the run to finish before deleting it")
    async with RUNS_LOCK:
        RUNS.pop(run_id, None)
    shutil.rmtree(UPLOAD_ROOT / run_id, ignore_errors=True)
    shutil.rmtree(OUTPUT_ROOT / run_id, ignore_errors=True)
    WS_CONNECTIONS.pop(run_id, None)
    return {"status": "deleted", "run_id": run_id}
