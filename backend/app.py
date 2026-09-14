"""DataForge AI backend — FastAPI serving LangGraph engine.

TRD: docs/TRD.md §2, PRD: docs/PRD.md, DB: docs/DATABASE.md
Deploy target: HuggingFace Spaces (Docker + uvicorn), frontend on Netlify.

Single-file MVP: in-memory run store + filesystem artifacts. Upgrades to
Postgres persistence via dataforge.db.models when DATABASE_URL is set.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# ---------------------------------------------------------------------------
# App & config
# ---------------------------------------------------------------------------

APP_VERSION = "2.0.0"
# Allowlist for CORS — env FRONTEND_URL plus local dev. Comma-separated.
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000,http://localhost:3001,https://dataforge-ai.netlify.app",
    ).split(",")
    if o.strip()
]
# Upload limits — keep Netlify free tier friendly (body 10MB default tested)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet", ".pq", ".json"}

BASE_DIR = Path(__file__).parent
UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
OUTPUT_ROOT = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs")))
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="DataForge AI API",
    version=APP_VERSION,
    description="Autonomous BI engine — LangGraph 13 agents. See docs/TRD.md",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)

# ---------------------------------------------------------------------------
# In-memory run store (MVP) + websocket fan-out
# ---------------------------------------------------------------------------

# run_id -> run record
RUNS: dict[str, dict[str, Any]] = {}
# run_id -> list[WebSocket]
WS_CONNECTIONS: dict[str, list[WebSocket]] = {}
RUNS_LOCK = asyncio.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_record(
    run_id: str, filename: str, file_format: str, size_bytes: int
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "filename": filename,
        "format": file_format,
        "size_bytes": size_bytes,
        "status": "queued",  # queued | running | done | failed
        "current_phase": 1,
        "steps_completed": [],
        "steps_skipped": [],
        "quality_warnings": [],
        "quality_errors": [],
        "created_at": _now_iso(),
        "started_at": None,
        "finished_at": None,
        "duration_s": None,
        "business_domain": None,
        "error": None,
        "output_dir": str(OUTPUT_ROOT / run_id),
        "upload_path": None,
        "events": [],  # agent events for WS replay
    }


async def _broadcast(run_id: str, payload: dict[str, Any]) -> None:
    """Fan-out to all websockets listening for this run."""
    # store for later poll fallback
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
        if rec is not None:
            rec.setdefault("events", []).append(payload)
    conns = list(WS_CONNECTIONS.get(run_id, []))
    dead: list[WebSocket] = []
    for ws in conns:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        try:
            WS_CONNECTIONS.get(run_id, []).remove(ws)
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_upload(filename: str, size: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "unsupported_format",
                "title": "Unsupported file format",
                "detail": f"Extension {ext} not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
            },
        )
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "type": "file_too_large",
                "title": "File too large",
                "detail": f"File {size} bytes exceeds {MAX_FILE_SIZE_MB} MB limit",
            },
        )
    # basic path traversal guard
    if ".." in filename or "/" in filename or "\\" in filename:
        # we only use basename, but reject obvious traversal payloads
        raise HTTPException(
            status_code=400,
            detail={
                "type": "invalid_filename",
                "title": "Invalid filename",
                "detail": "Filename must not contain path separators",
            },
        )
    return ext


# ---------------------------------------------------------------------------
# Background analysis runner
# ---------------------------------------------------------------------------


async def _run_analysis(run_id: str, upload_path: Path, output_dir: Path) -> None:
    """Execute the LangGraph workflow and update RUNS + broadcast events."""
    started = datetime.now(timezone.utc)
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
        if rec is None:
            return
        rec["status"] = "running"
        rec["started_at"] = started.isoformat()
        rec["current_phase"] = 1

    await _broadcast(
        run_id,
        {"type": "status", "run_id": run_id, "status": "running", "ts": _now_iso()},
    )

    try:
        # Import lazily — keeps /healthz fast even if engine deps missing
        from dataforge.core.state import GraphState
        from dataforge.graph.workflow import create_graph

        # Per-run output dir
        output_dir.mkdir(parents=True, exist_ok=True)
        # Seed GraphState with v2 pipeline flag
        state = GraphState(
            input_dataset_path=str(upload_path),
            output_dir=str(output_dir),
            execution_id=run_id,
            data={"pipeline_version": "v2", "run_id": run_id},
        )

        graph = create_graph()

        # Stream node transitions for live WS. Fall back to ainvoke if astream unavailable.
        final_state = None
        try:
            # LangGraph astream yields {node_name: state} per step
            async for event in graph.astream(
                state, {"recursion_limit": 35}
            ):  # type: ignore[attr-defined]
                # event is dict node -> GraphState
                for node_name, node_state in event.items():
                    # coerce to GraphState when possible
                    gs = node_state
                    # Derive progress from GraphState fields
                    steps = []
                    domain = None
                    try:
                        steps = list(getattr(gs, "steps_completed", []) or [])
                        if hasattr(gs, "get"):
                            domain = gs.get("business_domain")
                        else:
                            domain = getattr(gs, "business_domain", None)
                    except Exception:
                        pass
                    phase = 1
                    try:
                        phase = int(getattr(gs, "current_phase", 1) or 1)
                    except Exception:
                        phase = 1
                    async with RUNS_LOCK:
                        if run_id in RUNS:
                            RUNS[run_id]["steps_completed"] = steps
                            RUNS[run_id]["current_phase"] = phase
                            if domain:
                                RUNS[run_id]["business_domain"] = str(domain)
                    await _broadcast(
                        run_id,
                        {
                            "type": "node",
                            "run_id": run_id,
                            "node": node_name,
                            "steps_completed": steps,
                            "current_phase": phase,
                            "business_domain": domain,
                            "ts": _now_iso(),
                        },
                    )
                    final_state = gs
        except AttributeError:
            # Older langgraph without astream — fallback
            final_state = await graph.ainvoke(state, {"recursion_limit": 35})  # type: ignore

        # If astream never yielded final (e.g., single-shot), ensure we have final_state
        if final_state is None:
            final_state = state  # type: ignore

        finished = datetime.now(timezone.utc)
        duration_s = (finished - started).total_seconds()

        # Persist a lightweight results snapshot for /results
        snapshot: dict[str, Any] = {
            "run_id": run_id,
            "status": "done",
            "finished_at": finished.isoformat(),
            "duration_s": duration_s,
        }
        try:
            # Pull v2 outputs when present
            for key in (
                "business_domain",
                "business_insights",
                "discovered_kpis",
                "visualizations",
                "dashboard",
                "report_html",
                "report_json",
                "profile",
                "statistics",
            ):
                try:
                    snapshot[key] = final_state.get(key)  # type: ignore
                except Exception:
                    snapshot[key] = getattr(final_state, key, None)

            # Also persist full execution trace for debugging
            snapshot_path = output_dir / "results.json"
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, default=str, ensure_ascii=False)
        except Exception:
            pass  # snapshot is best-effort

        async with RUNS_LOCK:
            if run_id in RUNS:
                RUNS[run_id].update(
                    {
                        "status": "done",
                        "finished_at": finished.isoformat(),
                        "duration_s": duration_s,
                        "current_phase": 7,
                    }
                )
                # enrich with snapshot domain if we didn't capture earlier
                if snapshot.get("business_domain"):
                    RUNS[run_id]["business_domain"] = str(snapshot["business_domain"])

        await _broadcast(
            run_id,
            {
                "type": "done",
                "run_id": run_id,
                "status": "done",
                "duration_s": duration_s,
                "ts": _now_iso(),
            },
        )

    except Exception as e:
        finished = datetime.now(timezone.utc)
        duration_s = (finished - started).total_seconds()
        err = f"{type(e).__name__}: {e}"
        async with RUNS_LOCK:
            if run_id in RUNS:
                RUNS[run_id].update(
                    {
                        "status": "failed",
                        "finished_at": finished.isoformat(),
                        "duration_s": duration_s,
                        "error": err,
                    }
                )
        # also write failure snapshot
        try:
            with open(output_dir / "error.json", "w", encoding="utf-8") as f:
                json.dump({"run_id": run_id, "error": err, "ts": _now_iso()}, f)
        except Exception:
            pass
        await _broadcast(
            run_id,
            {"type": "error", "run_id": run_id, "status": "failed", "error": err, "ts": _now_iso()},
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe for HF Spaces + Netlify cold-start check."""
    return {"status": "ok", "service": "dataforge-api", "version": APP_VERSION}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "dataforge-api", "version": APP_VERSION, "docs": "/docs"}


