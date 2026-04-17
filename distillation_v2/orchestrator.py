"""Distillation v2 orchestrator.

Changes vs v1:
  - Student: Claude Code CLI in a sandbox (runner/claude_code_runner.py).
  - Judge:   LLMOnlyJudge using an auto-generated per-skill rubric.
  - Teacher: Same v1 teacher.py, but invoked inside anthropic_env() so
             ANTHROPIC_API_KEY/BASE_URL cannot bleed into subsequent calls.

Preserves v1's result layout, resume contract, stopping criteria, and summary
shape so downstream tooling (visualize_log.py, viewer.html) keeps working.
"""

from __future__ import annotations

import importlib.util
import json
import math
import shutil
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ── v1 module loading (avoid package-name collisions) ────────────────────────


def _load_v1_module(rel: str, name: str):
    p = Path(__file__).resolve().parent.parent / "distillation" / rel
    spec = importlib.util.spec_from_file_location(name, p)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Register "utils" so v1 internals that do `from utils import ...` resolve.
_v1_utils = _load_v1_module("utils.py", "utils")
get_logger = _v1_utils.get_logger
setup_logging = _v1_utils.setup_logging
write_api_call = _v1_utils.write_api_call
write_eval_detail = _v1_utils.write_eval_detail

# Pre-register v1's evaluator package so v1 internals resolve
# `from evaluator.base import EvalResult` correctly even though distillation_v2
# has its own `evaluator/` package.
import types as _types  # noqa: E402

_v1_eval_pkg = _types.ModuleType("evaluator")
_v1_eval_pkg.__path__ = [
    str(Path(__file__).resolve().parent.parent / "distillation" / "evaluator")
]
sys.modules["evaluator"] = _v1_eval_pkg

_v1_base = _load_v1_module("evaluator/base.py", "evaluator.base")
EvalResult = _v1_base.EvalResult

_v1_summarizer = _load_v1_module("summarizer.py", "_v1_summarizer")
_v1_teacher = _load_v1_module("teacher.py", "_v1_teacher")

# Now that v1 modules have loaded, remove the v1 evaluator shim so v2's
# `evaluator.llm_only_judge` import below resolves to the real v2 package.
del sys.modules["evaluator"]
del sys.modules["evaluator.base"]

# ── v2 local imports ─────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluator.llm_only_judge import LLMOnlyJudge  # noqa: E402
from evaluator.rubric_generator import generate_rubric  # noqa: E402
from runner.anthropic_env import anthropic_env  # noqa: E402
from runner.claude_code_runner import run_agent as claude_run_agent  # noqa: E402
from runner.config import RunConfigV2  # noqa: E402

_log = get_logger("v2.orchestrator")

_DEFAULT_ANTHROPIC_BASE = "https://api.anthropic.com"


# ── Resume helpers ────────────────────────────────────────────────────────────


def _is_batch_complete(
    results_path: Path, round_n: int, batch_idx: int, tc_ids: list[str]
) -> bool:
    batch_dir = results_path / f"round_{round_n}" / f"batch_{batch_idx}"
    if not batch_dir.exists():
        return False
    for tc_id in tc_ids:
        if not (batch_dir / tc_id).exists():
            return False
    return (batch_dir / "scores.json").exists()


def _find_last_completed_batch(results_path: Path, round_n: int, max_batch: int) -> int:
    for b in range(max_batch, 0, -1):
        if (results_path / f"round_{round_n}" / f"batch_{b}" / "scores.json").exists():
            return b
    return 0


# ── Serialization helpers ────────────────────────────────────────────────────


def _serialize_result(r: EvalResult) -> dict[str, Any]:
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


def _save_batch_scores(
    results_path: Path, round_n: int, batch_idx: int, results: list[EvalResult]
) -> None:
    p = results_path / f"round_{round_n}" / f"batch_{batch_idx}" / "scores.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "round": round_n,
                "batch": batch_idx,
                "avg_score": (
                    sum(r.hybrid_score for r in results) / len(results)
                    if results
                    else 0.0
                ),
                "eval_results": [_serialize_result(r) for r in results],
            },
            indent=2,
        )
    )


def _save_round_scores(results_path: Path, round_n: int, round_data: dict) -> None:
    p = results_path / f"round_{round_n}" / "scores.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(round_data, indent=2))


