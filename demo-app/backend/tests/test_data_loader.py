"""Unit tests for data_loader — direct calls into the service module
(no HTTP layer). Validates filesystem semantics: caching, fallbacks,
and 4xx mapping for unknown inputs."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.config import STABLE_DIR
from app.services import data_loader

requires_stable = pytest.mark.skipif(
    not STABLE_DIR.exists(),
    reason=f"distillation_v2 stable dir missing at {STABLE_DIR}",
)


def test_unknown_skill_raises_404() -> None:
    with pytest.raises(HTTPException) as exc:
        data_loader.get_summary("does-not-exist")
    assert exc.value.status_code == 404


@requires_stable
def test_get_summary_returns_full_history() -> None:
    s = data_loader.get_summary("docx")
    assert s["skill"] == "docx"
    assert len(s["score_history"]) == s["rounds_run"]
    assert 0.0 <= s["best_score"] <= 1.0


@requires_stable
def test_list_skills_keeps_canonical_order() -> None:
    skills = data_loader.list_skills()
    names = [s["name"] for s in skills]
    # Order in KNOWN_SKILLS is the canonical display order
    assert names == ["docx", "internal-comms", "slack-gif-creator"]


@requires_stable
def test_available_rounds_includes_zero() -> None:
    rounds = data_loader.available_rounds("docx")
    assert rounds == sorted(rounds)
    assert 0 in rounds


@requires_stable
def test_get_skill_md_exact_round() -> None:
    chosen, content = data_loader.get_skill_md("docx", 0)
    assert chosen == 0
    assert content.startswith("---")


@requires_stable
def test_get_skill_md_fallback_to_prior_round() -> None:
    # Pick a round that's certainly past the highest available
    chosen, _ = data_loader.get_skill_md("docx", 9999)
    assert chosen <= 9999
    assert chosen >= 0


@requires_stable
def test_summary_cache_returns_same_object_for_same_mtime() -> None:
    a = data_loader.get_summary("docx")
    b = data_loader.get_summary("docx")
    # LRU cache returns the same dict object for the same (skill, mtime) key
    assert a is b
