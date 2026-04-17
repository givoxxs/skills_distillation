# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **Skill Distillation pipeline** that automatically iterates on SKILL.md definitions to make skills portable across small large language models (SLLMs). The pipeline runs a student model, evaluates outputs, analyzes failures, and uses a teacher model (Claude) to rewrite the SKILL.md — repeating until quality improves or convergence.

## Environment Setup

```bash
# Install dependencies
bash requirements.sh
# OR: pip install -r skill_runner/requirements.txt && pip install anthropic click rich pyyaml

# Configure API keys
cp .env.example .env
# OPENROUTER_API_KEY=sk-or-v1-...   (student models via OpenRouter)
# ANTHROPIC_KEY=sk-ant-...           (teacher Claude API calls)

# Install pre-commit hooks
pre-commit install
```

## Key Commands

### Running the Distillation Pipeline
```bash
cd distillation/
python run.py --skill docx --rounds 3 --test-cases 5 --verbose
python run.py --skill docx --dry-run          # Skip teacher, test infrastructure only
python run.py --skill docx --no-llm-judge     # Rule-based scoring only (faster)
```

CLI options: `--skill` (required), `--rounds` / `-r`, `--batch-size` / `-b`, `--test-cases` / `-n`, `--student`, `--teacher`, `--verbose`, `--dry-run`, `--no-llm-judge`.

### Running the Skill Runner Directly
```bash
cd skill_runner/
python main.py run --skill docx --model qwen/qwen3-8b --prompt "Create a report" --verbose
python main.py list-skills
python main.py logs
```

### Running Batch Evaluation
```bash
cd skill_evaluation/
python run_eval.py --skill docx --model qwen/qwen3-8b
python run_eval.py --list
```

### Tests
```bash
cd skill_runner/
pytest tests/ -v    # Offline unit tests only — no API calls
```

### Linting & Formatting
```bash
pre-commit run --all-files   # ruff (lint+format) + markdownlint
```

## Architecture

### Pipeline Flow

```
run.py (CLI) → orchestrator.py (main loop)
                    │
        ┌───────────┼───────────────┐
        ▼           ▼               ▼
  skill_runner   evaluator/     summarizer.py
  (executes     (scores output)  (analyzes failures
   agent loop)                   → key_notes.md)
        │                               │
        └───────────────────────────────┘
                        │
                        ▼
                   teacher.py
              (rewrites SKILL.md via Anthropic API)
                        │
                        ▼
              SKILL.md v(n+1) → next round
```

### Module Responsibilities

| Module | Role |
|--------|------|
| `distillation/orchestrator.py` | Outer distillation loop; batching, stopping criteria, round management, resume support |
| `distillation/teacher.py` | Calls Anthropic SDK to rewrite SKILL.md based on key_notes |
| `distillation/summarizer.py` | Reads JSONL logs → structured markdown failure analysis |
| `distillation/evaluator/docx_rules.py` | Rule-based scoring: dynamic average of per-test-case checks (file validity, content, structure). Only applicable checks are counted per test case. |
| `distillation/evaluator/llm_judge.py` | Semantic scoring via Claude ensemble; hybrid = 80% rule + 20% LLM (configurable via `llm_judge_weight`) |
| `skill_runner/runner/agent_loop.py` | Core agent execution loop with tool calling; writes JSONL logs |
| `skill_runner/runner/prompt_builder.py` | Builds system prompt injecting SKILL.md content |
| `skill_runner/runner/openrouter_client.py` | OpenRouter API client with retries |

### Key Data Classes

- `RunConfig` (`skill_runner/config.py`): All runtime parameters for one agent execution
- `EvalResult` (`distillation/evaluator/base.py`): Per-test-case result with rule_score, llm_judge_score, hybrid_score
- `CheckResult`: Individual check (name, passed, score, reason)

### Scoring

- `rule_score`: Dynamic average of all applicable rule checks for a test case (pass threshold ≥ 0.60)
- `llm_judge_score`: Ensemble of N Claude calls (0–10, normalized); **only runs when rule_score passes** to save API cost
- `hybrid_score` = 0.80 × rule_score + 0.20 × llm_judge_score (weight set by `llm_judge_weight` in `config.yaml`)
- Stopping: `stop_threshold` (config.yaml default 0.70), or convergence delta < 0.02 for 3 consecutive rounds, or `max_rounds`

### Batching & Round Structure

Within each round, test cases are split into batches of `batch_size`. The Teacher is invoked **per batch** (not per round), so SKILL.md is progressively rewritten multiple times within a single round. If `batch_size=0` or `batch_size ≥ len(test_cases)`, the Teacher is called once per round (no intra-round batching).

The orchestrator supports **resume from partial runs**: `_is_batch_complete()` checks for existing output dirs and `scores.json` to skip already-completed batches on re-run.

### Results Layout

```
distillation/results/DD_MM_YYYY/round_<N>/batch_<M>/
    ├── <tc_id>/              # per-test-case output files
    ├── scores.json            # batch-level aggregated scores
    ├── evaluation_results.json
    └── key_notes.md           # Teacher's failure analysis for this batch
```

### Test Cases

Located in `distillation/test_cases/` as JSON files (one per skill). The docx schema (v3) defines 32 test cases grouped by workflow (A=Create, B=Read, C=Edit, D=Convert, E=Edge). Each test case has:
- `rule_checks`: XML/style checks (`xml.contains`, `xml.absent`, `style.*`)
- `content_checks`: Semantic checks (keywords, output_format)
- `must_have_docx`: Gate field — if the output docx doesn't exist, skip content checks

Fixtures for Read/Edit/Convert workflows live in `distillation/test_cases/fixtures/`.

### Skills

`skill_runner/skills/` contains 17 skill folders. Each skill has a `SKILL.md` that the agent uses as instructions. The distillation process improves the SKILL.md for a target skill (typically `docx`).

### Workspace Persistence

Between runs, the agent workspace preserves: `.npm/`, `node_modules/`, `package.json`, `_skills/`. Output files are copied to `output_dir` before the workspace is cleaned.

## Configuration

`distillation/config.yaml` defaults:
- `student_model`: qwen/qwen3-8b
- `teacher_model`: claude-haiku-4-5
- `max_rounds`: 3
- `stop_threshold`: 0.7
- `batch_size`: 5

CLI flags override config.yaml values.

## Known Issues

1. **Fixture files not passed to agent**: Test cases in workflows B (Read), C (Edit), D (Convert) require input `.docx` fixtures but the orchestrator doesn't currently copy them into the workspace before calling `run_agent()`. Fix: copy fixture files into workspace and inject their paths into the prompt.

2. **Missing fixture**: `tracked_deletion_review.docx` is needed for test case `tc_c08` but doesn't exist yet.
