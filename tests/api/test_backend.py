"""API tests for the FastAPI backend (backend/app.py)."""

import importlib
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("multipart")
from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CSV = (
    "order_id,region,product,revenue,quantity,discount\n"
    + "\n".join(
        f"{i},{['North', 'South', 'East'][i % 3]},P{i % 5},{100 + i * 13.5},{1 + i % 7},{(i % 4) * 0.05}"
        for i in range(1, 41)
    )
)


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("DATAFORGE_DISABLE_LLM", "1")
    monkeypatch.setenv("DATAFORGE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
    sys.path.insert(0, str(ROOT / "backend"))
    try:
        module = importlib.reload(importlib.import_module("app"))
    finally:
        sys.path.remove(str(ROOT / "backend"))
    with TestClient(module.app) as client:
        yield module, client


def _wait(client: TestClient, run_id: str, timeout: float = 240) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/api/status/{run_id}").json()
        if status["status"] in ("done", "failed"):
            return status
        time.sleep(0.5)
    raise AssertionError(f"run {run_id} did not finish")


def test_health(api):
    _, client = api
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    assert body["llm"] is False


def test_full_run_lifecycle(api):
    module, client = api
    resp = client.post("/api/analyze", files={"file": ("sales.csv", CSV, "text/csv")})
    assert resp.status_code == 201
    run_id = resp.json()["run_id"]

    status = _wait(client, run_id)
    assert status["status"] == "done", status.get("error")
    assert status["current_phase"] == 7
    agent_events = [e for e in status["events"] if e["type"] == "agent"]
    assert agent_events and agent_events[-1]["agent"] == "ReportingAgent"

    results = client.get(f"/api/results/{run_id}").json()
    assert results["status"] == "done"
    assert results["business_domain"] == "retail"
    assert results["counts"]["kpis"] > 0
    assert results["counts"]["insights"] > 0
    assert results["evaluation"]["passed"] is True
    assert results["trace"]["steps_completed"][-1] == "ReportingAgent"

    for fmt, media in (("html", "text/html"), ("json", "application/json"), ("pdf", "application/pdf")):
        dl = client.get(results["report_urls"][fmt])
        assert dl.status_code == 200
        assert dl.headers["content-type"].startswith(media)

    report = client.get(results["report_view_url"])
    assert report.status_code == 200 and "Executive Summary" in report.text
    chart = client.get(results["charts"][0]["url"])
    assert chart.status_code == 200
    assert client.get(f"/api/runs/{run_id}/files/visualizations/plotly.min.js").status_code == 200

    history = client.get("/api/history").json()
    assert history["runs"][0]["run_id"] == run_id

    # Metadata survives a restart.
    module.RUNS.clear()
    module._load_runs_from_disk()
    assert client.get(f"/api/status/{run_id}").json()["status"] == "done"

    assert client.delete(f"/api/runs/{run_id}").status_code == 403
    deleted = client.delete(f"/api/runs/{run_id}", headers={"X-Admin-Token": "secret"})
    assert deleted.status_code == 200
    assert client.get(f"/api/status/{run_id}").status_code == 404


def test_rejects_bad_uploads(api):
    _, client = api
    bad_ext = client.post("/api/analyze", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert bad_ext.status_code == 400
    empty = client.post("/api/analyze", files={"file": ("x.csv", b"", "text/csv")})
    assert empty.status_code == 400
    big = client.post("/api/analyze", files={"file": ("x.csv", b"a" * (1024 * 1024 + 1), "text/csv")})
    assert big.status_code == 413


def test_rejects_path_traversal(api):
    module, client = api
    assert client.get("/api/status/..%2F..%2Fetc").status_code == 404
    assert client.get("/api/results/not-a-uuid").status_code == 404

    resp = client.post("/api/analyze", files={"file": ("s.csv", CSV, "text/csv")})
    run_id = resp.json()["run_id"]
    _wait(client, run_id)
    secret = Path(module.OUTPUT_ROOT).parent / "secret.html"
    secret.write_text("nope")
    assert client.get(f"/api/runs/{run_id}/files/%2e%2e/%2e%2e/secret.html").status_code == 404
    assert client.get(f"/api/runs/{run_id}/files/run.py").status_code == 404


def test_unknown_run_and_bad_format(api):
    _, client = api
    missing = "00000000-0000-4000-8000-000000000000"
    assert client.get(f"/api/status/{missing}").status_code == 404
    assert client.get(f"/api/download/{missing}/exe").status_code == 400


def test_websocket_replays_agent_events(api):
    _, client = api
    run_id = client.post("/api/analyze", files={"file": ("s.csv", CSV, "text/csv")}).json()["run_id"]
    _wait(client, run_id)

    agents = []
    with client.websocket_connect(f"/ws/{run_id}") as ws:
        while True:
            event = ws.receive_json()
            if event["type"] == "agent":
                agents.append(event["agent"])
            if event["type"] in ("done", "error"):
                assert event["type"] == "done"
                break
    assert agents[0] == "DataValidationAgent"
    assert agents[-1] == "ReportingAgent"
    assert len(agents) == 13


def test_websocket_unknown_run(api):
    _, client = api
    with client.websocket_connect("/ws/not-a-run") as ws:
        assert ws.receive_json()["type"] == "error"
