"""Distillation v2 pipeline — main orchestration loop.

Flow per round:
  1. Run all batches (student → judge → run_log.md).
  2. Teacher reads ALL run_logs → generates SKILL_candidate.md.
  3. Validation: run 3 random TCs with SKILL_candidate.md.
  4. Keep candidate if val_score >= round_avg - rollback_threshold, else rollback.
  5. Check stopping criteria.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluator.base import EvalResult
from runner.config import RunConfigV2
from stages.judge import Judge
from stages.rubric_gen import generate_rubric
from stages.student import make_skip_result, run_student
from stages.summarizer import make_run_log
from stages.teacher import rewrite as teacher_rewrite
from utils import get_logger, write_api_call, write_eval_detail
from utils.rollback import choose_validation_tcs, decide, run_validation

_log = get_logger("v2.pipeline")


# ── Public entry point ────────────────────────────────────────────────────────


def run_distillation(
    skill: str,
    test_cases: list[dict[str, Any]],
    student_model: str,
    teacher_model: str = "claude-haiku-4-5",
    judge_model: str = "claude-haiku-4-5",
    anthropic_key: str | None = None,
    max_rounds: int = 3,
    batch_size: int = 5,
    stop_threshold: float = 0.7,
    converge_delta: float = 0.02,
    converge_k: int = 3,
    rollback_threshold: float = 0.05,
    validation_tc_count: int = 3,
    max_retry_per_tc: int = 3,
    max_image_pages: int = 10,
    results_dir: str = "./results",
    rubric_cache_dir: str = "./rubrics",
    skills_dir: str | None = None,
    test_cases_dir: str | None = None,
    regenerate_rubric: bool = True,
    watch_skill_hash: bool = False,
    keep_recent_rubrics: int = 5,
    ensemble_n: int = 1,
    sandbox_tmp_root: str = "~/.cache/distill_v2",
    sandbox_keep_on_fail: bool = True,
    claude_binary: str = "claude",
    verbose: bool = False,
    dry_run: bool = False,
    resume: bool = False,
) -> dict[str, Any]:
    anthropic_key = anthropic_key or os.getenv("ANTHROPIC_KEY")
    if not anthropic_key:
        raise RuntimeError("ANTHROPIC_KEY not set")

    v2_root = Path(__file__).resolve().parent
    results_path = Path(results_dir) / skill
    results_path.mkdir(parents=True, exist_ok=True)

    skills_dir = skills_dir or str(v2_root / "skills")
    test_cases_dir = test_cases_dir or str(v2_root / "test_cases")
    skill_dir = Path(skills_dir) / skill
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        raise FileNotFoundError(f"SKILL.md not found: {skill_md_path}")

    # ── Fresh-run cleanup (skip when resuming) ────────────────────────────────
    # Without --resume, wipe the entire skill results dir so each run starts
    # with a clean slate (no stale round dirs, logs, JSONL files, or SKILL
    # snapshots from a previous run).
    if not resume and results_path.exists():
        shutil.rmtree(results_path)
    results_path.mkdir(parents=True, exist_ok=True)

    # working_md is the mutable copy; original skill_md_path is never modified.
    working_md = results_path / "SKILL_current.md"
    if not working_md.exists():
        shutil.copy2(skill_md_path, working_md)

    # ── Rubric (once per pipeline run) ───────────────────────────────────────
    rubric = generate_rubric(
        skill_name=skill,
        skill_dir=skill_dir,
        test_cases=test_cases,
        cache_dir=rubric_cache_dir,
        model=judge_model,
        regenerate=regenerate_rubric,
        watch_skill_hash=watch_skill_hash,
        keep_recent=keep_recent_rubrics,
        anthropic_api_key=anthropic_key,
    )
    judge = Judge(
        rubric=rubric,
        model=judge_model,
        ensemble_n=ensemble_n,
        max_image_pages=max_image_pages,
        anthropic_api_key=anthropic_key,
    )

    # ── Run config for student ────────────────────────────────────────────────
    base_config = RunConfigV2(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        claude_binary=claude_binary,
        skills_dir=skills_dir,
        log_dir=str(v2_root / "logs"),
        sandbox_tmp_root=sandbox_tmp_root,
        sandbox_keep_on_fail=sandbox_keep_on_fail,
        verbose=verbose,
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    run_log_file = open(
        results_path / "run.log", "w" if not resume else "a", buffering=1
    )

    def emit(msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        run_log_file.write(line + "\n")
        if verbose:
            print(line, flush=True)

    eff_batch = (
        batch_size if (batch_size and batch_size < len(test_cases)) else len(test_cases)
    )
    n_batches = math.ceil(len(test_cases) / eff_batch)

    emit("=" * 60)
    emit(f"V2 START  skill={skill}  student={student_model}  teacher={teacher_model}")
    emit(f"Rubric: {len(rubric['criteria'])} criteria")
    emit(f"TCs: {len(test_cases)}  batches/round={n_batches}  batch_size={eff_batch}")
    if validation_tc_count == 0:
        emit("Rollback: DISABLED (--no-rollback)")
    else:
        emit(
            f"Rollback threshold: {rollback_threshold}  validation_tcs: {validation_tc_count}"
        )
    emit("=" * 60)

    _save_skill_version(working_md, results_path, round_n=0)

    history: list[dict] = []
    prev_avg: float | None = None
    recent_deltas: list[float] = []

    for round_n in range(1, max_rounds + 1):
        emit(f"\n--- Round {round_n}/{max_rounds} ---")
        round_start = time.time()
        all_results: list[EvalResult] = []
        run_logs: list[str] = []
        batch_log_paths: list[list[str]] = []

        batches = [
            test_cases[i : i + eff_batch] for i in range(0, len(test_cases), eff_batch)
        ]

        # ── Run all batches ───────────────────────────────────────────────────
        for batch_idx, batch in enumerate(batches, 1):
            if resume and _is_batch_complete(results_path, round_n, batch_idx):
                cached = _load_cached_batch(
                    results_path, round_n, batch_idx, batch, skill, student_model
                )
                all_results.extend(cached)
                emit(f"  [R{round_n}.B{batch_idx}] resumed ({len(cached)} tc)")
                continue

            emit(
                f"  [R{round_n}.B{batch_idx}/{n_batches}] running {len(batch)} TC(s)..."
            )
            batch_start = time.time()
            batch_results, batch_logs = _run_batch(
                batch=batch,
                skill=skill,
                student_model=student_model,
                judge=judge,
                results_path=results_path,
                test_cases_dir=test_cases_dir,
                base_config=base_config,
                round_n=round_n,
                batch_idx=batch_idx,
                max_retry_per_tc=max_retry_per_tc,
                current_skill_md=working_md,
                emit=emit,
            )
            all_results.extend(batch_results)
            batch_log_paths.append(batch_logs)

            # Generate run_log.md for this batch
            run_log_content = make_run_log(
                batch_results, round_n, batch_idx, batch_logs
            )
            run_log_path = (
                results_path / f"round_{round_n}" / f"batch_{batch_idx}" / "run_log.md"
            )
            run_log_path.parent.mkdir(parents=True, exist_ok=True)
            run_log_path.write_text(run_log_content, encoding="utf-8")
            run_logs.append(run_log_content)

            elapsed = time.time() - batch_start
            avg = (
                sum(r.hybrid_score for r in batch_results) / len(batch_results)
                if batch_results
                else 0.0
            )
            passed = sum(1 for r in batch_results if r.hybrid_score >= 0.6)
            emit(
                f"  [R{round_n}.B{batch_idx}] {passed}/{len(batch_results)} passed  avg={avg:.3f}  ({elapsed:.1f}s)"
            )
            _save_batch_scores(results_path, round_n, batch_idx, batch_results)
            for r in batch_results:
                write_eval_detail({"round": round_n, "batch": batch_idx, **asdict(r)})

        round_avg = (
            sum(r.hybrid_score for r in all_results) / len(all_results)
            if all_results
            else 0.0
        )

        # ── Teacher rewrite (once per round) ─────────────────────────────────
        if not dry_run and run_logs:
            emit(f"  Teacher rewriting SKILL.md from {len(run_logs)} run_log(s)...")
            teacher_start = time.time()
            try:
                new_skill = teacher_rewrite(
                    skill_md_path=working_md,
                    run_logs=run_logs,
                    model=teacher_model,
                    round_n=round_n,
                    anthropic_api_key=anthropic_key,
                )

                emit(
                    f"  Teacher done ({len(new_skill)} chars, {time.time() - teacher_start:.1f}s)"
                )

                # ── Validation + rollback ─────────────────────────────────────
                if validation_tc_count == 0:
                    # --no-rollback: always keep new SKILL.md without validation
                    emit("  [rollback] DISABLED — keeping new SKILL.md unconditionally")
                    working_md.write_text(new_skill, encoding="utf-8")
                else:
                    val_tcs = choose_validation_tcs(
                        test_cases, validation_tc_count, round_results=all_results
                    )

                    def _val_batch(tcs: list[dict]) -> list[EvalResult]:
                        results, _ = _run_batch(
                            batch=tcs,
                            skill=skill,
                            student_model=student_model,
                            judge=judge,
                            results_path=results_path
                            / "validation"
                            / f"round_{round_n}",
                            test_cases_dir=test_cases_dir,
                            base_config=base_config,
                            round_n=round_n,
                            batch_idx=0,
                            max_retry_per_tc=max_retry_per_tc,
                            current_skill_md=working_md,
                            emit=emit,
                        )
                        return results

                    val_score = run_validation(
                        skill_md_path=working_md,
                        new_skill_content=new_skill,
                        validation_tcs=val_tcs,
                        run_batch_fn=_val_batch,
                        emit=emit,
                    )
                    keep = decide(val_score, round_avg, rollback_threshold, emit)
                    if keep:
                        working_md.write_text(new_skill, encoding="utf-8")
                    # else: working_md unchanged (old content stays)

            except Exception as e:  # noqa: BLE001
                emit(f"  Teacher FAILED: {e}. Skipping rewrite.")
                write_api_call({"type": "teacher", "error": str(e), "round": round_n})
        elif dry_run:
            emit("  DRY RUN — skipping Teacher + rollback.")

        # ── Round summary ─────────────────────────────────────────────────────
        _save_skill_version(working_md, results_path, round_n)
        duration = time.time() - round_start
        bar = "█" * int(round_avg * 20)
        emit(f"  Round {round_n} avg={round_avg:.3f} {bar}  ({duration:.1f}s)")

        history.append(
            {
                "round": round_n,
                "avg_score": round_avg,
                "n_batches": len(batches),
                "eval_results": [_serialize_result(r) for r in all_results],
            }
        )
        _save_round_scores(results_path, round_n, history[-1])

        # ── Stopping criteria ─────────────────────────────────────────────────
        if round_avg >= stop_threshold:
            emit(f"  STOP: score {round_avg:.3f} >= threshold {stop_threshold}")
            break
        if prev_avg is not None:
            recent_deltas.append(abs(round_avg - prev_avg))
            if len(recent_deltas) >= converge_k and all(
                d < converge_delta for d in recent_deltas[-converge_k:]
            ):
                emit(f"  STOP: converged (Δ<{converge_delta} for {converge_k} rounds)")
                break
        if round_n == max_rounds:
            emit(f"  STOP: reached max_rounds={max_rounds}")
        prev_avg = round_avg

    best = (
        max(history, key=lambda h: h["avg_score"])
        if history
        else {"round": 0, "avg_score": 0.0}
    )
    summary = {
        "skill": skill,
        "student_model": student_model,
        "teacher_model": teacher_model,
        "judge_model": judge_model,
        "batch_size": eff_batch,
        "rounds_run": len(history),
        "final_score": history[-1]["avg_score"] if history else 0.0,
        "best_round": best["round"],
        "best_score": best["avg_score"],
        "score_history": [
            {"round": h["round"], "avg_score": h["avg_score"]} for h in history
        ],
        "rubric_cache_key": rubric.get("cache_key"),
    }
    (results_path / "summary.json").write_text(json.dumps(summary, indent=2))
    try:
        emit("")
        emit("=" * 60)
        emit(
            f"DONE. Best round: {summary['best_round']}  score={summary['best_score']:.3f}"
        )
    finally:
        run_log_file.close()
    return summary


# ── Batch runner ──────────────────────────────────────────────────────────────


def _run_batch(
    batch: list[dict],
    skill: str,
    student_model: str,
    judge: Judge,
    results_path: Path,
    test_cases_dir: str,
    base_config: RunConfigV2,
    round_n: int,
    batch_idx: int,
    max_retry_per_tc: int,
    current_skill_md: Path,
    emit: Callable[[str], None],
) -> tuple[list[EvalResult], list[str]]:
    results: list[EvalResult] = []
    log_paths: list[str] = []
    skill_dir = Path(base_config.skills_dir) / skill

    for tc_idx, tc in enumerate(batch, 1):
        output_dir = results_path / f"round_{round_n}" / f"batch_{batch_idx}" / tc["id"]
        output_dir.mkdir(parents=True, exist_ok=True)
        emit(f"    [{tc_idx}/{len(batch)}] {tc['id']}  '{tc.get('name', '')}'")
        tc_start = time.time()

        # Fixture handling
        input_files: list[Path] = []
        if tc.get("fixture_file"):
            src = Path(test_cases_dir) / tc["fixture_file"]
            if src.is_file():
                input_files.append(src)
            else:
                emit(f"      WARNING: fixture missing: {src}")

        user_prompt = tc.get("prompt", "")
        if input_files:
            user_prompt = (
                f"[File in your working dir: {input_files[0].name}]\n\n{user_prompt}"
            )

        config = RunConfigV2(
            openrouter_api_key=base_config.openrouter_api_key,
            claude_binary=base_config.claude_binary,
            skills_dir=base_config.skills_dir,
            log_dir=base_config.log_dir,
            output_dir=str(output_dir),
            input_files=input_files,
            sandbox_tmp_root=base_config.sandbox_tmp_root,
            sandbox_keep_on_fail=base_config.sandbox_keep_on_fail,
            verbose=base_config.verbose,
        )

        run = run_student(
            user_prompt=user_prompt,
            skill_name=skill,
            skill_dir=skill_dir,
            model=student_model,
            config=config,
            max_retries=max_retry_per_tc,
            current_skill_md=current_skill_md,
        )

        if run.get("skipped"):
            emit(f"      SKIPPED (all {max_retry_per_tc} retries failed)")
            results.append(
                make_skip_result(tc, skill, student_model, round_n, str(output_dir))
            )
            if run.get("log_file"):
                log_paths.append(run["log_file"])
            continue

        emit(
            f"      stop={run.get('stop_reason')}  iters={run.get('iterations')}  ({time.time()-tc_start:.1f}s)"
        )
        if run.get("log_file"):
            log_paths.append(run["log_file"])

        try:
            tc_with_skill = {**tc, "skill": skill}
            er = judge.score(
                output_dir=str(output_dir),
                test_case=tc_with_skill,
                model=student_model,
                round_n=round_n,
            )
        except Exception as e:  # noqa: BLE001
            _log.exception("judge.score() crashed for %s", tc["id"])
            emit(f"      JUDGE ERROR: {e}")
            er = make_skip_result(tc, skill, student_model, round_n, str(output_dir))

        results.append(er)
        status = "PASS" if er.hybrid_score >= 0.6 else "FAIL"
        emit(f"      [{status}] score={er.hybrid_score:.2f}")

    return results, log_paths


# ── Persistence helpers ───────────────────────────────────────────────────────


def _serialize_result(r: EvalResult) -> dict[str, Any]:
    return {
        "test_case_id": r.test_case_id,
        "rule_score": r.rule_score,
        "llm_score": r.llm_judge_score if r.llm_judge_score >= 0 else None,
        "hybrid_score": r.hybrid_score,
        "checks": [
            {"name": c.name, "passed": c.passed, "score": c.score, "reason": c.reason}
            for c in r.checks
        ],
    }


def _save_batch_scores(
    results_path: Path, round_n: int, batch_idx: int, results: list[EvalResult]
) -> None:
    p = results_path / f"round_{round_n}" / f"batch_{batch_idx}" / "scores.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    avg = sum(r.hybrid_score for r in results) / len(results) if results else 0.0
    p.write_text(
        json.dumps(
            {
                "round": round_n,
                "batch": batch_idx,
                "avg_score": avg,
                "eval_results": [_serialize_result(r) for r in results],
            },
            indent=2,
        )
    )


def _save_round_scores(results_path: Path, round_n: int, data: dict) -> None:
    p = results_path / f"round_{round_n}" / "scores.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def _save_skill_version(skill_md_path: Path, results_path: Path, round_n: int) -> None:
    shutil.copy2(skill_md_path, results_path / f"SKILL_round_{round_n}.md")


def _is_batch_complete(results_path: Path, round_n: int, batch_idx: int) -> bool:
    return (
        results_path / f"round_{round_n}" / f"batch_{batch_idx}" / "scores.json"
    ).exists()


def _load_cached_batch(
    results_path: Path,
    round_n: int,
    batch_idx: int,
    batch: list[dict],
    skill: str,
    model: str,
) -> list[EvalResult]:
    scores_path = (
        results_path / f"round_{round_n}" / f"batch_{batch_idx}" / "scores.json"
    )
    data = json.loads(scores_path.read_text())
    by_id = {e["test_case_id"]: e for e in data.get("eval_results", [])}
    results: list[EvalResult] = []
    for tc in batch:
        entry = by_id.get(tc["id"])
        if entry is None:
            raise ValueError(
                f"Cache miss for TC '{tc['id']}' in round {round_n} batch {batch_idx}. "
                "Test cases may have changed since last run — delete cached results or "
                "remove --resume to re-run from scratch."
            )
        er = EvalResult(
            test_case_id=tc["id"],
            skill=skill,
            model=model,
            round_n=round_n,
            output_dir=str(
                results_path / f"round_{round_n}" / f"batch_{batch_idx}" / tc["id"]
            ),
        )
        er._rule_weight = 0.0
        er._llm_weight = 1.0
        er._human_weight = 0.0
        er.rule_score = entry.get("rule_score", 0.0)
        er.llm_judge_score = entry.get("llm_score") or 0.0
        results.append(er)
    return results
