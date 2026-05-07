"""FastAPI backend for the Skill Distillation UI."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import mimetypes
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Load .env from repo root (OPENROUTER_API_KEY, ANTHROPIC_KEY)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_REPO_ROOT / ".env")

# Runner is in the same package
sys.path.insert(0, str(Path(__file__).parent))
from column_runner import (  # noqa: E402
    ANTHROPIC_SKILLS_DIR,
    LOGS_DIR,
    OUTPUTS_DIR,
    parse_log_file,
    run_column,
)

app = FastAPI(title="Skill Distillation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST endpoints ────────────────────────────────────────────────────────────


@app.get("/api/skills")
async def list_skills() -> list[str]:
    """Return available skill names from anthropic_skills/skills/."""
    if not ANTHROPIC_SKILLS_DIR.is_dir():
        return []
    return sorted(p.name for p in ANTHROPIC_SKILLS_DIR.iterdir() if p.is_dir())


@app.get("/api/runs")
async def list_runs() -> list[dict[str, Any]]:
    """Return all past run records parsed from JSONL logs."""
    LOGS_DIR.mkdir(exist_ok=True)
    runs: list[dict] = []
    for p in sorted(LOGS_DIR.glob("*.jsonl"), reverse=True):
        record = parse_log_file(p)
        if record:
            runs.append(record)
    return runs


@app.get("/api/runs/{run_id}/files")
async def list_run_files(run_id: str) -> list[str]:
    """List output files produced by a specific run."""
    out_dir = OUTPUTS_DIR / run_id
    if not out_dir.is_dir():
        return []
    return sorted(p.name for p in out_dir.iterdir() if p.is_file())


@app.get("/api/runs/{run_id}/files/{filename}")
async def get_run_file(run_id: str, filename: str) -> FileResponse:
    """Download a single output file from a run."""
    # Guard against path traversal
    out_dir = (OUTPUTS_DIR / run_id).resolve()
    file_path = (out_dir / filename).resolve()
    if not str(file_path).startswith(str(out_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type or "application/octet-stream",
    )


# ── WebSocket live run ────────────────────────────────────────────────────────


@app.websocket("/ws/run")
async def ws_run(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        params: dict[str, Any] = json.loads(raw)
    except Exception as exc:
        await websocket.send_json({"type": "error", "data": str(exc)})
        await websocket.close()
        return

    columns: list[str] = params.get(
        "columns", ["baseline", "default", "distilled", "ceiling"]
    )

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    done_set: set[str] = set()

    # Launch each column in a thread executor so blocking code doesn't stall the loop
    futures = [
        loop.run_in_executor(None, run_column, col, params, loop, queue)
        for col in columns
    ]

    # Drain queue until all columns have emitted "done"
    try:
        while len(done_set) < len(columns):
            msg = await asyncio.wait_for(queue.get(), timeout=360)
            await websocket.send_json(msg)
            if msg.get("type") == "done":
                done_set.add(msg["column"])

        # Wait for all executor futures (cleanup)
        await asyncio.gather(*futures, return_exceptions=True)
        await websocket.send_json({"type": "all_done"})
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        await websocket.send_json(
            {"type": "error", "data": "Timed out waiting for column results"}
        )
    finally:
        await websocket.close()
