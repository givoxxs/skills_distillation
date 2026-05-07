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
OUTPUTS_DIR = Path(__file__).parent / "outputs"

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
        prompt = f"Use skill {skill_name} to: {user_prompt}"
    elif column_id == "baseline":
        model = student_model
        skill_dir = None  # no skill at all
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = "https://openrouter.ai/api"
        prompt = user_prompt  # raw prompt, nothing added
    else:  # "default" or "distilled"
        model = student_model
        skill_dir = ANTHROPIC_SKILLS_DIR / skill_name
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = "https://openrouter.ai/api"
        prompt = f"Use skill {skill_name} to: {user_prompt}"

    badge = BADGE_MAP.get(column_id, column_id.title())
    emit_line(f"[SYSTEM] Initializing {badge} | model: {model}")

    try:
        result = _run_one(
            column_id=column_id,
            prompt=prompt,
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
                    "output_files": result.get("output_files", []),
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
    prompt: str,  # final prompt passed to claude — caller decides content
    skill_name: str,  # for log filename only
    skill_dir: Path | None,
    model: str,
    api_key: str,
    base_url: str | None,
    emit_line,
) -> dict[str, Any]:
    """Run Claude Code CLI in a sandbox; emit terminal lines; write JSONL log.

    `prompt` is passed verbatim to `claude -p`.  For baseline (no skill) the
    caller must pass the raw user prompt; for skill columns the caller should
    already have constructed the skill-aware prompt.  This function never
    injects skill context by itself.
    """

    LOGS_DIR.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S")
    safe_model = model.replace("/", "_").replace(":", "_")
    log_stem = f"{column_id}__{skill_name}__{safe_model}__{ts}"
    log_path = LOGS_DIR / f"{log_stem}.jsonl"

    stop_reason = "unknown"
    iterations = 0
    tokens: dict[str, int] = {"prompt": 0, "completion": 0}
    log_records: list[dict] = []
    output_files: list[str] = []

    with Sandbox(
        name=f"ui-{column_id}",
        api_key=api_key,
        base_url=base_url,
        keep_on_fail=False,
    ) as sandbox:
        _setup_sandbox(sandbox, skill_name, skill_dir, model)

        start_ts = time.time()

        # For skill columns, explicitly point --add-dir at cwd so CLAUDE.md is
        # loaded even under --bare (which skips auto-discovery).
        cmd = [
            "claude",
            "--model",
            model,
            "-p",
            prompt,
            "--bare",
            "--verbose",
            "--output-format",
            "stream-json",
            "--dangerously-skip-permissions",
            "--max-turns",
            str(CLAUDE_MAX_TURNS),
        ]
        if skill_dir is not None:
            cmd += ["--add-dir", str(sandbox.cwd)]

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
        stderr_lines: list[str] = []

        def _drain_stderr() -> None:
            """Stream stderr line-by-line so we don't miss output from crashes."""
            if proc.stderr:
                for line in proc.stderr:
                    line = line.strip()
                    if line:
                        stderr_lines.append(line)

        drainer = threading.Thread(target=_drain_stderr, daemon=True)
        drainer.start()

        # Watchdog: kill process if it exceeds CLAUDE_TIMEOUT total seconds.
        _killed_by_watchdog = threading.Event()

        def _watchdog() -> None:
            if not _killed_by_watchdog.wait(timeout=CLAUDE_TIMEOUT):
                # Timeout expired — cancel was never called, so kill process.
                if proc.poll() is None:
                    proc.kill()
                    _killed_by_watchdog.set()  # reuse as "was killed" flag

        watchdog = threading.Thread(target=_watchdog, daemon=True)
        watchdog.start()

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
        finally:
            _killed_by_watchdog.set()  # signal watchdog to stop waiting
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
            drainer.join(timeout=10)

        if _killed_by_watchdog.is_set() and stop_reason == "unknown":
            stop_reason = "timeout"
            emit_line(f"[SYSTEM] Timeout after {CLAUDE_TIMEOUT}s — process killed")

        if proc.returncode not in (0, None):
            if stop_reason == "unknown":
                stop_reason = f"cli_exit_{proc.returncode}"
            # Always surface stderr so the user sees API errors, auth failures, etc.
            if stderr_lines:
                emit_line(f"[STDERR] {' | '.join(stderr_lines[:5])[:400]}")

        # ── Copy output files out before sandbox is destroyed ─────────────────
        produced = sandbox.list_outputs(since_ts=start_ts)
        if produced:
            out_dir = OUTPUTS_DIR / log_stem
            out_dir.mkdir(parents=True, exist_ok=True)
            for src in produced:
                dst = out_dir / src.name
                shutil.copy2(src, dst)
                output_files.append(src.name)
                emit_line(f"[OUTPUT] {src.name} ({src.stat().st_size} bytes)")
            log_records.append(
                {
                    "event": "output_files",
                    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "files": output_files,
                }
            )

    # Write JSONL log
    with open(log_path, "w", encoding="utf-8") as lf:
        for rec in log_records:
            lf.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {
        "stop_reason": stop_reason,
        "iterations": iterations,
        "token_usage": tokens,
        "output_files": output_files,
    }


def _setup_sandbox(
    sandbox: Sandbox,
    skill_name: str,
    skill_dir: Path | None,
    model: str,
) -> None:
    """Write settings.json, then install skill if skill_dir is provided."""
    _write_settings(sandbox, model)
    if skill_dir and skill_dir.is_dir():
        _install_skill(sandbox, skill_name, skill_dir)


def _write_settings(sandbox: Sandbox, model: str) -> None:
    """Write ~/.claude/settings.json — the only thing baseline gets."""
    claude_dir = sandbox.home / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings: dict[str, Any] = {"autoCompactEnabled": False}
    if model:
        settings["model"] = model
    (claude_dir / "settings.json").write_text(
        json.dumps(settings, indent=2), encoding="utf-8"
    )


def _install_skill(sandbox: Sandbox, skill_name: str, skill_dir: Path) -> None:
    """Copy skill files into sandbox and write CLAUDE.md to cwd."""
    claude_dir = sandbox.home / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    skills_dst = claude_dir / "skills" / skill_name
    shutil.copytree(skill_dir, skills_dst, dirs_exist_ok=True)

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
    output_files: list[str] = []

    for rec in records:
        evt = rec.get("event", "")
        if evt == "end":
            stop_reason = rec.get("stop_reason", "unknown")
            iterations = rec.get("iterations", 0)
            duration = rec.get("duration_seconds", 0.0)
            trace.append({"type": "end_turn", "content": stop_reason})
        elif evt == "output_files":
            output_files = rec.get("files", [])
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
        "outputFiles": output_files,
    }
