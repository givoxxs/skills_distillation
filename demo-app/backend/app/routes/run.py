from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import RunRequest, RunResponse
from app.services import runner

router = APIRouter()


@router.post("/api/run", response_model=RunResponse)
async def start_run(req: RunRequest) -> RunResponse:
    run = runner.create_run(req.skill)
    return RunResponse(run_id=run.run_id)


@router.get("/api/run/{run_id}/stream")
async def stream_run(run_id: str):
    run = runner.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")

    return StreamingResponse(
        runner.stream_events(run),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
