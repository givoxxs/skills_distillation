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

    Files are grouped into five categories so small models immediately know
    what to run, import, read, or just reference by path:
      - RUNNABLE SCRIPTS: entry-point scripts to execute with bash
      - LIBRARY MODULES: helper modules to import, not run directly
      - TEMPLATES: files to read then copy/modify
      - REFERENCE DOCS: text files to read with read_file
      - BINARY/ASSET FILES: non-readable files; reference by absolute path only

    Large internal directories (schemas/, canvas-fonts/) are collapsed into a
    single summary line to avoid flooding the inventory with irrelevant files.

    LICENSE.txt and SKILL.md are excluded to save tokens (SKILL.md is already
    embedded in the <skill> block above).

    Args:
        skill_path: Absolute path to the skill folder in the workspace.

    Returns:
        Multi-line string with files grouped by category, using absolute paths.
    """
    skill_dir = Path(skill_path)

    SCRIPT_EXTS = {".py", ".sh", ".js", ".ts"}
    TEMPLATE_EXTS = {".html", ".htm", ".css", ".j2", ".jinja", ".tpl"}
    # True binary formats — cannot be opened with read_file
    BINARY_EXTS = {
        ".ttf",
        ".otf",
        ".woff",
        ".woff2",
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".webp",
    }
    # Directories whose .py/.js files are library modules, not CLI entry-points
    LIBRARY_DIRS = {"core", "helpers", "validators", "lib", "utils", "examples"}
    # Directories collapsed into a single summary line (too many files to list)
    COLLAPSIBLE_FOLDERS = {"schemas", "canvas-fonts"}
    EXCLUDE_FILES = {"LICENSE.txt", "LICENSE", ".gitkeep", "SKILL.md"}
    # Never directly executable
    EXCLUDE_SCRIPT_NAMES = {"__init__.py"}

    scripts: list[str] = []
    libraries: list[str] = []
    templates: list[str] = []
    docs: list[str] = []
    assets: list[str] = []
    # Maps relative dir key → list of Path objects for collapsed dirs
    collapsed: dict[str, list[Path]] = {}

    for f in sorted(skill_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.name in EXCLUDE_FILES or f.name in EXCLUDE_SCRIPT_NAMES:
            continue

        rel_parts = f.relative_to(skill_dir).parts

        # Collapse known large internal directories into a summary entry
        collapsible_ancestor = next(
            (p for p in rel_parts if p in COLLAPSIBLE_FOLDERS), None
        )
        if collapsible_ancestor:
            idx = rel_parts.index(collapsible_ancestor)
            key = "/".join(rel_parts[: idx + 1])
            collapsed.setdefault(key, []).append(f)
            continue

        rel = str(f.relative_to(skill_dir))
        abs_path = f"{skill_path}/{rel}"
        size = f.stat().st_size
        entry = f"  {abs_path} ({size:,} bytes)"

        if f.suffix.lower() in BINARY_EXTS:
            assets.append(entry)
        elif f.suffix in SCRIPT_EXTS:
            parent_names = {p.lower() for p in rel_parts[:-1]}
            if parent_names & LIBRARY_DIRS:
                libraries.append(entry)
            else:
                scripts.append(entry)
        elif f.suffix in TEMPLATE_EXTS or "template" in rel.lower():
            templates.append(entry)
        else:
            docs.append(entry)

    parts: list[str] = []
    if scripts:
        parts.append("RUNNABLE SCRIPTS — use bash to execute:\n" + "\n".join(scripts))
    if libraries:
        parts.append(
            "LIBRARY MODULES — import only, do not run directly:\n"
            + "\n".join(libraries)
        )
    if templates:
        parts.append(
            "TEMPLATES — use read_file to read, then copy & modify:\n"
            + "\n".join(templates)
        )
    if docs:
        parts.append("REFERENCE DOCS — use read_file to read:\n" + "\n".join(docs))
    if assets:
        parts.append(
            "BINARY/ASSET FILES — do NOT use read_file; reference by absolute path in scripts:\n"
            + "\n".join(assets)
        )

    for dir_key, files in sorted(collapsed.items()):
        abs_dir = f"{skill_path}/{dir_key}"
        font_files = [
            f for f in files if f.suffix.lower() in {".ttf", ".otf", ".woff", ".woff2"}
        ]
        if font_files:
            families = sorted({f.stem.rsplit("-", 1)[0] for f in font_files})
            sample = ", ".join(families[:6])
            extra = f" (+{len(families) - 6} more)" if len(families) > 6 else ""
            parts.append(
                f"FONT ASSETS — do NOT use read_file; reference by absolute path:\n"
                f"  dir: {abs_dir}\n"
                f"  available fonts: {sample}{extra}"
            )
        else:
            sample_names = ", ".join(f.stem for f in files[:5])
            ellipsis = "..." if len(files) > 5 else ""
            parts.append(
                f"[COLLAPSED — internal, do not read directly] {dir_key}/\n"
                f"  {len(files)} files ({sample_names}{ellipsis})\n"
                f"  path: {abs_dir}"
            )

    return "\n\n".join(parts) if parts else "  (no files found)"
