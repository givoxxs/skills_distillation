"""OpenAI function calling schema for all tools (OpenRouter compatible)."""

from typing import List, Dict, Any

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Execute a bash command. Use for: running scripts, installing packages, "
                "compiling code, or writing large files via heredoc. "
                "INSTALLING DEPENDENCIES: If a task requires a library that is not installed, install it first:\n"
                "  pip install <package>          # Python packages\n"
                "  npm install <package>          # Node.js — ALWAYS local, run in same dir as your .js script\n"
                "  NEVER use npm install -g       # -g is global and does NOT affect require() — use local only\n"
                "Always try to install missing dependencies rather than giving up on the task. "
                "IMPORTANT: Before running a script, verify it exists with list_directory. "
                "To write a large file (>500 chars), use bash heredoc instead of write_file:\n"
                "  cat << 'HEREDOC' > /path/output.html\n  [your content]\n  HEREDOC\n"
                "To run skill scripts: cd <skill_folder> && python scripts/xxx.py"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file. Use absolute paths. "
                "Can read files in workspace or in the skill folder "
                "(for reference docs like FORMS.md, REFERENCE.md, editing.md, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file to read"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or overwrite a file with the given content. Use absolute paths. "
                "Output files should go to the workspace directory. "
                "BEST FOR: Complete artifacts, entire file rewrites, small-medium files (<500 lines). "
                "WARNING: For very large files (>500 lines / >15KB), use bash heredoc instead to avoid JSON encoding issues: "
                "bash: cat << 'HEREDOC' > /path/file.html\n[content]\nHEREDOC"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to write the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories at the given path. Use absolute paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the directory to list"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_turn",
            "description": (
                "Call this tool when you have completed the task or have nothing more to do. "
                "This signals that you are done and the conversation should end. "
                "You MUST call this tool when your work is finished instead of continuing "
                "to call other tools unnecessarily."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A brief summary of what was accomplished"
                    }
                },
                "required": ["summary"]
            }
        }
    }
]


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Return all tool definitions."""
    return TOOLS
