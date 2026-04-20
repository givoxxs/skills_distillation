"""RunConfigV2 — runtime parameters for one Claude Code CLI invocation.

Mirrors v1's RunConfig shape where sensible, but drops skill_runner specifics
(workspace_dir, bash_timeout, temperature, max_tokens) since Claude Code manages
those internally.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (two levels up from distillation_v2/runner/)
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

_DEFAULT_SKILLS_DIR = str(Path(__file__).resolve().parent.parent / "skills")


@dataclass
class RunConfigV2:
    # ── Student model via OpenRouter ────────────────────────────────────────
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    openrouter_base_url: str = "https://openrouter.ai/api"

    # ── Claude Code CLI ──────────────────────────────────────────────────────
    claude_binary: str = "claude"
    max_turns: int = 30
    timeout_seconds: int = 300  # 5 min per test case

    # ── Paths ────────────────────────────────────────────────────────────────
    skills_dir: str = _DEFAULT_SKILLS_DIR
    log_dir: str = "./logs"
    output_dir: str | None = None  # per-testcase output dir; set by orchestrator

    # ── Sandbox ──────────────────────────────────────────────────────────────
    sandbox_tmp_root: str = "~/.cache/distill_v2"
    sandbox_keep_on_fail: bool = True

    # ── Input fixtures to copy into sandbox cwd before run ───────────────────
    input_files: list[Path] = field(default_factory=list)

    # ── Debug ────────────────────────────────────────────────────────────────
    verbose: bool = False

    def validate(self) -> None:
        if not self.openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key."
            )
