"""Run-state registry + simulated SSE event generator.

Mirrors the schema the frontend prototype already simulates locally so the same
client code paths exercise both routes. The simulation deliberately echoes the
contract the real ``distillation_v2/run.py`` subprocess will emit once wired in
— see ``HANDOFF.md`` for the parsing plan.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

# Baseline scores we want the simulated run to drift slightly above.
SUMMARY_R1 = {
    "docx": 0.793,
    "internal-comms": 0.735,
    "slack-gif-creator": 0.716,
}

# Speed factor — wall-clock time of the simulation = real_time * SPEEDUP.
# 0.35 matches the prototype's pacing (~50s for a "2-3 minute" feel).
SPEEDUP = 0.35


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


async def stream_events(run: Run) -> AsyncIterator[str]:
    """Yield SSE-formatted events that mimic a real Student → Judge → Teacher
    pipeline. Matches the contract in HANDOFF.md."""

    skill = run.skill
    target = SUMMARY_R1[skill] + 0.04
    tc_ids = ["tc_a01", "tc_a02", "tc_a03"]

    def jitter(seed: float) -> float:
        return seed + (random.random() - 0.5) * 0.04

    scores_plan = [
        max(0.55, min(0.98, jitter(target + 0.03))),
        max(0.55, min(0.98, jitter(target + 0.06))),
        max(0.55, min(0.98, jitter(target - 0.02))),
    ]

    async def sleep(seconds: float) -> None:
        await asyncio.sleep(seconds * SPEEDUP)

    # QUEUED
    yield _event("status", {"phase": "queued"})
    yield _event("log", {"line": "run accepted — preparing sandbox", "tag": "system"})
    await sleep(0.5)
    yield _event(
        "log",
        {
            "line": (
                f"python distillation_v2/run.py --skill {skill} --rounds 1 "
                "--test-cases 3 --batch-size 3"
            ),
            "tag": "system",
        },
    )
    await sleep(0.8)
    yield _event(
        "log", {"line": "loaded SKILL_round_0.md (Anthropic original)", "tag": "system"}
    )
    await sleep(0.6)
    yield _event(
        "log",
        {"line": "loading rubric · workflows=create,edit,validate", "tag": "system"},
    )
    await sleep(0.6)

    # RUNNING (student)
    yield _event("status", {"phase": "running"})
    yield _event("log", {"line": "student model invoked", "tag": "status"})
    for i in range(3):
        await sleep(0.8)
        yield _event(
            "log",
            {"line": f"{tc_ids[i]} · invoking google/gemma-3-26b-it", "tag": "student"},
        )
        await sleep(1.4)
        yield _event(
            "log",
            {
                "line": f"{tc_ids[i]} · 1842 prompt + 612 completion tokens · 1.8s",
                "tag": "student",
            },
        )
        await sleep(0.2)
        yield _event(
            "log", {"line": f"{tc_ids[i]} · rule checks: 4/5 passed", "tag": "rule"}
        )

    # JUDGING
    await sleep(0.6)
    yield _event("status", {"phase": "judging"})
    yield _event("log", {"line": "judge model invoked", "tag": "status"})
    for i in range(3):
        await sleep(1.1)
        yield _event(
            "log",
            {"line": f"{tc_ids[i]} · claude-sonnet-4.5 scoring rubric", "tag": "judge"},
        )
        await sleep(1.6)
        yield _event(
            "test_case_done",
            {"test_case_id": tc_ids[i], "hybrid_score": round(scores_plan[i], 3)},
        )

    # TEACHER
    await sleep(0.7)
    yield _event("status", {"phase": "teacher"})
    yield _event("log", {"line": "teacher model rewriting SKILL.md", "tag": "status"})
    await sleep(1.5)
    yield _event("log", {"line": "reading judge rationales (3/3)", "tag": "teacher"})
    await sleep(1.2)
    yield _event(
        "log",
        {"line": "diffing SKILL_round_0.md ↔ rewrite candidate", "tag": "teacher"},
    )
    await sleep(1.3)
    yield _event(
        "log",
        {"line": "wrote SKILL_round_1.md (+18 lines, −4 lines)", "tag": "teacher"},
    )

    # DONE
    avg = sum(scores_plan) / len(scores_plan)
    await sleep(0.5)
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
