"""String replacement tool implementation."""

import os
from pathlib import Path


def str_replace(path: str, old_str: str, new_str: str, workspace: str) -> str:
    """
    Replace a unique string in a file.

    Only allows edits inside the workspace directory.
    The old_str must appear exactly once (unique match required).

    Args:
        path: Absolute path to the file.
        old_str: Exact string to find (must be unique).
        new_str: Replacement string.
        workspace: Workspace directory.

    Returns:
        Success message or error string.
    """
    if not path:
        return "ERROR: No path provided"
    if not old_str:
        return "ERROR: old_str cannot be empty"

    ws = os.path.realpath(workspace)
    rp = os.path.realpath(path)

    if not rp.startswith(ws):
        return "ERROR: Can only edit files inside workspace."

    if not os.path.isfile(path):
        return f"ERROR: File not found: {path}"

    content = Path(path).read_text(encoding="utf-8")
    count = content.count(old_str)

    if count == 0:
        return "ERROR: String not found in file"
    if count > 1:
        return f"ERROR: String appears {count} times in the file (must be unique)"

    new_content = content.replace(old_str, new_str, 1)
    Path(path).write_text(new_content, encoding="utf-8")
    return f"Replaced string in {path}"
