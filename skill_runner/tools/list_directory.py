"""List directory tool implementation."""

import os


def list_directory(path: str, workspace: str) -> str:
    """
    List files and directories at the given path.

    Args:
        path: Absolute path to directory. If empty, defaults to workspace.
        workspace: Workspace directory.

    Returns:
        Formatted directory listing or error string.
    """
    if not path:
        path = workspace

    if not os.path.isdir(path):
        return f"ERROR: Directory not found: {path}"

    try:
        items = []
        for item in sorted(os.listdir(path)):
            full = os.path.join(path, item)
            if os.path.isdir(full):
                items.append(f"[DIR]  {item}/")
            else:
                size = os.path.getsize(full)
                items.append(f"[FILE] {item} ({size:,} bytes)")
        return "\n".join(items) if items else "(empty directory)"
    except PermissionError as e:
        return f"ERROR: {e}"
