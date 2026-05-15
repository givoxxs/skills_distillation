"""Unit tests for stream_parser — offline, feeds canned stream-json fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.stream_parser import Event, ParserState, parse_line  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def _parse_file(filename: str) -> tuple[list[Event], ParserState]:
    state = ParserState()
    events: list[Event] = []
    with (FIXTURES / filename).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.extend(parse_line(json.loads(line), state))
    return events, state


# ── stream_success.jsonl ──────────────────────────────────────────────────────


def test_success_emits_start_then_tool_calls_then_end():
    events, state = _parse_file("stream_success.jsonl")
    kinds = [e.kind for e in events]
    assert kinds[0] == "start"
    assert kinds[-1] == "end"
    assert "tool_call" in kinds
    assert "tool_result" in kinds


def test_success_end_has_tokens_and_duration():
    events, _ = _parse_file("stream_success.jsonl")
    end = next(e for e in events if e.kind == "end")
    assert end.data["stop_reason"] == "success"
    assert end.data["duration_seconds"] == pytest.approx(12.35, abs=0.01)
    assert end.data["tokens"]["prompt"] == 100
    assert end.data["tokens"]["completion"] == 50
    assert end.data["tokens"]["total"] == 150


def test_success_tool_result_references_prior_tool_name():
    events, _ = _parse_file("stream_success.jsonl")
    results = [e for e in events if e.kind == "tool_result"]
    assert len(results) == 2
    assert results[0].data["tool"] == "bash"
    assert results[1].data["tool"] == "read_file"
    assert results[1].data["result"] == "hi"  # content-list was flattened to text


def test_success_iteration_increments_per_tool_call():
    events, state = _parse_file("stream_success.jsonl")
    calls = [e for e in events if e.kind == "tool_call"]
    assert [c.data["iteration"] for c in calls] == [1, 2]
    assert state.iteration == 2


def test_success_assistant_text_kept_distinct():
    events, _ = _parse_file("stream_success.jsonl")
    texts = [e for e in events if e.kind == "assistant_text"]
    assert len(texts) == 1
    assert "docx" in texts[0].data["text"].lower()


# ── stream_tool_error.jsonl ───────────────────────────────────────────────────


def test_tool_error_is_flagged_but_does_not_become_api_error():
    events, _ = _parse_file("stream_tool_error.jsonl")
    # tool_result has is_error=True but the stream ended with subtype=success,
    # so we should NOT emit an api_error event — only the tool-level flag.
    kinds = [e.kind for e in events]
    assert "api_error" not in kinds
    result = next(e for e in events if e.kind == "tool_result")
    assert result.data["is_error"] is True
    assert result.data["result"] == "exit code 1"


# ── stream_max_turns.jsonl ────────────────────────────────────────────────────


def test_max_turns_emits_api_error_plus_end():
    events, _ = _parse_file("stream_max_turns.jsonl")
    kinds = [e.kind for e in events]
    assert "api_error" in kinds
    assert kinds[-1] == "end"
    end = events[-1]
    assert end.data["stop_reason"] == "error_max_turns"


# ── Defensive behavior ────────────────────────────────────────────────────────


def test_unknown_type_does_not_crash():
    state = ParserState()
    events = parse_line({"type": "brand_new_event_type_2028", "payload": "x"}, state)
    assert len(events) == 1
    assert events[0].kind == "unknown"


def test_empty_line_payload_returns_empty():
    state = ParserState()
    assert parse_line({}, state) == []


def test_assistant_without_content_is_noop():
    state = ParserState()
    assert parse_line({"type": "assistant", "message": {}}, state) == []
    assert parse_line({"type": "assistant", "message": {"content": []}}, state) == []


def test_tool_result_list_content_coalesced():
    """Claude Code sometimes sends content as a list of {type:text,text:...} blocks."""
    state = ParserState()
    parse_line(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "id": "tu-a", "name": "bash", "input": {}}
                ]
            },
        },
        state,
    )
    events = parse_line(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tu-a",
                        "content": [
                            {"type": "text", "text": "line 1"},
                            {"type": "text", "text": "line 2"},
                        ],
                    }
                ]
            },
        },
        state,
    )
    assert len(events) == 1
    assert events[0].data["result"] == "line 1\nline 2"


def test_truncation_of_large_tool_result():
    state = ParserState()
    state.tool_names["tu-x"] = "bash"
    big = "x" * 5000
    events = parse_line(
        {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "tu-x", "content": big}
                ]
            },
        },
        state,
    )
    assert events[0].data["result"].endswith("[truncated]")
    assert len(events[0].data["result"]) < 5000
