"""Tests for /api/skills/* routes — reads real files from
distillation_v2/results/stable/.

These tests require the upstream pipeline data to exist on disk (the
default DISTILL_REPO_ROOT in app.config). If the directory is missing
the tests are skipped, not failed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import STABLE_DIR

EXPECTED_SKILLS = {"docx", "internal-comms", "slack-gif-creator"}

requires_stable = pytest.mark.skipif(
    not STABLE_DIR.exists(),
    reason=f"distillation_v2 stable dir missing at {STABLE_DIR}",
)


@requires_stable
def test_list_skills(client: TestClient) -> None:
    r = client.get("/api/skills")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    names = {s["name"] for s in body}
    assert EXPECTED_SKILLS.issubset(names)
    for s in body:
        # Schema sanity
        assert s["rounds_run"] >= 1
        assert 0.0 <= s["final_score"] <= 1.0
        assert 0.0 <= s["best_score"] <= 1.0
        assert s["best_round"] >= 0


@requires_stable
@pytest.mark.parametrize("skill", sorted(EXPECTED_SKILLS))
def test_get_summary(client: TestClient, skill: str) -> None:
    r = client.get(f"/api/skills/{skill}/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["skill"] == skill
    assert "score_history" in body
    assert len(body["score_history"]) == body["rounds_run"]
    # First round score is R1 — must be a valid number
    assert body["score_history"][0]["round"] == 1


def test_summary_unknown_skill_returns_404(client: TestClient) -> None:
    r = client.get("/api/skills/does-not-exist/summary")
    assert r.status_code == 404


@requires_stable
def test_available_rounds(client: TestClient) -> None:
    r = client.get("/api/skills/docx/available-rounds")
    assert r.status_code == 200
    rounds = r.json()["rounds"]
    assert isinstance(rounds, list)
    assert 0 in rounds  # always has SKILL_round_0.md
    assert rounds == sorted(rounds)  # returned sorted


@requires_stable
def test_skill_md_real_round(client: TestClient) -> None:
    r = client.get("/api/skills/docx/skill-md?round=0")
    assert r.status_code == 200
    body = r.json()
    assert body["round"] == 0
    assert body["requested_round"] == 0
    assert body["fallback"] is False
    # SKILL_round_0.md must contain the YAML frontmatter marker
    assert body["content"].startswith("---")
    assert "name: docx" in body["content"]


@requires_stable
def test_skill_md_fallback_for_missing_round(client: TestClient) -> None:
    # round 999 doesn't exist for any skill — should fall back to closest prior
    r = client.get("/api/skills/docx/skill-md?round=999")
    assert r.status_code == 200
    body = r.json()
    assert body["requested_round"] == 999
    assert body["fallback"] is True
    assert body["round"] != 999
    assert body["round"] >= 0
