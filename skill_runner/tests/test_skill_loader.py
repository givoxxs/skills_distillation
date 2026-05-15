"""Unit tests for skill_loader."""

import os
import tempfile
import pytest
from pathlib import Path
from runner.skill_loader import load_skill, list_skill_files


@pytest.fixture
def skill_dirs():
    with tempfile.TemporaryDirectory() as skills_dir:
        with tempfile.TemporaryDirectory() as workspace_dir:
            yield skills_dir, workspace_dir


def _make_skill(
    skills_dir: str, name: str, skill_md_content: str, extra_files: dict | None = None
):
    skill_path = Path(skills_dir) / name
    skill_path.mkdir()
    (skill_path / "SKILL.md").write_text(skill_md_content, encoding="utf-8")
    if extra_files:
        for rel_path, content in extra_files.items():
            fp = skill_path / rel_path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
    return str(skill_path)


def test_load_simple_skill(skill_dirs):
    skills_dir, workspace_dir = skill_dirs
    _make_skill(skills_dir, "test-skill", "# Hello\nThis is the skill.")

    body, path, metadata = load_skill("test-skill", skills_dir, workspace_dir)

    assert "This is the skill." in body
    assert os.path.isdir(path)
    assert metadata == {}


def test_load_skill_with_frontmatter(skill_dirs):
    skills_dir, workspace_dir = skill_dirs
    content = "---\nname: Test\nversion: 1.0\n---\n# Body content"
    _make_skill(skills_dir, "test-skill", content)

    body, path, metadata = load_skill("test-skill", skills_dir, workspace_dir)

    assert "Body content" in body
    assert metadata["name"] == "Test"
    assert metadata["version"] == 1.0


def test_skill_files_copied_to_workspace(skill_dirs):
    skills_dir, workspace_dir = skill_dirs
    _make_skill(
        skills_dir,
        "pdf",
        "# PDF Skill",
        extra_files={
            "FORMS.md": "Forms content",
            "scripts/check.py": "#!/usr/bin/env python\nprint('ok')",
        },
    )

    body, path, metadata = load_skill("pdf", skills_dir, workspace_dir)

    assert os.path.isfile(os.path.join(path, "SKILL.md"))
    assert os.path.isfile(os.path.join(path, "FORMS.md"))
    assert os.path.isfile(os.path.join(path, "scripts", "check.py"))


def test_skill_not_found(skill_dirs):
    skills_dir, workspace_dir = skill_dirs
    with pytest.raises(FileNotFoundError):
        load_skill("nonexistent", skills_dir, workspace_dir)


def test_skill_missing_skill_md(skill_dirs):
    skills_dir, workspace_dir = skill_dirs
    (Path(skills_dir) / "empty-skill").mkdir()

    with pytest.raises(FileNotFoundError):
        load_skill("empty-skill", skills_dir, workspace_dir)


def test_list_skill_files(skill_dirs):
    skills_dir, workspace_dir = skill_dirs
    _make_skill(
        skills_dir,
        "pptx",
        "# PPTX",
        extra_files={
            "editing.md": "Edit instructions",
            "scripts/thumbnail.py": "print('thumb')",
            "LICENSE.txt": "MIT",  # should be excluded
        },
    )

    _, path, _ = load_skill("pptx", skills_dir, workspace_dir)
    listing = list_skill_files(path)

    assert "editing.md" in listing
    assert "thumbnail.py" in listing
    assert "SKILL.md" not in listing  # excluded — already in <skill> block
    assert "LICENSE.txt" not in listing  # excluded


def test_list_skill_files_library_modules(skill_dirs):
    """Files inside core/, helpers/, validators/ are LIBRARY MODULES, not RUNNABLE."""
    skills_dir, workspace_dir = skill_dirs
    _make_skill(
        skills_dir,
        "gif",
        "# GIF",
        extra_files={
            "core/builder.py": "# builder",
            "helpers/utils.py": "# utils",
            "scripts/run.py": "# entry",
        },
    )

    _, path, _ = load_skill("gif", skills_dir, workspace_dir)
    listing = list_skill_files(path)

    assert "LIBRARY MODULES" in listing
    assert "core/builder.py" in listing
    assert "helpers/utils.py" in listing
    assert "RUNNABLE SCRIPTS" in listing
    assert "scripts/run.py" in listing
    # Library modules must NOT appear in RUNNABLE SCRIPTS section
    runnable_section = listing.split("LIBRARY MODULES")[0]
    assert "core/builder.py" not in runnable_section


def test_list_skill_files_init_excluded(skill_dirs):
    """__init__.py files are never listed as runnable scripts."""
    skills_dir, workspace_dir = skill_dirs
    _make_skill(
        skills_dir,
        "myskill",
        "# skill",
        extra_files={
            "scripts/__init__.py": "",
            "scripts/run.py": "print('ok')",
        },
    )

    _, path, _ = load_skill("myskill", skills_dir, workspace_dir)
    listing = list_skill_files(path)

    assert "__init__.py" not in listing
    assert "run.py" in listing


def test_list_skill_files_binary_assets(skill_dirs):
    """Binary files are listed under BINARY/ASSET FILES, not REFERENCE DOCS."""
    skills_dir, workspace_dir = skill_dirs
    _make_skill(
        skills_dir,
        "design",
        "# design",
        extra_files={
            "showcase.pdf": b"fake pdf".decode(),
            "readme.md": "# readme",
        },
    )

    _, path, _ = load_skill("design", skills_dir, workspace_dir)
    listing = list_skill_files(path)

    assert "BINARY/ASSET FILES" in listing
    assert "showcase.pdf" in listing
    assert "readme.md" in listing
    # PDF must NOT appear before the BINARY/ASSET FILES section
    before_binary = listing.split("BINARY/ASSET FILES")[0]
    assert "showcase.pdf" not in before_binary


def test_list_skill_files_collapsed_schemas(skill_dirs):
    """Files inside schemas/ are collapsed into a single summary line."""
    skills_dir, workspace_dir = skill_dirs
    _make_skill(
        skills_dir,
        "docx",
        "# DOCX",
        extra_files={
            "scripts/validate.py": "# validate",
            "scripts/schemas/wml.xsd": "<schema/>",
            "scripts/schemas/pml.xsd": "<schema/>",
            "scripts/schemas/sml.xsd": "<schema/>",
        },
    )

    _, path, _ = load_skill("docx", skills_dir, workspace_dir)
    listing = list_skill_files(path)

    assert "COLLAPSED" in listing
    assert "schemas" in listing
    # Individual schema files must not be individually listed
    assert "wml.xsd" not in listing.replace("COLLAPSED", "").split("path:")[0]
    assert "validate.py" in listing


def test_scripts_are_executable(skill_dirs):
    skills_dir, workspace_dir = skill_dirs
    _make_skill(
        skills_dir, "pdf", "# PDF", extra_files={"scripts/gen.py": "print('hi')"}
    )

    _, path, _ = load_skill("pdf", skills_dir, workspace_dir)
    script = Path(path) / "scripts" / "gen.py"
    assert os.access(str(script), os.X_OK)
