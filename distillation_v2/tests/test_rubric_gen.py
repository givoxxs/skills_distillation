"""Tests for stages/rubric_gen.py.

Unit tests run without API keys.
Live test (test_rubric_gen_live_criteria_count) requires ANTHROPIC_KEY — run manually:
    pytest tests/test_rubric_gen.py -v -k live
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stages.rubric_gen import _cache_key, _parse_and_validate, _skill_md_hash


# ── Cache key helpers ─────────────────────────────────────────────────────────


def test_cache_key_deterministic():
    k1 = _cache_key("skill content", ["tc_a01", "tc_b02"])
    k2 = _cache_key("skill content", ["tc_a01", "tc_b02"])
    assert k1 == k2


def test_cache_key_changes_on_skill_change():
    k1 = _cache_key("skill v1", ["tc_a01"])
    k2 = _cache_key("skill v2", ["tc_a01"])
    assert k1 != k2


def test_cache_key_changes_on_tc_change():
    k1 = _cache_key("same skill", ["tc_a01"])
    k2 = _cache_key("same skill", ["tc_a01", "tc_b02"])
    assert k1 != k2


def test_skill_md_hash_returns_empty_when_missing(tmp_path):
    assert _skill_md_hash(tmp_path) == ""


def test_skill_md_hash_changes_on_content_change(tmp_path):
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("version 1")
    h1 = _skill_md_hash(tmp_path)
    skill_md.write_text("version 2")
    h2 = _skill_md_hash(tmp_path)
    assert h1 != h2


# ── Response parser ───────────────────────────────────────────────────────────


def _valid_criteria(n: int = 5) -> list[dict]:
    weight = round(1.0 / n, 6)
    return [
        {
            "name": f"C{i}",
            "description": f"desc {i}",
            "weight": weight,
            "pass_threshold": 0.6,
        }
        for i in range(n)
    ]


def test_parse_valid_json():
    raw = json.dumps({"criteria": _valid_criteria(5), "notes": "ok"})
    result = _parse_and_validate(raw)
    assert len(result["criteria"]) == 5
    assert abs(sum(c["weight"] for c in result["criteria"]) - 1.0) < 1e-3


def test_parse_strips_markdown_fence():
    inner = json.dumps({"criteria": _valid_criteria(3), "notes": "ok"})
    raw = f"```json\n{inner}\n```"
    result = _parse_and_validate(raw)
    assert len(result["criteria"]) == 3


def test_parse_normalizes_weights():
    criteria = [
        {"name": "A", "description": "d", "weight": 2.0, "pass_threshold": 0.6},
        {"name": "B", "description": "d", "weight": 3.0, "pass_threshold": 0.6},
    ]
    raw = json.dumps({"criteria": criteria, "notes": "ok"})
    result = _parse_and_validate(raw)
    weights = [c["weight"] for c in result["criteria"]]
    assert abs(sum(weights) - 1.0) < 1e-6
    assert abs(weights[0] - 0.4) < 1e-6
    assert abs(weights[1] - 0.6) < 1e-6


def test_parse_rejects_missing_criteria():
    with pytest.raises((ValueError, KeyError)):
        _parse_and_validate(json.dumps({"notes": "missing criteria"}))


def test_parse_rejects_missing_criterion_field():
    criteria = [
        {"name": "X", "description": "d", "weight": 1.0}
    ]  # missing pass_threshold
    with pytest.raises(ValueError, match="pass_threshold"):
        _parse_and_validate(json.dumps({"criteria": criteria}))


# ── Live test (requires ANTHROPIC_KEY) ───────────────────────────────────────


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_KEY"),
    reason="ANTHROPIC_KEY not set — live API test skipped",
)
def test_rubric_gen_live_criteria_count(tmp_path):
    """Call real API and print how many criteria the LLM generates.

    Run with: pytest tests/test_rubric_gen.py -v -k live -s
    """
    from stages.rubric_gen import generate_rubric

    skill_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "skill_runner"
        / "skills"
        / "docx"
    )
    if not skill_dir.is_dir():
        pytest.skip("docx skill_dir not found")

    sample_tcs = [
        {
            "id": "tc_a01",
            "prompt": "Create a simple Word document with a title.",
            "expected_behavior": "Valid .docx file",
        },
        {
            "id": "tc_b01",
            "prompt": "Read and summarize a Word document.",
            "expected_behavior": "Summary text",
        },
        {
            "id": "tc_c01",
            "prompt": "Edit a Word document to change heading styles.",
            "expected_behavior": "Modified .docx",
        },
        {
            "id": "tc_d01",
            "prompt": "Convert a .doc to .docx format.",
            "expected_behavior": "Valid .docx",
        },
        {
            "id": "tc_e01",
            "prompt": "Handle a corrupted Word file gracefully.",
            "expected_behavior": "Error message or partial output",
        },
    ]

    rubric = generate_rubric(
        skill_name="docx",
        skill_dir=skill_dir,
        test_cases=sample_tcs,
        cache_dir=str(tmp_path / "rubrics"),
        regenerate=True,
    )

    n_criteria = len(rubric["criteria"])
    print(f"\n[LIVE] Generated {n_criteria} criteria:")
    for c in rubric["criteria"]:
        print(f"  - {c['name']} (w={c['weight']:.3f}): {c['description'][:60]}")
    print(f"  Notes: {rubric.get('notes', '')}")

    assert n_criteria >= 4, f"Expected at least 4 criteria, got {n_criteria}"
    assert abs(sum(c["weight"] for c in rubric["criteria"]) - 1.0) < 1e-3
