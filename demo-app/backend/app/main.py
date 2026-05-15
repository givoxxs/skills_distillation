"""Skill Distillation Lab — FastAPI backend.

Serves Server-Sent Events for the /run page of the demo dashboard.
Frontend at http://localhost:3000 fetches POST /api/run then opens an
EventSource on /api/run/{id}/stream.

Data for the viewer pages is currently embedded in the Next.js frontend
(see frontend/lib/mock-data.ts); this backend only exposes /api/run and
/api/health. See HANDOFF.md for the plan to broaden data_loader endpoints
once we wire ``distillation_v2/run.py`` for real.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import HealthResponse
from app.routes import run as run_route

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

app.include_router(run_route.router)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
