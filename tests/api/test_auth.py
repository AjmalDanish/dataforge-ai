"""Auth and rate-limit tests with Clerk mode on (tokens signed by a local test key)."""

import importlib
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("multipart")
jwt = pytest.importorskip("jwt")
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ISSUER = "https://test-instance.clerk.accounts.dev"
FRONTEND = "https://dataforge.example"
CSV = "region,revenue,units\n" + "\n".join(f"{'NS'[i % 2]},{100 + i * 7},{i % 9 + 1}" for i in range(30))
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeJWKS:
    def get_signing_key_from_jwt(self, token):
        return type("SigningKey", (), {"key": KEY.public_key()})()


def token(sub: str, **overrides) -> str:
    now = int(time.time())
    claims = {"sub": sub, "iss": ISSUER, "iat": now, "exp": now + 60, "azp": FRONTEND, **overrides}
    return jwt.encode(claims, KEY, algorithm="RS256")


def auth(sub: str) -> dict:
    return {"Authorization": f"Bearer {token(sub)}"}


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("DATAFORGE_DISABLE_LLM", "1")
    monkeypatch.setenv("CLERK_ISSUER", ISSUER)
    monkeypatch.setenv("FRONTEND_URL", f"{FRONTEND},http://localhost:3000")
    monkeypatch.setenv("USER_RUNS_PER_HOUR", "3")
    monkeypatch.setenv("ANON_RUNS_PER_HOUR", "2")
    monkeypatch.delenv("DATAFORGE_ADMIN_TOKEN", raising=False)
    sys.path.insert(0, str(ROOT / "backend"))
    try:
        security = importlib.import_module("security")
        monkeypatch.setattr(security, "_jwks", lambda issuer: _FakeJWKS())
        module = importlib.reload(importlib.import_module("app"))
    finally:
        sys.path.remove(str(ROOT / "backend"))
    with TestClient(module.app) as client:
        yield module, client


def _wait(client, run_id: str, **kwargs) -> dict:
    for _ in range(400):
        status = client.get(f"/api/status/{run_id}", **kwargs).json()
        if status["status"] in ("done", "failed"):
            return status
        time.sleep(0.5)
    raise AssertionError("run did not finish")


def _upload(client, headers=None):
    return client.post("/api/analyze", files={"file": ("s.csv", CSV, "text/csv")}, headers=headers or {})


def test_health_reports_clerk_mode(api):
    _, client = api
    assert client.get("/healthz").json()["auth"] == "clerk"


def test_upload_requires_valid_session(api):
    _, client = api
    assert _upload(client).status_code == 401
    assert _upload(client, {"Authorization": "Bearer not-a-jwt"}).status_code == 401
    expired = token("user_a", exp=int(time.time()) - 120, iat=int(time.time()) - 200)
    assert _upload(client, {"Authorization": f"Bearer {expired}"}).status_code == 401
    other_issuer = token("user_a", iss="https://evil.clerk.accounts.dev")
    assert _upload(client, {"Authorization": f"Bearer {other_issuer}"}).status_code == 401
    other_origin = token("user_a", azp="https://evil.example")
    assert _upload(client, {"Authorization": f"Bearer {other_origin}"}).status_code == 401
    assert client.get("/api/history").status_code == 401


def test_runs_are_private_to_their_owner(api):
    _, client = api
    started = _upload(client, auth("user_a"))
    assert started.status_code == 201
    run_id, share = started.json()["run_id"], started.json()["share_token"]
    status = _wait(client, run_id, headers=auth("user_a"))
    assert status["status"] == "done" and status["is_owner"] is True

    # Another user, or nobody, cannot see it — and gets 404, not 403.
    assert client.get(f"/api/status/{run_id}", headers=auth("user_b")).status_code == 404
    assert client.get(f"/api/results/{run_id}").status_code == 404
    assert client.get(f"/api/download/{run_id}/pdf").status_code == 404
    assert client.get(f"/api/status/{run_id}?t=wrong").status_code == 404
    assert client.get("/api/history", headers=auth("user_b")).json()["runs"] == []
    assert client.delete(f"/api/runs/{run_id}", headers=auth("user_b")).status_code == 403

    # The share link grants read access (not ownership).
    shared = client.get(f"/api/results/{run_id}?t={share}").json()
    assert shared["status"] == "done"
    assert client.get(shared["report_urls"]["pdf"]).status_code == 200
    assert client.get(shared["report_view_url"]).status_code == 200
    assert client.get(f"/api/status/{run_id}?t={share}", headers=auth("user_b")).json()["is_owner"] is False

    history = client.get("/api/history", headers=auth("user_a")).json()["runs"]
    assert [r["run_id"] for r in history] == [run_id]
    assert client.delete(f"/api/runs/{run_id}", headers=auth("user_a")).status_code == 200


