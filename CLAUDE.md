# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **Skill Distillation** system that automatically optimizes Anthropic Skill definitions (SKILL.md files) so smaller student models (Qwen, Phi via OpenRouter) can follow them more reliably — without fine-tuning. A teacher model (Claude) rewrites skill instructions based on evaluation feedback.

## Common Commands

### Install dependencies
```bash
bash requirements.sh
```

### Run distillation pipeline
```bash
cd distillation
python run.py --skill docx --rounds 3 --batch-size 5
python run.py --skill docx --rounds 5 --test-cases 10 --student-model qwen/qwen3-8b
```

### Evaluate a skill manually
```bash
cd skill_evaluation
python run_eval.py --skill docx --model qwen/qwen3-8b
```

### Run tests
```bash
python -m pytest tests/
```

### Environment setup
Copy `.env` (or `skill_runner/.env.example`) and set:
- `OPENROUTER_AI_KEY` — for student model inference
- `ANTHROPIC_KEY` — for teacher model (Claude)

## Architecture

### Pipeline flow

```
run.py → orchestrator.py → [round loop]
    ├── skill_runner: run student model on test cases
    ├── evaluator: hybrid score (docx_rules 50% + llm_judge 50%)
    ├── summarizer: analyze failures → key_notes
    └── teacher: rewrite SKILL.md using Claude + key_notes
```

Outputs per run: `SKILL_round_0.md`, `SKILL_round_1.md`, ..., `summary.json`

### Key modules

| Module | File | Role |
|--------|------|------|
| **Orchestrator** | `distillation/orchestrator.py` | Main loop: batches test cases, calls evaluator+teacher, checks stopping criteria |
| **Teacher** | `distillation/teacher.py` | Calls Anthropic API to rewrite SKILL.md given error notes |
| **Summarizer** | `distillation/summarizer.py` | Reads eval results + execution logs → structured `key_notes` for teacher |
| **LLM Judge** | `distillation/evaluator/llm_judge.py` | Semantic scoring via Claude (3x ensemble, 0.0–1.0) |
| **Rule Evaluator** | `distillation/evaluator/docx_rules.py` | Format/structural checks for .docx output |
| **Agent Loop** | `skill_runner/runner/agent_loop.py` | Core agentic loop: OpenRouter model → tool calls → repeat |
| **Skill Loader** | `skill_runner/runner/skill_loader.py` | Loads skill folder, strips YAML frontmatter from SKILL.md |

### Skill format

Each skill lives in `skill_runner/skills/<name>/` with:
- `SKILL.md` — YAML frontmatter + markdown instructions (the artifact being distilled)
- `scripts/` — helper scripts the agent can call
- `templates/` — optional file templates

### Stopping criteria (configurable in `distillation/config.yaml`)

- `stop_threshold: 0.80` — stop when avg score ≥ threshold
- `converge_delta: 0.02` + `converge_k: 3` — stop after 3 rounds with < 0.02 improvement
- `max_rounds: 10` — hard cap

### Test cases

Defined in `skill_evaluation/test_cases/<skill>.json`. Each case includes:
- `prompt` — user instruction given to student agent
- `expected_behavior` — description for LLM judge
- `auto_eval` — rule checks: `xml_must_contain`, `xml_must_not_contain`, `keywords_in_text`
- `structural_checks` — schema validation (has_list, page_count, etc.)

### Default models

- Student: `qwen/qwen3-8b` (via OpenRouter)
- Teacher: `claude-haiku-4-5` (via Anthropic API)