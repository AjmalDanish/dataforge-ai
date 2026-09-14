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

APP_VERSION = "2.0.0"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000,http://localhost:3001,https://dataforge-ai.netlify.app,https://frontend-eight-pi-72.vercel.app,https://frontend-7hpg0n00d-azylas.vercel.app,https://frontend-3dmsqk6ev-azylas.vercel.app",
    ).split(",")
    if o.strip()
]
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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)


@app.on_event("startup")
async def _load_existing_runs() -> None:
    """Rehydrate runs that already have output on disk (survives restarts)."""
    try:
        for p in OUTPUT_ROOT.iterdir():
            if p.is_dir() and (p / "results.json").exists() and p.name not in RUNS:
                try:
                    rec = _load_run_from_disk(p.name)
                    if rec:
                        RUNS[p.name] = rec
                except Exception:
                    continue
    except Exception:
        pass

RUNS: dict[str, dict[str, Any]] = {}
WS_CONNECTIONS: dict[str, list[WebSocket]] = {}
RUNS_LOCK = asyncio.Lock()


def _load_run_from_disk(run_id: str) -> dict[str, Any] | None:
    """Rehydrate a run that exists on disk but not in memory (after restart)."""
    out = OUTPUT_ROOT / run_id
    if not out.exists():
        return None
    # if results.json exists -> done, else try to infer from files
    results_path = out / "results.json"
    if results_path.exists():
        try:
            snap = json.loads(results_path.read_text(encoding="utf-8"))
            # snap was written with business_domain, kpis, etc., but may not have steps_completed
            # Try to recover steps_completed from results.json or from report existence
            steps = snap.get("steps_completed") or []
            # Fallback: if snapshot has no steps, infer from known pipeline (done = 24 steps)
            if not steps:
                # Check if report exists -> assume full pipeline completed
                if (out / "report.html").exists():
                    steps = [
                        "PlannerAgent","DataValidationAgent","PlannerAgent","DataCleaningAgent","PlannerAgent","SchemaDetectionAgent","PlannerAgent","BusinessDomainDetectionAgent","PlannerAgent","BusinessObjectiveDetectionAgent","PlannerAgent","DataProfilingAgent","PlannerAgent","FeatureEngineeringAgent","PlannerAgent","KPIDiscoveryAgent","PlannerAgent","StatisticalAnalysisAgent","PlannerAgent","InsightGenerationAgent","PlannerAgent","VisualizationAgent","PlannerAgent","ReportingAgent",
                    ]
            rec = _new_run_record(run_id, snap.get("filename") or "unknown", snap.get("format") or "csv", snap.get("size_bytes") or 0)
            rec.update(
                {
                    "status": "done",
                    "business_domain": snap.get("business_domain") or "hr",
                    "steps_completed": steps,
                    "current_phase": 7,
                    "finished_at": snap.get("finished_at"),
                    "duration_s": snap.get("duration_s"),
                    "output_dir": str(out),
                }
            )
            # try to find original upload filename from upload dir
            up_dir = UPLOAD_ROOT / run_id
            if up_dir.exists():
                for f in up_dir.iterdir():
                    if f.is_file():
                        rec["filename"] = f.name
                        rec["upload_path"] = str(f)
                        break
            return rec
        except Exception:
            pass
    # No results.json but output dir exists -> treat as done if report exists, else failed
    if (out / "report.html").exists():
        rec = _new_run_record(run_id, "unknown", "csv", 0)
        rec.update({"status": "done", "current_phase": 7, "steps_completed": [], "output_dir": str(out)})
        return rec
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_record(run_id: str, filename: str, file_format: str, size_bytes: int) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "filename": filename,
        "format": file_format,
        "size_bytes": size_bytes,
        "status": "queued",
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
        "events": [],
    }


async def _broadcast(run_id: str, payload: dict[str, Any]) -> None:
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
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "invalid_filename",
                "title": "Invalid filename",
                "detail": "Filename must not contain path separators",
            },
        )
    return ext


