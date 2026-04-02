"""Bash tool implementation."""

import os
import subprocess


def bash(command: str, workspace: str, timeout: int = 60) -> str:
    """
    Execute a bash command in the workspace directory.

    Args:
        command: Shell command string to run.
        workspace: Working directory for the command.
        timeout: Maximum seconds to wait (default 60).

    Returns:
        Combined stdout/stderr, truncated if needed.
    """
    if not command.strip():
        return "ERROR: Empty command"
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
        if result.stdout:
            parts.append(result.stdout)
        if result.stderr:
            parts.append(f"[STDERR]: {result.stderr}")
        if result.returncode != 0:
            parts.append(f"[EXIT CODE]: {result.returncode}")
        output = "\n".join(parts).strip()
        return output if output else "(no output)"
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {timeout}s"
