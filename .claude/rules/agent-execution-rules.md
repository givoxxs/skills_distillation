---
paths: ["skill_runner/**/*.py", "skill_runner/runner/**/*.py"]
---

# Agent Execution Rules

## Agent Loop
The core loop is in `skill_runner/runner/agent_loop.py`. It handles tool calling, error recovery, and writes one JSONL log per run to `skill_runner/logs/`. NEVER bypass the agent loop by calling OpenRouter directly in orchestrator code.

## Workspace Persistence
Between runs the workspace (`skill_runner/workspace/`) is cleaned but these dirs/files are always preserved: `.npm/`, `node_modules/`, `package.json`, `_skills/`. Do NOT assume a sterile workspace for package-management side effects.

## Known Issue: Fixtures Not Injected
IMPORTANT: Workflows B (Read), C (Edit), D (Convert) require input `.docx` fixtures but the orchestrator currently does NOT copy them into the workspace before calling `run_agent()`. The fix is to copy fixture files into the workspace and inject their paths into the prompt — see `distillation/orchestrator.py` for the `run_agent()` call site.

## System Prompt Construction
The system prompt is built by `skill_runner/runner/prompt_builder.py`, which injects the full SKILL.md content. NEVER hard-code skill instructions outside of SKILL.md files — the prompt builder is the single injection point.

## OpenRouter Client
`skill_runner/runner/openrouter_client.py` wraps the OpenRouter API with retries. Use `OPENROUTER_API_KEY` (exact name) in `.env`. The common mistake is using `OPENROUTER_AI_KEY` — this will silently fail with auth errors.

## JSONL Logs
Each agent run appends a structured JSONL record to `skill_runner/logs/`. The summarizer (`distillation/summarizer.py`) reads these logs to produce `key_notes.md` for the Teacher. NEVER delete logs mid-pipeline run — the summarizer depends on them being present.
