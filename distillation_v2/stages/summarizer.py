"""Summarize batch results into run_log.md for the Teacher.

Each batch generates one run_log.md with:
- Score summary (pass/fail counts, avg)
- Per-criterion failure breakdown
- Per-TC results (ID, pass/fail, failed criteria, output snippet)
- Agent behavior patterns from JSONL logs
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from evaluator.base import EvalResult

_log = logging.getLogger("distillation.v2.summarizer")

_MAX_SNIPPET_CHARS = 300


def make_run_log(
    batch_results: list[EvalResult],
    round_n: int,
    batch_idx: int,
    log_paths: list[str] | None = None,
    prev_round_results: list[EvalResult] | None = None,
) -> str:
    """Build run_log.md content for one batch."""
    lines: list[str] = []
    lines.append(f"# Run Log — Round {round_n}, Batch {batch_idx}")
    lines.append("")

    avg = (
        sum(r.llm_judge_score for r in batch_results if r.llm_judge_score >= 0)
        / len(batch_results)
        if batch_results
        else 0.0
    )
    passed = sum(1 for r in batch_results if r.llm_judge_score >= 0.8)
    lines.append("## Batch Score Summary")
    lines.append(f"- Test cases: {len(batch_results)}")
    lines.append(f"- Passed (≥0.8): {passed}/{len(batch_results)}")
    lines.append(f"- Average score: {avg:.3f}")
    if prev_round_results:
        prev_avg = sum(
            r.llm_judge_score for r in prev_round_results if r.llm_judge_score >= 0
        ) / len(prev_round_results)
        sign = "+" if avg >= prev_avg else ""
        lines.append(f"- Delta from prev round avg: {sign}{avg - prev_avg:.3f}")
    lines.append("")

    # Criterion failure breakdown
    fail_counts: dict[str, int] = {}
    fail_reasons: dict[str, list[str]] = {}
    for r in batch_results:
        for c in r.failed_checks:
            fail_counts[c.name] = fail_counts.get(c.name, 0) + 1
            if c.reason:
                fail_reasons.setdefault(c.name, []).append(c.reason)

    lines.append("## Failed Criteria")
    if fail_counts:
        for name, count in sorted(fail_counts.items(), key=lambda x: -x[1]):
            pct = count / len(batch_results) * 100
            lines.append(f"- `{name}`: {count}/{len(batch_results)} ({pct:.0f}%)")
            for reason in list(dict.fromkeys(fail_reasons.get(name, [])))[:2]:
                lines.append(f"  • {reason}")
    else:
        lines.append("- None")
    lines.append("")

    # Per-TC detail
    lines.append("## Per Test-Case Results")
    for r in batch_results:
        score = r.llm_judge_score if r.llm_judge_score >= 0 else 0.0
        status = "PASS" if score >= 0.8 else "FAIL"
        fails = ", ".join(c.name for c in r.failed_checks) or "none"
        snippet = _get_output_snippet(r.output_dir)
        lines.append(
            f"- [{status}] `{r.test_case_id}` score={score:.2f} failed=[{fails}]"
        )
        if snippet:
            lines.append(f"  output: {snippet}")
    lines.append("")

    # Agent behavior patterns
    if log_paths:
        patterns = _extract_patterns(log_paths)
        if patterns:
            lines.append("## Agent Behavior Patterns")
            for p in patterns:
                lines.append(f"- {p}")
            lines.append("")

    return "\n".join(lines)


def _get_output_snippet(output_dir: str) -> str:
    """Return a short text snippet from any text output file in output_dir."""
    out = Path(output_dir)
    if not out.is_dir():
        return ""
    for ext in (".txt", ".md", ".json"):
        for f in sorted(out.glob(f"*{ext}")):
            try:
                text = f.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    return text[:_MAX_SNIPPET_CHARS].replace("\n", " ")
            except Exception:  # noqa: BLE001
                continue
    return ""


def _extract_patterns(log_paths: list[str]) -> list[str]:
    patterns: list[str] = []
    stop_reasons: dict[str, int] = {}
    tool_errors: dict[str, int] = {}
    iterations: list[int] = []

    for path_str in log_paths:
        path = Path(path_str)
        if not path.exists():
            continue
        try:
            events = [
                json.loads(line)
                for line in path.read_text().splitlines()
                if line.strip()
            ]
        except Exception:  # noqa: BLE001
            continue
        for ev in events:
            etype = ev.get("event")
            if etype == "tool_result":
                result = ev.get("result", "")
                if result.startswith("ERROR:") or "[EXIT CODE]:" in result:
                    tool = ev.get("tool", "unknown")
                    tool_errors[tool] = tool_errors.get(tool, 0) + 1
            elif etype == "end":
                reason = ev.get("stop_reason", "unknown")
                stop_reasons[reason] = stop_reasons.get(reason, 0) + 1
                iters = ev.get("iterations")
                if iters:
                    iterations.append(iters)

    for reason, count in stop_reasons.items():
        patterns.append(f"Stop reason '{reason}': {count} run(s)")
    if iterations:
        patterns.append(f"Avg iterations: {sum(iterations)/len(iterations):.1f}")
    for tool, count in sorted(tool_errors.items(), key=lambda x: -x[1]):
        patterns.append(f"Tool '{tool}' errored {count} time(s)")

    return patterns
