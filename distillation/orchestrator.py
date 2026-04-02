"""Orchestrator: coordinates the full Skill Distillation loop.

Loop per round:
  1. Split test cases into batches of `batch_size`
  2. For each batch:
     a. Run student model on batch via skill_runner
     b. Score each run with Evaluator
     c. Summarize batch failures → key_notes
     d. Teacher rewrites SKILL.md (progressive improvement within the round)
  3. Compute round avg score from all batches
  4. Check stopping criteria
  5. Save versioned SKILL.md → next round

If batch_size=0 or batch_size >= len(test_cases): Teacher is called once per round
(original behaviour).
"""

from __future__ import annotations

import json
import math
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

_SKILL_RUNNER = Path(__file__).parent.parent / "skill_runner"
sys.path.insert(0, str(_SKILL_RUNNER))

from config import RunConfig  # noqa: E402
from runner.agent_loop import run_agent  # noqa: E402

from evaluator.base import EvalResult  # noqa: E402
from evaluator.docx_rules import DocxEvaluator  # noqa: E402
import summarizer  # noqa: E402
import teacher as teacher_module  # noqa: E402

# ── Default stopping criteria (overridable via run_distillation args) ─────────
_STOP_THRESHOLD = 0.80
_CONVERGE_DELTA = 0.02
_CONVERGE_K = 3
_MAX_ROUNDS = 10


def _build_evaluators(judge_model: str, use_llm_judge: bool) -> dict:
    return {
        "docx": DocxEvaluator(judge_model=judge_model, use_llm_judge=use_llm_judge),
    }


