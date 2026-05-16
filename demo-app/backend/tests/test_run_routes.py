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


def test_stream_emits_expected_event_schema(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Speed the replay up for the test — the full multi-round stream is
    # designed to run for ~120 s wall-clock in production, which would
    # blow up the pytest timeout.
    from app.services import runner as runner_module

    monkeypatch.setattr(runner_module, "SPEEDUP", 0.02)

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

    # Must visit every phase at least once, end with 'done'.
    statuses = [d["phase"] for e, d in parsed if e == "status"]
    assert {"queued", "running", "judging", "teacher", "done"}.issubset(set(statuses))
    assert statuses[0] == "queued"
    assert statuses[-1] == "done"

    # Multi-round replay: one round_started + one round_done per round.
    round_started = [d for e, d in parsed if e == "round_started"]
    round_done = [d for e, d in parsed if e == "round_done"]
    assert len(round_started) == len(round_done) >= 2
    rounds_sequence = [d["round"] for d in round_done]
    assert rounds_sequence == sorted(rounds_sequence), "rounds out of order"

    # test_case_done per TC per round.
    tc_done = [d for e, d in parsed if e == "test_case_done"]
    assert len(tc_done) >= len(round_done) * 3
    for d in tc_done:
        assert d["test_case_id"].startswith("tc_")
        assert 0.0 <= d["hybrid_score"] <= 1.0
        assert "round" in d

    # complete carries skill + final_score
    complete = [d for e, d in parsed if e == "complete"]
    assert len(complete) == 1
    assert complete[0]["skill"] == "docx"
    assert 0.0 <= complete[0]["final_score"] <= 1.0
