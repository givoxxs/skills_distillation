"""Tests for stages/student.py — retry logic and skip behavior."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.config import RunConfigV2
from stages.student import (
    _build_prompt,
    _install_skill_in_sandbox,
    make_skip_result,
    run_student,
)
from runner.sandbox import Sandbox


def _make_config(tmp_path: Path) -> RunConfigV2:
    return RunConfigV2(
        openrouter_api_key="sk-fake",
        claude_binary="claude",
        skills_dir=str(tmp_path),
        log_dir=str(tmp_path / "logs"),
        output_dir=str(tmp_path / "output"),
        sandbox_tmp_root=str(tmp_path / "sandbox"),
        sandbox_keep_on_fail=False,
    )


def test_build_prompt_uses_slash_command():
    prompt = _build_prompt("docx", "Write a report.")
    assert prompt == "Use skill docx to: Write a report."


def test_build_prompt_different_skills():
    assert _build_prompt("xlsx", "do task") == "Use skill xlsx to: do task"


def test_install_skill_copies_entire_folder_to_skills_dir(tmp_path, monkeypatch):
    """Toàn bộ skill folder phải được copy vào .claude/skills/<name>/."""
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    skill_dir = tmp_path / "skills" / "docx"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# SKILL\nDo task.", encoding="utf-8")
    (skill_dir / "LICENSE.txt").write_text("MIT", encoding="utf-8")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "helper.py").write_text("# helper", encoding="utf-8")

    with Sandbox("test", api_key="sk-fake", parent_tmp=tmp_path / "sb") as sandbox:
        _install_skill_in_sandbox(sandbox, "docx", skill_dir)
        skills_dst = sandbox.home / ".claude" / "skills" / "docx"
        assert (skills_dst / "SKILL.md").is_file()
        assert "# SKILL" in (skills_dst / "SKILL.md").read_text()
        assert (skills_dst / "LICENSE.txt").is_file()
        assert (skills_dst / "scripts" / "helper.py").is_file()
        # CLAUDE.md phải được ghi ra cwd để mọi model đều nhận skill instructions
        assert (sandbox.cwd / "CLAUDE.md").exists()
        assert "# SKILL" in (sandbox.cwd / "CLAUDE.md").read_text()


def test_install_skill_working_copy_overrides_skill_md(tmp_path, monkeypatch):
    """current_skill_md phải ghi đè SKILL.md bên trong sandbox, không sửa bản gốc."""
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    skill_dir = tmp_path / "skills" / "docx"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("original", encoding="utf-8")

    working_copy = tmp_path / "SKILL_current.md"
    working_copy.write_text("teacher rewrite", encoding="utf-8")

    with Sandbox("test", api_key="sk-fake", parent_tmp=tmp_path / "sb") as sandbox:
        _install_skill_in_sandbox(
            sandbox, "docx", skill_dir, current_skill_md=working_copy
        )
        skills_dst = sandbox.home / ".claude" / "skills" / "docx"
        assert (skills_dst / "SKILL.md").read_text() == "teacher rewrite"
        # CLAUDE.md cũng phải dùng working copy
        assert (sandbox.cwd / "CLAUDE.md").read_text() == "teacher rewrite"
    # bản gốc không bị sửa
    assert (skill_dir / "SKILL.md").read_text() == "original"


def test_make_skip_result_has_zero_score():
    tc = {"id": "tc_a01", "name": "test"}
    er = make_skip_result(tc, "docx", "gemma", round_n=1, output_dir="/tmp/out")
    assert er.llm_judge_score == 0.0
    assert er.test_case_id == "tc_a01"
    assert any(not c.passed for c in er.checks)


def test_run_student_skips_after_max_retries(tmp_path):
    config = _make_config(tmp_path)

    # Make _run_once always return a retriable failure
    retriable = {
        "stop_reason": "runner_error: SandboxError",
        "iterations": 0,
        "output_files": [],
        "log_file": str(tmp_path / "log.jsonl"),
        "duration_seconds": 0.1,
        "token_usage": {"prompt": 0, "completion": 0},
        "_attempt": 3,
    }

    with patch("stages.student._run_once", return_value=retriable):
        result = run_student(
            user_prompt="task",
            skill_name="docx",
            skill_dir=tmp_path / "skills" / "docx",
            model="gemma",
            config=config,
            max_retries=3,
        )

    assert result.get("skipped") is True


def test_run_student_succeeds_on_first_attempt(tmp_path):
    config = _make_config(tmp_path)

    success = {
        "stop_reason": "end_turn",
        "iterations": 5,
        "output_files": [str(tmp_path / "output.docx")],
        "log_file": str(tmp_path / "log.jsonl"),
        "duration_seconds": 2.5,
        "token_usage": {"prompt": 100, "completion": 50},
        "_attempt": 1,
    }

    with patch("stages.student._run_once", return_value=success):
        result = run_student(
            user_prompt="task",
            skill_name="docx",
            skill_dir=tmp_path / "skills" / "docx",
            model="gemma",
            config=config,
            max_retries=3,
        )

    assert result.get("skipped") is False
    assert result["stop_reason"] == "end_turn"