def run_distillation(
    skill: str,
    test_cases: list[dict],
    student_model: str,
    teacher_model: str = "claude-haiku-4-5",
    max_rounds: int = _MAX_ROUNDS,
    batch_size: int = 5,
    stop_threshold: float = _STOP_THRESHOLD,
    converge_delta: float = _CONVERGE_DELTA,
    converge_k: int = _CONVERGE_K,
    results_dir: str = "./results",
    skills_dir: str | None = None,
    workspace_dir: str | None = None,
    log_dir: str | None = None,
    verbose: bool = False,
    runner_verbose: bool = False,
    use_llm_judge: bool = True,
) -> dict:
    """Run the full distillation loop for one skill.

    Args:
        skill:          Skill name (must match a folder in skills_dir).
        test_cases:     List of test case dicts.
        student_model:  OpenRouter model ID for the student.
        teacher_model:  Claude model ID for the teacher.
        max_rounds:     Hard cap on rounds.
        batch_size:     Test cases per Teacher feedback cycle within a round.
                        0 = no batching (teacher called once per round).
        stop_threshold: avg hybrid score that triggers early stop.
        converge_delta: min improvement per round before convergence stop.
        converge_k:     Consecutive stagnant rounds before convergence stop.
        results_dir:    Root dir for saving versioned SKILL.md and scores.
        skills_dir:     Path to skill_runner/skills/ (auto-detected if None).
        workspace_dir:  Path to skill_runner workspace (auto-detected if None).
        log_dir:        Path to skill_runner logs (auto-detected if None).
        verbose:        Print progress to stdout.
        runner_verbose: Show skill_runner tool calls.
        use_llm_judge:  Whether to run LLM Judge (slower, more accurate).

    Returns:
        Dict with keys: rounds, final_score, best_round, skill_md_versions.
    """
    evaluators = _build_evaluators(
        judge_model=teacher_model, use_llm_judge=use_llm_judge
    )
    if skill not in evaluators:
        raise ValueError(
            f"No evaluator registered for skill '{skill}'. "
            f"Available: {list(evaluators.keys())}"
        )

    evaluator = evaluators[skill]
    results_path = Path(results_dir) / skill
    results_path.mkdir(parents=True, exist_ok=True)

    sr = _SKILL_RUNNER
    skills_dir = skills_dir or str(sr / "skills")
    workspace_dir = workspace_dir or str(sr / "workspace")
    log_dir = log_dir or str(sr / "logs")

    skill_md_path = Path(skills_dir) / skill / "SKILL.md"
    if not skill_md_path.exists():
        raise FileNotFoundError(f"SKILL.md not found at {skill_md_path}")

    # Effective batch size — 0 means "all at once"
    eff_batch = (
        batch_size if (batch_size and batch_size < len(test_cases)) else len(test_cases)
    )
    n_batches = math.ceil(len(test_cases) / eff_batch)

    run_log_path = results_path / "run.log"
    run_log_file = open(run_log_path, "a", buffering=1)

    def emit(msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        run_log_file.write(line + "\n")
        run_log_file.flush()
        if verbose:
            print(line, flush=True)

    emit("=" * 60)
    emit(f"START  skill={skill}  student={student_model}  teacher={teacher_model}")
    emit(
        f"Test cases: {len(test_cases)}  |  batch_size={eff_batch}  |  batches/round={n_batches}"
    )
    emit(
        f"Max rounds: {max_rounds}  |  stop≥{stop_threshold}  |  converge Δ<{converge_delta} × {converge_k}"
    )
    emit("=" * 60)

    _save_skill_version(skill_md_path, results_path, round_n=0)

    history: list[dict] = []
    prev_all_results: list[EvalResult] = []
    recent_deltas: list[float] = []

    for round_n in range(1, max_rounds + 1):
        emit("")
        emit(f"--- Round {round_n}/{max_rounds} ---")
        round_start = time.time()
        all_round_results: list[EvalResult] = []

        # Split test cases into batches
        batches = [
            test_cases[i : i + eff_batch] for i in range(0, len(test_cases), eff_batch)
        ]

        for batch_idx, batch in enumerate(batches, 1):
            batch_label = f"R{round_n}.B{batch_idx}/{n_batches}"
            emit(f"  [{batch_label}] Running {len(batch)} test case(s) ...")
            batch_results: list[EvalResult] = []
            log_paths: list[str] = []

            # ── Run student on this batch ─────────────────────────────────────
            for tc_idx, tc in enumerate(batch, 1):
                output_dir = str(
                    results_path / f"round_{round_n}" / f"batch_{batch_idx}" / tc["id"]
                )
                emit(
                    f"    [{tc_idx}/{len(batch)}] tc={tc['id']}  '{tc.get('name', '')}' ..."
                )
                tc_start = time.time()

                config = RunConfig(
                    model=student_model,
                    skills_dir=skills_dir,
                    workspace_dir=workspace_dir,
                    log_dir=log_dir,
                    output_dir=output_dir,
                    verbose=runner_verbose,
                )
                try:
                    run_result = run_agent(
                        user_prompt=tc["prompt"],
                        skill_name=skill,
                        model=student_model,
                        config=config,
                    )
                    tc_dur = time.time() - tc_start
                    emit(
                        f"      stop={run_result['stop_reason']}  "
                        f"iters={run_result['iterations']}  ({tc_dur:.1f}s)"
                    )
                    for f in run_result.get("output_files") or []:
                        emit(f"      output: {Path(f).name}")
                    if not run_result.get("output_files"):
                        emit("      output: (none)")
                except Exception as e:
                    emit(f"      ERROR: {e}")
                    batch_results.append(
                        EvalResult(
                            test_case_id=tc["id"],
                            skill=skill,
                            model=student_model,
                            round_n=round_n,
                            output_dir=output_dir,
                            rule_score=0.0,
                        )
                    )
                    continue

                log_path = _find_latest_log(log_dir, skill)
                if log_path:
                    log_paths.append(log_path)

                result = evaluator.score(output_dir, tc, student_model, round_n)
                batch_results.append(result)
                emit(f"      score: {result.summary_line()}")

            all_round_results.extend(batch_results)

            # ── Batch summary ─────────────────────────────────────────────────
            batch_avg = (
                sum(r.rule_score for r in batch_results) / len(batch_results)
                if batch_results
                else 0.0
            )
            emit(f"  [{batch_label}] batch_avg={batch_avg:.3f}")
            _save_batch_scores(results_path, round_n, batch_idx, batch_results)

            # ── Teacher feedback after this batch (if more batches remain or
            #    single-batch mode — always rewrite to update SKILL.md) ────────
            emit(f"  [{batch_label}] Summarizing → Teacher ...")
            key_notes = summarizer.summarize(
                eval_results=batch_results,
                log_paths=log_paths,
                prev_round_results=prev_all_results if prev_all_results else None,
                round_n=round_n,
            )
            key_notes_path = (
                results_path
                / f"round_{round_n}"
                / f"batch_{batch_idx}"
                / "key_notes.md"
            )
            key_notes_path.parent.mkdir(parents=True, exist_ok=True)
            key_notes_path.write_text(key_notes)

            try:
                new_skill_md = teacher_module.rewrite(
                    skill_md_path=str(skill_md_path),
                    key_notes=key_notes,
                    model=teacher_model,
                )
                skill_md_path.write_text(new_skill_md)
                emit(f"  [{batch_label}] SKILL.md updated ({len(new_skill_md)} chars)")
            except RuntimeError as e:
                emit(f"  [{batch_label}] Teacher FAILED: {e}. Skipping rewrite.")

        # ── Round summary ─────────────────────────────────────────────────────
        avg_score = (
            sum(r.rule_score for r in all_round_results) / len(all_round_results)
            if all_round_results
            else 0.0
        )
        history.append(
            {
                "round": round_n,
                "avg_score": avg_score,
                "n_batches": len(batches),
                "eval_results": [_serialize_result(r) for r in all_round_results],
            }
        )
        _save_round_scores(results_path, round_n, history[-1])
        _save_skill_version(skill_md_path, results_path, round_n=round_n)

        duration = time.time() - round_start
        bar = "█" * int(avg_score * 20)
        emit(f"  Round {round_n} avg={avg_score:.3f} {bar}  ({duration:.1f}s total)")

        # ── Stopping criteria ─────────────────────────────────────────────────
        if avg_score >= stop_threshold:
            emit(f"  ✓ STOP: score {avg_score:.3f} ≥ threshold {stop_threshold}")
            break

        if prev_all_results:
            prev_avg = sum(r.rule_score for r in prev_all_results) / len(
                prev_all_results
            )
            delta = avg_score - prev_avg
            recent_deltas.append(abs(delta))
            if len(recent_deltas) >= converge_k:
                if all(d < converge_delta for d in recent_deltas[-converge_k:]):
                    emit(
                        f"  ✓ STOP: converged (Δ<{converge_delta} for {converge_k} rounds)"
                    )
                    break

        if round_n == max_rounds:
            emit(f"  ✓ STOP: reached max_rounds={max_rounds}")
            break

        prev_all_results = all_round_results

    # ── Final summary ─────────────────────────────────────────────────────────
    best = max(history, key=lambda h: h["avg_score"])
    summary = {
        "skill": skill,
        "student_model": student_model,
        "teacher_model": teacher_model,
        "batch_size": eff_batch,
        "rounds_run": len(history),
        "final_score": history[-1]["avg_score"] if history else 0.0,
        "best_round": best["round"],
        "best_score": best["avg_score"],
        "score_history": [
            {
                "round": h["round"],
                "avg_score": h["avg_score"],
                "n_batches": h["n_batches"],
            }
            for h in history
        ],
    }
    _save_summary(results_path, summary)

    emit("")
    emit("=" * 60)
    emit(f"DONE.  Best round: {best['round']}  score={best['avg_score']:.3f}")
    emit(f"Results: {results_path}")

    run_log_file.close()
    return summary


# ── helpers ───────────────────────────────────────────────────────────────────


def _find_latest_log(log_dir: str, skill: str) -> str | None:
    log_path = Path(log_dir)
    if not log_path.exists():
        return None
    files = sorted(
        log_path.glob(f"{skill}_*.jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return str(files[0]) if files else None


def _save_skill_version(skill_md_path: Path, results_path: Path, round_n: int) -> None:
    shutil.copy2(skill_md_path, results_path / f"SKILL_round_{round_n}.md")


def _save_batch_scores(
    results_path: Path,
    round_n: int,
    batch_idx: int,
    results: list[EvalResult],
) -> None:
    path = results_path / f"round_{round_n}" / f"batch_{batch_idx}" / "scores.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "round": round_n,
                "batch": batch_idx,
                "avg_score": sum(r.rule_score for r in results) / len(results)
                if results
                else 0.0,
                "eval_results": [_serialize_result(r) for r in results],
            },
            indent=2,
        )
    )


def _save_round_scores(results_path: Path, round_n: int, round_data: dict) -> None:
    path = results_path / f"round_{round_n}" / "scores.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(round_data, indent=2))


def _save_summary(results_path: Path, summary: dict) -> None:
    (results_path / "summary.json").write_text(json.dumps(summary, indent=2))


def _serialize_result(r: EvalResult) -> dict:
    return {
        "test_case_id": r.test_case_id,
        "rule_score": r.rule_score,
        "llm_score": r.llm_judge_score if r.llm_judge_score >= 0 else None,
        "llm_reasoning": r.llm_judge_reasoning or None,
        "hybrid_score": r.hybrid_score,
        "checks": [
            {"name": c.name, "passed": c.passed, "score": c.score, "reason": c.reason}
            for c in r.checks
        ],
    }
