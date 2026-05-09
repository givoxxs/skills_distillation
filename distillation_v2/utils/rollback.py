"""Rollback logic: run validation TCs, decide keep vs rollback SKILL.md."""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from evaluator.base import EvalResult

_log = logging.getLogger("distillation.v2.rollback")


def choose_validation_tcs(
    all_tcs: list[dict[str, Any]],
    n: int,
    round_results: list["EvalResult"] | None = None,
    seed: int | None = None,
) -> tuple[list[dict[str, Any]], float]:
    """Select TCs at rank 6-8 (by score) for post-Teacher validation.

    Returns (val_tcs, baseline_score) where baseline_score is the avg score
    of those TCs in the current round (with the old SKILL.md).

    Rank 6-8 are "borderline" TCs: not trivially easy (rank 1-5 ceiling at 1.0)
    and not always-failing. Their scores are sensitive to SKILL.md quality.

    Falls back to random selection when round_results is absent.
    """
    if round_results:
        score_by_id = {r.test_case_id: r.llm_judge_score for r in round_results}
        ranked = sorted(
            all_tcs, key=lambda tc: score_by_id.get(tc["id"], 0.0), reverse=True
        )
        # Take rank 6-8 (0-indexed: 5,6,7). If fewer TCs available, shift start left.
        start = min(5, max(0, len(ranked) - n))
        val_tcs = ranked[start : start + n]
        baseline = (
            sum(score_by_id.get(tc["id"], 0.0) for tc in val_tcs) / len(val_tcs)
            if val_tcs
            else 0.0
        )
        return val_tcs, baseline
    rng = random.Random(seed)
    val_tcs = rng.sample(all_tcs, min(n, len(all_tcs)))
    return val_tcs, 0.0


def run_validation(
    skill_md_path: Path,
    new_skill_content: str,
    validation_tcs: list[dict[str, Any]],
    run_batch_fn: Callable,
    emit: Callable[[str], None],
) -> float:
    """Write new SKILL.md temporarily, run validation TCs, return avg score.

    The original SKILL.md is restored after scoring regardless of outcome.
    `run_batch_fn` must have the same signature as pipeline._run_batch().
    """
    original = skill_md_path.read_text(encoding="utf-8")
    try:
        skill_md_path.write_text(new_skill_content, encoding="utf-8")
        emit(f"  [gate1] running {len(validation_tcs)} TC(s) with new SKILL.md...")
        results = run_batch_fn(validation_tcs)
        if not results:
            emit("  [gate1] no results — treating as 0.0")
            return 0.0
        avg = sum(r.llm_judge_score for r in results if r.llm_judge_score >= 0) / len(
            results
        )
        emit(f"  [gate1] val_score={avg:.3f}")
        return avg
    finally:
        try:
            skill_md_path.write_text(original, encoding="utf-8")
        except Exception as exc:
            emit(f"  [gate1] CRITICAL: failed to restore SKILL.md: {exc}")
            _log.error("Failed to restore SKILL.md at %s: %s", skill_md_path, exc)


def decide(
    val_score: float,
    baseline_score: float,
    threshold: float,
    emit: Callable[[str], None],
) -> bool:
    """Return True (keep new SKILL.md) or False (rollback).

    Keep when: val_score >= baseline_score - threshold
    baseline_score = avg score of val TCs in the previous round (old SKILL.md).
    """
    delta = val_score - baseline_score
    keep = val_score >= baseline_score - threshold
    if keep:
        emit(
            f"  [gate1] KEEP new SKILL.md (val={val_score:.3f}, baseline={baseline_score:.3f}, Δ={delta:+.3f})"
        )
    else:
        emit(
            f"  [gate1] ROLLBACK to old SKILL.md "
            f"(val={val_score:.3f} < baseline={baseline_score:.3f} - {threshold})"
        )
    return keep
