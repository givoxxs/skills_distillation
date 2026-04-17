"""Claude Code CLI runner — replaces v1's skill_runner.

Exposes `run_agent(...)` with the same return-dict shape as v1's
skill_runner.runner.agent_loop.run_agent, so the orchestrator interface stays
stable. Internally:

  1. Load SKILL.md, inline it into the prompt.
  2. Open a Sandbox with explicit env (OpenRouter key + base URL, fresh HOME).
  3. Copy any input fixtures into sandbox cwd.
  4. Invoke `claude --output-format stream-json` via subprocess.Popen with
     env=sandbox.env and cwd=sandbox.cwd.
  5. Stream stdout line-by-line → parse → write v1-schema JSONL via AgentLogger.
  6. On completion: copy new files from sandbox cwd to output_dir.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import RunConfigV2
from .sandbox import Sandbox
from .stream_parser import Event, ParserState, parse_line


def _load_v1_agent_logger():
    """Load v1's AgentLogger by absolute path to avoid the runner/runner
    package-name collision with skill_runner.runner."""
    v1_logger_path = (
        Path(__file__).resolve().parent.parent.parent
        / "skill_runner"
        / "runner"
        / "logger.py"
    )
    spec = importlib.util.spec_from_file_location("_v1_logger", v1_logger_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AgentLogger


AgentLogger = _load_v1_agent_logger()

_log = logging.getLogger("distillation.v2.claude_code_runner")


# ── SKILL.md loading ─────────────────────────────────────────────────────────


def _load_skill_md(skills_dir: str, skill_name: str) -> str:
    """Read SKILL.md for the given skill, stripping YAML frontmatter if present."""
    path = Path(skills_dir) / skill_name / "SKILL.md"
    if not path.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {path}")
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            content = content[end + 4 :].lstrip()
    return content


def _build_prompt(skill_md: str, user_prompt: str, input_files: list[Path]) -> str:
    """Inline SKILL.md + input file references + the user task into one prompt."""
    input_section = ""
    if input_files:
        listing = "\n".join(f"  - {p.name}" for p in input_files)
        input_section = (
            "\n\n## Input Files\nThe following files are in your current directory:\n"
            f"{listing}\n"
        )
    return (
        "You are an agent that follows the skill instructions below to complete "
        "the user task. Write output files to your current working directory. "
        "When done, produce a short final text summary.\n\n"
        "---\n\n"
        f"# Skill Instructions\n\n{skill_md}\n\n"
        "---\n"
        f"{input_section}"
        f"\n## Task\n\n{user_prompt}\n"
    )


# ── Event → v1 log mapping ───────────────────────────────────────────────────


def _emit(logger: AgentLogger, event: Event) -> None:
    """Forward a parsed Event to v1's AgentLogger schema."""
    d = event.data
    if event.kind == "start":
        # We already called log_start() with the raw prompt before streaming began;
        # don't re-emit here. Instead, log as generic event.
        logger.log_event(
            0,
            "cli_init",
            {"session_id": d.get("session_id"), "tools": d.get("tools", [])},
        )
    elif event.kind == "tool_call":
        logger.log_tool_call(d["iteration"], d["tool"], d.get("args", {}))
    elif event.kind == "tool_result":
        prefix = "[ERROR] " if d.get("is_error") else ""
        logger.log_tool_result(d["iteration"], d["tool"], prefix + d.get("result", ""))
    elif event.kind == "assistant_text":
        logger.log_event(d["iteration"], "assistant_text", {"text": d["text"]})
    elif event.kind == "api_error":
        logger.log_error(d.get("iteration", 0), d.get("error", ""))
    elif event.kind == "end":
        logger.log_end(
            iterations=d.get("iterations", 0),
            stop_reason=d.get("stop_reason", "unknown"),
            duration=d.get("duration_seconds", 0.0),
            tokens=d.get("tokens", {"prompt": 0, "completion": 0}),
        )
    elif event.kind == "unknown":
        logger.log_event(0, "unknown_stream_event", d)


# ── Output collection ────────────────────────────────────────────────────────


