"""Read file tool implementation."""

import os
from pathlib import Path


def read_file(path: str, workspace: str, skill_path: str, max_chars: int = 4000) -> str:
    """
    Read a file's contents.

    Allowed locations: workspace directory OR skill folder (model needs to read
    reference docs like FORMS.md, REFERENCE.md from the skill folder).

    Args:
        path: Absolute path to the file.
        workspace: Absolute path to the workspace directory.
        skill_path: Absolute path to the skill folder.
        max_chars: Truncation limit for output.

    Returns:
        File contents as string, or an error message.
    """
    if not path:
        return "ERROR: No path provided"

    ws = os.path.realpath(workspace)
    sp = os.path.realpath(skill_path)
    rp = os.path.realpath(path)

    if not (rp.startswith(ws) or rp.startswith(sp)):
        return "ERROR: Access denied. Can only read files in workspace or skill folder."

    if not os.path.isfile(path):
        return f"ERROR: File not found: {path}"

    try:
        content = Path(path).read_text(encoding="utf-8")
        if len(content) > max_chars:
            content = (
                content[:max_chars]
                + f"\n... [TRUNCATED — {len(content):,} total chars]"
            )
        return content
    except UnicodeDecodeError:
        return f"ERROR: Cannot read binary file: {path}"
