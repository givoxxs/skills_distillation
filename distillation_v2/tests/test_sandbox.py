"""Offline tests for Sandbox + anthropic_env context managers.

Verifies:
  - Parent env vars (ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY) are not leaked back.
  - Sandbox HOME points inside the tmp dir.
  - Sandbox env dict is explicit (not os.environ.copy()).
  - Cleanup happens on normal exit; dir is kept on exception when keep_on_fail.
  - Pre-flight guard raises when parent env has openrouter base URL.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.anthropic_env import anthropic_env  # noqa: E402
from runner.sandbox import Sandbox, SandboxError  # noqa: E402


# ── anthropic_env ──────────────────────────────────────────────────────────────


def test_anthropic_env_swaps_then_restores(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "parent-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://parent.example.com")

    with anthropic_env("child-key"):
        assert os.environ["ANTHROPIC_API_KEY"] == "child-key"
        assert "ANTHROPIC_BASE_URL" not in os.environ

    assert os.environ["ANTHROPIC_API_KEY"] == "parent-key"
    assert os.environ["ANTHROPIC_BASE_URL"] == "https://parent.example.com"


def test_anthropic_env_restores_unset_parent(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

    with anthropic_env("tmp-key", base_url="https://override.example.com"):
        assert os.environ["ANTHROPIC_API_KEY"] == "tmp-key"
        assert os.environ["ANTHROPIC_BASE_URL"] == "https://override.example.com"

    assert "ANTHROPIC_API_KEY" not in os.environ
    assert "ANTHROPIC_BASE_URL" not in os.environ


def test_anthropic_env_restores_on_exception(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "parent")
    with pytest.raises(RuntimeError, match="boom"):
        with anthropic_env("child"):
            raise RuntimeError("boom")
    assert os.environ["ANTHROPIC_API_KEY"] == "parent"


def test_anthropic_env_rejects_empty_key():
    with pytest.raises(ValueError):
        with anthropic_env(""):
            pass


# ── Sandbox ────────────────────────────────────────────────────────────────────


@pytest.fixture
def clean_env(monkeypatch):
    """Ensure no openrouter pollution in the parent env for the test."""
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return monkeypatch


def test_sandbox_env_does_not_leak_to_parent(tmp_path, clean_env):
    with Sandbox(
        "test",
        api_key="sk-fake",
        base_url="https://openrouter.ai/api",
        parent_tmp=tmp_path,
    ) as sb:
        assert sb.env["ANTHROPIC_API_KEY"] == "sk-fake"
        assert sb.env["ANTHROPIC_BASE_URL"] == "https://openrouter.ai/api"

    # Parent env must be unchanged
    assert "ANTHROPIC_BASE_URL" not in os.environ
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_sandbox_home_points_into_tmp(tmp_path, clean_env):
    with Sandbox("student", api_key="sk-fake", parent_tmp=tmp_path) as sb:
        home = Path(sb.env["HOME"])
        assert home.is_dir()
        assert str(tmp_path.resolve()) in str(home.resolve())
        assert sb.cwd.is_dir()
        assert sb.home == home


def test_sandbox_env_is_minimal(tmp_path, clean_env, monkeypatch):
    """env dict must NOT be a full copy of os.environ."""
    monkeypatch.setenv("SOME_SECRET_FROM_PARENT", "leaked")
    with Sandbox("test", api_key="sk-fake", parent_tmp=tmp_path) as sb:
        assert "SOME_SECRET_FROM_PARENT" not in sb.env


def test_sandbox_cleans_up_on_success(tmp_path, clean_env):
    with Sandbox("test", api_key="sk-fake", parent_tmp=tmp_path) as sb:
        sandbox_root = sb.root
        assert sandbox_root.exists()
    assert not sandbox_root.exists()


def test_sandbox_keeps_on_fail_when_exception(tmp_path, clean_env):
    sandbox_root = None
    with pytest.raises(RuntimeError, match="boom"):
        with Sandbox(
            "test",
            api_key="sk-fake",
            parent_tmp=tmp_path,
            keep_on_fail=True,
        ) as sb:
            sandbox_root = sb.root
            raise RuntimeError("boom")
    assert sandbox_root is not None and sandbox_root.exists()


def test_sandbox_cleans_on_fail_when_keep_disabled(tmp_path, clean_env):
    sandbox_root = None
    with pytest.raises(RuntimeError, match="boom"):
        with Sandbox(
            "test",
            api_key="sk-fake",
            parent_tmp=tmp_path,
            keep_on_fail=False,
        ) as sb:
            sandbox_root = sb.root
            raise RuntimeError("boom")
    assert sandbox_root is not None and not sandbox_root.exists()


def test_sandbox_preflight_rejects_openrouter_parent(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://openrouter.ai/api/v1")
    with pytest.raises(SandboxError, match="OpenRouter"):
        with Sandbox("test", api_key="sk-fake", parent_tmp=tmp_path):
            pass


def test_sandbox_rejects_bad_name(tmp_path, clean_env):
    with pytest.raises(ValueError):
        with Sandbox("bad name!", api_key="sk-fake", parent_tmp=tmp_path):
            pass


def test_sandbox_rejects_empty_key(tmp_path, clean_env):
    with pytest.raises(ValueError):
        with Sandbox("test", api_key="", parent_tmp=tmp_path):
            pass


def test_sandbox_list_outputs_only_new_files(tmp_path, clean_env):
    import time

    with Sandbox("test", api_key="sk-fake", parent_tmp=tmp_path) as sb:
        old_file = sb.cwd / "old.txt"
        old_file.write_text("old")
        # Backdate the old file
        past = time.time() - 3600
        os.utime(old_file, (past, past))

        start_ts = time.time()
        time.sleep(0.05)  # ensure new file mtime strictly exceeds start_ts

        new_file = sb.cwd / "new.docx"
        new_file.write_text("new")

        outputs = sb.list_outputs(start_ts)
        names = {p.name for p in outputs}
        assert "new.docx" in names
        assert "old.txt" not in names


def test_sandbox_list_outputs_skips_hidden(tmp_path, clean_env):
    import time

    with Sandbox("test", api_key="sk-fake", parent_tmp=tmp_path) as sb:
        start_ts = time.time() - 1
        hidden_dir = sb.cwd / ".claude"
        hidden_dir.mkdir()
        (hidden_dir / "config.json").write_text("{}")
        (sb.cwd / "visible.md").write_text("hi")

        outputs = sb.list_outputs(start_ts)
        names = {p.name for p in outputs}
        assert "visible.md" in names
        assert "config.json" not in names


def test_sandbox_copy_input(tmp_path, clean_env):
    src = tmp_path / "fixture.docx"
    src.write_bytes(b"fake docx")
    with Sandbox("test", api_key="sk-fake", parent_tmp=tmp_path) as sb:
        dst = sb.copy_input(src)
        assert dst.exists()
        assert dst.parent == sb.cwd
        assert dst.read_bytes() == b"fake docx"
