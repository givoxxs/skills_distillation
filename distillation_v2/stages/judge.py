"""LLM Judge: score output using rubric + PNG images of the DOCX output.

Flow per test case:
  1. Find .docx in output_dir → convert to PNG[] via utils.converter.
  2. Build Anthropic API call: rubric JSON + task prompt + PNG image blocks.
  3. Parse per-criterion scores → aggregate → EvalResult.

Fallback: if PNG conversion fails, send text description of failure (score=0).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import statistics
from pathlib import Path
from typing import Any


from evaluator.base import CheckResult, EvalResult
from utils import write_api_call
from utils.converter import docx_to_images, find_docx
from utils.llm_call import call_llm

_log = logging.getLogger("distillation.v2.judge")

DEFAULT_MODEL = "claude-haiku-4-5"
MAX_IMAGE_PAGES = 10

_SYSTEM_PROMPT = """You evaluate AI agent outputs using a provided rubric and \
screenshots of the output document.

You receive:
1. A rubric with named criteria, descriptions, weights, and pass_thresholds.
2. The original task prompt and expected behavior.
3. PNG screenshots of the output file (one per page), or a note that no output was produced.

For EACH criterion, assign a score 0.0-1.0 and a one-sentence reason.
Compute overall = sum(score * weight) across all criteria.

Respond ONLY with valid JSON (no markdown, no prose):
{
  "criteria": [
    {"name": "<name>", "score": <float>, "reason": "<one sentence>"},
    ...
  ],
  "overall": <float 0.0-1.0>,
  "verdict": "PASS" | "FAIL"
}

