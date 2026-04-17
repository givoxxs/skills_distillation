"""Sandbox for invoking Claude Code CLI with isolated env + HOME.

Goal: protect the developer's own Claude Code session from pollution by our
OpenRouter base_url / API key overrides. We pass an *explicit* env dict to the
subprocess (NOT os.environ.copy()) and point HOME at a fresh temp directory so
the CLI doesn't read the user's real ~/.claude/.

Typical usage:

    with Sandbox("student", api_key=OR_KEY, base_url="https://openrouter.ai/api") as sb:
        proc = subprocess.Popen(
            ["claude", "-p", "--model", "qwen/qwen3-8b", ...],
            env=sb.env,
            cwd=sb.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional

_log = logging.getLogger("distillation.v2.sandbox")

_DEFAULT_PARENT = Path.home() / ".cache" / "distill_v2"
_OPENROUTER_HOSTS = ("openrouter.ai", "openrouter.com")


class SandboxError(RuntimeError):
    """Raised when the sandbox detects a dangerous parent env or fails setup."""


class Sandbox:
    """Filesystem + env isolation for Claude Code CLI invocations.

    Creates a disposable directory containing:
        {parent_tmp}/{name}-{uuid}/
            ├── home/   → HOME for the subprocess (fresh ~/.claude/)
            └── cwd/    → working directory for the subprocess

    The env dict exposed to the subprocess contains ONLY what the CLI needs:
    PATH, HOME, TERM, LANG, ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL (optional).
    """

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: Optional[str] = None,
        parent_tmp: Optional[Path] = None,
        keep_on_fail: bool = True,
        claude_binary: str = "claude",
    ) -> None:
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Sandbox name must be alphanumeric (got: {name!r})")
        if not api_key:
            raise ValueError("Sandbox: api_key must be non-empty")

        self._name = name
        self._api_key = api_key
        self._base_url = base_url
        self._keep_on_fail = keep_on_fail
        self._claude_binary = claude_binary

        root = parent_tmp if parent_tmp is not None else _DEFAULT_PARENT
        self._root = Path(os.path.expanduser(str(root))).resolve()

        self._dir: Optional[Path] = None
        self._home: Optional[Path] = None
        self._cwd: Optional[Path] = None
        self._env: Optional[dict[str, str]] = None

    # ── Context manager protocol ─────────────────────────────────────────────
    def __enter__(self) -> "Sandbox":
        self._preflight_check()
        self._root.mkdir(parents=True, exist_ok=True)

        self._dir = self._root / f"{self._name}-{uuid.uuid4().hex[:8]}"
        self._home = self._dir / "home"
        self._cwd = self._dir / "cwd"
        self._home.mkdir(parents=True, exist_ok=True)
        self._cwd.mkdir(parents=True, exist_ok=True)

        self._env = self._build_env()
        self._claude_logout_best_effort()
        _log.debug("Sandbox %s created at %s", self._name, self._dir)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._dir is None:
            return
        if exc_type is not None and self._keep_on_fail:
            _log.warning(
                "Sandbox %s kept for debugging (exception raised): %s",
                self._name,
                self._dir,
            )
            return
        try:
            shutil.rmtree(self._dir, ignore_errors=True)
            _log.debug("Sandbox %s cleaned up", self._name)
        except Exception as e:  # noqa: BLE001
            _log.warning("Sandbox cleanup failed: %s", e)

    # ── Properties ───────────────────────────────────────────────────────────
    @property
    def env(self) -> dict[str, str]:
        if self._env is None:
            raise SandboxError("Sandbox not entered")
        return self._env

    @property
    def cwd(self) -> Path:
        if self._cwd is None:
            raise SandboxError("Sandbox not entered")
        return self._cwd

    @property
    def home(self) -> Path:
        if self._home is None:
            raise SandboxError("Sandbox not entered")
        return self._home

    @property
    def root(self) -> Path:
        if self._dir is None:
            raise SandboxError("Sandbox not entered")
        return self._dir

    # ── Helpers ──────────────────────────────────────────────────────────────
    def copy_input(self, src: Path | str) -> Path:
        """Copy an input file (e.g. a docx fixture) into the sandbox cwd."""
        src_path = Path(src)
        if not src_path.is_file():
            raise FileNotFoundError(src_path)
        dst = self.cwd / src_path.name
        shutil.copy2(src_path, dst)
        return dst

    def list_outputs(self, since_ts: float) -> list[Path]:
        """Return files created/modified in cwd after `since_ts`.

        Skips hidden dirs (.claude, .git) and anything in `home/`.
        """
        out: list[Path] = []
        if self._cwd is None:
            return out
        for path in self._cwd.rglob("*"):
            if not path.is_file():
                continue
            parts = path.relative_to(self._cwd).parts
            if any(p.startswith(".") for p in parts):
                continue
            try:
                if path.stat().st_mtime >= since_ts:
                    out.append(path)
            except OSError:
                continue
        return out

    # ── Internal ─────────────────────────────────────────────────────────────
    def _preflight_check(self) -> None:
        """Refuse to start if the parent shell is already pointing at OpenRouter.

        This catches nested invocations where the dev has manually exported
        ANTHROPIC_BASE_URL and would leak it further.
        """
        parent_base = os.environ.get("ANTHROPIC_BASE_URL", "")
        if any(h in parent_base.lower() for h in _OPENROUTER_HOSTS):
            raise SandboxError(
                "Parent shell already has ANTHROPIC_BASE_URL pointing at OpenRouter "
                f"({parent_base!r}). Unset it before running distillation_v2 to avoid "
                "cross-contaminating your Claude Code session."
            )

    def _build_env(self) -> dict[str, str]:
        """Build the minimal env dict for the subprocess.

        Explicitly NOT a copy of os.environ — we want a clean slate with only
        what Claude Code and the shell wrapper need.
        """
        env: dict[str, str] = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
            "HOME": str(self._home),
            "TERM": "dumb",
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "ANTHROPIC_API_KEY": self._api_key,
        }
        if self._base_url:
            env["ANTHROPIC_BASE_URL"] = self._base_url
        # Preserve NODE_PATH / npm paths if present (Claude Code shells out to node)
        for key in ("NODE_PATH", "NVM_DIR", "NVM_BIN", "SHELL"):
            if key in os.environ:
                env[key] = os.environ[key]
        return env

    def _claude_logout_best_effort(self) -> None:
        """Try to clear any cached auth in sandbox HOME. Non-fatal on failure."""
        try:
            subprocess.run(
                [self._claude_binary, "logout"],
                env=self._env,
                cwd=str(self._cwd),
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            _log.debug("claude logout skipped: %s", e)
        except Exception as e:  # noqa: BLE001
            _log.debug("claude logout non-fatal error: %s", e)
