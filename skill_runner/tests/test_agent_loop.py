"""Unit tests for agent_loop helpers."""

import os
import tempfile
from pathlib import Path
from runner.agent_loop import _clean_workspace


def test_clean_workspace_removes_files():
    with tempfile.TemporaryDirectory() as workspace:
        # Create some files and dirs
        (Path(workspace) / "output.pdf").write_text("data")
        (Path(workspace) / "subdir").mkdir()
        (Path(workspace) / "subdir" / "file.txt").write_text("x")
        # Create _skills (should be preserved)
        skills = Path(workspace) / "_skills" / "pdf"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_text("skill content")

        _clean_workspace(workspace)

        items = list(Path(workspace).iterdir())
        names = [i.name for i in items]

        assert "output.pdf" not in names
        assert "subdir" not in names
        assert "_skills" in names
        assert (Path(workspace) / "_skills" / "pdf" / "SKILL.md").exists()


def test_clean_workspace_creates_if_missing():
    with tempfile.TemporaryDirectory() as parent:
        workspace = os.path.join(parent, "workspace")
        assert not os.path.exists(workspace)

        _clean_workspace(workspace)

        assert os.path.isdir(workspace)
