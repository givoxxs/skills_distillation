"""Core agentic loop: call model → execute tools → loop or stop."""

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from config import RunConfig
from runner.openrouter_client import create_openrouter_client, call_with_retry
from runner.skill_loader import load_skill, list_skill_files
from runner.prompt_builder import build_system_prompt, build_system_prompt_no_skill
from runner.tool_definitions import get_tool_definitions
from runner.tool_executor import execute_tool
from runner.logger import AgentLogger

console = Console()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _bash_fingerprint(cmd: str) -> str:
    """Return a fingerprint key for a bash command.

    Splits on `&&`/`;` and returns the first non-trivial command token.
    This allows each command in a chain to be tracked independently.
    E.g. "cd foo && node bar" → "node"; "npm install; node server" → "npm"
    """
    # Strip leading "cd /path && cd /path &&" prefixes
    stripped = re.sub(r"^(cd\s+\S+\s*&&\s*)+", "", cmd.strip()).strip()
    return stripped.split()[0] if stripped else "bash"


def _trim_messages(messages: list[dict], window: int) -> list[dict]:
    """Compress old tool-call/result pairs to prevent O(n²) token growth.

    Keeps the initial user message plus the last `window` assistant turns in full.
    Turns older than the window are replaced by a single compact summary message so
    the model retains context of what it has already done without re-sending full
    bash outputs.

    A "turn" is one assistant message (possibly containing tool_calls) plus all
    the immediately following tool-result messages.
    """
    if not messages:
        return messages

    # Split into: [user_msg] + [turns...]
    # A turn boundary = every assistant message in the list.
    user_msg = messages[0]
    history = messages[1:]

    # Partition history into turns: each turn starts with an assistant message.
    turns: list[list[dict]] = []
    current: list[dict] = []
    for msg in history:
        if msg.get("role") == "assistant":
            if current:
                turns.append(current)
            current = [msg]
        else:
            current.append(msg)
    if current:
        turns.append(current)

    if len(turns) <= window:
        return messages  # nothing to trim

    old_turns = turns[:-window]
    keep_turns = turns[-window:]

    # Build compact summary from old turns
    lines: list[str] = []
    for turn in old_turns:
        asst = turn[0]
        tool_calls = asst.get("tool_calls") or []
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "?")
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {}
            if name == "bash":
                cmd = args.get("command", "")[:120]
                lines.append(f"- bash: {cmd!r}")
            elif name in ("read_file", "write_file"):
                lines.append(f"- {name}: {args.get('path','?')}")
            elif name == "end_turn":
                lines.append("- end_turn called")
            else:
                lines.append(f"- {name}")
        # Append tool result summary (first 80 chars of each result)
        for msg in turn[1:]:
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") for c in content if isinstance(c, dict)
                )
            snippet = str(content)[:80].replace("\n", " ")
            lines.append(f"  → {snippet}")

    summary_content = "Summary of earlier steps (already done):\n" + "\n".join(lines)
    summary_msg = {"role": "user", "content": summary_content}

    result = [user_msg, summary_msg]
    for turn in keep_turns:
        result.extend(turn)
    return result


# Directories/files kept across workspace cleans (npm cache, installed packages).
# These are expensive to reinstall and safe to reuse between runs.
_WORKSPACE_PERSISTENT = {
    "_skills",
    ".npm",
    "node_modules",
    "package.json",
    "package-lock.json",
    "Library",
}

# Same set excluded when copying outputs — they are build artifacts, not results.
_OUTPUT_EXCLUDE = {
    "_skills",
    ".npm",
    "node_modules",
    "package.json",
    "package-lock.json",
    "Library",
}


