# DataForge AI API — engine + FastAPI in one image.
# Runs as a non-root user on port 7860 (HuggingFace Spaces default; override with PORT).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    UPLOAD_DIR=/data/uploads \
    OUTPUT_DIR=/data/outputs

RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown app /data
WORKDIR /app

COPY requirements.txt ./
COPY backend/requirements.txt backend/
RUN pip install -r backend/requirements.txt

COPY dataforge/ dataforge/
COPY backend/app.py backend/security.py backend/
COPY datasets/ datasets/

USER app
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz')"
CMD ["sh", "-c", "uvicorn app:app --app-dir backend --host 0.0.0.0 --port ${PORT}"]
