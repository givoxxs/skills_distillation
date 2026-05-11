"""Generate a shared evaluation rubric once per skill, cache and reuse.

Teacher LLM reads SKILL.md + all test cases → produces 4-8 criteria (rubrics.json).
Cache key = sha256(skill_dir_content) + sha256(sorted TC IDs).
Regeneration triggers: explicit flag OR SKILL.md hash change (if watch_skill_hash=True).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any


from utils import write_api_call
from utils.llm_call import call_llm

_log = logging.getLogger("distillation.v2.rubric_gen")

DEFAULT_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 4096

_TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".sh",
    ".toml",
    ".cfg",
    ".ini",
}
_MAX_FILE_BYTES = 3000
_SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".npm"}

_SYSTEM_PROMPT = """You design evaluation rubrics for AI agent skills executed \
by small language models via Claude Code CLI.

Given the full skill context (SKILL.md, helper scripts) and test cases for a \
specific workflow, produce as many independent, objectively checkable criteria \
as needed to fully cover that workflow's requirements. Use your judgment — \
a simple workflow may need 3–5 criteria, a complex one may need 10+.

Rules:
1. Each criterion must be independently checkable by a judge LLM viewing the output or its screenshots.
2. Cover every distinct failure mode visible across the provided test cases.
3. Weights must sum to exactly 1.0. Distribute weights proportionally to importance.
4. pass_threshold is the per-criterion minimum (0.0-1.0) for "acceptable".
5. MUST include at least one FILE VALIDITY criterion (file exists, non-empty, correct format).
6. MUST include at least one TASK COMPLETION criterion (did it actually do what was asked?).
7. Write criterion descriptions in imperative form so a judge knows exactly what to check.
8. Do NOT merge distinct requirements into one criterion — split them.
9. Do NOT include criteria for other workflow types — focus only on the given workflow.
10. CRITICAL: Every criterion MUST apply to ALL test cases in this workflow batch. Never create a criterion that only applies to one specific test case — if a requirement is TC-specific, express it as a general principle (e.g., "Output file exists in the format requested by the task" covers txt/json/docx/md outputs across all TCs).

Output ONLY valid JSON, no prose, no markdown fence:
{
  "criteria": [
    {"name": "...", "description": "...", "weight": 0.0, "pass_threshold": 0.0},
    ...
  ],
  "notes": "one-sentence rationale explaining coverage decisions"
}"""


# ── Cache helpers ─────────────────────────────────────────────────────────────


def _read_skill_context(skill_dir: Path) -> str:
    parts: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        parts.append(f"# SKILL.md\n\n{skill_md.read_text(encoding='utf-8')}")
    for fpath in sorted(skill_dir.rglob("*")):
        if fpath == skill_md:
            continue
        if any(p in _SKIP_DIRS for p in fpath.parts):
            continue
        if not fpath.is_file() or fpath.suffix.lower() not in _TEXT_EXTENSIONS:
            continue
        rel = fpath.relative_to(skill_dir)
        try:
            raw = fpath.read_text(encoding="utf-8", errors="replace")
            if len(raw) > _MAX_FILE_BYTES:
                raw = raw[:_MAX_FILE_BYTES] + f"\n... [truncated, {len(raw)} chars]"
            parts.append(f"# {rel}\n\n{raw}")
        except Exception:  # noqa: BLE001
            pass
    return "\n---\n".join(parts)


def _cache_key(
    skill_content: str, tc_ids: list[str], workflow: str | None = None
) -> str:
    h1 = hashlib.sha256(skill_content.encode()).hexdigest()[:12]
    h2 = hashlib.sha256(",".join(sorted(tc_ids)).encode()).hexdigest()[:12]
    base = f"{h1}_{h2}"
    return f"{workflow}_{base}" if workflow else base


def _skill_md_hash(skill_dir: Path) -> str:
    p = skill_dir / "SKILL.md"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.is_file() else ""


def _cleanup_old_rubrics(
    cache_dir: Path, skill_name: str, workflow: str | None, keep: int
) -> None:
    """Delete old rubric files for this skill+workflow, keeping the N most recent."""
    if keep <= 0:
        return
    prefix = f"{skill_name}_{workflow}_" if workflow else f"{skill_name}_"
    files = sorted(
        cache_dir.glob(f"{prefix}*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in files[keep:]:
        try:
            old.unlink()
            _log.debug("deleted old rubric: %s", old.name)
        except Exception as exc:  # noqa: BLE001
            _log.warning("failed to delete old rubric %s: %s", old.name, exc)


# ── Public API ─────────────────────────────────────────────────────────────────


def generate_rubric(
    skill_name: str,
    skill_dir: str | Path,
    test_cases: list[dict[str, Any]],
    cache_dir: str | Path,
    model: str = DEFAULT_MODEL,
    workflow: str | None = None,
    regenerate: bool = False,
    watch_skill_hash: bool = False,
    keep_recent: int = 5,
    anthropic_api_key: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Return rubric dict for the given workflow, generating + caching if needed.

    Args:
        workflow: Workflow type (create/read/edit/convert/edge). When provided,
                  generates a focused rubric for that workflow only.
        watch_skill_hash: If True, regenerate when SKILL.md content has changed
                          since the cached rubric was produced (stored in cache).
        keep_recent: Keep only the N most recent rubric files for this skill+workflow;
                     older files are deleted after a new rubric is saved.
    """
    skill_dir = Path(skill_dir)
    skill_content = _read_skill_context(skill_dir)
    tc_ids = [tc.get("id", "") for tc in test_cases]
    key = _cache_key(skill_content, tc_ids, workflow)

    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    fname = (
        f"{skill_name}_{workflow}_{key}.json"
        if workflow
        else f"{skill_name}_{key}.json"
    )
    cache_file = cache_root / fname

    # Determine if we must regenerate
    must_regen = regenerate
    if not must_regen and cache_file.is_file() and watch_skill_hash:
        try:
            cached = json.loads(cache_file.read_text())
            current_hash = _skill_md_hash(skill_dir)
            if cached.get("skill_md_hash") != current_hash:
                _log.info("SKILL.md changed — regenerating rubric")
                must_regen = True
        except Exception:  # noqa: BLE001
            must_regen = True

    if cache_file.is_file() and not must_regen:
        _log.info("rubric cache hit: %s", cache_file.name)
        try:
            return json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            _log.warning("corrupt rubric cache, regenerating")

    label = f"{skill_name}/{workflow}" if workflow else skill_name
    _log.info(
        "generating rubric via %s (%s, %d test cases)...", model, label, len(test_cases)
    )
    if not anthropic_api_key:
        raise RuntimeError("rubric_gen requires an OpenRouter API key")
    api_key = anthropic_api_key

    rubric = _call_api(
        skill_name, skill_content, test_cases, model, api_key, base_url, workflow
    )
    rubric["cache_key"] = key
    rubric["workflow"] = workflow
    rubric["skill_md_hash"] = _skill_md_hash(skill_dir)
    cache_file.write_text(json.dumps(rubric, indent=2, ensure_ascii=False))
    _log.info("rubric saved [%s]: %d criteria", label, len(rubric.get("criteria", [])))
    _cleanup_old_rubrics(cache_root, skill_name, workflow, keep=keep_recent)
    return rubric


