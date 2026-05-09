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
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _or_model(model: str) -> str:
    """Prefix model with 'anthropic/' for OpenRouter if not already namespaced."""
    return model if "/" in model else f"anthropic/{model}"


# ── Public entry point ────────────────────────────────────────────────────────


def run_distillation(
    skill: str,
    test_cases: list[dict[str, Any]],
    rubric_test_cases: list[dict[str, Any]] | None = None,
    student_model: str = "google/gemma-4-26b-a4b-it",
    teacher_model: str = "claude-haiku-4-5",
    judge_model: str = "claude-haiku-4-5",
    anthropic_key: str | None = None,
    llm_api_key: str | None = None,
    llm_base_url: str | None = OPENROUTER_BASE_URL,
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
    no_llm_judge: bool = False,
    concurrent_tcs: int = 1,
) -> dict[str, Any]:
    # Resolve LLM backend key: prefer explicit llm_api_key, then OPENROUTER_API_KEY,
    # then fall back to legacy anthropic_key for backward compatibility.
    resolved_llm_key = (
        llm_api_key
        or os.getenv("OPENROUTER_API_KEY")
        or anthropic_key
        or os.getenv("ANTHROPIC_KEY")
    )
    if not resolved_llm_key:
        raise RuntimeError(
            "No LLM API key found. Set OPENROUTER_API_KEY or ANTHROPIC_KEY."
        )

    # When routing through OpenRouter, auto-prefix model names with 'anthropic/'
    resolved_base_url = llm_base_url
    if resolved_base_url and "openrouter" in resolved_base_url:
        teacher_model = _or_model(teacher_model)
        judge_model = _or_model(judge_model)

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

    # ── Per-workflow rubrics (once per pipeline run) ──────────────────────────
    # Use rubric_test_cases (all TCs) for rubric generation when provided,
    # so the rubric covers every workflow even if only a subset is being run.
    _rubric_pool = rubric_test_cases if rubric_test_cases is not None else test_cases
    workflows = sorted(set(tc.get("workflow", "create") for tc in _rubric_pool))
    judges: dict[str, Judge] = {}
    rubric_keys: dict[str, str] = {}
    for wf in workflows:
        wf_tcs = [tc for tc in _rubric_pool if tc.get("workflow", "create") == wf]
        wf_rubric = generate_rubric(
            skill_name=skill,
            skill_dir=skill_dir,
            test_cases=wf_tcs,
            workflow=wf,
            cache_dir=rubric_cache_dir,
            model=judge_model,
            regenerate=regenerate_rubric,
            watch_skill_hash=watch_skill_hash,
            keep_recent=keep_recent_rubrics,
            anthropic_api_key=resolved_llm_key,
            base_url=resolved_base_url,
        )
        judges[wf] = Judge(
            rubric=wf_rubric,
            model=judge_model,
            ensemble_n=ensemble_n,
            max_image_pages=max_image_pages,
            anthropic_api_key=resolved_llm_key,
            base_url=resolved_base_url,
        )
        rubric_keys[wf] = wf_rubric.get("cache_key", "")

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
    for wf, j in judges.items():
        emit(f"Rubric [{wf}]: {len(j.rubric['criteria'])} criteria")
    emit(f"TCs: {len(test_cases)}  batches/round={n_batches}  batch_size={eff_batch}")
    if validation_tc_count == 0:
        emit("Rollback: DISABLED (--no-rollback)")
    else:
        emit(
            f"Rollback threshold: {rollback_threshold}  validation_tcs: {validation_tc_count}"
        )
    emit("=" * 60)

    _save_skill_version(working_md, results_path, round_n=0, skip_if_exists=resume)

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
                judges=judges,
                results_path=results_path,
                test_cases_dir=test_cases_dir,
                base_config=base_config,
                round_n=round_n,
                batch_idx=batch_idx,
                max_retry_per_tc=max_retry_per_tc,
                current_skill_md=working_md,
                emit=emit,
                concurrent_tcs=concurrent_tcs,
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
                sum(r.llm_judge_score for r in batch_results if r.llm_judge_score >= 0)
                / len(batch_results)
                if batch_results
                else 0.0
            )
            passed = sum(1 for r in batch_results if r.llm_judge_score >= 0.8)
            emit(
                f"  [R{round_n}.B{batch_idx}] {passed}/{len(batch_results)} passed  avg={avg:.3f}  ({elapsed:.1f}s)"
            )
            _save_batch_scores(results_path, round_n, batch_idx, batch_results)
            for r in batch_results:
                write_eval_detail({"round": round_n, "batch": batch_idx, **asdict(r)})

        round_avg = (
            sum(r.llm_judge_score for r in all_results if r.llm_judge_score >= 0)
            / len(all_results)
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
                    anthropic_api_key=resolved_llm_key,
                    base_url=resolved_base_url,
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
                            judges=judges,
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
        _save_skill_version(working_md, results_path, round_n, skip_if_exists=resume)
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
        "rubric_cache_keys": rubric_keys,
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
    judges: dict[str, Judge],
    results_path: Path,
    test_cases_dir: str,
    base_config: RunConfigV2,
    round_n: int,
    batch_idx: int,
    max_retry_per_tc: int,
    current_skill_md: Path,
    emit: Callable[[str], None],
    concurrent_tcs: int = 1,
) -> tuple[list[EvalResult], list[str]]:
    skill_dir = Path(base_config.skills_dir) / skill
    n = len(batch)

    # Thread-safe emit wrapper (no-op lock when sequential)
    _lock = threading.Lock()

    def _emit(msg: str) -> None:
        with _lock:
            emit(msg)

    def _run_one(tc_idx: int, tc: dict) -> tuple[EvalResult, list[str]]:
        tc_log_paths: list[str] = []
        output_dir = results_path / f"round_{round_n}" / f"batch_{batch_idx}" / tc["id"]
        output_dir.mkdir(parents=True, exist_ok=True)
        _emit(f"    [{tc_idx}/{n}] {tc['id']}  '{tc.get('name', '')}'")
        tc_start = time.time()

        # Fixture handling — supports both fixture_file (str) and fixture_files (list)
        input_files: list[Path] = []
        raw = tc.get("fixture_files") or (
            [tc["fixture_file"]] if tc.get("fixture_file") else []
        )
        for rel in raw:
            src = Path(test_cases_dir) / rel
            if src.is_file():
                input_files.append(src)
            else:
                _emit(f"      WARNING: fixture missing: {src}")

        user_prompt = tc.get("prompt", "")
        workflow = tc.get("workflow", "create")
        if workflow == "read":
            user_prompt = (
                "[CRITICAL: You MUST save your output to a file on disk (e.g. output.txt, output.json). Do NOT just print to the terminal — the evaluator reads files only.]\n\n"
                + user_prompt
            )
        if input_files:
            names = ", ".join(f.name for f in input_files)
            user_prompt = f"[Files in your working dir: {names}]\n\n{user_prompt}"

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
            _emit(f"      SKIPPED (all {max_retry_per_tc} retries failed)")
            er = make_skip_result(tc, skill, student_model, round_n, str(output_dir))
            if run.get("log_file"):
                tc_log_paths.append(run["log_file"])
            return er, tc_log_paths

        _emit(
            f"      stop={run.get('stop_reason')}  iters={run.get('iterations')}  ({time.time()-tc_start:.1f}s)"
        )
        if run.get("log_file"):
            tc_log_paths.append(run["log_file"])

        try:
            wf = tc.get("workflow", "create")
            tc_judge = judges.get(wf) or next(iter(judges.values()))
            tc_with_skill = {**tc, "skill": skill}
            er = tc_judge.score(
                output_dir=str(output_dir),
                test_case=tc_with_skill,
                model=student_model,
                round_n=round_n,
                input_files=input_files if wf == "read" else None,
            )
        except Exception as e:  # noqa: BLE001
            _log.exception("judge.score() crashed for %s", tc["id"])
            _emit(f"      JUDGE ERROR: {e}")
            er = make_skip_result(tc, skill, student_model, round_n, str(output_dir))

        score = er.llm_judge_score if er.llm_judge_score >= 0 else 0.0
        status = "PASS" if score >= 0.8 else "FAIL"
        _emit(f"      [{status}] score={score:.2f}")
        return er, tc_log_paths

    # ── Execute: sequential or parallel ──────────────────────────────────────
    if concurrent_tcs <= 1:
        pairs = [_run_one(i, tc) for i, tc in enumerate(batch, 1)]
    else:
        pairs: list[tuple[EvalResult, list[str]]] = [None] * n  # type: ignore[list-item]
        with ThreadPoolExecutor(max_workers=concurrent_tcs) as pool:
            future_to_pos = {
                pool.submit(_run_one, i, tc): pos
                for pos, (i, tc) in enumerate(enumerate(batch, 1))
            }
            for future in as_completed(future_to_pos):
                pairs[future_to_pos[future]] = future.result()

    results = [er for er, _ in pairs]
    log_paths = [lp for _, lps in pairs for lp in lps]
    return results, log_paths


# ── Persistence helpers ───────────────────────────────────────────────────────


def _serialize_result(r: EvalResult) -> dict[str, Any]:
    return {
        "test_case_id": r.test_case_id,
        "llm_score": r.llm_judge_score if r.llm_judge_score >= 0 else None,
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
    avg = (
        sum(r.llm_judge_score for r in results if r.llm_judge_score >= 0) / len(results)
        if results
        else 0.0
    )
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


def _save_skill_version(
    skill_md_path: Path,
    results_path: Path,
    round_n: int,
    skip_if_exists: bool = False,
) -> None:
    dest = results_path / f"SKILL_round_{round_n}.md"
    if skip_if_exists and dest.exists():
        return
    shutil.copy2(skill_md_path, dest)


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
        er.llm_judge_score = entry.get("llm_score") or 0.0
        results.append(er)
    return results
