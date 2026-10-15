"""Authentication (Clerk session tokens) and rate limiting for the API.

Auth model
----------
- Signed-in users send ``Authorization: Bearer <Clerk session token>``. The
  token is verified against the Clerk instance's JWKS (RS256), including
  issuer, expiry and — when ``FRONTEND_URL`` lists origins — the ``azp``
  (authorized party) claim.
- ``CLERK_ISSUER`` (e.g. ``https://xyz.clerk.accounts.dev``) turns auth on.
  When it is unset the API runs in *dev mode*: every request acts as the
  single local user ``dev``. ``/healthz`` reports which mode is active.
- ``DATAFORGE_REQUIRE_AUTH=1`` (set on public deployments) forbids dev mode:
  without ``CLERK_ISSUER`` every caller is anonymous (samples only), so a
  missing setting can never open uploads and history to everyone.
- Browser-navigated URLs (report, charts, PDF, WebSocket) cannot carry an
  Authorization header, so each run also has an unguessable ``share_token``
  that grants read access when passed as ``?t=``.

Rate limiting
-------------
In-memory sliding windows keyed by user id (signed in) or client IP
(anonymous sample runs). Fine for a single API instance; move to Redis when
running several.
"""

from __future__ import annotations

import os
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request

DEV_USER_ID = "dev"


def clerk_issuer() -> str:
    return os.getenv("CLERK_ISSUER", "").strip().rstrip("/")


@dataclass(frozen=True)
class User:
    id: str


def require_auth() -> bool:
    return os.getenv("DATAFORGE_REQUIRE_AUTH", "").strip().lower() in ("1", "true", "yes")


def auth_mode() -> str:
    if clerk_issuer():
        return "clerk"
    return "unconfigured" if require_auth() else "dev"


_jwks_clients: dict[str, jwt.PyJWKClient] = {}
_jwks_lock = threading.Lock()


def _jwks(issuer: str) -> jwt.PyJWKClient:
    with _jwks_lock:
        if issuer not in _jwks_clients:
            _jwks_clients[issuer] = jwt.PyJWKClient(
                f"{issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600
            )
        return _jwks_clients[issuer]


def _allowed_parties() -> set[str]:
    origins = {o.strip().rstrip("/") for o in os.getenv("FRONTEND_URL", "*").split(",")}
    return {o for o in origins if o and o != "*"}


def verify_token(token: str) -> User:
    """Verify a Clerk session token and return its user, or raise 401."""
    issuer = clerk_issuer()
    try:
        key = _jwks(issuer).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "iss"]},
            leeway=5,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=401,
            detail={"type": "invalid_token", "title": "Invalid session", "detail": str(e)},
        ) from e
    allowed = _allowed_parties()
    azp = claims.get("azp")
    if allowed and azp and azp.rstrip("/") not in allowed:
        raise HTTPException(
            status_code=401,
            detail={"type": "invalid_token", "title": "Invalid session", "detail": "Token issued for another origin"},
        )
    return User(id=str(claims["sub"]))


def optional_user(request: Request) -> User | None:
    """The signed-in user, or None for anonymous requests (dev mode: always ``dev``)."""
    if not clerk_issuer():
        return None if require_auth() else User(id=DEV_USER_ID)
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return verify_token(token.strip())


def require_user(request: Request) -> User:
    user = optional_user(request)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"type": "auth_required", "title": "Sign in required", "detail": "Sign in to use this endpoint"},
        )
    return user


def new_share_token() -> str:
    return secrets.token_urlsafe(24)


def can_read(rec: dict, user: User | None, token: str | None) -> bool:
    """Owner, or anyone holding the run's share token."""
    if token and secrets.compare_digest(token, rec.get("share_token") or ""):
        return True
    return user is not None and rec.get("owner") is not None and user.id == rec["owner"]


def client_ip(request: Request) -> str:
    """The caller's IP as seen by our edge proxy.

    Clients can put anything in X-Forwarded-For; each proxy *appends* the
    address it saw. So the trustworthy entry is the one added by our own proxy
    layer: ``TRUSTED_PROXY_HOPS`` entries from the right (1 = a single
    load balancer, as on Render). Without the header, use the socket peer.
    """
    forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    hops = limit_from_env("TRUSTED_PROXY_HOPS", 1)
    if len(forwarded) >= hops:
        return forwarded[-hops]
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Sliding-window limiter: at most ``limit`` events per ``window`` seconds per key."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window: float = 3600.0) -> None:
        """Record an event for ``key`` or raise 429 with Retry-After."""
        now = time.monotonic()
        with self._lock:
            events = self._events[key]
            while events and now - events[0] >= window:
                events.popleft()
            if len(events) >= limit:
                retry_after = int(window - (now - events[0])) + 1
                minutes = max(1, round(retry_after / 60))
                raise HTTPException(
                    status_code=429,
                    detail={
                        "type": "rate_limited",
                        "title": "Too many analyses",
                        "detail": f"Limit is {limit} per hour. Try again in about {minutes} minute(s).",
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


def limit_from_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default
