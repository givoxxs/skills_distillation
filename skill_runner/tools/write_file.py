"""Write file tool implementation."""

import os
from pathlib import Path


def write_file(path: str, content: str, workspace: str) -> str:
    """
    Create or overwrite a file with the given content.

    Only allows writing inside the workspace directory for security.

    Args:
        path: Absolute path to write.
        content: Text content to write.
        workspace: Workspace directory (writes must stay inside).

    Returns:
        Success message or error string.
    """
    if not path:
        return "ERROR: No path provided"

    ws = os.path.realpath(workspace)
    rp = os.path.realpath(path)

    if not rp.startswith(ws):
        return f"ERROR: Can only write files inside workspace: {workspace}"

    try:
        os.makedirs(os.path.dirname(rp), exist_ok=True)
        Path(rp).write_text(content, encoding="utf-8")
        return f"File written: {path} ({len(content):,} bytes)"
    except OSError as e:
        return f"ERROR: {e}"
