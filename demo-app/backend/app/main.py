"""Skill Distillation Lab — FastAPI backend.

Endpoints split into two groups:

* ``/api/skills/*`` — read-only data loader over
  ``distillation_v2/results/stable/<skill>/``. Returns the real
  ``summary.json`` + ``SKILL_round_*.md`` from disk.
* ``/api/run`` + ``/api/run/{id}/stream`` — simulated SSE for the live demo
  on the /run page (no LLM calls).

CORS is open to localhost:3000 only.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import HealthResponse
from app.routes import run as run_route
from app.routes import skills as skills_route

app = FastAPI(
    title="Skill Distillation Lab — Backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(skills_route.router)
app.include_router(run_route.router)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