def test_anonymous_samples_are_shareable_but_unlisted(api):
    _, client = api
    started = client.post("/api/samples/employees.csv")
    assert started.status_code == 201
    run_id, share = started.json()["run_id"], started.json()["share_token"]
    assert started.json()["run_page"] == f"/runs/{run_id}?t={share}"
    assert _wait(client, run_id, params={"t": share})["status"] == "done"
    assert client.get(f"/api/status/{run_id}").status_code == 404
    # Nobody owns it, so nobody can delete it without the admin token.
    assert client.delete(f"/api/runs/{run_id}", headers=auth("user_a")).status_code == 403


def test_rate_limits(api):
    _, client = api
    # Anonymous samples: 2 per hour per IP.
    assert client.post("/api/samples/products.csv").status_code == 201
    assert client.post("/api/samples/products.csv").status_code == 201
    limited = client.post("/api/samples/products.csv", headers={"X-Forwarded-For": "203.0.113.9"})
    assert limited.status_code == 201  # a different client IP has its own budget
    limited = client.post("/api/samples/products.csv")
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0
    assert "per hour" in limited.json()["detail"]["detail"]

    # Signed-in users: 3 per hour, shared between uploads and samples.
    assert _upload(client, auth("user_a")).status_code == 201
    assert client.post("/api/samples/employees.csv", headers=auth("user_a")).status_code == 201
    assert _upload(client, auth("user_a")).status_code == 201
    assert _upload(client, auth("user_a")).status_code == 429
    assert _upload(client, auth("user_b")).status_code == 201  # per-user budgets


def test_websocket_requires_share_token(api):
    _, client = api
    started = _upload(client, auth("user_a")).json()
    _wait(client, started["run_id"], headers=auth("user_a"))
    with client.websocket_connect(f"/ws/{started['run_id']}") as ws:
        assert ws.receive_json()["type"] == "error"
    with client.websocket_connect(started["ws"]) as ws:
        assert ws.receive_json()["type"] in ("status", "agent")


def test_forwarded_for_spoofing_does_not_bypass_ip_limit(api):
    _, client = api
    # The proxy appends the real client (203.0.113.7); a client-supplied first
    # entry must not create a fresh budget.
    for fake in ("1.1.1.1", "2.2.2.2"):
        r = client.post("/api/samples/products.csv", headers={"X-Forwarded-For": f"{fake}, 203.0.113.7"})
        assert r.status_code == 201
    spoofed = client.post("/api/samples/products.csv", headers={"X-Forwarded-For": "3.3.3.3, 203.0.113.7"})
    assert spoofed.status_code == 429


def test_require_auth_without_clerk_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("DATAFORGE_DISABLE_LLM", "1")
    monkeypatch.setenv("DATAFORGE_REQUIRE_AUTH", "1")
    monkeypatch.delenv("CLERK_ISSUER", raising=False)
    sys.path.insert(0, str(ROOT / "backend"))
    try:
        module = importlib.reload(importlib.import_module("app"))
    finally:
        sys.path.remove(str(ROOT / "backend"))
    with TestClient(module.app) as client:
        assert client.get("/healthz").json()["auth"] == "unconfigured"
        assert _upload(client).status_code == 401
        assert client.get("/api/history").status_code == 401
        assert client.post("/api/samples/products.csv").status_code == 201  # demo still works


def test_token_that_expired_during_upload_is_accepted(api):
    _, client = api
    now = int(time.time())
    # Minted before a slow upload / cold start; expired 30s ago (within the 60s grace).
    recent = token("user_a", iat=now - 90, exp=now - 30)
    assert _upload(client, {"Authorization": f"Bearer {recent}"}).status_code == 201
    stale = token("user_a", iat=now - 300, exp=now - 120)
    rejected = _upload(client, {"Authorization": f"Bearer {stale}"})
    assert rejected.status_code == 401
    assert rejected.json()["detail"]["detail"] == "Your session expired. Please try again."