# ── API call ──────────────────────────────────────────────────────────────────


def _call_api(
    skill_name: str,
    skill_content: str,
    test_cases: list[dict[str, Any]],
    model: str,
    api_key: str,
    base_url: str | None = None,
    workflow: str | None = None,
) -> dict[str, Any]:
    tc_lines = []
    for tc in test_cases:
        tc_id = tc.get("id", "tc_unknown")
        prompt = (tc.get("prompt") or "")[:300]
        expected = (tc.get("expected_behavior") or "")[:200]
        tc_lines.append(f"**{tc_id}**\nPrompt: {prompt}\nExpected: {expected}")

    workflow_line = (
        f"Workflow: {workflow.upper()} (generate criteria for this workflow ONLY)\n\n"
        if workflow
        else ""
    )
    user_prompt = (
        f"Skill: {skill_name}\n\n{workflow_line}"
        f"## Skill Context\n\n{skill_content}\n\n"
        f"---\n\n## Test Cases ({len(test_cases)})\n\n"
        + "\n\n".join(tc_lines)
        + f"\n\n---\n\nProduce the rubric JSON for {skill_name}"
        + (f" [{workflow.upper()} workflow]" if workflow else "")
        + " now."
    )

    raw, usage = call_llm(
        system=_SYSTEM_PROMPT,
        user=user_prompt,
        model=model,
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        base_url=base_url,
    )
    write_api_call(
        {
            "type": "rubric_gen",
            "model": model,
            "skill": skill_name,
            "workflow": workflow,
            "n_test_cases": len(test_cases),
            **usage,
        }
    )

    rubric = _parse_and_validate(raw)
    rubric["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    rubric["model"] = model
    rubric["token_usage"] = usage
    return rubric


def _parse_and_validate(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            lines[1:-1] if lines[-1].startswith("```") else lines[1:]
        ).strip()

    data = json.loads(text)
    if not isinstance(data, dict) or "criteria" not in data:
        raise ValueError("missing 'criteria' key")
    criteria = data["criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("'criteria' must be a non-empty list")
    for c in criteria:
        for k in ("name", "description", "weight", "pass_threshold"):
            if k not in c:
                raise ValueError(f"criterion missing '{k}'")

    total = sum(float(c["weight"]) for c in criteria)
    if total <= 0:
        raise ValueError("weights sum to <= 0")
    if abs(total - 1.0) > 1e-3:
        for c in criteria:
            c["weight"] = float(c["weight"]) / total
    return data
