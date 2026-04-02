"""Teacher: calls Anthropic API to rewrite SKILL.md given key_notes from Summarizer."""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DEFAULT_MODEL = "claude-haiku-4-5"
MAX_TOKENS    = 8192

SYSTEM_PROMPT = """You are an expert technical writer specializing in optimizing \
AI agent skill definitions.

Your task: rewrite a SKILL.md file to improve how well a small language model \
(Qwen3-8B) can execute the skill. The model has limited reasoning ability and \
struggles with complex multi-step instructions.

Rules for rewriting:
1. PRESERVE passing cases: if a test case passed in the error analysis (rule_score ≥ 0.6),
   do NOT remove or weaken the instructions that made it pass. Only add or strengthen.
2. Do not delete any code snippet, CRITICAL block, or warning that already exists —
   they may be preventing failures in other test cases not shown in this batch.
3. Add fallback strategies where the model gets stuck (e.g., "if JS fails, use Python").
4. Add a complete, minimal working code template for the most common task pattern.
5. Make instructions explicit and sequential — small models cannot infer intent.
6. Add a "Common Mistakes" section listing the failure patterns from the error analysis.
7. Keep it concise — small models lose track with very long prompts.
8. Output ONLY the new SKILL.md content (no explanation, no markdown wrapper).
"""


def rewrite(
    skill_md_path: str,
    key_notes: str,
    model: str = DEFAULT_MODEL,
    dry_run: bool = False,
) -> str:
    """Call Anthropic API to rewrite SKILL.md.

    Args:
        skill_md_path: Path to the current SKILL.md file.
        key_notes:     Output from summarizer.summarize() — error analysis text.
        model:         Claude model ID (default: claude-haiku-4-5).
        dry_run:       If True, print the prompt and return unchanged content.

    Returns:
        The new SKILL.md content as a string.

    Raises:
        RuntimeError: If the API call fails.
    """
    current_md = Path(skill_md_path).read_text()
    user_prompt = _build_prompt(current_md, key_notes)

    if dry_run:
        print("=== DRY RUN: Teacher Prompt (first 2000 chars) ===")
        print(user_prompt[:2000])
        print("...")
        return current_md

    return _call_api(user_prompt, model)


def _build_prompt(current_md: str, key_notes: str) -> str:
    return f"""Below is the current SKILL.md and an error analysis from running \
a small language model (Qwen3-8B) on test cases using this skill.

Rewrite the SKILL.md to fix the identified problems. Follow the rules in your \
system prompt exactly.

---
# Current SKILL.md

{current_md}

---
# Error Analysis (key_notes from Evaluator)

{key_notes}

---
Now write the improved SKILL.md:"""


def _call_api(user_prompt: str, model: str) -> str:
    api_key = os.getenv("ANTHROPIC_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    output = message.content[0].text.strip()
    if not output:
        raise RuntimeError("Anthropic API returned empty response")

    return output