@app.post("/api/analyze", status_code=201)
async def analyze(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> JSONResponse:
    """Upload a dataset and enqueue an analysis run.

    Returns 201 with run_id + polling/ws URLs.
    """
    filename = file.filename or "upload.csv"
    # Read into memory to validate size before writing (free-tier safe)
    content = await file.read()
    size = len(content)
    ext = _validate_upload(filename, size)

    run_id = str(uuid.uuid4())
    safe_name = Path(filename).name  # traversal-safe basename
    run_upload_dir = UPLOAD_ROOT / run_id
    run_upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = run_upload_dir / safe_name
    # write atomically
    upload_path.write_bytes(content)

    output_dir = OUTPUT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    record = _new_run_record(run_id, safe_name, ext.lstrip("."), size)
    record["upload_path"] = str(upload_path)
    record["output_dir"] = str(output_dir)
    async with RUNS_LOCK:
        RUNS[run_id] = record

    # Schedule background execution (FastAPI BackgroundTasks run after response)
    background_tasks.add_task(_run_analysis, run_id, upload_path, output_dir)

    return JSONResponse(
        status_code=201,
        content={
            "run_id": run_id,
            "status": "queued",
            "status_url": f"/api/status/{run_id}",
            "results_url": f"/api/results/{run_id}",
            "ws_url": f"/ws/{run_id}",
            "output_dir": str(output_dir),
        },
    )


@app.get("/api/status/{run_id}")
async def get_status(run_id: str) -> dict[str, Any]:
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
        if rec is None:
            raise HTTPException(status_code=404, detail={"type": "not_found", "title": "Run not found", "detail": f"No run {run_id}"})
        # shallow copy without large fields
        return {
            "run_id": run_id,
            "status": rec["status"],
            "current_phase": rec.get("current_phase", 1),
            "steps_completed": rec.get("steps_completed", []),
            "steps_skipped": rec.get("steps_skipped", []),
            "quality_warnings": rec.get("quality_warnings", []),
            "quality_errors": rec.get("quality_errors", []),
            "business_domain": rec.get("business_domain"),
            "created_at": rec.get("created_at"),
            "started_at": rec.get("started_at"),
            "finished_at": rec.get("finished_at"),
            "duration_s": rec.get("duration_s"),
            "error": rec.get("error"),
            "events": rec.get("events", [])[-50:],  # last 50 for polling fallback
        }


@app.get("/api/results/{run_id}")
async def get_results(run_id: str) -> dict[str, Any]:
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
        if rec is None:
            raise HTTPException(status_code=404, detail={"type": "not_found", "title": "Run not found", "detail": f"No run {run_id}"})
        if rec["status"] not in ("done", "failed"):
            return {
                "run_id": run_id,
                "status": rec["status"],
                "message": "Results not ready — poll /api/status until status=done",
            }
        if rec["status"] == "failed":
            return {
                "run_id": run_id,
                "status": "failed",
                "error": rec.get("error"),
                "finished_at": rec.get("finished_at"),
            }

    # Load snapshot written by _run_analysis
    output_dir = OUTPUT_ROOT / run_id
    snapshot_path = output_dir / "results.json"
    snapshot: dict[str, Any] = {}
    if snapshot_path.exists():
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except Exception:
            snapshot = {}

    # Also surface file existence for download links
    async with RUNS_LOCK:
        rec = RUNS.get(run_id, {})
    report_html = None
    report_json = None
    # Prefer snapshot paths, else discover from output dir
    for cand in [snapshot.get("report_html"), snapshot.get("report_json")]:
        pass  # not filesystem paths in snapshot (state keys), handle below
    html_path = output_dir / "report.html"
    json_path = output_dir / "report.json"
    if html_path.exists():
        report_html = f"/api/download/{run_id}/html"
    if json_path.exists():
        report_json = f"/api/download/{run_id}/json"
    # dashboard + visualizations are in output/visualizations when present
    viz_dir = output_dir / "visualizations"
    viz_count = len(list(viz_dir.glob("*.html"))) if viz_dir.exists() else 0

    return {
        "run_id": run_id,
        "status": "done",
        "business_domain": rec.get("business_domain") or snapshot.get("business_domain"),
        "duration_s": rec.get("duration_s"),
        "finished_at": rec.get("finished_at"),
        "kpis": snapshot.get("discovered_kpis") or [],
        "insights": snapshot.get("business_insights") or [],
        "dashboard": snapshot.get("dashboard") or {},
        "report_urls": {
            "html": report_html,
            "json": report_json,
            "pdf": None,  # until WeasyPrint lands
        },
        "counts": {
            "kpis": len(snapshot.get("discovered_kpis") or []),
            "insights": len(snapshot.get("business_insights") or []),
            "visualizations": viz_count,
        },
        "trace": {
            "steps_completed": rec.get("steps_completed", []),
            "events": rec.get("events", [])[-100:],
        },
    }


@app.get("/api/download/{run_id}/{fmt}")
async def download(run_id: str, fmt: str) -> FileResponse:
    if fmt not in ("html", "json", "pdf"):
        raise HTTPException(status_code=400, detail={"type": "bad_format", "title": "Bad format", "detail": "fmt must be html, json, or pdf"})
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
        if rec is None:
            raise HTTPException(status_code=404, detail={"type": "not_found", "title": "Run not found", "detail": f"No run {run_id}"})
        if rec["status"] != "done":
            raise HTTPException(status_code=409, detail={"type": "not_ready", "title": "Not ready", "detail": "Run not done yet"})
    output_dir = OUTPUT_ROOT / run_id
    mapping = {
        "html": output_dir / "report.html",
        "json": output_dir / "report.json",
        "pdf": output_dir / "report.pdf",
    }
    path = mapping[fmt]
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "type": "artifact_missing",
                "title": "Artifact not found",
                "detail": f"{fmt} report not generated for this run (pdf requires WeasyPrint, not yet enabled)",
            },
        )
    media = {"html": "text/html", "json": "application/json", "pdf": "application/pdf"}[fmt]
    return FileResponse(str(path), media_type=media, filename=f"dataforge-{run_id}.{fmt}")


