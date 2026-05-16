# Dockerfile lives in demo-app/backend/ but the build context is the
# REPO ROOT so we can COPY the pipeline data alongside the app source.
# Wire it that way in render.yaml (dockerContext: ".").

FROM python:3.12-slim

# Faster, smaller installs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime deps only — pin to roughly the versions verified locally in the
# conda env "skills" so the production runtime matches dev behaviour.
RUN pip install \
    "fastapi>=0.135.1,<1.0" \
    "uvicorn[standard]>=0.42.0,<1.0" \
    "pydantic>=2.12.5,<3.0" \
    "httpx>=0.28.0,<1.0"

# Backend source.
COPY demo-app/backend/app/ ./app/

# Upstream data the read-only data_loader serves. Baked into the image
# so the container is self-contained — Render can't mount the repo.
# Keep this small: only stable results + test_cases (≈5 MB total).
COPY distillation_v2/results/stable/ /data/distillation_v2/results/stable/
COPY distillation_v2/test_cases/     /data/distillation_v2/test_cases/

# data_loader resolves paths from DISTILL_REPO_ROOT.
ENV DISTILL_REPO_ROOT=/data

# Render injects $PORT; default 8000 for local docker run.
ENV PORT=8000
EXPOSE 8000

# Hard-coded production origins live in env (ALLOWED_ORIGINS) so the
# image stays redeployable when the frontend domain changes.
ENV ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Run via uvicorn directly (not gunicorn) — SSE long-poll behaves better
# with a single-worker async server. Render's free tier has 0.5 vCPU so
# 1 worker is the right answer anyway.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
