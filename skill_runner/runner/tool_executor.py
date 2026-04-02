"""Dispatch and execute tool calls from the model."""

import os
import re
import subprocess
from pathlib import Path
from typing import Any


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    workspace: str,
    skill_path: str,
    timeout: int = 60,
) -> str:
    """
    Execute a tool call and return the result as a string.

    Security model:
    - read_file: allowed in workspace OR skill folder (model needs to read reference docs).
    - write_file: only allowed in workspace.
    - bash: cwd=workspace, but commands may cd into skill_path.
    - list_directory: allowed in workspace and skill folder.
    - str_replace: only allowed in workspace.

    All exceptions are caught and returned as error strings — the framework never crashes
    due to a bad tool call.

    Output is truncated to 4000 chars to protect small model context windows.

    Args:
        tool_name: One of bash, read_file, write_file, list_directory, str_replace, end_turn.
        arguments: Parsed tool arguments dict.
        workspace: Absolute path to workspace directory.
        skill_path: Absolute path to skill folder in workspace.
        timeout: Timeout in seconds for bash commands.

    Returns:
        String result to be returned to the model as a tool message.
    """
    try:
        if tool_name == "bash":
            return _execute_bash(arguments.get("command", ""), workspace, timeout)
        elif tool_name == "read_file":
            return _execute_read_file(arguments.get("path", ""), workspace, skill_path)
        elif tool_name == "write_file":
            return _execute_write_file(
                arguments.get("path", ""), arguments.get("content", ""), workspace
            )
        elif tool_name == "list_directory":
            return _execute_list_directory(
                arguments.get("path", ""), workspace, skill_path
            )
        elif tool_name == "str_replace":
            return _execute_str_replace(
                arguments.get("path", ""),
                arguments.get("old_str", ""),
                arguments.get("new_str", ""),
                workspace,
            )
        elif tool_name == "end_turn":
            summary = arguments.get("summary", "No summary provided")
            return f"Turn ended. Summary: {summary}"
        else:
            return f"ERROR: Unknown tool '{tool_name}'"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def _execute_bash(command: str, workspace: str, timeout: int) -> str:
    if not command.strip():
        return "ERROR: Empty command"

    # Normalize "/workspace/" shorthand → actual workspace path.
    # Models often write "/workspace/foo.js" instead of the full absolute path.
    command = _normalize_workspace_refs(command, workspace)

    # Intercept `npm install -g <pkg>` — global installs don't affect require().
    # Rewrite to local install so node_modules/ is created in cwd (workspace).
    npm_g = re.match(r"npm\s+install\s+-g\s+(.+)", command.strip())
    if npm_g:
        pkg = npm_g.group(1).strip()
        command = f"npm install {pkg}"
        note = f"[AUTO-FIXED] Redirected `npm install -g {pkg}` → `npm install {pkg}` (local). Global installs don't work with require().\n"
    else:
        note = ""

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "HOME": workspace},
        )
        parts = []
        if note:
            parts.append(note)
        if result.stdout:
            parts.append(result.stdout)
        if result.stderr:
            parts.append(f"[STDERR]: {result.stderr}")
        if result.returncode != 0:
            parts.append(f"[EXIT CODE]: {result.returncode}")
            hint = _bash_error_hint(command, result.stdout or "", result.stderr or "")
            if hint:
                parts.append(f"HINT: {hint}")
        output = "\n".join(parts).strip()
        return _truncate(output) if output else "(no output)"
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {timeout}s"


def _execute_read_file(path: str, workspace: str, skill_path: str) -> str:
    if not path:
        return "ERROR: No path provided"
    path = _normalize_workspace_refs(path, workspace)
    resolved = _resolve_path(path, workspace)
    ws = os.path.realpath(workspace)
    sp = os.path.realpath(skill_path)
    rp = os.path.realpath(resolved)
    if not (rp.startswith(ws) or rp.startswith(sp)):
        return "ERROR: Access denied. Can only read files in workspace or skill folder."
    if not os.path.isfile(resolved):
        return f"ERROR: File not found: {path}"
    try:
        content = Path(resolved).read_text(encoding="utf-8")
        return _truncate(content)
    except UnicodeDecodeError:
        return f"ERROR: Cannot read binary file: {path}"


def _execute_write_file(path: str, content: str, workspace: str) -> str:
    if not path:
        return "ERROR: No path provided"
    path = _normalize_workspace_refs(path, workspace)
    # Also normalize /workspace/ shortcuts inside the script content itself.
    # e.g. wb.save('/workspace/out.xlsx') → wb.save('/actual/workspace/out.xlsx')
    content = _normalize_workspace_refs(content, workspace)
    resolved = _resolve_path(path, workspace)
    ws = os.path.realpath(workspace)
    # Ensure destination is inside workspace
    if not (os.path.realpath(resolved).startswith(ws)):
        return f"ERROR: Can only write files in workspace: {workspace}"
    os.makedirs(os.path.dirname(os.path.abspath(resolved)), exist_ok=True)
    Path(resolved).write_text(content, encoding="utf-8")
    return f"File written: {path} ({len(content):,} bytes)"


