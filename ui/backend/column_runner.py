"""Column runner: wraps distillation_v2 sandbox + stream_parser for UI streaming."""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

# ── Paths ────────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DV2_PATH = _REPO_ROOT / "distillation_v2"

if str(_DV2_PATH) not in sys.path:
    sys.path.insert(0, str(_DV2_PATH))

from runner.sandbox import Sandbox  # noqa: E402
from runner.stream_parser import Event, ParserState, parse_line  # noqa: E402

ANTHROPIC_SKILLS_DIR = _REPO_ROOT / "anthropic_skills" / "skills"
LOGS_DIR = Path(__file__).parent / "logs"

BADGE_MAP: dict[str, str] = {
    "baseline": "Baseline",
    "default": "Default",
    "distilled": "Distilled",
    "ceiling": "Ceiling",
}

CLAUDE_MAX_TURNS = 20
CLAUDE_TIMEOUT = 300


# ── Public API ────────────────────────────────────────────────────────────────


def run_column(
    column_id: str,
    params: dict[str, Any],
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> None:
    """Blocking function: runs one column and puts events into `queue` (thread-safe)."""

    def emit(msg: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    def emit_line(text: str) -> None:
        emit({"column": column_id, "type": "line", "data": text})

    skill_name: str = params["skill"]
    student_model: str = params["studentModel"]
    ceiling_model: str = params["ceilingModel"]
    user_prompt: str = params["prompt"]

    if column_id == "ceiling":
        model = ceiling_model
        skill_dir: Path | None = ANTHROPIC_SKILLS_DIR / skill_name
        api_key = os.getenv("ANTHROPIC_KEY", "")
        base_url = None
    elif column_id == "baseline":
        model = student_model
        skill_dir = None
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = "https://openrouter.ai/api"
    else:  # "default" or "distilled"
        model = student_model
        skill_dir = ANTHROPIC_SKILLS_DIR / skill_name
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = "https://openrouter.ai/api"

    badge = BADGE_MAP.get(column_id, column_id.title())
    emit_line(f"[SYSTEM] Initializing {badge} | model: {model}")

    try:
        result = _run_one(
            column_id=column_id,
            user_prompt=user_prompt,
            skill_name=skill_name,
            skill_dir=skill_dir,
            model=model,
            api_key=api_key,
            base_url=base_url,
            emit_line=emit_line,
        )
        stop = result["stop_reason"]
        score = 1.0 if stop in ("success", "end_turn") else 0.0
        emit(
            {
                "column": column_id,
                "type": "done",
                "data": {
                    "stop_reason": stop,
                    "score": score,
                    "tools": result.get("iterations", 0),
                    "tokens": result.get("token_usage", {}).get("completion", 0),
                },
            }
        )
    except Exception as exc:
        emit_line(f"[ERROR] {type(exc).__name__}: {exc}")
        emit(
            {
                "column": column_id,
                "type": "done",
                "data": {"stop_reason": "error", "score": 0.0, "tools": 0, "tokens": 0},
            }
        )


# ── Internal runner ───────────────────────────────────────────────────────────


def _run_one(
    column_id: str,
    user_prompt: str,
    skill_name: str,
    skill_dir: Path | None,
    model: str,
    api_key: str,
    base_url: str | None,
    emit_line,
) -> dict[str, Any]:
    """Run Claude Code CLI in a sandbox; emit terminal lines; write JSONL log."""

    full_prompt = (
        f"Use skill {skill_name} to: {user_prompt}" if skill_dir else user_prompt
    )

    LOGS_DIR.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S")
    safe_model = model.replace("/", "_").replace(":", "_")
    log_path = LOGS_DIR / f"{column_id}__{skill_name}__{safe_model}__{ts}.jsonl"

    stop_reason = "unknown"
    iterations = 0
    tokens: dict[str, int] = {"prompt": 0, "completion": 0}
    log_records: list[dict] = []

    with Sandbox(
        name=f"ui-{column_id}",
        api_key=api_key,
        base_url=base_url,
        keep_on_fail=False,
    ) as sandbox:
        _setup_sandbox(sandbox, skill_name, skill_dir, model)

        cmd = [
            "claude",
            "--model",
            model,
            "-p",
            full_prompt,
            "--bare",
            "--verbose",
            "--output-format",
            "stream-json",
            "--dangerously-skip-permissions",
            "--max-turns",
            str(CLAUDE_MAX_TURNS),
        ]

        proc = subprocess.Popen(
            cmd,
            env=sandbox.env,
            cwd=str(sandbox.cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        state = ParserState()
        stderr_chunks: list[str] = []

        def _drain_stderr() -> None:
            if proc.stderr:
                data = proc.stderr.read()
                if data:
                    stderr_chunks.append(data)

        drainer = threading.Thread(target=_drain_stderr, daemon=True)
        drainer.start()

        try:
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                for event in parse_line(payload, state):
                    line = _format_event(event)
                    if line:
                        emit_line(line)
                    rec = _event_to_record(event)
                    if rec:
                        log_records.append(rec)
                    if event.kind == "end":
                        stop_reason = event.data.get("stop_reason", stop_reason)
                        iterations = event.data.get("iterations", iterations)
                        tokens = event.data.get("tokens", tokens)

            drainer.join(timeout=30)
            proc.wait(timeout=CLAUDE_TIMEOUT)

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
            stop_reason = "timeout"
            emit_line("[SYSTEM] Timeout reached — process killed")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

        if proc.returncode not in (0, None) and stop_reason == "unknown":
            stop_reason = f"cli_exit_{proc.returncode}"
            stderr = stderr_chunks[0][:300] if stderr_chunks else ""
            if stderr:
                emit_line(f"[ERROR] {stderr}")

    # Write JSONL log
    with open(log_path, "w", encoding="utf-8") as lf:
        for rec in log_records:
            lf.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {"stop_reason": stop_reason, "iterations": iterations, "token_usage": tokens}


def _setup_sandbox(
    sandbox: Sandbox,
    skill_name: str,
    skill_dir: Path | None,
    model: str,
) -> None:
    """Install skill into sandbox, or just write settings.json for baseline."""
    claude_dir = sandbox.home / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    settings: dict[str, Any] = {"autoCompactEnabled": False}
    if model:
        settings["model"] = model
    (claude_dir / "settings.json").write_text(
        json.dumps(settings, indent=2), encoding="utf-8"
    )

    if not skill_dir or not skill_dir.is_dir():
        return  # baseline: no skill

    # Copy entire skill folder → sandbox_home/.claude/skills/<name>/
    skills_dst = claude_dir / "skills" / skill_name
    shutil.copytree(skill_dir, skills_dst, dirs_exist_ok=True)

    # Write SKILL.md to cwd/CLAUDE.md so all models receive skill instructions
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        shutil.copy2(skill_md, sandbox.cwd / "CLAUDE.md")


# ── Event formatters ──────────────────────────────────────────────────────────


def _format_event(event: Event) -> str:
    d = event.data
    if event.kind == "start":
        sid = str(d.get("session_id", ""))[:16]
        return f"[SYSTEM] Session initialized | {sid}"
    if event.kind == "assistant_text":
        text = d.get("text", "")[:300].replace("\n", " ")
        return f"[AGENT] {text}"
    if event.kind == "tool_call":
        tool = d.get("tool", "?")
        args = str(d.get("args", {}))[:120].replace("\n", " ")
        return f"[TOOL_CALL] {tool}({args})"
    if event.kind == "tool_result":
        prefix = "[FAIL] " if d.get("is_error") else ""
        result = d.get("result", "")[:120].replace("\n", " ")
        return f"[TOOL_RESULT] {prefix}{result}"
    if event.kind == "end":
        stop = d.get("stop_reason", "?")
        iters = d.get("iterations", 0)
        dur = d.get("duration_seconds", 0)
        return f"[SYSTEM] {stop} | {iters} steps | {dur}s"
    if event.kind == "api_error":
        err = d.get("error", "")[:200]
        return f"[ERROR] {err}"
    return ""


def _event_to_record(event: Event) -> dict | None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    d = event.data
    if event.kind == "start":
        return {"event": "start", "ts": now, "session_id": d.get("session_id")}
    if event.kind == "assistant_text":
        return {
            "event": "assistant_text",
            "ts": now,
            "iteration": d.get("iteration", 0),
            "text": d.get("text", ""),
        }
    if event.kind == "tool_call":
        return {
            "event": "tool_call",
            "ts": now,
            "iteration": d.get("iteration", 0),
            "tool": d.get("tool"),
            "args": d.get("args", {}),
        }
    if event.kind == "tool_result":
        return {
            "event": "tool_result",
            "ts": now,
            "iteration": d.get("iteration", 0),
            "tool": d.get("tool"),
            "result": d.get("result", ""),
            "is_error": d.get("is_error", False),
        }
    if event.kind == "end":
        return {
            "event": "end",
            "ts": now,
            "iterations": d.get("iterations", 0),
            "stop_reason": d.get("stop_reason"),
            "duration_seconds": d.get("duration_seconds", 0),
            "tokens": d.get("tokens", {}),
        }
    if event.kind == "api_error":
        return {"event": "api_error", "ts": now, "error": d.get("error", "")}
    return None


# ── Log parsing for Trajectory tab ───────────────────────────────────────────


def parse_log_file(path: Path) -> dict | None:
    """Parse a JSONL log file written by run_column into a RunRecord dict."""
    stem = path.stem  # {column}__{skill}__{safe_model}__{ts}
    parts = stem.split("__")
    if len(parts) < 4:
        return None

    column_id, skill, safe_model, _ts = parts[0], parts[1], parts[2], parts[3]
    # Reconstruct model name heuristically: first "_" in safe_model is "/"
    model = safe_model.replace("_", "/", 1)

    badge = BADGE_MAP.get(column_id, column_id.title())

    records: list[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except Exception:
        return None

    if not records:
        return None

    stop_reason = "unknown"
    iterations = 0
    duration = 0.0
    trace: list[dict] = []

    for rec in records:
        evt = rec.get("event", "")
        if evt == "end":
            stop_reason = rec.get("stop_reason", "unknown")
            iterations = rec.get("iterations", 0)
            duration = rec.get("duration_seconds", 0.0)
            trace.append({"type": "end_turn", "content": stop_reason})
        elif evt == "assistant_text":
            trace.append({"type": "assistant", "content": rec.get("text", "")[:500]})
        elif evt == "tool_call":
            tool = rec.get("tool", "?")
            args = rec.get("args", {})
            trace.append(
                {
                    "type": "tool_call",
                    "toolName": tool,
                    "params": args,
                    "content": f"Calling {tool}...",
                }
            )
        elif evt == "tool_result":
            result = rec.get("result", "")
            is_err = rec.get("is_error", False)
            trace.append(
                {
                    "type": "tool_result",
                    "content": result[:200],
                    "result": {"output": result[:500], "is_error": is_err},
                }
            )
        elif evt == "api_error":
            trace.append(
                {
                    "type": "assistant",
                    "content": f"[ERROR] {rec.get('error', '')[:300]}",
                }
            )

    status = "pass" if stop_reason in ("success", "end_turn") else "fail"
    score = 1.0 if status == "pass" else 0.0

    return {
        "id": path.stem,
        "model": model,
        "badge": badge,
        "skill": skill,
        "status": status,
        "score": score,
        "stepsCount": iterations,
        "duration": f"{duration}s",
        "trace": trace,
    }
