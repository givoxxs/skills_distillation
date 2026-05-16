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
# 0.35 keeps the demo around 20–30 s — enough for the committee to follow,
# fast enough that they don't get bored.
SPEEDUP = 0.35

# How many test cases to replay per run.
N_TEST_CASES = 3


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


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds * SPEEDUP)


async def stream_events(run: Run) -> AsyncIterator[str]:
    """Replay real eval_detail.jsonl + api_calls.jsonl as a Student →
    Judge → Teacher SSE stream."""
    skill = run.skill

    # Pull real round-1 records. If anything is missing we degrade to the
    # tiny simulated fallback at the bottom of this module.
    try:
        eval_round1 = data_loader.get_eval_detail(skill, round_n=1)
        api_calls = data_loader.get_api_calls(skill, round_n=1)
        summary = data_loader.get_summary(skill)
    except Exception:  # noqa: BLE001 — fall back rather than 500
        async for evt in _stream_simulated_fallback(run, reason="data loader failed"):
            yield evt
        return

    if not eval_round1:
        async for evt in _stream_simulated_fallback(
            run, reason="no eval_detail for round 1"
        ):
            yield evt
        return

    # Stable pick: first N test cases ordered by id so the demo is repeatable.
    selected = sorted(eval_round1, key=lambda r: r["test_case_id"])[:N_TEST_CASES]
    student_model = summary.get("student_model", "google/gemma-4-26b-a4b-it")
    judge_model = summary.get("judge_model", "anthropic/claude-haiku-4-5")
    teacher_model = summary.get("teacher_model", "anthropic/claude-haiku-4-5")

    # Index judge calls by test_case for quick lookup.
    judge_by_tc: dict[str, dict] = {}
    teacher_record: dict | None = None
    for c in api_calls:
        if c.get("type") == "judge" and c.get("test_case"):
            # First record per test_case is the primary ensemble call.
            judge_by_tc.setdefault(c["test_case"], c)
        elif c.get("type") == "teacher":
            teacher_record = teacher_record or c

    # ── QUEUED ───────────────────────────────────────────────────────────
    yield _event("status", {"phase": "queued"})
    yield _event("log", {"line": "run accepted — preparing sandbox", "tag": "system"})
    await _sleep(0.5)
    yield _event(
        "log",
        {
            "line": (
                f"python distillation_v2/run.py --skill {skill} --rounds 1 "
                f"--test-cases {N_TEST_CASES} --batch-size {N_TEST_CASES}"
            ),
            "tag": "system",
        },
    )
    await _sleep(0.8)
    yield _event(
        "log",
        {"line": "loaded SKILL_round_0.md (Anthropic original)", "tag": "system"},
    )
    await _sleep(0.5)
    workflows_seen = sorted({r.get("workflow", "create") for r in selected})
    yield _event(
        "log",
        {
            "line": f"loading rubric · workflows={','.join(workflows_seen) or 'create'}",
            "tag": "system",
        },
    )
    await _sleep(0.5)

    # ── RUNNING ──────────────────────────────────────────────────────────
    yield _event("status", {"phase": "running"})
    yield _event("log", {"line": "student model invoked", "tag": "status"})
    for r in selected:
        tc_id = r["test_case_id"]
        pt, ct, lat = _student_tokens_for(tc_id)
        checks = r.get("rule_checks", [])
        passed = sum(1 for c in checks if c.get("passed"))
        total_checks = len(checks)
        await _sleep(0.7)
        yield _event(
            "log",
            {"line": f"{tc_id} · invoking {student_model}", "tag": "student"},
        )
        await _sleep(lat)
        yield _event(
            "log",
            {
                "line": (
                    f"{tc_id} · {pt} prompt + {ct} completion tokens · {lat:.1f}s"
                ),
                "tag": "student",
            },
        )
        await _sleep(0.25)
        yield _event(
            "log",
            {
                "line": f"{tc_id} · rule checks: {passed}/{total_checks} passed",
                "tag": "rule",
            },
        )

    # ── JUDGING ──────────────────────────────────────────────────────────
    await _sleep(0.6)
    yield _event("status", {"phase": "judging"})
    yield _event("log", {"line": "judge model invoked", "tag": "status"})
    for r in selected:
        tc_id = r["test_case_id"]
        jc = judge_by_tc.get(tc_id)
        if jc:
            pt = jc.get("prompt_tokens", 0)
            ct = jc.get("completion_tokens", 0)
            token_note = f"{pt} prompt + {ct} completion tokens"
        else:
            token_note = "tokens not recorded"
        await _sleep(0.9)
        yield _event(
            "log",
            {
                "line": f"{tc_id} · {judge_model} scoring rubric · {token_note}",
                "tag": "judge",
            },
        )
        await _sleep(1.2)
        hybrid = float(r.get("hybrid_score", 0.0))
        yield _event(
            "test_case_done",
            {"test_case_id": tc_id, "hybrid_score": round(hybrid, 3)},
        )

    # ── TEACHER ──────────────────────────────────────────────────────────
    await _sleep(0.7)
    yield _event("status", {"phase": "teacher"})
    yield _event(
        "log",
        {"line": "teacher model rewriting SKILL.md", "tag": "status"},
    )
    await _sleep(1.0)
    yield _event(
        "log",
        {
            "line": f"reading judge rationales ({len(selected)}/{len(selected)})",
            "tag": "teacher",
        },
    )
    await _sleep(0.8)
    yield _event(
        "log",
        {"line": "diffing SKILL_round_0.md ↔ rewrite candidate", "tag": "teacher"},
    )
    await _sleep(0.8)
    if teacher_record:
        pt = teacher_record.get("prompt_tokens", 0)
        ct = teacher_record.get("completion_tokens", 0)
        elapsed = teacher_record.get("elapsed_s", 0.0)
        yield _event(
            "log",
            {
                "line": (
                    f"{teacher_model} · {pt} prompt + {ct} completion tokens · "
                    f"{elapsed:.1f}s (replayed)"
                ),
                "tag": "teacher",
            },
        )
        await _sleep(0.6)
    yield _event(
        "log",
        {"line": "wrote SKILL_round_1.md", "tag": "teacher"},
    )

    # ── DONE ────────────────────────────────────────────────────────────
    avg = sum(float(r["hybrid_score"]) for r in selected) / max(len(selected), 1)
    await _sleep(0.4)
    yield _event(
        "round_done",
        {"round": 1, "avg_score": round(avg, 3)},
    )
    yield _event("status", {"phase": "done"})
    yield _event(
        "complete",
        {"skill": skill, "final_score": round(avg, 3)},
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
                f"--test-cases {N_TEST_CASES} --batch-size {N_TEST_CASES}"
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
