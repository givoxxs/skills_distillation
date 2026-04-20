"""LLM-only judge: scores a test case output against an auto-generated rubric.

Differences vs v1 LLM Judge:
  - Accepts a rubric (dict from rubric_generator) instead of hard-coded criteria.
  - Requests per-criterion scores so we can log rubric discrimination.
  - Produces an EvalResult with rule_weight=0, llm_weight=1 → hybrid_score == overall
    (summarizer and stopping criteria stay compatible with v1).

Reuses v1's content extraction (_extract_content) to read docx/pdf/xlsx outputs.
"""

from __future__ import annotations

import json
import logging
import os
import statistics
from pathlib import Path
from typing import Any

import anthropic

from utils import write_api_call
from evaluator.base import CheckResult, EvalResult
from evaluator.llm_judge import _extract_content
from runner.anthropic_env import anthropic_env

_log = logging.getLogger("distillation.v2.llm_only_judge")

DEFAULT_MODEL = "claude-haiku-4-5"
MAX_CONTENT_CHARS = 3000


# ── Prompt ────────────────────────────────────────────────────────────────────

_JUDGE_SYSTEM = """You are an evaluator for AI agent outputs.

You will receive:
  1. A rubric (list of criteria with names, descriptions, weights, pass_thresholds).
  2. The user's original task prompt.
  3. The expected behavior (if provided).
  4. Extracted content from the agent's output file(s).

For EACH criterion, assign a score 0.0-1.0 and a one-sentence reason. Then compute
an overall score as the weight-weighted average.

Respond ONLY with valid JSON (no markdown fence, no prose):
{
  "criteria": [
    {"name": "<criterion name>", "score": <float>, "reason": "<one sentence>"},
    ...
  ],
  "overall": <float 0.0-1.0>,
  "verdict": "PASS" | "FAIL"
}

Rules:
  - "overall" MUST equal sum(criterion.score * criterion.weight) across all criteria.
  - "verdict" is PASS if overall >= 0.6, else FAIL.
  - If the output is empty or missing, score all criteria 0.0.
"""


class LLMOnlyJudge:
    """Pure LLM-Judge evaluator backed by an auto-generated rubric."""

    def __init__(
        self,
        rubric: dict[str, Any],
        model: str = DEFAULT_MODEL,
        ensemble_n: int = 1,
        anthropic_api_key: str | None = None,
    ) -> None:
        if not isinstance(rubric, dict) or "criteria" not in rubric:
            raise ValueError("rubric must be a dict with a 'criteria' list")
        self.rubric = rubric
        self.model = model
        self.ensemble_n = max(1, int(ensemble_n))
        self._api_key = anthropic_api_key or os.getenv("ANTHROPIC_KEY")
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_KEY not set (LLMOnlyJudge requires it)")

    # ── BaseEvaluator protocol ───────────────────────────────────────────────
    def score(
        self,
        output_dir: str,
        test_case: dict[str, Any],
        model: str,
        round_n: int,
    ) -> EvalResult:
        tc_id = test_case.get("id", "unknown")
        skill = test_case.get("skill", "unknown")

        fixture_basename = Path(test_case.get("fixture_file", "")).name
        content = _extract_content(output_dir, skill, fixture_basename=fixture_basename)

        result = EvalResult(
            test_case_id=tc_id,
            skill=skill,
            model=model,
            round_n=round_n,
            output_dir=str(output_dir),
        )
        # v2: rule weight=0, llm weight=1 → hybrid_score == llm_judge_score
        result._rule_weight = 0.0
        result._llm_weight = 1.0
        result._human_weight = 0.0
        result.rule_score = 0.0  # unused in v2 but preserved for schema compat

        if not content.strip():
            result.llm_judge_score = 0.0
            result.llm_judge_reasoning = "No extractable content in output_dir"
            result.checks.append(
                CheckResult(
                    name="output_present",
                    passed=False,
                    score=0.0,
                    reason="no output file found or empty",
                )
            )
            return result

        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS] + "\n... [truncated]"

        prompt = self._build_user_prompt(test_case, content)

        overalls: list[float] = []
        per_criterion_agg: dict[str, list[tuple[float, str]]] = {
            c["name"]: [] for c in self.rubric["criteria"]
        }

        for i in range(self.ensemble_n):
            parsed = self._call_once(prompt, tc_id, i)
            if parsed is None:
                continue
            overalls.append(parsed["overall"])
            for c in parsed.get("criteria", []):
                if c["name"] in per_criterion_agg:
                    per_criterion_agg[c["name"]].append(
                        (c["score"], c.get("reason", ""))
                    )

        if not overalls:
            result.llm_judge_score = 0.0
            result.llm_judge_reasoning = "All Judge calls failed"
            return result

        median_overall = float(statistics.median(overalls))
        result.llm_judge_score = median_overall

        reason_parts: list[str] = []
        for c in self.rubric["criteria"]:
            name = c["name"]
            votes = per_criterion_agg[name]
            if not votes:
                result.checks.append(
                    CheckResult(
                        name=name, passed=False, score=0.0, reason="no judge vote"
                    ),
                )
                continue
            c_median = float(statistics.median(v[0] for v in votes))
            last_reason = votes[-1][1]
            passed = c_median >= float(c.get("pass_threshold", 0.6))
            result.checks.append(
                CheckResult(
                    name=name, passed=passed, score=c_median, reason=last_reason
                ),
            )
            reason_parts.append(f"{name}={c_median:.2f}: {last_reason}")

        result.llm_judge_reasoning = " | ".join(reason_parts)[:1000]
        return result

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_user_prompt(self, test_case: dict[str, Any], content: str) -> str:
        rubric_json = json.dumps(
            {
                "criteria": [
                    {
                        "name": c["name"],
                        "description": c["description"],
                        "weight": c["weight"],
                        "pass_threshold": c["pass_threshold"],
                    }
                    for c in self.rubric["criteria"]
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        return f"""## Rubric

{rubric_json}

## Task

Prompt: {test_case.get("prompt", "")[:500]}

Expected behavior: {test_case.get("expected_behavior", "")[:300]}

## Output content

{content}

---

Score now (JSON only)."""

    def _call_once(
        self, prompt: str, tc_id: str, ensemble_idx: int
    ) -> dict[str, Any] | None:
        try:
            with anthropic_env(self._api_key):
                client = anthropic.Anthropic()
                message = client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=_JUDGE_SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                )
            raw = message.content[0].text.strip()
            parsed = _parse_judge_response(raw)
            write_api_call(
                {
                    "type": "llm_only_judge",
                    "model": self.model,
                    "test_case": tc_id,
                    "ensemble_idx": ensemble_idx,
                    "overall": parsed["overall"],
                    "verdict": parsed.get("verdict", ""),
                    "prompt_tokens": message.usage.input_tokens,
                    "completion_tokens": message.usage.output_tokens,
                }
            )
            return parsed
        except Exception as e:  # noqa: BLE001
            _log.warning("judge call failed for %s (i=%d): %s", tc_id, ensemble_idx, e)
            return None


# ── Response parser ──────────────────────────────────────────────────────────


def _parse_judge_response(raw: str) -> dict[str, Any]:
    """Parse a judge response. Tolerates ```json fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    if "overall" not in data:
        raise ValueError("judge response missing 'overall'")
    overall = float(data["overall"])
    data["overall"] = max(0.0, min(1.0, overall))
    return data