def _clean_workspace(workspace_dir: str, preserve: list[str] | None = None) -> None:
    """Remove all workspace contents except persistent dirs and any user input files."""
    ws = Path(workspace_dir)
    ws.mkdir(parents=True, exist_ok=True)
    keep = _WORKSPACE_PERSISTENT | set(preserve or [])
    for item in ws.iterdir():
        if item.name in keep:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def _collect_output_files(
    workspace_dir: str,
    output_dir: str,
    input_files: list[str] | None = None,
) -> list[str]:
    """Copy output files from workspace to output_dir, skipping build artifacts.

    Excludes: _skills/, .npm/, node_modules/, package.json, package-lock.json.
    Also excludes any files whose name matches input_files (e.g. fixture copies).
    Returns list of destination paths.
    """
    ws = Path(workspace_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Normalize input filenames to a set of basenames for O(1) lookup
    exclude_basenames: set[str] = {Path(f).name for f in (input_files or [])}
    copied = []
    for item in ws.rglob("*"):
        # Skip excluded top-level dirs (check every ancestor at ws depth)
        rel = item.relative_to(ws)
        if rel.parts[0] in _OUTPUT_EXCLUDE:
            continue
        # Skip files that are fixture/input file copies (same basename as injected files)
        if item.name in exclude_basenames:
            continue
        if item.is_dir():
            continue
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, dest)
        copied.append(str(dest))
    return copied