async def _run_analysis(run_id: str, upload_path: Path, output_dir: Path) -> None:
    started = datetime.now(timezone.utc)
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
        if rec is None:
            return
        rec["status"] = "running"
        rec["started_at"] = started.isoformat()
        rec["current_phase"] = 1

    await _broadcast(run_id, {"type": "status", "run_id": run_id, "status": "running", "ts": _now_iso()})

    try:
        from dataforge.core.state import GraphState
        from dataforge.graph.workflow import create_graph

        output_dir.mkdir(parents=True, exist_ok=True)
        state = GraphState(
            input_dataset_path=str(upload_path),
            output_dir=str(output_dir),
            execution_id=run_id,
            data={"pipeline_version": "v2", "run_id": run_id},
        )

        graph = create_graph()
        final_state = await graph.ainvoke(state, {"recursion_limit": 35})  # type: ignore

        if isinstance(final_state, dict):
            steps_completed = list(final_state.get("steps_completed") or [])
            current_phase_final = final_state.get("current_phase", 7)
            domain_final = (final_state.get("data") or {}).get("business_domain")
            data_dict = final_state.get("data") or {}
        else:
            steps_completed = list(getattr(final_state, "steps_completed", []) or [])
            current_phase_final = getattr(final_state, "current_phase", 7)
            try:
                domain_final = final_state.get("business_domain")  # type: ignore
            except Exception:
                domain_final = getattr(final_state, "business_domain", None)
            data_dict = getattr(final_state, "data", {}) or {}
        # Normalize BusinessDomain enum to lowercase string
        if domain_final is not None and hasattr(domain_final, "value"):
            try:
                domain_final = str(domain_final.value).lower()
            except Exception:
                domain_final = str(domain_final).lower()
        elif domain_final is not None:
            domain_final = str(domain_final).lower()
            # strip "businessdomain." prefix if str(enum) was stored
            if domain_final.startswith("businessdomain."):
                domain_final = domain_final.split(".", 1)[1]

        # Build snapshot for /results
        # Normalize business_domain for JSON (enum → string)
        _bd_snap = domain_final
        if _bd_snap is not None and hasattr(_bd_snap, "value"):
            try:
                _bd_snap = str(_bd_snap.value).lower()
            except Exception:
                _bd_snap = str(_bd_snap).lower()
        elif _bd_snap is not None:
            _bd_snap = str(_bd_snap).lower()
            if _bd_snap.startswith("businessdomain."):
                _bd_snap = _bd_snap.split(".", 1)[1]
        snapshot: dict[str, Any] = {
            "run_id": run_id,
            "status": "done",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_s": (datetime.now(timezone.utc) - started).total_seconds(),
            "business_domain": _bd_snap,
            "steps_completed": steps_completed,
            "steps_skipped": [],
            "current_phase": current_phase_final,
        }
        # pull v2 outputs (keep normalized business_domain)
        for key in (
            "business_insights",
            "discovered_kpis",
            "visualizations",
            "dashboard",
            "report_html",
            "report_json",
            "profile",
            "statistics",
        ):
            snapshot[key] = data_dict.get(key)
        # ensure business_domain stays normalized
        snapshot["business_domain"] = _bd_snap

        try:
            with open(output_dir / "results.json", "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, default=str, ensure_ascii=False)
        except Exception:
            pass

        finished = datetime.now(timezone.utc)
        duration_s = (finished - started).total_seconds()
        snapshot["finished_at"] = finished.isoformat()
        snapshot["duration_s"] = duration_s
        try:
            with open(output_dir / "results.json", "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, default=str, ensure_ascii=False)
        except Exception:
            pass

        async with RUNS_LOCK:
            if run_id in RUNS:
                RUNS[run_id].update(
                    {
                        "status": "done",
                        "finished_at": finished.isoformat(),
                        "duration_s": duration_s,
                        "current_phase": 7,
                        "steps_completed": steps_completed,
                    }
                )
                if domain_final:
                    RUNS[run_id]["business_domain"] = str(domain_final)
                elif snapshot.get("business_domain"):
                    RUNS[run_id]["business_domain"] = str(snapshot["business_domain"])

        await _broadcast(run_id, {"type": "done", "run_id": run_id, "status": "done", "duration_s": duration_s, "ts": _now_iso()})

    except Exception as e:
        finished = datetime.now(timezone.utc)
        duration_s = (finished - started).total_seconds()
        err = f"{type(e).__name__}: {e}"
        async with RUNS_LOCK:
            if run_id in RUNS:
                RUNS[run_id].update(
                    {"status": "failed", "finished_at": finished.isoformat(), "duration_s": duration_s, "error": err}
                )
        try:
            with open(output_dir / "error.json", "w", encoding="utf-8") as f:
                json.dump({"run_id": run_id, "error": err, "ts": _now_iso()}, f)
        except Exception:
            pass
        await _broadcast(run_id, {"type": "error", "run_id": run_id, "status": "failed", "error": err, "ts": _now_iso()})


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "dataforge-api", "version": APP_VERSION}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "dataforge-api", "version": APP_VERSION, "docs": "/docs"}


