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
) -> list[dict[str, Any]]:
    """Select n test cases for post-Teacher validation.

    When round_results is provided, picks the top-N scoring TCs from the round.
    Falls back to random selection when round_results is absent or insufficient.
    """
    if round_results:
        score_by_id = {r.test_case_id: r.hybrid_score for r in round_results}
        ranked = sorted(
            all_tcs, key=lambda tc: score_by_id.get(tc["id"], 0.0), reverse=True
        )
        return ranked[: min(n, len(ranked))]
    rng = random.Random(seed)
    return rng.sample(all_tcs, min(n, len(all_tcs)))


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
        emit(f"  [validation] running {len(validation_tcs)} TC(s) with new SKILL.md...")
        results = run_batch_fn(validation_tcs)
        if not results:
            emit("  [validation] no results — treating as 0.0")
            return 0.0
        avg = sum(r.hybrid_score for r in results) / len(results)
        emit(f"  [validation] avg_score={avg:.3f}")
        return avg
    finally:
        try:
            skill_md_path.write_text(original, encoding="utf-8")
        except Exception as exc:
            emit(f"  [validation] CRITICAL: failed to restore SKILL.md: {exc}")
            _log.error("Failed to restore SKILL.md at %s: %s", skill_md_path, exc)


def decide(
    new_score: float,
    baseline_score: float,
    threshold: float,
    emit: Callable[[str], None],
) -> bool:
    """Return True (keep new SKILL.md) or False (rollback).

    Keep when: new_score >= baseline_score - threshold
    Rollback when: new_score < baseline_score - threshold
    Tie (equal): keep new.
    """
    delta = new_score - baseline_score
    keep = new_score >= baseline_score - threshold
    if keep:
        emit(f"  [rollback] KEEP new SKILL.md (Δ={delta:+.3f}, threshold={threshold})")
    else:
        emit(
            f"  [rollback] ROLLBACK to old SKILL.md " f"(Δ={delta:+.3f} < -{threshold})"
        )
    return keep
