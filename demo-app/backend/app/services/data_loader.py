"""Read summary.json + SKILL_round_*.md from distillation_v2/results/stable/.

This module is **read-only** — never writes back into the upstream repo.
Per HANDOFF.md, the stable results directory is the source of truth.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

from app.config import KNOWN_SKILLS, STABLE_DIR

_ROUND_RE = re.compile(r"^SKILL_round_(\d+)\.md$")


def _skill_dir(skill: str) -> Path:
    if skill not in KNOWN_SKILLS:
        raise HTTPException(status_code=404, detail=f"unknown skill: {skill}")
    path = STABLE_DIR / skill
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=502, detail=f"stable dir missing for {skill}")
    return path


@lru_cache(maxsize=8)
def _read_summary(skill: str, mtime: float) -> dict:
    """Cache keyed by (skill, mtime). New mtime → fresh read."""
    del mtime  # mtime is just a cache key; the real read uses skill.
    summary_path = _skill_dir(skill) / "summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=502, detail=f"summary.json missing for {skill}")
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=502, detail=f"summary.json invalid for {skill}: {e}"
        ) from e


def get_summary(skill: str) -> dict:
    summary_path = _skill_dir(skill) / "summary.json"
    return _read_summary(skill, summary_path.stat().st_mtime)


def list_skills() -> list[dict]:
    """Return a slim card for each known skill — drives the Overview page."""
    out = []
    for skill in KNOWN_SKILLS:
        if not (STABLE_DIR / skill).exists():
            continue
        s = get_summary(skill)
        out.append(
            {
                "name": skill,
                "rounds_run": s.get("rounds_run", 0),
                "final_score": s.get("final_score", 0.0),
                "best_score": s.get("best_score", 0.0),
                "best_round": s.get("best_round", 0),
                "student_model": s.get("student_model", ""),
                "teacher_model": s.get("teacher_model", ""),
            }
        )
    return out


def available_rounds(skill: str) -> list[int]:
    """List round numbers that have a SKILL_round_<N>.md file on disk."""
    rounds: list[int] = []
    for entry in _skill_dir(skill).iterdir():
        m = _ROUND_RE.match(entry.name)
        if m:
            rounds.append(int(m.group(1)))
    rounds.sort()
    return rounds


@lru_cache(maxsize=128)
def _read_skill_md(skill: str, round_n: int, mtime: float) -> str:
    del mtime
    path = _skill_dir(skill) / f"SKILL_round_{round_n}.md"
    return path.read_text(encoding="utf-8")


def get_skill_md(skill: str, round_n: int) -> tuple[int, str]:
    """Return (effective_round, content). Falls back to the closest *lower*
    round if the exact one is missing — matches the prototype's fill rule."""
    rounds = available_rounds(skill)
    if not rounds:
        raise HTTPException(status_code=502, detail=f"no SKILL_round_*.md for {skill}")

    if round_n in rounds:
        chosen = round_n
    else:
        prior = [r for r in rounds if r <= round_n]
        if not prior:
            chosen = rounds[0]
        else:
            chosen = max(prior)

    path = _skill_dir(skill) / f"SKILL_round_{chosen}.md"
    return chosen, _read_skill_md(skill, chosen, path.stat().st_mtime)
