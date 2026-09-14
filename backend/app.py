"""DataForge AI backend entrypoint (HuggingFace Spaces).

FastAPI serving the LangGraph engine in dataforge/.
TRD: docs/TRD.md §2. Full routes land in backend/routers/ (next step).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DataForge AI API", version="2.0.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe for HF Spaces + Netlify cold-start check."""
    return {"status": "ok", "service": "dataforge-api"}


def configure_cors(app: FastAPI, allow_origins: list[str]) -> None:
    """Restrict cross-origin access to the Netlify frontend."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        max_age=600,
    )