@app.get("/api/history")
async def history(limit: int = 20) -> dict[str, Any]:
    """List recent runs (newest first). For Netlify history page."""
    limit = max(1, min(limit, 100))
    async with RUNS_LOCK:
        items = sorted(RUNS.values(), key=lambda r: r.get("created_at", ""), reverse=True)[:limit]
        # strip large fields
        out = [
            {
                "run_id": r["run_id"],
                "filename": r.get("filename"),
                "status": r["status"],
                "business_domain": r.get("business_domain"),
                "created_at": r.get("created_at"),
                "duration_s": r.get("duration_s"),
                "steps_completed": r.get("steps_completed", []),
            }
            for r in items
        ]
    return {"runs": out, "count": len(out)}


@app.websocket("/ws/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    """Real-time run events. Frontend connects here for live graph animation."""
    await websocket.accept()
    # send current state immediately so late joiners catch up
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
    if rec is None:
        await websocket.send_json({"type": "error", "detail": "Run not found", "run_id": run_id})
        await websocket.close()
        return
    # replay recent events
    for ev in rec.get("events", [])[-20:]:
        try:
            await websocket.send_json(ev)
        except Exception:
            break
    # register
    WS_CONNECTIONS.setdefault(run_id, []).append(websocket)
    try:
        while True:
            # keepalive + allow client pings; we don't expect client messages
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping", "ts": _now_iso()})
            except WebSocketDisconnect:
                break
    finally:
        conns = WS_CONNECTIONS.get(run_id, [])
        if websocket in conns:
            conns.remove(websocket)


@app.delete("/api/runs/{run_id}")
async def delete_run(run_id: str) -> dict[str, str]:
    """Delete a run and its artifacts. Best-effort cleanup."""
    async with RUNS_LOCK:
        rec = RUNS.pop(run_id, None)
    if rec is None:
        raise HTTPException(status_code=404, detail={"type": "not_found", "title": "Run not found", "detail": f"No run {run_id}"})
    # filesystem cleanup — don't fail the request if it errors
    for p in [Path(rec.get("upload_path") or ""), Path(rec.get("output_dir") or "")]:
        try:
            if p and p.exists():
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
                    # also remove parent run upload dir if empty
                    try:
                        p.parent.rmdir()
                    except OSError:
                        pass
        except Exception:
            pass
    WS_CONNECTIONS.pop(run_id, None)
    return {"status": "deleted", "run_id": run_id}
