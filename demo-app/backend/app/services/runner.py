"""Run-state registry + SSE event generator.

Replays real data from ``distillation_v2/results/stable/<skill>/``:
- test case ids, scores, rule-check counts come from ``eval_detail.jsonl``
- judge token counts + teacher token counts come from ``api_calls.jsonl``
- student token counts are synthesised (the upstream pipeline doesn't
  log them — student runs through Claude Code CLI, not the API client)

The events match the schema in HANDOFF.md so the same client code paths
exercise this replay and any future real subprocess wrapper. Falls back
to a hardcoded simulation if the upstream files are missing.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.services import data_loader

# Wall-clock playback speed multiplier. real_time * SPEEDUP = wall-clock.
# 1.0 lets a full multi-round replay (8–10 rounds × ~26 TCs) breathe at
# around 120 s — long enough for the committee to actually read the log
# AND watch the learning curve grow round by round.
SPEEDUP = 1.0

# Mini-batch size for student/judge calls within a round. Each batch is
# announced with a "batch X/Y" log line so the demo looks like the real
# pipeline progress (parallel=5 per batch) instead of one giant flat list.
BATCH_SIZE = 5


@dataclass
class Run:
    run_id: str
    skill: str
    created_at: float = field(default_factory=time.time)
    finished: bool = False


_runs: dict[str, Run] = {}


def create_run(skill: str) -> Run:
    run_id = uuid.uuid4().hex[:12]
    run = Run(run_id=run_id, skill=skill)
    _runs[run_id] = run
    return run


def get_run(run_id: str) -> Run | None:
    return _runs.get(run_id)


def _event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _student_tokens_for(tc_id: str) -> tuple[int, int, float]:
    """Synthesised but deterministic-per-id student token counts + latency.
    Student calls don't go through api_calls.jsonl so we can't quote them
    exactly; pick plausible numbers anchored to the test case id so the
    same replay always shows the same figures."""
    h = sum(ord(c) for c in tc_id)
    pt = 1200 + (h * 13) % 900
    ct = 400 + (h * 17) % 500
    latency_s = 1.4 + (h % 8) / 10.0
    return pt, ct, latency_s


def _batch_avg_tokens(
    batch: list[dict], lookup: dict[str, tuple[int, int]] | None = None
) -> tuple[int, int]:
    """Average (prompt, completion) tokens across a batch — for compact
    batch-level log lines instead of per-TC spam."""
    pts = []
    cts = []
    for r in batch:
        if lookup and r["test_case_id"] in lookup:
            p, c = lookup[r["test_case_id"]]
        else:
            p, c, _ = _student_tokens_for(r["test_case_id"])
        pts.append(p)
        cts.append(c)
    return sum(pts) // max(len(pts), 1), sum(cts) // max(len(cts), 1)


def _md_change_stats(skill: str, round_n: int) -> tuple[int, int]:
    """Compare SKILL_round_{N-1}.md vs SKILL_round_N.md → (added, removed)
    line counts via difflib. Used in the teacher log."""
    import difflib

    try:
        _, prev = data_loader.get_skill_md(skill, round_n - 1)
        _, curr = data_loader.get_skill_md(skill, round_n)
    except Exception:  # noqa: BLE001
        return 0, 0
    diff = list(difflib.ndiff(prev.splitlines(), curr.splitlines()))
    added = sum(1 for d in diff if d.startswith("+ "))
    removed = sum(1 for d in diff if d.startswith("- "))
    return added, removed


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds * SPEEDUP)


async def stream_events(run: Run) -> AsyncIterator[str]:
    """Replay the FULL multi-round pipeline run for the chosen skill,
    one round at a time. Each round emits Student → Judge → Teacher
    phase batches with real per-TC scores and real token counts; the
    Teacher log carries a SKILL.md diff stat (+X / −Y lines) computed
    from the actual SKILL_round_*.md files on disk."""
    skill = run.skill

    try:
        summary = data_loader.get_summary(skill)
        all_api_calls = data_loader.get_api_calls(skill)
    except Exception:  # noqa: BLE001 — degrade rather than 500
        async for evt in _stream_simulated_fallback(run, reason="data loader failed"):
            yield evt
        return

    rounds_n = summary.get("rounds_run", 0)
    score_history = summary.get("score_history", [])
    if not rounds_n or not score_history:
        async for evt in _stream_simulated_fallback(
            run, reason="summary.json missing rounds_run / score_history"
        ):
            yield evt
        return

    student_model = summary.get("student_model", "google/gemma-4-26b-a4b-it")
    judge_model = summary.get("judge_model", "anthropic/claude-haiku-4-5")
    teacher_model = summary.get("teacher_model", "anthropic/claude-haiku-4-5")

    # Group teacher api_call records by round so each round-teacher
    # log can quote the real token count + elapsed_s for THAT round.
    teacher_by_round: dict[int, dict] = {
        c["round"]: c
        for c in all_api_calls
        if c.get("type") == "teacher" and "round" in c
    }

    # Eval entries grouped by round (one fetch, group locally).
    all_eval = data_loader.get_eval_detail(skill)
    eval_by_round: dict[int, list[dict]] = {}
    for r in all_eval:
        eval_by_round.setdefault(r["round"], []).append(r)

    # ── QUEUED ──────────────────────────────────────────────────────────
    yield _event("status", {"phase": "queued"})
    yield _event("log", {"line": "run accepted — preparing sandbox", "tag": "system"})
    await _sleep(0.4)
    yield _event(
        "log",
        {
            "line": (
                f"python distillation_v2/run.py --skill {skill} --rounds {rounds_n} "
                f"--batch-size {BATCH_SIZE}"
            ),
            "tag": "system",
        },
    )
    await _sleep(0.5)
    yield _event(
        "log",
        {"line": "loaded SKILL_round_0.md (Anthropic original)", "tag": "system"},
    )
    await _sleep(0.4)
    sample_round = eval_by_round.get(1, [])
    workflows_seen = sorted({r.get("workflow", "create") for r in sample_round})
    if workflows_seen:
        yield _event(
            "log",
            {
                "line": f"loading rubric · workflows={','.join(workflows_seen)}",
                "tag": "system",
            },
        )
        await _sleep(0.3)

    # Pre-flight summary so the UI can size the progress bar.
    yield _event(
        "log",
        {
            "line": (
                f"plan: {rounds_n} rounds × ~{len(sample_round)} test cases "
                f"(batch {BATCH_SIZE}, parallel {BATCH_SIZE})"
            ),
            "tag": "system",
        },
    )
    await _sleep(0.4)

    # ── ITERATE OVER ALL ROUNDS ─────────────────────────────────────────
    for sh in score_history:
        round_n = sh["round"]
        real_avg = float(sh["avg_score"])
        round_evals = sorted(
            eval_by_round.get(round_n, []),
            key=lambda r: r["test_case_id"],
        )
        n_tcs = len(round_evals)
        if n_tcs == 0:
            # No eval rows for this round → skip with a marker but still
            # emit a round_done with the recorded avg so the curve fills in.
            yield _event(
                "log",
                {"line": f"round {round_n}: no eval_detail rows", "tag": "system"},
            )
            yield _event(
                "round_done",
                {"round": round_n, "avg_score": round(real_avg, 3)},
            )
            await _sleep(0.2)
            continue

        batches = [round_evals[i : i + BATCH_SIZE] for i in range(0, n_tcs, BATCH_SIZE)]
        n_batches = len(batches)

        # Build judge lookup for this round's test cases.
        round_tc_ids = {r["test_case_id"] for r in round_evals}
        judge_by_tc: dict[str, dict] = {}
        for c in all_api_calls:
            if c.get("type") != "judge":
                continue
            tc = c.get("test_case")
            if tc in round_tc_ids:
                judge_by_tc.setdefault(tc, c)

        # ── Round banner ───────────────────────────────────────────────
        await _sleep(0.6)
        yield _event(
            "round_started",
            {
                "round": round_n,
                "rounds_total": rounds_n,
                "n_test_cases": n_tcs,
                "n_batches": n_batches,
            },
        )
        yield _event(
            "log",
            {
                "line": f"════ round {round_n}/{rounds_n} · {n_tcs} TCs · {n_batches} batches ════",
                "tag": "system",
            },
        )

        # ── RUNNING (student, batched, parallel=BATCH_SIZE) ────────────
        yield _event("status", {"phase": "running"})
        for bi, batch in enumerate(batches, start=1):
            await _sleep(0.5)
            avg_pt, avg_ct = _batch_avg_tokens(batch)
            ids_in_batch = ", ".join(r["test_case_id"] for r in batch)
            yield _event(
                "log",
                {
                    "line": (
                        f"batch {bi}/{n_batches} · {student_model} × {len(batch)} "
                        f"parallel ({ids_in_batch})"
                    ),
                    "tag": "student",
                },
            )
            await _sleep(0.7)
            yield _event(
                "log",
                {
                    "line": (
                        f"batch {bi}/{n_batches} · {len(batch)}/{len(batch)} returned · "
                        f"avg {avg_pt} prompt + {avg_ct} completion tokens"
                    ),
                    "tag": "student",
                },
            )
            # Rule check summary at batch level.
            await _sleep(0.25)
            passes = []
            for r in batch:
                checks = r.get("rule_checks", [])
                total = len(checks) or 1
                passed = sum(1 for c in checks if c.get("passed"))
                passes.append((passed, total))
            avg_passed = sum(p for p, _ in passes) // max(len(passes), 1)
            avg_total = sum(t for _, t in passes) // max(len(passes), 1)
            yield _event(
                "log",
                {
                    "line": (
                        f"batch {bi}/{n_batches} · rule checks: avg "
                        f"{avg_passed}/{avg_total} passed"
                    ),
                    "tag": "rule",
                },
            )

        # ── JUDGING (parallel=BATCH_SIZE per batch) ────────────────────
        await _sleep(0.5)
        yield _event("status", {"phase": "judging"})
        for bi, batch in enumerate(batches, start=1):
            await _sleep(0.4)
            # Collect real token counts where available.
            jc_pts, jc_cts = [], []
            for r in batch:
                jc = judge_by_tc.get(r["test_case_id"])
                if jc:
                    jc_pts.append(jc.get("prompt_tokens", 0))
                    jc_cts.append(jc.get("completion_tokens", 0))
            avg_jpt = sum(jc_pts) // max(len(jc_pts), 1) if jc_pts else 0
            avg_jct = sum(jc_cts) // max(len(jc_cts), 1) if jc_cts else 0
            yield _event(
                "log",
                {
                    "line": (
                        f"batch {bi}/{n_batches} · {judge_model} × {len(batch)} parallel · "
                        f"avg {avg_jpt} prompt + {avg_jct} completion tokens"
                    ),
                    "tag": "judge",
                },
            )
            await _sleep(0.6)
            # Emit test_case_done per TC in batch — feeds the live counter.
            for r in batch:
                hybrid = float(r.get("hybrid_score", 0.0))
                yield _event(
                    "test_case_done",
                    {
                        "test_case_id": r["test_case_id"],
                        "round": round_n,
                        "hybrid_score": round(hybrid, 3),
                    },
                )

        # ── TEACHER (1 call per round) ─────────────────────────────────
        await _sleep(0.5)
        yield _event("status", {"phase": "teacher"})
        added, removed = _md_change_stats(skill, round_n)
        tr = teacher_by_round.get(round_n)
        if tr:
            pt = tr.get("prompt_tokens", 0)
            ct = tr.get("completion_tokens", 0)
            elapsed = tr.get("elapsed_s", 0.0)
            yield _event(
                "log",
                {
                    "line": (
                        f"teacher · {teacher_model} · {pt} prompt + {ct} completion tokens · "
                        f"{elapsed:.1f}s"
                    ),
                    "tag": "teacher",
                },
            )
            await _sleep(0.5)
        yield _event(
            "log",
            {
                "line": (
                    f"wrote SKILL_round_{round_n}.md (+{added} lines, −{removed} lines)"
                ),
                "tag": "teacher",
            },
        )

        # ── ROUND DONE ─────────────────────────────────────────────────
        await _sleep(0.3)
        yield _event(
            "round_done",
            {
                "round": round_n,
                "avg_score": round(real_avg, 3),
                "lines_added": added,
                "lines_removed": removed,
            },
        )

    # ── COMPLETE ────────────────────────────────────────────────────────
    await _sleep(0.5)
    final_score = float(summary.get("final_score", 0.0))
    best_round = int(summary.get("best_round", rounds_n))
    best_score = float(summary.get("best_score", final_score))
    yield _event(
        "log",
        {
            "line": (
                f"run complete · final {final_score:.3f} · peak {best_score:.3f} at R{best_round}"
            ),
            "tag": "system",
        },
    )
    yield _event("status", {"phase": "done"})
    yield _event(
        "complete",
        {
            "skill": skill,
            "final_score": round(final_score, 3),
            "best_round": best_round,
            "best_score": round(best_score, 3),
        },
    )
    run.finished = True


# ── Fallback ────────────────────────────────────────────────────────────
# Hardcoded mock for the day the upstream files vanish. Same as the old
# implementation; kept inline so the runner has a single entry point.

_SUMMARY_R1_FALLBACK = {
    "docx": 0.793,
    "internal-comms": 0.735,
    "slack-gif-creator": 0.716,
}


async def _stream_simulated_fallback(run: Run, reason: str) -> AsyncIterator[str]:
    skill = run.skill
    base = _SUMMARY_R1_FALLBACK.get(skill, 0.75)
    target = base + 0.04
    tc_ids = ["tc_a01", "tc_a02", "tc_a03"]

    def jitter(seed: float) -> float:
        return seed + (random.random() - 0.5) * 0.04

    scores_plan = [
        max(0.55, min(0.98, jitter(target + 0.03))),
        max(0.55, min(0.98, jitter(target + 0.06))),
        max(0.55, min(0.98, jitter(target - 0.02))),
    ]

    yield _event("status", {"phase": "queued"})
    yield _event(
        "log",
        {"line": f"(fallback simulation — {reason})", "tag": "system"},
    )
    await _sleep(0.5)
    yield _event(
        "log",
        {
            "line": (
                f"python distillation_v2/run.py --skill {skill} --rounds 1 "
                f"--test-cases 3 --batch-size 3"
            ),
            "tag": "system",
        },
    )
    await _sleep(0.6)

    yield _event("status", {"phase": "running"})
    for tc in tc_ids:
        await _sleep(0.8)
        yield _event(
            "log",
            {"line": f"{tc} · invoking google/gemma-4-26b-a4b-it", "tag": "student"},
        )
        await _sleep(1.2)
        yield _event(
            "log",
            {"line": f"{tc} · ~1800 prompt + ~600 completion tokens", "tag": "student"},
        )
        await _sleep(0.2)
        yield _event("log", {"line": f"{tc} · rule checks: 4/5 passed", "tag": "rule"})

    await _sleep(0.5)
    yield _event("status", {"phase": "judging"})
    for tc, score in zip(tc_ids, scores_plan):
        await _sleep(1.0)
        yield _event(
            "log",
            {"line": f"{tc} · claude-haiku-4-5 scoring rubric", "tag": "judge"},
        )
        await _sleep(1.2)
        yield _event(
            "test_case_done", {"test_case_id": tc, "hybrid_score": round(score, 3)}
        )

    await _sleep(0.6)
    yield _event("status", {"phase": "teacher"})
    yield _event("log", {"line": "teacher rewriting SKILL.md", "tag": "teacher"})
    await _sleep(1.5)
    yield _event("log", {"line": "wrote SKILL_round_1.md", "tag": "teacher"})

    avg = sum(scores_plan) / len(scores_plan)
    await _sleep(0.4)
    yield _event("round_done", {"round": 1, "avg_score": round(avg, 3)})
    yield _event("status", {"phase": "done"})
    yield _event("complete", {"skill": skill, "final_score": round(avg, 3)})
    run.finished = True