Rules:
- "overall" MUST equal the weight-averaged sum of criterion scores.
- "verdict" is PASS if overall >= 0.8, else FAIL.
- If no output exists, score all criteria 0.0."""


class Judge:
    """Image-based LLM judge backed by an auto-generated rubric."""

    def __init__(
        self,
        rubric: dict[str, Any],
        model: str = DEFAULT_MODEL,
        ensemble_n: int = 1,
        max_image_pages: int = MAX_IMAGE_PAGES,
        anthropic_api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        if not isinstance(rubric, dict) or "criteria" not in rubric:
            raise ValueError("rubric must have a 'criteria' list")
        self.rubric = rubric
        self.model = model
        self.ensemble_n = max(1, int(ensemble_n))
        self.max_image_pages = max_image_pages
        self._api_key = anthropic_api_key or os.getenv("ANTHROPIC_KEY")
        self._base_url = base_url
        if not self._api_key:
            raise RuntimeError(
                "No API key set for Judge (ANTHROPIC_KEY or OpenRouter key required)"
            )

    def score(
        self,
        output_dir: str,
        test_case: dict[str, Any],
        model: str,
        round_n: int,
        input_files: list[Path] | None = None,
    ) -> EvalResult:
        tc_id = test_case.get("id", "unknown")
        skill = test_case.get("skill", "unknown")

        result = EvalResult(
            test_case_id=tc_id,
            skill=skill,
            model=model,
            round_n=round_n,
            output_dir=str(output_dir),
        )
        image_paths = self._get_images(Path(output_dir))
        text_output = (
            self._get_text_output(Path(output_dir)) if not image_paths else None
        )
        content_blocks = self._build_content(
            test_case, image_paths, text_output, input_files
        )

        overalls: list[float] = []
        per_criterion: dict[str, list[tuple[float, str]]] = {
            c["name"]: [] for c in self.rubric["criteria"]
        }

        for i in range(self.ensemble_n):
            parsed = self._call_once(content_blocks, tc_id, i)
            if parsed is None:
                continue
            overalls.append(parsed["overall"])
            for c in parsed.get("criteria", []):
                name = c.get("name", "")
                if name in per_criterion:
                    per_criterion[name].append((c["score"], c.get("reason", "")))

        if not overalls:
            result.llm_judge_score = 0.0
            result.llm_judge_reasoning = "all judge calls failed"
            return result

        result.llm_judge_score = float(statistics.median(overalls))

        reason_parts: list[str] = []
        for c in self.rubric["criteria"]:
            name = c["name"]
            votes = per_criterion[name]
            if not votes:
                result.checks.append(
                    CheckResult(
                        name=name, passed=False, score=0.0, reason="no judge vote"
                    )
                )
                continue
            c_score = float(statistics.median(v[0] for v in votes))
            reason = votes[-1][1]
            passed = c_score >= float(c.get("pass_threshold", 0.8))
            result.checks.append(
                CheckResult(name=name, passed=passed, score=c_score, reason=reason)
            )
            reason_parts.append(f"{name}={c_score:.2f}: {reason}")

        result.llm_judge_reasoning = " | ".join(reason_parts)[:1000]
        return result

    # ── Image / text handling ─────────────────────────────────────────────────

    def _get_images(self, output_dir: Path) -> list[Path]:
        docx = find_docx(output_dir)
        if docx is None:
            _log.debug("judge: no .docx found in %s", output_dir)
            return []
        images = docx_to_images(docx, max_pages=self.max_image_pages)
        if not images:
            _log.debug("judge: image conversion failed for %s", docx)
        return images

    def _get_text_output(self, output_dir: Path) -> str | None:
        """Return text content from .txt/.json/.md when no .docx exists."""
        for ext in (".txt", ".json", ".md"):
            for f in sorted(output_dir.glob(f"*{ext}")):
                try:
                    text = f.read_text(encoding="utf-8", errors="replace").strip()
                    if text:
                        return text[:8000]
                except Exception:  # noqa: BLE001
                    continue
        return None

    def _build_content(
        self,
        test_case: dict[str, Any],
        image_paths: list[Path],
        text_output: str | None = None,
        input_files: list[Path] | None = None,
    ) -> list[dict[str, Any]]:
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
        intro = (
            f"## Rubric\n\n{rubric_json}\n\n"
            f"## Task\n\nPrompt: {test_case.get('prompt', '')[:500]}\n\n"
            f"Expected: {test_case.get('expected_behavior', '')[:300]}\n\n"
        )
        blocks: list[dict[str, Any]] = [{"type": "text", "text": intro}]

        # Inject input fixture pages so judge can verify extraction correctness
        if input_files:
            for src in input_files:
                if not src.is_file():
                    continue
                fixture_images = docx_to_images(src, max_pages=self.max_image_pages)
                if fixture_images:
                    blocks.append(
                        {"type": "text", "text": f"## Input Document: {src.name}\n"}
                    )
                    for img_path in fixture_images:
                        try:
                            data = base64.standard_b64encode(
                                img_path.read_bytes()
                            ).decode()
                            blocks.append(
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": data,
                                    },
                                }
                            )
                        except Exception:  # noqa: BLE001
                            _log.warning(
                                "judge: failed to encode fixture image %s", img_path
                            )

        if image_paths:
            blocks.append(
                {
                    "type": "text",
                    "text": f"## Output Document ({len(image_paths)} page(s))\n",
                }
            )
            for img_path in image_paths:
                try:
                    data = base64.standard_b64encode(img_path.read_bytes()).decode()
                    blocks.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": data,
                            },
                        }
                    )
                except Exception as e:  # noqa: BLE001
                    _log.warning("judge: failed to encode image %s: %s", img_path, e)
        elif text_output is not None:
            blocks.append(
                {
                    "type": "text",
                    "text": f"## Output File Content\n\n{text_output}",
                }
            )
        else:
            blocks.append(
                {
                    "type": "text",
                    "text": "## Output\n\nNo output file was produced by the agent.",
                }
            )

        blocks.append({"type": "text", "text": "\n---\nScore now (JSON only)."})
        return blocks

    # ── API call ──────────────────────────────────────────────────────────────

    def _call_once(
        self,
        content_blocks: list[dict[str, Any]],
        tc_id: str,
        ensemble_idx: int,
    ) -> dict[str, Any] | None:
        try:
            raw, usage = call_llm(
                system=_SYSTEM_PROMPT,
                user=content_blocks,
                model=self.model,
                api_key=self._api_key,
                max_tokens=2048,
                base_url=self._base_url,
            )
            parsed = _parse_response(raw)
            write_api_call(
                {
                    "type": "judge",
                    "model": self.model,
                    "test_case": tc_id,
                    "ensemble_idx": ensemble_idx,
                    "overall": parsed["overall"],
                    "has_images": any(b.get("type") == "image" for b in content_blocks),
                    **usage,
                }
            )
            return parsed
        except Exception as e:  # noqa: BLE001
            _log.warning("judge call failed for %s (i=%d): %s", tc_id, ensemble_idx, e)
            return None


# ── Response parser ───────────────────────────────────────────────────────────


def _parse_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            lines[1:-1] if lines[-1].startswith("```") else lines[1:]
        ).strip()
    data = json.loads(text)
    if "overall" not in data:
        raise ValueError("judge response missing 'overall'")
    data["overall"] = max(0.0, min(1.0, float(data["overall"])))
    return data
