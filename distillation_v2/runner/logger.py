"""JSONL execution logger."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AgentLogger:
    """Write structured JSONL logs for each agent execution."""

    def __init__(self, log_dir: str, skill_name: str, model: str) -> None:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        safe_model = model.replace("/", "_").replace(":", "_")
        filename = f"{skill_name}_{safe_model}_{ts}.jsonl"
        self._path = os.path.join(log_dir, filename)
        self._fh = open(self._path, "w", encoding="utf-8")

    def __enter__(self) -> "AgentLogger":
        return self

    def __exit__(self, *_) -> None:
        if not self._fh.closed:
            self._fh.close()

    def __del__(self) -> None:
        """Safety net: close file handle if log_end() was never called (e.g. exception)."""
        if hasattr(self, "_fh") and not self._fh.closed:
            self._fh.close()

    def _write(self, record: dict[str, Any]) -> None:
        record["ts"] = datetime.now(timezone.utc).isoformat()
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()

    def log_start(self, skill: str, model: str, prompt: str) -> None:
        self._write(
            {"event": "start", "skill": skill, "model": model, "prompt": prompt}
        )

    def log_event(self, iteration: int, event: str, data: dict[str, Any]) -> None:
        self._write({"event": event, "iteration": iteration, **data})

    def log_tool_call(self, iteration: int, tool: str, args: dict[str, Any]) -> None:
        self._write(
            {"event": "tool_call", "iteration": iteration, "tool": tool, "args": args}
        )

    def log_tool_result(self, iteration: int, tool: str, result: str) -> None:
        self._write(
            {
                "event": "tool_result",
                "iteration": iteration,
                "tool": tool,
                "result": result[:500],
            }
        )

    def log_error(self, iteration: int, error: str) -> None:
        self._write({"event": "api_error", "iteration": iteration, "error": error})

    def log_end(
        self, iterations: int, stop_reason: str, duration: float, tokens: dict[str, int]
    ) -> None:
        self._write(
            {
                "event": "end",
                "iterations": iterations,
                "stop_reason": stop_reason,
                "duration_seconds": round(duration, 2),
                "tokens": tokens,
            }
        )
        # File is closed by __exit__ (context manager) or __del__ (safety net).
        # Closing here would cause a double-close if the logger is used as a
        # context manager, since __exit__ also calls close.

    @property
    def log_path(self) -> str:
        return self._path