def _copy_outputs(sandbox: Sandbox, since_ts: float, output_dir: Path) -> list[str]:
    """Copy all new files from sandbox cwd to output_dir. Returns copied paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for src in sandbox.list_outputs(since_ts):
        rel = src.relative_to(sandbox.cwd)
        dst = output_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst))
    return copied


# ── Public entrypoint ────────────────────────────────────────────────────────


def run_agent(
    user_prompt: str,
    skill_name: str,
    model: str,
    config: RunConfigV2,
) -> dict[str, Any]:
    """Execute one task via Claude Code CLI inside a sandbox.

    Return dict matches v1's shape:
      {messages, iterations, stop_reason, model, skill, duration_seconds,
       token_usage, output_files, log_file}
    """
    config.validate()
    skill_md = _load_skill_md(config.skills_dir, skill_name)
    full_prompt = _build_prompt(skill_md, user_prompt, config.input_files)

    # v1-compatible JSONL log file
    logger = AgentLogger(log_dir=config.log_dir, skill_name=skill_name, model=model)
    logger.log_start(skill_name, model, user_prompt)

    stop_reason = "unknown"
    iterations = 0
    tokens = {"prompt": 0, "completion": 0}
    final_text = ""
    output_files: list[str] = []
    start_ts = time.time()

    try:
        with Sandbox(
            name=f"student-{skill_name}",
            api_key=config.openrouter_api_key,
            base_url=config.openrouter_base_url,
            parent_tmp=Path(os.path.expanduser(config.sandbox_tmp_root)),
            keep_on_fail=config.sandbox_keep_on_fail,
            claude_binary=config.claude_binary,
        ) as sandbox:
            # Copy fixtures into sandbox cwd
            for f in config.input_files:
                if Path(f).is_file():
                    sandbox.copy_input(Path(f))

            run_start_ts = time.time()  # for output file mtime filter
            stop_reason, iterations, tokens, final_text = _invoke_claude_stream(
                full_prompt=full_prompt,
                model=model,
                config=config,
                sandbox=sandbox,
                logger=logger,
            )

            if config.output_dir:
                output_files = _copy_outputs(
                    sandbox,
                    since_ts=run_start_ts,
                    output_dir=Path(config.output_dir),
                )
    except Exception as e:  # noqa: BLE001
        _log.error("run_agent failed: %s", e, exc_info=config.verbose)
        stop_reason = f"runner_error: {type(e).__name__}"
        logger.log_error(0, str(e))
        duration = time.time() - start_ts
        logger.log_end(iterations, stop_reason, duration, tokens)

    return {
        "messages": [{"role": "user", "content": user_prompt}],
        "iterations": iterations,
        "stop_reason": stop_reason,
        "model": model,
        "skill": skill_name,
        "duration_seconds": round(time.time() - start_ts, 2),
        "token_usage": tokens,
        "output_files": output_files,
        "log_file": logger.log_path,
        "final_text": final_text,
    }


# ── Internal: subprocess + streaming loop ────────────────────────────────────


def _invoke_claude_stream(
    full_prompt: str,
    model: str,
    config: RunConfigV2,
    sandbox: Sandbox,
    logger: AgentLogger,
) -> tuple[str, int, dict[str, int], str]:
    """Run the `claude` subprocess, stream-parse stdout, forward to logger.

    Returns (stop_reason, iterations, tokens, final_text).
    """
    cmd = [
        config.claude_binary,
        "--model",
        model,
        "-p",
        full_prompt,
        "--verbose",
        "--output-format",
        "stream-json",
        "--dangerously-skip-permissions",
        "--max-turns",
        str(config.max_turns),
    ]

    if config.verbose:
        _log.info("Invoking: %s ... (cwd=%s)", " ".join(cmd[:6]) + " ...", sandbox.cwd)

    proc = subprocess.Popen(
        cmd,
        env=sandbox.env,
        cwd=str(sandbox.cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # line-buffered
    )

    state = ParserState()
    stop_reason = "no_end_event"
    iterations = 0
    tokens = {"prompt": 0, "completion": 0}
    final_text = ""

    try:
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                _log.debug("non-json line from claude CLI: %s", raw_line[:200])
                continue
            for event in parse_line(payload, state):
                _emit(logger, event)
                if event.kind == "end":
                    stop_reason = event.data.get("stop_reason", stop_reason)
                    iterations = event.data.get("iterations", iterations)
                    tokens = event.data.get("tokens", tokens)
                    final_text = event.data.get("final_text", "")

        # Wait for process cleanup within timeout
        try:
            _, stderr_text = proc.communicate(timeout=config.timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr_text = proc.communicate()
            stop_reason = "timeout"

        if proc.returncode != 0 and stop_reason == "no_end_event":
            stop_reason = f"cli_exit_{proc.returncode}"
            if stderr_text:
                logger.log_error(iterations, stderr_text.strip()[:500])
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    return stop_reason, iterations, tokens, final_text
