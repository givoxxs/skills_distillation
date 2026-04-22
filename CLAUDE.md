# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

A **Skill Distillation pipeline** that automatically iterates on `SKILL.md` definitions to make skills portable across small large language models (SLLMs). The pipeline runs a student model, evaluates outputs, analyzes failures, and uses a teacher model (Claude) to rewrite the `SKILL.md` — repeating until quality improves or convergence.

**Stack:** Python 3.11+, Anthropic SDK, OpenRouter API, Click, Rich, PyYAML, Ruff, pytest.

## Core CLI Commands

```bash
# Setup
bash requirements.sh
cp .env.example .env   # set OPENROUTER_API_KEY and ANTHROPIC_KEY

# Distillation pipeline
cd distillation/ && python run.py --skill docx --rounds 3 --test-cases 5 --verbose
python run.py --skill docx --dry-run        # skip teacher; test infra only
python run.py --skill docx --no-llm-judge   # rule-based scoring only (faster)

# Skill runner
cd skill_runner/ && python main.py run --skill docx --model qwen/qwen3-8b --prompt "..."
python main.py list-skills && python main.py logs

# Evaluation
cd skill_evaluation/ && python run_eval.py --skill docx --model qwen/qwen3-8b

# Tests & lint
cd skill_runner/ && pytest tests/ -v
pre-commit run --all-files
```

## Path Aliases

| Alias | Path |
|-------|------|
| Pipeline entry | `distillation/run.py` |
| Main loop | `distillation/orchestrator.py` |
| Teacher (SKILL rewriter) | `distillation/teacher.py` |
| Failure summarizer | `distillation/summarizer.py` |
| Rule-based evaluator | `distillation/evaluator/docx_rules.py` |
| LLM Judge | `distillation/evaluator/llm_judge.py` |
| Agent loop | `skill_runner/runner/agent_loop.py` |
| Skill definitions | `skill_runner/skills/<skill>/SKILL.md` |
| Test cases | `distillation/test_cases/<skill>.json` |
| Pipeline config | `distillation/config.yaml` |

## Known Issues

1. **Fixtures not injected**: Workflows B/C/D require input `.docx` fixtures but the orchestrator doesn't copy them into the workspace before calling `run_agent()`. See `agent-execution-rules.md` for the fix.
2. **Missing fixture**: `tracked_deletion_review.docx` is needed for `tc_c08` but doesn't exist yet.

## Domain Rules

See @.claude/rules/pipeline-rules.md for orchestration, batching, and round structure.
See @.claude/rules/evaluation-rules.md for scoring logic and evaluator extensibility.
See @.claude/rules/agent-execution-rules.md for agent loop, workspace, and OpenRouter patterns.
See @.claude/rules/skills-testcases-rules.md for SKILL.md format and test case schema.

## AI Behavior Guidelines

Derived from Andrej Karpathy's observations on systematic LLM coding failure modes.
These apply universally, regardless of project type.

### 1. Think Before Coding
- State assumptions explicitly before implementing. If uncertain, ASK — never guess silently.
- If multiple interpretations exist, present them. Do NOT pick one without disclosing.
- If a simpler approach exists, say so and push back.
- NEVER proceed when confused. Name what is unclear and stop until resolved.

### 2. Simplicity First
- Write the minimum code that solves the problem. Nothing speculative.
- No abstractions for single-use code. No unrequested "flexibility" or "configurability".
- NEVER add error handling for impossible scenarios.
- YOU MUST rewrite if 200 lines could be 50. Ask: "Would a senior engineer call this overcomplicated?"

### 3. Surgical Changes
- Touch ONLY what the user's request requires. Do NOT "improve" adjacent code, comments, or formatting.
- Match existing style, even if you would do it differently.
- If you notice unrelated dead code, MENTION it — never delete it unprompted.
- YOU MUST remove imports/variables/functions that YOUR changes made unused, but NEVER touch pre-existing dead code unless explicitly asked.
- The test: every changed line must trace directly to the user's request.

### 4. Goal-Driven Execution
- Transform tasks into verifiable success criteria before starting:
  - "Fix the bug" → "Write a test that reproduces it, then make it pass."
  - "Add validation" → "Write tests for invalid inputs, then make them pass."
- For multi-step tasks, state a brief plan with a `verify:` checkpoint for each step.
- Strong success criteria allow autonomous looping. Weak criteria ("make it work") require constant clarification.

## Agent Self-Evolution & Context Maintenance

You have authority to autonomously update memory files as the codebase evolves:

- "Do not assume a human will document your code patterns. If you build it, document it."
- **Existing rules change**: Update the relevant file in `.claude/rules/`.
- **New domains/layers**: CREATE a new rule file in `.claude/rules/` (with `paths: [...]` frontmatter) AND APPEND its `@` import to the "Domain Rules" section above.
- **Global changes** (project overview, commands, known issues): Update `CLAUDE.md` directly.
