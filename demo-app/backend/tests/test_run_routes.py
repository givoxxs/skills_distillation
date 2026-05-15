"""Tests for /api/run — POST returns a run_id, GET /stream emits SSE
events that match the documented schema."""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


def test_run_rejects_unknown_skill(client: TestClient) -> None:
    r = client.post("/api/run", json={"skill": "not-a-skill"})
    assert r.status_code == 422  # Pydantic validation error


@pytest.mark.parametrize("skill", ["docx", "internal-comms", "slack-gif-creator"])
def test_run_returns_run_id(client: TestClient, skill: str) -> None:
    r = client.post("/api/run", json={"skill": skill})
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body
    assert re.fullmatch(r"[0-9a-f]{12}", body["run_id"])


def test_stream_404_for_unknown_run(client: TestClient) -> None:
    r = client.get("/api/run/does-not-exist/stream")
    assert r.status_code == 404


def test_stream_emits_expected_event_schema(client: TestClient) -> None:
    create = client.post("/api/run", json={"skill": "docx"})
    run_id = create.json()["run_id"]

    # Collect the full SSE stream — simulated runner finishes in ~30s
    # wall-clock at SPEEDUP=0.35; if it ever slows down dramatically
    # we'll hear about it in the test runtime.
    with client.stream("GET", f"/api/run/{run_id}/stream") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        raw = "".join(chunk for chunk in r.iter_text())

    # Parse SSE blocks
    blocks = [b for b in raw.strip().split("\n\n") if b.strip()]
    parsed: list[tuple[str, dict]] = []
    for b in blocks:
        lines = b.split("\n")
        event = next(
            (ln[len("event: ") :] for ln in lines if ln.startswith("event:")), None
        )
        data_ln = next(
            (ln[len("data: ") :] for ln in lines if ln.startswith("data:")), None
        )
        if event and data_ln:
            parsed.append((event, json.loads(data_ln)))

    events = [e for e, _ in parsed]

    # Ordering invariants
    assert events[0] == "status"
    assert parsed[0][1]["phase"] == "queued"
    assert events[-1] == "complete"

    # Must hit every phase in order
    statuses = [d["phase"] for e, d in parsed if e == "status"]
    expected_phases = ["queued", "running", "judging", "teacher", "done"]
    assert statuses == expected_phases, statuses

    # 3 test_case_done events with scores in [0.55, 0.98]
    tc_done = [d for e, d in parsed if e == "test_case_done"]
    assert len(tc_done) == 3
    for d in tc_done:
        assert d["test_case_id"].startswith("tc_a")
        assert 0.55 <= d["hybrid_score"] <= 0.98

    # round_done + complete carry consistent final_score
    round_done = [d for e, d in parsed if e == "round_done"]
    complete = [d for e, d in parsed if e == "complete"]
    assert len(round_done) == 1
    assert len(complete) == 1
    assert round_done[0]["round"] == 1
    assert complete[0]["skill"] == "docx"
    assert complete[0]["final_score"] == round_done[0]["avg_score"]
