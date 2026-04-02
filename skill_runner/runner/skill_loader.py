"""Load and prepare skill folders for the agent."""

import shutil
from pathlib import Path
from typing import Tuple, Dict, Any

import yaml


def load_skill(
    skill_name: str,
    skills_dir: str = "./skills",
    workspace_dir: str = "./workspace",
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Load a skill FOLDER and prepare the workspace.

    Does NOT just read SKILL.md — copies the ENTIRE skill folder into the workspace
    so the model can read_file reference docs and bash-run scripts.

    Args:
        skill_name: Name of the skill folder (e.g. "pdf", "pptx").
        skills_dir: Root directory containing skill folders.
        workspace_dir: Working directory; skill will be copied to workspace/_skills/.

    Returns:
        Tuple of:
        - skill_md_content: Body of SKILL.md (frontmatter stripped).
        - skill_path_in_workspace: Absolute path to the copied skill folder.
        - metadata: Parsed YAML frontmatter from SKILL.md (may be empty dict).

    Raises:
        FileNotFoundError: If the skill folder or SKILL.md does not exist.
    """
    skill_source = Path(skills_dir) / skill_name
    if not skill_source.exists():
        raise FileNotFoundError(f"Skill folder not found: {skill_source}")

    skill_md = skill_source / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in: {skill_source}")

    # Copy entire skill folder into workspace/_skills/<name>/
    workspace = Path(workspace_dir)
    skill_dest = workspace / "_skills" / skill_name

    if skill_dest.exists():
        shutil.rmtree(skill_dest)
    shutil.copytree(skill_source, skill_dest)

    # Make scripts executable
    for pattern in ("*.py", "*.sh"):
        for script in skill_dest.rglob(pattern):
            script.chmod(0o755)

    # Parse SKILL.md: strip YAML frontmatter
    raw = skill_md.read_text(encoding="utf-8")
    metadata: Dict[str, Any] = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            metadata = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()

    return body, str(skill_dest.resolve()), metadata


def list_skill_files(skill_path: str) -> str:
    """
    Return a categorized listing of all files in the skill folder.

    Files are grouped into: scripts (runnable), templates, and docs.
    This helps small models immediately understand what can be run vs read,
    without needing to call list_directory first.

    LICENSE.txt is excluded to save tokens.

    Args:
        skill_path: Absolute path to the skill folder in the workspace.

    Returns:
        Multi-line string with files grouped by category, using absolute paths.
    """
    skill_dir = Path(skill_path)

    scripts: list[str] = []
    templates: list[str] = []
    docs: list[str] = []

    SCRIPT_EXTS = {".py", ".sh", ".js", ".ts"}
    TEMPLATE_EXTS = {".html", ".htm", ".css", ".j2", ".jinja", ".tpl"}
    EXCLUDE = {"LICENSE.txt", "LICENSE", ".gitkeep"}

    for f in sorted(skill_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.name in EXCLUDE:
            continue
        rel = str(f.relative_to(skill_dir))
        size = f.stat().st_size
        abs_path = f"{skill_path}/{rel}"
        entry = f"  {abs_path} ({size:,} bytes)"

        if f.suffix in SCRIPT_EXTS:
            scripts.append(entry)
        elif f.suffix in TEMPLATE_EXTS or "template" in rel.lower():
            templates.append(entry)
        else:
            docs.append(entry)

    parts: list[str] = []
    if scripts:
        parts.append("RUNNABLE SCRIPTS — use bash to execute:\n" + "\n".join(scripts))
    if templates:
        parts.append("TEMPLATES — use read_file to read, then copy & modify:\n" + "\n".join(templates))
    if docs:
        parts.append("REFERENCE DOCS — use read_file to read:\n" + "\n".join(docs))

    return "\n\n".join(parts) if parts else "  (no files found)"
