"""Auto-generate a per-skill evaluation rubric once, cache it, reuse for all tests.

Replaces v1's hand-written rule_checks. The LLM reads SKILL.md + a handful of
sample test cases and produces 4-8 criteria with weights — one unified rubric
that applies to every test case for that skill.

Cache key = sha256(SKILL.md content) + sha256(sorted test case IDs). If SKILL.md
changes (Teacher rewrites it) or the test set changes, the cache invalidates.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import anthropic


def _load_v1_module(rel: str, name: str):
    """Load a v1 module by absolute path to avoid package-name collisions."""
    p = Path(__file__).resolve().parent.parent.parent / "distillation" / rel
    spec = importlib.util.spec_from_file_location(name, p)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_v1_utils = _load_v1_module("utils.py", "_v1_utils_for_rubric")
write_api_call = _v1_utils.write_api_call

_V2_ROOT = Path(__file__).resolve().parent.parent
if str(_V2_ROOT) not in sys.path:
    sys.path.insert(0, str(_V2_ROOT))
from runner.anthropic_env import anthropic_env  # noqa: E402

_log = logging.getLogger("distillation.v2.rubric_generator")

DEFAULT_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 4096

_SYSTEM_PROMPT = """You design evaluation rubrics for AI agent skills executed \
by SMALL language models (e.g. Qwen3-8B via Claude Code CLI).

Given:
  - Full skill context (SKILL.md, helper scripts, requirements)
  - ALL test cases for the skill (30 cases typical)

Produce a rubric of 4-8 independent, checkable criteria that distinguish \
high-quality from low-quality outputs for THIS skill. The rubric must work for \
ALL test cases (CREATE, READ, EDIT, CONVERT, EDGE workflows).

Rules:
1. Each criterion must be OBJECTIVELY checkable by another LLM reading the output.
2. Weights must sum to exactly 1.0.
3. pass_threshold is the per-criterion minimum score (0.0-1.0) for "acceptable".
4. Include at least one criterion about FILE VALIDITY / FORMAT (e.g. valid DOCX, \
parseable JSON, non-empty output).
5. Include at least one criterion about TASK COMPLETION (did it do what was asked?).
6. Include criteria specific to the skill's technical requirements (structure, \
API usage, edge cases covered by test cases).
7. Write descriptions in imperative form so a judge LLM knows how to evaluate.

