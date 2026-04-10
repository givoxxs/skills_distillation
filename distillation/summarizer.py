"""Summarizer: reads JSONL execution logs + EvalResults → key_notes for Teacher.

The key_notes are a compact, structured text that tells the Teacher:
  - What the student model did wrong (error patterns, loop types)
  - Which checks failed and why
  - What already improved vs last round
  - Scores per round for trend context
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from evaluator.base import EvalResult

_logger = logging.getLogger("distillation.summarizer")


def summarize(
    eval_results: list[EvalResult],
    log_paths: list[str],
    prev_round_results: list[EvalResult] | None = None,
    round_n: int = 0,
) -> str:
    """Build key_notes text from eval results and JSONL logs.

    Args:
        eval_results:       Scored results for this round.
        log_paths:          Paths to JSONL log files from skill_runner.
        prev_round_results: Scored results from previous round (for delta).
        round_n:            Current round number.

    Returns:
        A structured text string to pass to Teacher.
    """
    lines: list[str] = []
    lines.append(f"# Distillation Round {round_n} — Error Analysis")
    lines.append("")

    # ── Score summary ─────────────────────────────────────────────────────────
    avg_score = (
        sum(r.rule_score for r in eval_results) / len(eval_results)
        if eval_results
        else 0.0
    )
    pass_count = sum(1 for r in eval_results if r.rule_score >= 0.6)
    lines.append("## Score Summary")
    lines.append(f"- Test cases run: {len(eval_results)}")
    lines.append(f"- Pass (≥0.6): {pass_count}/{len(eval_results)}")
    lines.append(f"- Average rule score: {avg_score:.2f}")

    if prev_round_results:
        prev_avg = sum(r.rule_score for r in prev_round_results) / len(
            prev_round_results
        )
        delta = avg_score - prev_avg
        sign = "+" if delta >= 0 else ""
        lines.append(f"- Delta from round {round_n - 1}: {sign}{delta:.2f}")
    lines.append("")

    _logger.debug(
        "summarizer round=%d: %d results, avg=%.3f, pass=%d/%d",
        round_n,
        len(eval_results),
        avg_score,
        pass_count,
        len(eval_results),
    )

    # ── Failed checks breakdown ───────────────────────────────────────────────
    lines.append("## Failed Checks (all test cases)")
    fail_counts: dict[str, int] = {}
    fail_reasons: dict[str, list[str]] = {}
    for r in eval_results:
        for c in r.failed_checks:
            fail_counts[c.name] = fail_counts.get(c.name, 0) + 1
            if c.reason:
                fail_reasons.setdefault(c.name, []).append(c.reason)

    if fail_counts:
        for check_name, count in sorted(fail_counts.items(), key=lambda x: -x[1]):
            pct = count / len(eval_results) * 100
            lines.append(
                f"- `{check_name}`: failed {count}/{len(eval_results)} cases ({pct:.0f}%)"
            )
            reasons = fail_reasons.get(check_name, [])
            seen = set()
            for r in reasons[:3]:  # show up to 3 unique reasons
                if r not in seen:
                    lines.append(f"    • {r}")
                    seen.add(r)
    else:
        lines.append("- No failed checks.")
    lines.append("")

    # ── Agent behavior patterns from JSONL logs ───────────────────────────────
    lines.append("## Agent Behavior Patterns (from execution logs)")
    patterns = _extract_patterns(log_paths)
    _logger.debug(
        "summarizer: parsed %d log files → %d patterns",
        len(log_paths),
        len(patterns),
    )
    if patterns:
        for p in patterns:
            lines.append(f"- {p}")
    else:
        lines.append("- No logs available.")
    lines.append("")

    # ── Per test-case breakdown ───────────────────────────────────────────────
    lines.append("## Per Test-Case Results")
    for r in eval_results:
        lines.append(f"- {r.summary_line()}")
    lines.append("")

    # ── Rewrite guidance hint ─────────────────────────────────────────────────
    lines.append("## Suggested Focus for SKILL.md Rewrite")
    hints = _generate_hints(fail_counts, patterns)
    _logger.debug(
        "summarizer: fail_counts=%s → %d hints generated",
        dict(sorted(fail_counts.items(), key=lambda x: -x[1])[:5]),
        len(hints),
    )
    for h in hints:
        lines.append(f"- {h}")

    key_notes = "\n".join(lines)
    _logger.debug("summarizer: key_notes generated: %d chars", len(key_notes))
    return key_notes


def _extract_patterns(log_paths: list[str]) -> list[str]:
    """Parse JSONL logs and extract recurring error/behavior patterns."""
    patterns: list[str] = []
    tool_error_counts: dict[str, int] = {}
    loop_detected_count = 0
    stop_reasons: dict[str, int] = {}
    avg_iterations: list[int] = []

    for log_path in log_paths:
        path = Path(log_path)
        if not path.exists():
            continue

        try:
            events = [
                json.loads(line)
                for line in path.read_text().splitlines()
                if line.strip()
            ]
        except Exception as exc:
            _logger.warning("summarizer: failed to parse JSONL %s: %s", log_path, exc)
            continue

        for event in events:
            etype = event.get("event")

            if etype == "tool_result":
                result = event.get("result", "")
                tool = event.get("tool", "")
                if result.startswith("ERROR:") or "[EXIT CODE]:" in result:
                    tool_error_counts[tool] = tool_error_counts.get(tool, 0) + 1

            elif etype == "loop_detected":
                loop_detected_count += 1

            elif etype == "end":
                stop_reasons[event.get("stop_reason", "unknown")] = (
                    stop_reasons.get(event.get("stop_reason", "unknown"), 0) + 1
                )
                iters = event.get("iterations")
                if iters:
                    avg_iterations.append(iters)

    if stop_reasons:
        for reason, count in stop_reasons.items():
            patterns.append(f"Stop reason '{reason}': {count} run(s)")

    if avg_iterations:
        avg = sum(avg_iterations) / len(avg_iterations)
        patterns.append(f"Average iterations per run: {avg:.1f}")

    if loop_detected_count:
        patterns.append(
            f"Loop detected {loop_detected_count} time(s) — model repeated same failing command"
        )

    for tool, count in sorted(tool_error_counts.items(), key=lambda x: -x[1]):
        patterns.append(f"Tool '{tool}' errored {count} time(s) across all runs")

    return patterns


def _generate_hints(
    fail_counts: dict[str, int],
    patterns: list[str],
) -> list[str]:
    """Generate actionable hints for the Teacher based on failure analysis."""
    hints = []

    if fail_counts.get("file_exists", 0):
        hints.append(
            "Model failed to produce output file — add explicit instruction: "
            "'You MUST save the final .docx to the workspace root before calling end_turn'"
        )
    if fail_counts.get("file_parseable", 0):
        hints.append(
            "Output file was corrupt or invalid — add instruction to verify file "
            "with python-docx or by checking file size after creation"
        )
    if fail_counts.get("min_paragraphs", 0) or fail_counts.get("min_word_count", 0):
        hints.append(
            "Output content too sparse — add minimum content requirements to SKILL.md "
            "(e.g., 'document must contain at least 3 substantive paragraphs')"
        )
    if fail_counts.get("no_placeholders", 0):
        hints.append(
            "Model left unfilled placeholders — add instruction: "
            "'Never leave [INSERT...] or {{field}} placeholders — fill all content directly'"
        )
    if fail_counts.get("has_heading", 0):
        hints.append(
            "Model did not use heading styles — add example showing how to apply "
            "Heading 1/2/3 styles in the chosen library (docx-js or python-docx)"
        )
    if fail_counts.get("has_table", 0):
        hints.append(
            "Model omitted required table — add explicit table creation example to SKILL.md"
        )
    if fail_counts.get("has_toc", 0):
        hints.append(
            "Model omitted table of contents — add step-by-step TOC creation instructions"
        )
    if fail_counts.get("heading_hierarchy", 0):
        hints.append(
            "Heading levels are out of order — add rule: 'Use H1→H2→H3 in order, never skip levels'"
        )

    any_loop = any("loop" in p.lower() for p in patterns)
    if any_loop:
        hints.append(
            "Model got stuck in a loop — add fallback strategy: "
            "'If JavaScript fails after 2 attempts, switch to python-docx instead'"
        )

    max_iter = any("max_iterations" in p for p in patterns)
    if max_iter:
        hints.append(
            "Runs hit max_iterations — SKILL.md may be too complex; "
            "simplify the workflow and provide a complete working code template"
        )

    if not hints:
        hints.append(
            "No obvious issues — consider improving content quality or edge case handling"
        )

    return hints