def _save_summary(results_path: Path, summary: dict) -> None:
    (results_path / "summary.json").write_text(json.dumps(summary, indent=2))


def _save_skill_version(skill_md_path: Path, results_path: Path, round_n: int) -> None:
    shutil.copy2(skill_md_path, results_path / f"SKILL_round_{round_n}.md")


# ── Main entry point ─────────────────────────────────────────────────────────


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
    results_dir: str = "./results",
    rubric_cache_dir: str = "./rubrics",
    skills_dir: str | None = None,
    test_cases_dir: str | None = None,
    regenerate_rubric: bool = False,
    ensemble_n: int = 1,
    sandbox_tmp_root: str = "~/.cache/distill_v2",
    sandbox_keep_on_fail: bool = True,
    claude_binary: str = "claude",
    verbose: bool = False,
    dry_run: bool = False,
    resume: bool = False,
) -> dict[str, Any]:
    """Run the v2 distillation loop."""
    import os

    anthropic_key = anthropic_key or os.getenv("ANTHROPIC_KEY")
    if not anthropic_key:
        raise RuntimeError("ANTHROPIC_KEY not set (orchestrator_v2 requires it)")

    v2_root = Path(__file__).resolve().parent
    results_path = Path(results_dir) / skill
    results_path.mkdir(parents=True, exist_ok=True)

    skills_dir = skills_dir or str(v2_root.parent / "skill_runner" / "skills")
    test_cases_dir = test_cases_dir or str(
        v2_root.parent / "distillation" / "test_cases"
    )
    skill_dir = Path(skills_dir) / skill
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {skill_md_path}")

    # ── Rubric (one-time per (skill_dir, all test cases)) ────────────────────
    rubric = generate_rubric(
        skill_name=skill,
        skill_dir=skill_dir,  # ← pass full skill directory
        test_cases=test_cases,  # ← pass ALL test cases
        cache_dir=rubric_cache_dir,
        model=judge_model,
        regenerate=regenerate_rubric,
        anthropic_api_key=anthropic_key,
    )
    judge = LLMOnlyJudge(
        rubric=rubric,
        model=judge_model,
        ensemble_n=ensemble_n,
        anthropic_api_key=anthropic_key,
    )

    # ── Run log setup ────────────────────────────────────────────────────────
    run_log_path = results_path / "run.log"
    run_log_file = open(run_log_path, "a", buffering=1)

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
    emit(
        f"Rubric: {len(rubric['criteria'])} criteria (cache_key={rubric.get('cache_key')})"
    )
    emit(
        f"Test cases: {len(test_cases)}  batches/round={n_batches}  batch_size={eff_batch}"
    )
    emit("=" * 60)

    _save_skill_version(skill_md_path, results_path, round_n=0)

    history: list[dict] = []
    prev_all_results: list[EvalResult] = []
    recent_deltas: list[float] = []
    round_key_notes_history: list[str] = []

    for round_n in range(1, max_rounds + 1):
        emit("")
        emit(f"--- Round {round_n}/{max_rounds} ---")
        round_start = time.time()
        all_round_results: list[EvalResult] = []

        batches = [
            test_cases[i : i + eff_batch] for i in range(0, len(test_cases), eff_batch)
        ]

        skip_batches = 0
        if resume:
            skip_batches = _find_last_completed_batch(
                results_path, round_n, len(batches)
            )
            if skip_batches > 0:
                emit(f"  [RESUME] batches 1-{skip_batches} already complete.")

        for batch_idx, batch in enumerate(batches, 1):
            tc_ids = [tc["id"] for tc in batch]
            if batch_idx <= skip_batches and _is_batch_complete(
                results_path, round_n, batch_idx, tc_ids
            ):
                loaded = _load_cached_batch(
                    results_path, round_n, batch_idx, batch, skill, student_model
                )
                all_round_results.extend(loaded)
                emit(f"  [R{round_n}.B{batch_idx}] resumed ({len(loaded)} tc).")
                continue

            batch_label = f"R{round_n}.B{batch_idx}/{n_batches}"
            batch_start = time.time()
            emit(f"  [{batch_label}] running {len(batch)} test cases...")

            batch_results = _run_batch(
                batch=batch,
                skill=skill,
                student_model=student_model,
                judge=judge,
                results_path=results_path,
                test_cases_dir=test_cases_dir,
                skills_dir=skills_dir,
                sandbox_tmp_root=sandbox_tmp_root,
                sandbox_keep_on_fail=sandbox_keep_on_fail,
                claude_binary=claude_binary,
                round_n=round_n,
                batch_idx=batch_idx,
                verbose=verbose,
                emit=emit,
            )
            all_round_results.extend(batch_results)

            batch_elapsed = time.time() - batch_start
            _emit_batch_summary(emit, batch_label, batch_results, batch_elapsed)
            _save_batch_scores(results_path, round_n, batch_idx, batch_results)
            for r in batch_results:
                write_eval_detail({"round": round_n, "batch": batch_idx, **asdict(r)})

            # Teacher pass
            if dry_run:
                emit(f"  [{batch_label}] DRY RUN — skipping Teacher.")
                continue

            emit(f"  [{batch_label}] summarizing → Teacher...")
            key_notes = _v1_summarizer.summarize(
                eval_results=batch_results,
                log_paths=[r.output_dir for r in batch_results],
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

            _teacher_rewrite(
                skill_md_path=skill_md_path,
                key_notes=key_notes,
                teacher_model=teacher_model,
                anthropic_key=anthropic_key,
                round_key_notes_history=round_key_notes_history,
                round_n=round_n,
                batch_idx=batch_idx,
                emit=emit,
            )
            round_key_notes_history.append(key_notes)

        # Round summary
        avg_score = (
            sum(r.hybrid_score for r in all_round_results) / len(all_round_results)
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
        emit(f"  Round {round_n} avg={avg_score:.3f} {bar}  ({duration:.1f}s)")

        # Stopping criteria
        if avg_score >= stop_threshold:
            emit(f"  ✓ STOP: score {avg_score:.3f} ≥ threshold {stop_threshold}")
            break
        if prev_all_results:
            prev_avg = sum(r.hybrid_score for r in prev_all_results) / len(
                prev_all_results
            )
            recent_deltas.append(abs(avg_score - prev_avg))
            if len(recent_deltas) >= converge_k and all(
                d < converge_delta for d in recent_deltas[-converge_k:]
            ):
                emit(
                    f"  ✓ STOP: converged (Δ<{converge_delta} for {converge_k} rounds)"
                )
                break
        if round_n == max_rounds:
            emit(f"  ✓ STOP: reached max_rounds={max_rounds}")
            break
        prev_all_results = all_round_results

    best = (
        max(history, key=lambda h: h["avg_score"])
        if history
        else {"round": 0, "avg_score": 0}
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
            {
                "round": h["round"],
                "avg_score": h["avg_score"],
                "n_batches": h["n_batches"],
            }
            for h in history
        ],
        "rubric_cache_key": rubric.get("cache_key"),
    }
    _save_summary(results_path, summary)
    emit("")
    emit("=" * 60)
    emit(
        f"DONE.  Best round: {summary['best_round']}  score={summary['best_score']:.3f}"
    )
    emit(f"Results: {results_path}")
    run_log_file.close()
    return summary


# ── Batch runner ─────────────────────────────────────────────────────────────


def _run_batch(
    batch: list[dict],
    skill: str,
    student_model: str,
    judge: LLMOnlyJudge,
    results_path: Path,
    test_cases_dir: str,
    skills_dir: str,
    sandbox_tmp_root: str,
    sandbox_keep_on_fail: bool,
    claude_binary: str,
    round_n: int,
    batch_idx: int,
    verbose: bool,
    emit,
) -> list[EvalResult]:
    import os

    v2_root = Path(__file__).resolve().parent
    results: list[EvalResult] = []
    for tc_idx, tc in enumerate(batch, 1):
        output_dir = results_path / f"round_{round_n}" / f"batch_{batch_idx}" / tc["id"]
        output_dir.mkdir(parents=True, exist_ok=True)
        emit(f"    [{tc_idx}/{len(batch)}] tc={tc['id']}  '{tc.get('name','')}'")
        tc_start = time.time()

        # Fixture handling: pass absolute path, claude_code_runner copies it.
        input_files: list[Path] = []
        if tc.get("fixture_file"):
            src = Path(test_cases_dir) / tc["fixture_file"]
            if src.is_file():
                input_files.append(src)
                emit(f"      fixture: {src.name}")
            else:
                emit(f"      WARNING: fixture missing: {src}")

        user_prompt = tc["prompt"]
        if input_files:
            user_prompt = (
                f"[File available in your working directory: {input_files[0].name}]\n\n"
                + user_prompt
            )

        config = RunConfigV2(
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            skills_dir=skills_dir,
            log_dir=str(v2_root / "logs"),
            output_dir=str(output_dir),
            input_files=input_files,
            sandbox_tmp_root=sandbox_tmp_root,
            sandbox_keep_on_fail=sandbox_keep_on_fail,
            claude_binary=claude_binary,
            verbose=verbose,
        )

        try:
            run = claude_run_agent(
                user_prompt=user_prompt,
                skill_name=skill,
                model=student_model,
                config=config,
            )
        except Exception as e:  # noqa: BLE001
            emit(f"      RUNNER ERROR: {e}")
            results.append(
                _empty_result(tc, skill, student_model, round_n, str(output_dir))
            )
            continue

        emit(
            f"      stop={run.get('stop_reason')}  iters={run.get('iterations')}  "
            f"({time.time()-tc_start:.1f}s)"
        )
        for f in run.get("output_files") or []:
            emit(f"      output: {Path(f).name}")
        if not run.get("output_files"):
            emit("      output: (none)")

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
            er = _empty_result(tc, skill, student_model, round_n, str(output_dir))

        results.append(er)
        emit(f"      score: {er.summary_line()}")
    return results


def _empty_result(
    tc: dict, skill: str, model: str, round_n: int, output_dir: str
) -> EvalResult:
    er = EvalResult(
        test_case_id=tc["id"],
        skill=skill,
        model=model,
        round_n=round_n,
        output_dir=output_dir,
    )
    er._rule_weight = 0.0
    er._llm_weight = 1.0
    er._human_weight = 0.0
    er.llm_judge_score = 0.0
    return er


def _emit_batch_summary(
    emit, label: str, results: list[EvalResult], elapsed: float
) -> None:
    if not results:
        emit(f"  [{label}] done: 0 results")
        return
    avg = sum(r.hybrid_score for r in results) / len(results)
    passed = sum(1 for r in results if r.hybrid_score >= 0.6)
    emit(
        f"  [{label}] done: {passed}/{len(results)} passed  avg_hybrid={avg:.3f}  ({elapsed:.1f}s)"
    )


def _teacher_rewrite(
    skill_md_path: Path,
    key_notes: str,
    teacher_model: str,
    anthropic_key: str,
    round_key_notes_history: list[str],
    round_n: int,
    batch_idx: int,
    emit,
) -> None:
    teacher_start = time.time()
    try:
        with anthropic_env(anthropic_key):
            new_skill_md = _v1_teacher.rewrite(
                skill_md_path=str(skill_md_path),
                key_notes=key_notes,
                model=teacher_model,
                round_history=(round_key_notes_history or None),
            )
        prev_len = len(skill_md_path.read_text())
        if len(new_skill_md) < int(prev_len * 0.80):
            emit(
                f"  Teacher WARNING: new SKILL.md too short ({len(new_skill_md)} < 80% of {prev_len}). Keeping previous."
            )
        else:
            skill_md_path.write_text(new_skill_md)
            emit(
                f"  Teacher done: SKILL.md updated ({len(new_skill_md)} chars, "
                f"{time.time() - teacher_start:.1f}s)"
            )
        write_api_call(
            {
                "type": "teacher",
                "model": teacher_model,
                "round": round_n,
                "batch": batch_idx,
                "key_notes_chars": len(key_notes),
                "new_skill_chars": len(new_skill_md),
                "elapsed_s": round(time.time() - teacher_start, 2),
            }
        )
    except RuntimeError as e:
        emit(f"  Teacher FAILED: {e}. Skipping rewrite.")
        write_api_call(
            {"type": "teacher", "error": str(e), "round": round_n, "batch": batch_idx}
        )


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
        entry = by_id.get(tc["id"], {})
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
        er.llm_judge_reasoning = entry.get("llm_reasoning") or ""
        results.append(er)
    return results