def run_agent(
    user_prompt: str,
    skill_name: str | None,
    model: str,
    config: RunConfig,
) -> dict[str, Any]:
    """
    Run the main agentic loop.

    Stop conditions (in priority order):
    1. model calls end_turn tool → stop_reason = "end_turn"
    2. finish_reason == "stop" with no tool_calls → stop_reason = "natural_stop"
    3. No tool_calls in response → stop_reason = "no_tool_calls"
    4. max_iterations reached → stop_reason = "max_iterations"
    5. API error → stop_reason = "api_error"

    Args:
        user_prompt: The user's task description.
        skill_name: Skill folder name, or None for bare-tools mode.
        model: OpenRouter model ID (e.g. "qwen/qwen3-8b").
        config: RunConfig instance.

    Returns:
        Dict with keys: messages, iterations, stop_reason, model, skill,
        duration_seconds, token_usage.
    """
    config.validate()

    # 1. Clean workspace (keep _skills/ and any user-supplied input files)
    _clean_workspace(config.workspace_dir, preserve=config.input_files)
    workspace_abs = os.path.abspath(config.workspace_dir)

    # 2. Load skill (if specified)
    skill_path = workspace_abs  # fallback: point to workspace itself
    input_note = ""
    if config.input_files:
        file_list = "\n".join(f"  {workspace_abs}/{f}" for f in config.input_files)
        input_note = f"\n\n## Input Files\nThe following files have been placed in your workspace for this task:\n{file_list}"

    if skill_name:
        try:
            skill_content, skill_path, _ = load_skill(
                skill_name, config.skills_dir, config.workspace_dir
            )
            skill_files = list_skill_files(skill_path)
            system_prompt = (
                build_system_prompt(
                    skill_content=skill_content,
                    skill_path=skill_path,
                    skill_files=skill_files,
                    workspace_path=workspace_abs,
                )
                + input_note
            )
        except FileNotFoundError as e:
            raise ValueError(f"Cannot load skill '{skill_name}': {e}") from e
    else:
        system_prompt = (
            build_system_prompt_no_skill(workspace_path=workspace_abs) + input_note
        )

    # 3. Init state
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]
    tools = get_tool_definitions()
    client = create_openrouter_client(config.api_key, config.base_url)
    # Keep only the last N full tool-call/result pairs in the message list.
    # Older pairs are collapsed into a single summary message to prevent O(n²)
    # token growth. The user turn at index 0 is always preserved.
    _HISTORY_WINDOW = 4  # number of recent assistant+tool_result pairs to keep in full
    logger = AgentLogger(
        log_dir=config.log_dir,
        skill_name=skill_name or "none",
        model=model,
    )

    logger.log_start(skill_name or "none", model, user_prompt)
    start_time = time.time()
    stop_reason = "max_iterations"
    total_tokens: dict[str, int] = {"prompt": 0, "completion": 0}
    iteration = 0
    # Track consecutive errors per (tool, command_fingerprint) to detect loops.
    # For bash: split by `&&`/`;` and track each distinct command independently.
    # json_parse_error is also tracked — loop intervention triggers after MAX_CONSECUTIVE_ERRORS.
    consecutive_errors: dict[str, int] = {}
    MAX_CONSECUTIVE_ERRORS = 2  # Warn after 2 identical failures, not 3

    if config.verbose:
        console.print(
            Panel(
                f"[bold]Model:[/bold] {model}\n[bold]Skill:[/bold] {skill_name or 'none'}\n[bold]Prompt:[/bold] {user_prompt[:200]}",
                title="Agent Run Started",
            )
        )

    # 4. Agentic loop
    for iteration in range(config.max_iterations):
        # === API call ===
        try:
            trimmed = _trim_messages(messages, _HISTORY_WINDOW)
            response = call_with_retry(
                lambda: client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}] + trimmed,
                    tools=tools,
                    tool_choice="auto",
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    extra_headers={
                        "HTTP-Referer": "https://github.com/skill-distillation",
                        "X-Title": "Skill Runner",
                    },
                )
            )
        except Exception as e:
            logger.log_error(iteration, str(e))
            stop_reason = "api_error"
            break

        # Track tokens
        if response.usage:
            total_tokens["prompt"] += response.usage.prompt_tokens or 0
            total_tokens["completion"] += response.usage.completion_tokens or 0

        choice = response.choices[0]
        assistant_msg = choice.message

        # === Build assistant message dict ===
        msg_dict: dict[str, Any] = {
            "role": "assistant",
            "content": assistant_msg.content or "",
        }
        if assistant_msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_msg.tool_calls
            ]
        messages.append(msg_dict)

        # === Stop condition: model finished naturally ===
        if choice.finish_reason not in ("tool_calls", "function_call"):
            if not assistant_msg.tool_calls:
                logger.log_event(
                    iteration, "natural_stop", {"finish_reason": choice.finish_reason}
                )
                stop_reason = "natural_stop"
                break

        # === Stop condition: no tool calls ===
        if not assistant_msg.tool_calls:
            logger.log_event(iteration, "no_tool_calls", {})
            stop_reason = "no_tool_calls"
            break

        tool_calls = assistant_msg.tool_calls
        has_end_turn = any(tc.function.name == "end_turn" for tc in tool_calls)

        if config.verbose:
            tool_names = [tc.function.name for tc in tool_calls]
            console.print(f"[dim]Iteration {iteration + 1}[/dim] → tools: {tool_names}")

        # === Execute non-end_turn tools ===
        tool_results: list[dict[str, Any]] = []

        for tc in tool_calls:
            if tc.function.name == "end_turn":
                continue

            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError as parse_err:
                logger.log_event(
                    iteration,
                    "json_parse_error",
                    {
                        "tool": tc.function.name,
                        "error": str(parse_err),
                    },
                )
                # Track consecutive parse errors — same fingerprint logic as execute errors
                if tc.function.name == "bash":
                    # The JSON parsing already failed, so tc.function.arguments is raw text.
                    # Try to extract "command" field manually before the parse error position.
                    cmd_str = ""
                    raw = tc.function.arguments
                    key = r'"command"\s*:\s*"'
                    start = raw.find(key)
                    if start >= 0:
                        val_start = raw.find('"', start + len(key)) + 1
                        val_end = raw.find('"', val_start)
                        if val_end > val_start:
                            cmd_str = raw[val_start:val_end]
                    tool_key = f"bash:{_bash_fingerprint(cmd_str)}"
                else:
                    tool_key = tc.function.name

                consecutive_errors[tool_key] = consecutive_errors.get(tool_key, 0) + 1
                is_loop = consecutive_errors[tool_key] >= MAX_CONSECUTIVE_ERRORS

                base_msg = (
                    f"ERROR: Could not parse tool arguments as JSON: {parse_err}. "
                    "If writing a large file, try writing it in chunks using bash with a heredoc, "
                    "or break the content into smaller write_file calls."
                )
                if is_loop:
                    base_msg = (
                        f"{base_msg}\n\n"
                        f"LOOP DETECTED: '{tool_key}' has produced {consecutive_errors[tool_key]} "
                        f"consecutive parse errors. You MUST change your approach — do NOT repeat the same command. "
                        "Alternative strategies:\n"
                        "- If using bash heredoc with large content, split into multiple write_file calls instead\n"
                        "- If a script has a JSON syntax error, read the script with read_file, fix it, then retry\n"
                        "- If the tool is receiving corrupted arguments, try a completely different approach\n"
                        "If you cannot complete the task, call end_turn with an explanation."
                    )
                    logger.log_event(
                        iteration,
                        "loop_detected",
                        {"tool": tool_key, "count": consecutive_errors[tool_key]},
                    )
                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": base_msg,
                    }
                )
                continue

            logger.log_tool_call(iteration, tc.function.name, args)

            result = execute_tool(
                tool_name=tc.function.name,
                arguments=args,
                workspace=workspace_abs,
                skill_path=skill_path,
                timeout=config.bash_timeout,
            )

            # Track consecutive errors per (tool, command_fingerprint) to detect loops.
            # For bash: split by `&&`/`;` and track each distinct command independently.
            # This prevents a `node` failure from masking an `npm install` failure in the same call.
            if tc.function.name == "bash":
                cmd = args.get("command", "").strip()
                # Split on `&&` or `;` and track each command independently
                parts = re.split(r"\s+&&\s+|\s+;\s+", cmd)
                first_key = f"bash:{_bash_fingerprint(parts[0])}"
                tool_key = first_key
                # Reset errors for ALL other bash fingerprints in this call
                for p in parts[1:]:
                    other = f"bash:{_bash_fingerprint(p)}"
                    if other != first_key:
                        consecutive_errors[other] = 0
            else:
                tool_key = tc.function.name

            is_error = result.startswith("ERROR:") or "[EXIT CODE]:" in result
            if is_error:
                consecutive_errors[tool_key] = consecutive_errors.get(tool_key, 0) + 1
                if consecutive_errors[tool_key] >= MAX_CONSECUTIVE_ERRORS:
                    result = (
                        f"{result}\n\n"
                        f"⚠️ LOOP DETECTED: '{tool_key}' has failed {consecutive_errors[tool_key]} times in a row. "
                        "You MUST change your approach — do NOT repeat the same command. "
                        "Alternative strategies:\n"
                        "- bash sed fails: use write_file to rewrite the file instead\n"
                        "- bash node fails 'Cannot find module': run `npm install <pkg>` (local, not -g) in the same directory as your script\n"
                        "- bash npm install loops: the package is already installed — move on\n"
                        "- bash script fails: read the error carefully, fix the script with write_file, then retry\n"
                        "If you cannot complete the task, call end_turn with an explanation."
                    )
                    logger.log_event(
                        iteration,
                        "loop_detected",
                        {"tool": tool_key, "count": consecutive_errors[tool_key]},
                    )
            else:
                consecutive_errors[tool_key] = 0  # reset on success

            logger.log_tool_result(iteration, tc.function.name, result)

            if config.verbose:
                preview = result[:200].replace("\n", " ")
                console.print(f"  [green]{tc.function.name}[/green] → {preview}")

            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

        # === Handle end_turn ===
        if has_end_turn:
            for tc in tool_calls:
                if tc.function.name != "end_turn":
                    continue
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"summary": "Task completed"}

                summary = args.get("summary", "Task completed")
                logger.log_event(iteration, "end_turn", {"summary": summary})

                if config.verbose:
                    console.print(
                        Panel(
                            f"[bold green]end_turn:[/bold green] {summary}",
                            title="Agent Done",
                        )
                    )

                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"Turn ended. Summary: {summary}",
                    }
                )

            messages.extend(tool_results)
            stop_reason = "end_turn"
            break

        messages.extend(tool_results)

    else:
        logger.log_event(config.max_iterations - 1, "max_iterations_reached", {})

    duration = time.time() - start_time

    # Collect output files before workspace gets cleaned by the next run
    output_files: list[str] = []
    if config.output_dir:
        output_files = _collect_output_files(
            workspace_abs, config.output_dir, input_files=config.input_files
        )
        logger.log_event(
            iteration,
            "output_collected",
            {
                "output_dir": config.output_dir,
                "files": output_files,
            },
        )

    logger.log_end(iteration + 1, stop_reason, duration, total_tokens)

    return {
        "messages": messages,
        "iterations": iteration + 1,
        "stop_reason": stop_reason,
        "model": model,
        "skill": skill_name or "none",
        "duration_seconds": round(duration, 2),
        "token_usage": total_tokens,
        "output_files": output_files,
        "output_dir": config.output_dir,
        "log_file": Path(logger.log_path).name,
    }
