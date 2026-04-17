"""Parse Claude Code CLI `--output-format stream-json` into v1 log events.

Claude Code prints one JSON object per line. Observed shapes (schema may drift):

  {"type":"system","subtype":"init","session_id":"...","model":"...","tools":[...]}
  {"type":"assistant","message":{"id":"...","content":[{"type":"text","text":"..."},
                                                        {"type":"tool_use","id":"...","name":"...","input":{...}}]}}
  {"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"...","content":"...","is_error":false}]}}
  {"type":"result","subtype":"success","duration_ms":...,"usage":{...},"result":"..."}
  {"type":"result","subtype":"error_max_turns",...}

We map these to v1's AgentLogger events (see skill_runner/runner/logger.py):
  - start:       {skill, model, prompt}
  - tool_call:   {iteration, tool, args}
  - tool_result: {iteration, tool, result}
  - assistant_text: {iteration, text}  (v2-only convenience event; kept distinct from v1 schema)
  - end:         {iterations, stop_reason, duration_seconds, tokens}
  - api_error:   {iteration, error}

Unknown event types are returned as a single `unknown` event with the raw payload
(truncated) so debugging is still possible without crashing the runner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger("distillation.v2.stream_parser")

_MAX_RESULT_CHARS = 2000  # log truncation for tool_result bodies
_MAX_TEXT_CHARS = 4000  # log truncation for assistant text blocks


@dataclass
class Event:
    """Normalized event emitted for each parsed stream-json line."""

    kind: str  # "start" | "tool_call" | "tool_result" | "assistant_text" | "end" | "api_error" | "unknown"
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParserState:
    """Mutable state carried across calls to parse_line().

    Tracks the current iteration counter (a rough proxy for tool-call depth)
    and the tool_use id → name mapping so tool_result events can be labeled.
    """

    iteration: int = 0
    tool_names: dict[str, str] = field(default_factory=dict)  # tool_use_id → name
    started: bool = False


def parse_line(raw: dict[str, Any], state: ParserState) -> list[Event]:
    """Translate ONE stream-json line into zero or more v1-schema events.

    Args:
        raw:   The decoded JSON object from one line of `claude --output-format
               stream-json` stdout.
        state: Mutable parser state carried across calls.

    Returns: List of Event — empty if the line had no mappable content.
    """
    t = raw.get("type")
    if not t:
        return []

    if t == "system":
        return _handle_system(raw, state)
    if t == "assistant":
        return _handle_assistant(raw, state)
    if t == "user":
        return _handle_user(raw, state)
    if t == "result":
        return _handle_result(raw, state)

    _log.debug("stream_parser: unknown type %r", t)
    return [Event("unknown", {"raw_type": t, "payload": _truncate_str(raw, 500)})]


# ── Per-type handlers ───────────────────────────────────────────────────────────


def _handle_system(raw: dict, state: ParserState) -> list[Event]:
    subtype = raw.get("subtype")
    if subtype == "init":
        state.started = True
        return [
            Event(
                "start",
                {
                    "session_id": raw.get("session_id"),
                    "model": raw.get("model"),
                    "tools": raw.get("tools", []),
                    "cwd": raw.get("cwd"),
                },
            )
        ]
    return []


def _handle_assistant(raw: dict, state: ParserState) -> list[Event]:
    msg = raw.get("message") or {}
    content = msg.get("content") or []
    out: list[Event] = []
    for block in content:
        btype = block.get("type")
        if btype == "tool_use":
            state.iteration += 1
            tool_name = block.get("name", "?")
            tool_id = block.get("id")
            if tool_id:
                state.tool_names[tool_id] = tool_name
            out.append(
                Event(
                    "tool_call",
                    {
                        "iteration": state.iteration,
                        "tool": tool_name,
                        "args": block.get("input", {}),
                        "tool_use_id": tool_id,
                    },
                )
            )
        elif btype == "text":
            text = (block.get("text") or "").strip()
            if text:
                out.append(
                    Event(
                        "assistant_text",
                        {
                            "iteration": state.iteration,
                            "text": _truncate_str(text, _MAX_TEXT_CHARS),
                        },
                    )
                )
    return out


def _handle_user(raw: dict, state: ParserState) -> list[Event]:
    msg = raw.get("message") or {}
    content = msg.get("content") or []
    out: list[Event] = []
    for block in content:
        if block.get("type") != "tool_result":
            continue
        tool_id = block.get("tool_use_id")
        tool_name = state.tool_names.get(tool_id, "?")
        body = block.get("content")
        out.append(
            Event(
                "tool_result",
                {
                    "iteration": state.iteration,
                    "tool": tool_name,
                    "result": _stringify_result(body),
                    "is_error": bool(block.get("is_error", False)),
                    "tool_use_id": tool_id,
                },
            )
        )
    return out


def _handle_result(raw: dict, state: ParserState) -> list[Event]:
    subtype = raw.get("subtype", "")
    is_error = subtype != "success"
    usage = raw.get("usage") or {}
    tokens = {
        "prompt": usage.get("input_tokens", 0),
        "completion": usage.get("output_tokens", 0),
        "total": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
    }
    duration_ms = raw.get("duration_ms", 0)
    events: list[Event] = []
    if is_error:
        events.append(
            Event(
                "api_error",
                {
                    "iteration": state.iteration,
                    "error": raw.get("result") or subtype or "unknown_error",
                },
            )
        )
    events.append(
        Event(
            "end",
            {
                "iterations": state.iteration,
                "stop_reason": subtype or ("success" if not is_error else "error"),
                "duration_seconds": round(duration_ms / 1000.0, 2),
                "tokens": tokens,
                "final_text": _truncate_str(raw.get("result", ""), _MAX_TEXT_CHARS),
            },
        )
    )
    return events


# ── Helpers ───────────────────────────────────────────────────────────────────


def _stringify_result(body: Any) -> str:
    """tool_result `content` can be a str, a list of content blocks, or None."""
    if body is None:
        return ""
    if isinstance(body, str):
        return _truncate_str(body, _MAX_RESULT_CHARS)
    if isinstance(body, list):
        parts: list[str] = []
        for b in body:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(str(b.get("text", "")))
            elif isinstance(b, str):
                parts.append(b)
            else:
                parts.append(str(b))
        return _truncate_str("\n".join(parts), _MAX_RESULT_CHARS)
    return _truncate_str(str(body), _MAX_RESULT_CHARS)


def _truncate_str(value: Any, limit: int) -> str:
    s = value if isinstance(value, str) else str(value)
    if len(s) <= limit:
        return s
    return s[:limit] + "... [truncated]"
