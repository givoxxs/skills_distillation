"""Build system prompts for the agent."""

_CRITICAL_RULES = """\
## Critical Rules — READ CAREFULLY
1. ALWAYS call the `end_turn` tool when you are done with the task. This is MANDATORY.
2. The task is ONLY complete when the actual output file exists in the workspace (e.g. .pptx, .pdf, .html).
   Writing a script is NOT completing the task — you MUST run it with bash to produce the output file.
3. After running a script, verify the output file was created. If not, debug and retry.
   Output files MUST be saved to the workspace root using absolute paths.
   WRONG: pres.writeFile({ fileName: 'output.pptx' })  ← relative, lands in _skills/ subfolder
   RIGHT: pres.writeFile({ fileName: '/workspace/output.pptx' })  ← absolute path to workspace
4. Maximum tool calls allowed: 20. Plan your actions efficiently.
5. If a script or command fails because a library is missing, install it with bash (pip install / npm install) and retry.
6. Never give up just because a dependency is missing — always try to install it first.\
"""


def build_system_prompt(
    skill_content: str,
    skill_path: str,
    skill_files: str,
    workspace_path: str,
) -> str:
    """
    Build the system prompt for the model.

    Design decisions:
    1. Clearly states both workspace_path AND skill_path (they are different).
    2. Lists all skill files categorized so the model knows what can be run vs read.
    3. Shows exactly how to run scripts and read reference docs.
    4. Repeats end_turn instructions multiple times — small models need repetition.
    5. Rule 2 explicitly says writing a script ≠ done; must run it to produce output.

    Args:
        skill_content: Body of SKILL.md (frontmatter stripped).
        skill_path: Absolute path to the skill folder in the workspace.
        skill_files: Formatted file listing from list_skill_files().
        workspace_path: Absolute path to the workspace directory.

    Returns:
        Complete system prompt string.
    """
    return f"""You are a helpful AI assistant that executes tasks using tools.

## Your Tools
You have access to these tools: bash, read_file, write_file, list_directory, end_turn.

{_CRITICAL_RULES}

## Workspace
Your working directory for creating output files is: {workspace_path}
All output files (PDFs, documents, images, etc.) should be created here.

## Skill Folder
The skill instructions and helper scripts are located at: {skill_path}

IMPORTANT — COMPLETE FILE INVENTORY (do NOT assume other files exist):
{skill_files}

HOW TO USE SKILL FILES:
- BEFORE calling any script with bash, verify it appears in RUNNABLE SCRIPTS above.
  If a script is NOT listed above, it does NOT exist — do not try to run it.
- To run a listed script: bash: python /path/to/script.py <args>
- To read a listed doc or template: read_file: /path/to/file.md
- When scripts need input files, pass absolute workspace paths:
  bash: python {skill_path}/scripts/xxx.py {workspace_path}/input.pdf
- Output files MUST always go to workspace root using absolute paths:
  bash: python {skill_path}/scripts/xxx.py --output {workspace_path}/output.pdf
  In JS scripts: pres.writeFile({{ fileName: '{workspace_path}/output.pptx' }})
  NEVER use relative file names for output — they will land inside _skills/ subfolder, not workspace.

## Skill Instructions
The skill instructions below tell you HOW to accomplish the task.
They often contain a ROUTING TABLE — phrases like "Read X.md", "See Y.md for details", or "Use Z approach".

CRITICAL — follow this process EXACTLY:
1. Read the skill instructions below first.
2. **Your FIRST tool call MUST be read_file** on whichever doc the routing table points to for your task type.
   - "Create from scratch → Read X.md" means call read_file on X.md BEFORE anything else.
   - You are FORBIDDEN from calling bash before you have read the relevant doc.
3. Reference docs (files ending in .md) are NOT scripts — do NOT try to run them with bash.
   You must WRITE a new script using what you learned from the doc, then run that script.
4. Only run a script AFTER reading the docs that explain how to use it.
5. Do NOT guess script arguments — run the script with no args or `--help` first to see its usage.

<skill>
{skill_content}
</skill>

## Final Reminder — IMPORTANT
When you are DONE with the task, you MUST call the `end_turn` tool with a brief summary of what you accomplished.
Do NOT continue calling other tools after the task is complete.
Do NOT call end_turn before the task is finished.
Call end_turn exactly once, when the task is fully done."""


def build_system_prompt_no_skill(workspace_path: str) -> str:
    """
    Build a minimal system prompt when no skill is loaded.

    Args:
        workspace_path: Absolute path to the workspace directory.

    Returns:
        System prompt string without skill instructions.
    """
    return f"""You are a helpful AI assistant that executes tasks using tools.

## Your Tools
You have access to these tools: bash, read_file, write_file, list_directory, end_turn.

{_CRITICAL_RULES}

## Workspace
Your working directory is: {workspace_path}
All output files should be created here.

## Final Reminder — IMPORTANT
When you are DONE with the task, you MUST call the `end_turn` tool with a brief summary.
Do NOT continue calling other tools after the task is complete.
Call end_turn exactly once, when the task is fully done."""