@app.post("/api/analyze", status_code=201)
async def analyze(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> JSONResponse:
    filename = file.filename or "upload.csv"
    content = await file.read()
    size = len(content)
    ext = _validate_upload(filename, size)
    run_id = str(uuid.uuid4())
    safe_name = Path(filename).name
    run_upload_dir = UPLOAD_ROOT / run_id
    run_upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = run_upload_dir / safe_name
    upload_path.write_bytes(content)
    output_dir = OUTPUT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    record = _new_run_record(run_id, safe_name, ext.lstrip("."), size)
    record["upload_path"] = str(upload_path)
    record["output_dir"] = str(output_dir)
    async with RUNS_LOCK:
        RUNS[run_id] = record
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
            # Try to rehydrate from disk (survives restarts)
            rec = _load_run_from_disk(run_id)
            if rec is not None:
                RUNS[run_id] = rec
            else:
                raise HTTPException(status_code=404, detail={"type": "not_found", "title": "Run not found", "detail": f"No run {run_id}"})
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
            "events": rec.get("events", [])[-50:],
        }


@app.get("/api/results/{run_id}")
async def get_results(run_id: str) -> dict[str, Any]:
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
        if rec is None:
            rec = _load_run_from_disk(run_id)
            if rec is not None:
                RUNS[run_id] = rec
            else:
                raise HTTPException(status_code=404, detail={"type": "not_found", "title": "Run not found", "detail": f"No run {run_id}"})
        if rec["status"] not in ("done", "failed"):
            return {"run_id": run_id, "status": rec["status"], "message": "Results not ready — poll /api/status until status=done"}
        if rec["status"] == "failed":
            return {"run_id": run_id, "status": "failed", "error": rec.get("error"), "finished_at": rec.get("finished_at")}
    output_dir = OUTPUT_ROOT / run_id
    snapshot_path = output_dir / "results.json"
    snapshot: dict[str, Any] = {}
    if snapshot_path.exists():
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except Exception:
            snapshot = {}
    async with RUNS_LOCK:
        rec = RUNS.get(run_id, {})
    html_path = output_dir / "report.html"
    json_path = output_dir / "report.json"
    report_html = f"/api/download/{run_id}/html" if html_path.exists() else None
    report_json = f"/api/download/{run_id}/json" if json_path.exists() else None
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
        "report_urls": {"html": report_html, "json": report_json, "pdf": None},
        "counts": {"kpis": len(snapshot.get("discovered_kpis") or []), "insights": len(snapshot.get("business_insights") or []), "visualizations": viz_count},
        "trace": {"steps_completed": rec.get("steps_completed", []), "events": rec.get("events", [])[-100:]},
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
    mapping = {"html": output_dir / "report.html", "json": output_dir / "report.json", "pdf": output_dir / "report.pdf"}
    path = mapping[fmt]
    if not path.exists():
        raise HTTPException(status_code=404, detail={"type": "artifact_missing", "title": "Artifact not found", "detail": f"{fmt} report not generated"})
    media = {"html": "text/html", "json": "application/json", "pdf": "application/pdf"}[fmt]
    return FileResponse(str(path), media_type=media, filename=f"dataforge-{run_id}.{fmt}")


@app.get("/api/history")
async def history(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    async with RUNS_LOCK:
        items = sorted(RUNS.values(), key=lambda r: r.get("created_at", ""), reverse=True)[:limit]
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
    await websocket.accept()
    async with RUNS_LOCK:
        rec = RUNS.get(run_id)
    if rec is None:
        await websocket.send_json({"type": "error", "detail": "Run not found", "run_id": run_id})
        await websocket.close()
        return
    for ev in rec.get("events", [])[-20:]:
        try:
            await websocket.send_json(ev)
        except Exception:
            break
    WS_CONNECTIONS.setdefault(run_id, []).append(websocket)
    try:
        while True:
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
    async with RUNS_LOCK:
        rec = RUNS.pop(run_id, None)
    if rec is None:
        raise HTTPException(status_code=404, detail={"type": "not_found", "title": "Run not found", "detail": f"No run {run_id}"})
    for p in [Path(rec.get("upload_path") or ""), Path(rec.get("output_dir") or "")]:
        try:
            if p and p.exists():
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
                    try:
                        p.parent.rmdir()
                    except OSError:
                        pass
        except Exception:
            pass
    WS_CONNECTIONS.pop(run_id, None)
    return {"status": "deleted", "run_id": run_id}