Output ONLY valid JSON, no prose, no markdown fence. Schema:
{
  "criteria": [
    {"name": "...", "description": "...", "weight": 0.0, "pass_threshold": 0.0},
    ...
  ],
  "notes": "one-sentence rationale covering key skill requirements"
}"""


# ── Cache helpers ─────────────────────────────────────────────────────────────


def _read_skill_context(skill_dir: Path) -> str:
    """Read SKILL.md + scripts + requirements from skill folder."""
    parts = []

    # 1. SKILL.md
    skill_md_path = skill_dir / "SKILL.md"
    if skill_md_path.is_file():
        content = skill_md_path.read_text(encoding="utf-8")
        parts.append(f"# SKILL.md\n\n{content}")

    # 2. Helper scripts (first 1KB each to avoid huge tokens)
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        parts.append("\n# Scripts\n")
        for py_file in sorted(scripts_dir.glob("*.py")):
            try:
                content = py_file.read_text(encoding="utf-8")[:1000]
                parts.append(f"## {py_file.name}\n\n{content}...")
            except Exception as e:  # noqa: BLE001
                _log.debug("Failed to read %s: %s", py_file, e)

    # 3. Requirements
    req_file = skill_dir / "requirements.txt"
    if req_file.is_file():
        try:
            parts.append(f"\n# requirements.txt\n\n{req_file.read_text()}")
        except Exception as e:  # noqa: BLE001
            _log.debug("Failed to read requirements.txt: %s", e)

    return "\n---\n".join(parts)


def _cache_key(skill_dir_content: str, test_case_ids: list[str]) -> str:
    """Generate cache key from skill_dir content + all test_case IDs."""
    skill_hash = hashlib.sha256(skill_dir_content.encode("utf-8")).hexdigest()[:12]
    ids_hash = hashlib.sha256(
        ",".join(sorted(test_case_ids)).encode("utf-8")
    ).hexdigest()[:12]
    return f"{skill_hash}_{ids_hash}"


def _cache_path(cache_dir: Path, skill_name: str, key: str) -> Path:
    return cache_dir / f"{skill_name}_{key}.json"


# ── Public API ────────────────────────────────────────────────────────────────


def generate_rubric(
    skill_name: str,
    skill_dir: str | Path,
    test_cases: list[dict[str, Any]],
    cache_dir: str | Path,
    model: str = DEFAULT_MODEL,
    regenerate: bool = False,
    anthropic_api_key: str | None = None,
) -> dict[str, Any]:
    """Return a rubric dict for the skill, generating + caching if needed.

    Args:
        skill_name:       Folder name of the skill (e.g. "docx").
        skill_dir:        Path to the skill folder (contains SKILL.md + scripts/).
        test_cases:       List of ALL test case dicts with 'id', 'prompt',
                          'expected_behavior'. This will be passed in full to Claude.
        cache_dir:        Root directory for cached rubric JSON files.
        model:            Claude model ID for rubric generation.
        regenerate:       If True, bypass the cache and always call the API.
        anthropic_api_key: If provided, used via anthropic_env context manager.
                           Defaults to ANTHROPIC_KEY env var.

    Returns:
        dict with keys: criteria (list), notes (str), generated_at, model,
        token_usage, cache_key.
    """
    skill_dir = Path(skill_dir)
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"skill_dir not found: {skill_dir}")

    # Read full skill context (SKILL.md + scripts + requirements)
    skill_content = _read_skill_context(skill_dir)
    tc_ids = [tc.get("id", "") for tc in test_cases]
    key = _cache_key(skill_content, tc_ids)

    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(cache_root, skill_name, key)

    if cache_file.is_file() and not regenerate:
        _log.info("rubric cache hit: %s", cache_file.name)
        try:
            return json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            _log.warning("corrupt rubric cache, regenerating: %s", cache_file)

    _log.info(
        "rubric cache miss, generating via %s… (%d test cases)",
        model,
        len(test_cases),
    )
    api_key = anthropic_api_key or os.getenv("ANTHROPIC_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_KEY not set (rubric generator requires it)")

    rubric = _call_api(
        skill_name=skill_name,
        skill_content=skill_content,
        test_cases=test_cases,  # ← pass ALL, not sampled
        model=model,
        api_key=api_key,
    )
    rubric["cache_key"] = key
    cache_file.write_text(json.dumps(rubric, indent=2, ensure_ascii=False))
    _log.info(
        "rubric written to %s (%d criteria)",
        cache_file,
        len(rubric.get("criteria", [])),
    )
    return rubric


# ── API call ──────────────────────────────────────────────────────────────────


def _call_api(
    skill_name: str,
    skill_content: str,
    test_cases: list[dict[str, Any]],
    model: str,
    api_key: str,
) -> dict[str, Any]:
    user_prompt = _build_user_prompt(skill_name, skill_content, test_cases)

    with anthropic_env(api_key):
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

    raw = message.content[0].text.strip()
    usage = {
        "prompt_tokens": message.usage.input_tokens,
        "completion_tokens": message.usage.output_tokens,
    }
    write_api_call(
        {
            "type": "rubric_generator",
            "model": model,
            "skill": skill_name,
            "test_cases_count": len(test_cases),
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
        }
    )

    try:
        rubric = _parse_and_validate(raw)
    except ValueError as e:
        raise RuntimeError(
            f"Rubric generator returned invalid JSON: {e}\nRaw:\n{raw[:500]}"
        )

    rubric["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    rubric["model"] = model
    rubric["token_usage"] = usage
    return rubric


def _build_user_prompt(
    skill_name: str, skill_content: str, test_cases: list[dict[str, Any]]
) -> str:
    """Build prompt with full skill context and ALL test cases."""
    # Format all test cases
    test_lines: list[str] = []
    for tc in test_cases:
        tc_id = tc.get("id", "tc_unknown")
        name = tc.get("name", "")
        prompt = (tc.get("prompt") or "")[:300]  # truncate to avoid huge prompt
        exp = (tc.get("expected_behavior") or "")[:200]
        test_lines.append(f"**{tc_id}** ({name})\nPrompt: {prompt}\nExpected: {exp}")
    test_cases_str = "\n\n".join(test_lines)

    return f"""Skill name: {skill_name}

## Full Skill Context

{skill_content}

---

## All Test Cases ({len(test_cases)} cases)

{test_cases_str}

---

Based on the full skill context and all {len(test_cases)} test cases, produce \
the evaluation rubric JSON now."""


def _parse_and_validate(raw: str) -> dict[str, Any]:
    """Parse JSON, strip optional ```json fence, normalize weights."""
    text = raw.strip()
    if text.startswith("```"):
        # strip fence
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    data = json.loads(text)
    if not isinstance(data, dict) or "criteria" not in data:
        raise ValueError("missing 'criteria' key")
    criteria = data["criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("'criteria' must be a non-empty list")

    for c in criteria:
        if not isinstance(c, dict):
            raise ValueError("each criterion must be an object")
        for k in ("name", "description", "weight", "pass_threshold"):
            if k not in c:
                raise ValueError(f"criterion missing '{k}'")

    # Normalize weights → sum to 1.0 (LLM may be slightly off)
    total = sum(float(c["weight"]) for c in criteria)
    if total <= 0:
        raise ValueError("criterion weights sum to <= 0")
    if abs(total - 1.0) > 1e-3:
        for c in criteria:
            c["weight"] = float(c["weight"]) / total

    return data