def _execute_list_directory(path: str, workspace: str, skill_path: str) -> str:
    if not path:
        path = workspace
    path = _normalize_workspace_refs(path, workspace)
    resolved = _resolve_path(path, workspace)
    if not os.path.isdir(resolved):
        return f"ERROR: Directory not found: {path}"
    items = []
    try:
        for item in sorted(os.listdir(resolved)):
            full = os.path.join(resolved, item)
            if os.path.isdir(full):
                items.append(f"[DIR]  {item}/")
            else:
                size = os.path.getsize(full)
                items.append(f"[FILE] {item} ({size:,} bytes)")
    except PermissionError as e:
        return f"ERROR: {e}"
    return "\n".join(items) if items else "(empty directory)"


def _execute_str_replace(path: str, old_str: str, new_str: str, workspace: str) -> str:
    if not path:
        return "ERROR: No path provided"
    resolved = _resolve_path(path, workspace)
    ws = os.path.realpath(workspace)
    if not os.path.realpath(resolved).startswith(ws):
        return "ERROR: Can only edit files in workspace."
    if not os.path.isfile(resolved):
        return f"ERROR: File not found: {path}"
    if not old_str:
        return "ERROR: old_str cannot be empty"
    content = Path(resolved).read_text(encoding="utf-8")
    count = content.count(old_str)
    if count == 0:
        return (
            f"ERROR: String not found in file '{path}'. "
            "The old_str must match the file content character-for-character. "
            "NEXT STEPS: (1) Use read_file to see the actual file content and find the exact string, "
            "OR (2) Use write_file to rewrite the entire file with your changes — "
            "this is the better approach for replacing large code blocks."
        )
    if count > 1:
        return f"ERROR: String appears {count} times (must be unique). Add more surrounding context to old_str to make it unique."
    new_content = content.replace(old_str, new_str, 1)
    Path(resolved).write_text(new_content, encoding="utf-8")
    return f"Replaced string in {path}"


def _bash_error_hint(command: str, stdout: str, stderr: str) -> str:
    """
    Return a targeted hint based on common bash failure patterns.
    These hints surface immediately so the model can fix the issue in the next call
    instead of retrying the same broken command.
    """
    combined = (stdout + stderr).lower()
    cmd = command.strip()

    # macOS sed -i requires an empty string argument: sed -i '' '...'
    if "sed" in cmd and "sed: 1:" in stderr and "bad flag" in combined:
        return (
            "macOS sed requires an empty-string backup argument: `sed -i '' 's/old/new/' file`. "
            "Or use write_file to rewrite the file entirely — that's simpler and more reliable."
        )

    # node Cannot find module — global npm install doesn't help require()
    if "node" in cmd and "cannot find module" in combined:
        m = re.search(r"Cannot find module '([^']+)'", stderr, re.IGNORECASE)
        pkg = m.group(1) if m else "<package>"
        node_m = re.search(r"node\s+(\S+)", cmd)
        script_dir = os.path.dirname(node_m.group(1)) if node_m else "workspace"
        return (
            f"Node.js cannot find '{pkg}'. "
            "Global `npm install -g` does NOT affect require() — you need a LOCAL install. "
            f"Run: `cd {script_dir} && npm install {pkg}` "
            "so node_modules/ is created next to your script."
        )

    # npm install already done but module still not found — probably wrong cwd
    if "npm install" in cmd and "cannot find module" in combined:
        return (
            "npm install ran but module still not found. "
            "Make sure you run npm install in the SAME directory as your .js script, not the workspace root."
        )

    # Python wrong args (usage message in stderr)
    if any(
        kw in combined
        for kw in ("usage:", "error: the following", "unrecognized argument")
    ):
        m = re.search(r"python\s+(\S+\.py)", cmd)
        if m:
            return f"Wrong arguments. Run `python {m.group(1)} --help` to see correct usage."

    # python -c "..." with mixed quotes causes NameError/SyntaxError — suggest write_file
    if re.search(r"python\s+-c\s+['\"]", cmd) and any(
        kw in combined for kw in ("nameerror", "syntaxerror", "typeerror")
    ):
        return (
            "python -c with mixed quotes is fragile. "
            "Use write_file to save a .py script, then run it with `python script.py`. "
            "This avoids all quote-escaping issues."
        )

    # Python / node file not found
    if "no such file or directory" in combined or "does not exist" in combined:
        return "File or directory not found. Check the path is correct and the file exists before running."

    return ""


def _normalize_workspace_refs(text: str, workspace: str) -> str:
    """
    Replace '/workspace/' shorthand with the actual workspace path.
    Models often write '/workspace/foo.js' instead of the full absolute path.

    Only replaces /workspace when it is NOT preceded by a word char or slash —
    this avoids doubling paths like '/Users/.../skill_runner/workspace/_skills/'.
    """
    ws = workspace.rstrip("/")
    # Replace "/workspace/" only when not part of a longer absolute path
    text = re.sub(r"(?<![/\w])/workspace/", ws + "/", text)
    # Replace bare "/workspace" (e.g. "cd /workspace") same guard
    text = re.sub(r"(?<![/\w])/workspace(?=[^/\w]|$)", ws, text)
    return text


def _resolve_path(path: str, workspace: str) -> str:
    """Absolute paths are kept; relative paths resolve against workspace."""
    if os.path.isabs(path):
        return path
    return os.path.join(workspace, path)


def _truncate(text: str, max_chars: int = 4000) -> str:
    """Truncate long output to protect small-model context windows."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [TRUNCATED — {len(text):,} total chars]"
