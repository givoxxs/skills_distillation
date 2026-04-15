# Copilot Instructions for Skill Distillation Project

**Purpose:** Bootstrap AI agent productivity on the skill distillation pipeline. Navigate quickly to the right architecture, conventions, and commands.

---

## Quick Facts

- **What:** Automated optimization of Agent Skill definitions (SKILL.md) for small large language models using a Teacher LLM (Claude) and rule-based evaluator
- **Status:** Active research + development project (2026); reproducible end-to-end pipeline
- **Tech Stack:** Python 3.11+, OpenRouter API (student models), Anthropic SDK (teacher), Bash/file tools, YAML config
- **Key Dependencies:** `anthropic`, `click`, `rich`, `pyyaml`

---

## Environment Setup (Conda)

### Recommended: Use Conda Environment `skills`

This project uses a **conda environment named `skills`** for reproducibility. Set it up once, then reuse:

```bash
# 1. Create and activate conda environment (first time only)
conda create -n skills python=3.11 -y
conda activate skills

# 2. Install dependencies
cd /Users/soc_036/study_dir/skill_distillation
bash requirements.sh
# OR: pip install -r skill_runner/requirements.txt anthropic click rich pyyaml

# 3. Configure API keys (required)
cp .env.example .env
# Edit .env with OPENROUTER_API_KEY and ANTHROPIC_KEY

# 4. (Optional) Install pre-commit hooks
pre-commit install

# 5. From now on, just activate:
conda activate skills
cd skill_distillation
```

### Running Commands in Conda Environment

**Option A: Activate once, then run multiple commands**
```bash
conda activate skills
cd distillation/
python run.py --skill docx --rounds 1 --test-cases 3 --verbose
# Subsequent commands reuse same environment
python run.py --skill xlsx --rounds 1 --test-cases 5
```

**Option B: Run one-off commands without activating**
```bash
# Single command via conda run (no activation needed)
conda run -n skills python distillation/run.py --skill docx --rounds 1 -n 3

# Multiple commands
conda run -n skills bash -c "cd distillation && python run.py --skill docx -n 3"
```

### Verify Environment Setup

```bash
# Check conda environment exists
conda env list | grep skills

# Check Python version (should be 3.11+)
conda run -n skills python --version

# Check dependencies are installed
conda run -n skills python -c "import anthropic, click, rich, yaml; print('All deps OK')"

# Check API keys are set
conda run -n skills python -c "import os; print('OPENROUTER_API_KEY:', 'SET' if os.getenv('OPENROUTER_API_KEY') else 'MISSING')"
```

### Troubleshooting Conda Setup

| Issue | Solution |
|-------|----------|
| `conda: command not found` | Install Miniconda/Anaconda from https://docs.conda.io/projects/miniconda/en/latest/ |
| `The environment 'skills' does not exist` | Run `conda create -n skills python=3.11 -y` first |
| `ModuleNotFoundError: No module named 'anthropic'` | Activate with `conda activate skills`, then reinstall: `pip install anthropic` |
| `OPENROUTER_API_KEY not found` | Check `.env` file exists and has correct var name (not `_AI_KEY`) |

---

## Where to Find Essential Knowledge

### **1. Architecture & Responsibility Map**
→ **[CLAUDE.md](../CLAUDE.md)** — THE authoritative reference
Use when: understanding component responsibilities, data flow, module breakdown, or debugging tool chains
Key sections: Project Overview, Architecture, Configuration, Known Issues

### **2. Pipeline Mechanics & Workflows**
→ **[distillation/README.md](../distillation/README.md)** — Visual system diagram + flow explanation
Use when: starting a new distillation round, understanding stopping criteria, interpreting results

### **3. Skill Execution (Agent Loop)**
→ **[skill_runner/README.md](../skill_runner/README.md)** — CLI options, workspace persistence, tool reference
→ **[skill_runner/docs/](../skill_runner/docs/)** — Components, lessons learned, detailed workflow

### **4. Project Status & Pitfalls**
→ **[context/project_state.md](../context/project_state.md)** — Known bugs, blockers, build status
Use when: troubleshooting environment issues or understanding test failures

### **5. Quick Command Reference**
→ See **[Commands](#commands)** section below

### **6. AI Agent Customizations**
→ **[docs/customizations-guide.md](../docs/customizations-guide.md)** — How to use the 3 specialized agents (create-distillation-task, distillation-debugger, skill-evolution)
Use when: Running distillation, debugging failures, evolving SKILL.md definitions
Includes: Example prompts, workflows, quality checklists, tips & tricks

---

## Commands

### Setup with Conda Environment

```bash
# One-time: Create conda environment
conda create -n skills python=3.11 -y
conda activate skills

# Install dependencies
cd /Users/soc_036/study_dir/skill_distillation
bash requirements.sh

# Configure API keys (required for both environments)
cp .env.example .env
# Edit .env with:
#   OPENROUTER_API_KEY=sk-or-v1-...   (student models; register at openrouter.ai)
#   ANTHROPIC_KEY=sk-ant-...          (teacher; from console.anthropic.com)

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Running Distillation Pipeline

```bash
cd distillation/

# Standard 3-round distillation on docx skill with 5 test cases each
python run.py --skill docx --rounds 3 --test-cases 5 --verbose

# Dry-run: test infrastructure without teacher rewrite (faster debugging)
python run.py --skill docx --dry-run --test-cases 3

# Rule-based scoring only (skip LLM Judge for speed)
python run.py --skill docx --no-llm-judge --rounds 2

# Single round, high verbosity
python run.py --skill docx --rounds 1 -n 10 -v
```

### Running Skill Executor Directly

```bash
cd skill_runner/

# Single task on default model (Qwen 3-8B)
python main.py run --skill docx --prompt "Create a report on Q1 sales"

# On a specific model with verbose logging
python main.py run --skill docx --model anthropic/claude-haiku-4-5 --prompt "..." --verbose

# List available skills
python main.py list-skills

# View execution logs
python main.py logs
```

### Batch Evaluation

```bash
cd skill_evaluation/

# Evaluate docx skill on specific model
python run_eval.py --skill docx --model qwen/qwen3-8b

# List all available evaluators
python run_eval.py --list
```

### Testing & Linting

```bash
cd skill_runner/

# Run unit tests (offline, no API calls)
pytest tests/ -v

# Lint + format (ruff + markdownlint)
pre-commit run --all-files
```

---

## Project Structure at a Glance

```
skill_distillation/
├── CLAUDE.md                    ← Detailed architecture (READ FIRST)
├── README.md                    ← Research problem statement + context
├── .env.example                 ← Copy to .env, add API keys
│
├── distillation/                ← Main pipeline orchestrator
│  ├── run.py                    ← Entry point (python run.py --skill docx ...)
│  ├── orchestrator.py           ← Main loop: batch scheduling, stopping criteria
│  ├── teacher.py                ← Calls Claude API to rewrite SKILL.md
│  ├── summarizer.py             ← Analyzes JSONL logs → key_notes.md
│  ├── config.yaml               ← Default params (rounds, thresholds, models)
│  └── evaluator/
│     ├── docx_rules.py          ← Rule-based scoring: XML validity, structure
│     └── llm_judge.py           ← Semantic scoring via Claude ensemble
│
├── skill_runner/                ← Agent executor; runs tasks on OpenRouter
│  ├── main.py                   ← CLI: python main.py run --skill X --prompt Y
│  ├── runner/
│  │  ├── agent_loop.py          ← Core: tool calling, error handling, JSONL logs
│  │  └── openrouter_client.py   ← OpenRouter API wrapper
│  ├── skills/                   ← SKILL.md definitions (injected into system prompt)
│  ├── workspace/                ← Agent's working directory (persists node_modules, etc.)
│  ├── logs/                     ← JSONL execution logs (one per run)
│  └── tests/                    ← Unit tests (offline)
│
├── skill_evaluation/            ← Batch evaluation harness
│  ├── run_eval.py
│  └── test_cases/
│
├── anthropic_skills/            ← Anthropic's official skill library
│  └── skills/                   ← Reference implementations (docx, xlsx, pptx, etc.)
│
├── context/                     ← Project context docs
│  ├── architecture.md           ← Detailed component boundaries
│  ├── project_state.md          ← Build status, known bugs
│  └── MEMORY.md                 ← Index to all context materials
│
└── distillation/results/        ← Versioned output: round_<N>/batch_<M>/
   └── DD_MM_YYYY/
```

---

## Conventions & Requirements

### Configuration

| File | Purpose | How to Use |
|------|---------|-----------|
| `.env` | API key configuration | Copy `.env.example` → `.env`, fill in keys (required for both orchestrator & skill_runner) |
| `distillation/config.yaml` | Pipeline defaults | Edit for global params; CLI flags override |
| `skill_runner/config.py` | RunConfig dataclass | Programmatic API for skills; defines all runtime params |

### Skills & Test Cases

| Item | Convention | Example |
|------|-----------|---------|
| Skill folder | `skills/<skill_name>/` with `SKILL.md` | `skills/docx/SKILL.md` |
| Test case ID | `tc_<workflow><number>` where workflow ∈ {A=Create, B=Read, C=Edit, D=Convert, E=Edge} | `tc_a01`, `tc_c12`, `tc_e05` |
| Test case file | One JSON per skill; 30–40 cases per skill | `distillation/test_cases/docx.json` |
| Fixture | Input files in `test_cases/fixtures/` | `test_cases/fixtures/sample_docx.docx` |

### Environment Variables (Required)

```bash
OPENROUTER_API_KEY=sk-or-v1-...     # From openrouter.ai (e.g., qwen/qwen3-8b)
ANTHROPIC_KEY=sk-ant-...            # From console.anthropic.com (Claude teacher)
```

**⚠️ Common mistakes:**
- `OPENROUTER_AI_KEY` ❌ → use `OPENROUTER_API_KEY` ✅
- Missing `load_dotenv()` at top of Python scripts
- `.env` not gitignored (use `.env.example` for sharing)

### Scoring & Evaluation

**⚠️ Scoring formula is FLEXIBLE and test-case dependent (NOT fixed):**

- **Rule Score:** Dynamic average of checks specific to each test case
  - Checks are defined per test case in `distillation/test_cases/<skill>.json`
  - File validity checks (file exists, parseable, not empty)
  - Content quality checks (min paragraphs, word count, no placeholders)
  - Structure checks (has heading, table, list, etc. — only if test case requires)
  - **Formula:** score = average of all applicable checks for that test case
  - **Example:** If test case doesn't require a table, `has_table` check is not applied
  - **Pass threshold:** rule_score ≥ 0.60 (configurable)

- **LLM Judge Score:** Ensemble of N Claude calls (0–10 range, normalized) — optional
  - Only run if rule_score passes to save API costs
  - Semantic quality validation

- **Hybrid Score:** Configurable weighting (default: 0.80 × rule_score + 0.20 × llm_judge_score)
  - Can be adjusted per evaluator in config

### Stopping Criteria

Pipeline stops when ANY condition is met:
1. `stop_threshold`: Average hybrid score ≥ 0.70 (configurable)
2. Convergence: Score delta < 0.02 for 3 consecutive rounds
3. `max_rounds`: Reaches max_rounds (default 3)

---

## Development Workflows

### **Workflow: Running a Distillation Round**

1. Set up environment (see Setup above)
2. Choose a skill: `ls skill_runner/skills/`
3. Run pipeline:
   ```bash
   cd distillation/
   python run.py --skill docx --rounds 3 --test-cases 5 --verbose
   ```
4. Check results:
   ```bash
   # View output directory
   ls distillation/results/15_04_2026/round_*/
   # Each round has: evaluation_results.json, key_notes.md, updated SKILL.md
   ```

### **Workflow: Debugging a Single Test Case**

1. Identify test case ID (from evaluator output or test_cases/docx.json)
2. Extract prompt from test_cases/docx.json
3. Run skill_runner directly:
   ```bash
   cd skill_runner/
   python main.py run \
     --skill docx \
     --model qwen/qwen3-8b \
     --prompt "Your extracted prompt here" \
     --verbose
   # Check workspace/ and logs/
   ```

### **Workflow: Adding a New Test Case**

1. Create fixture file (if needed): `distillation/test_cases/fixtures/<name>.docx`
2. Add entry to `distillation/test_cases/docx.json`:
   ```json
   {
     "test_case_id": "tc_a32",
     "workflow": "A",
     "prompt": "Create a...",
     "rule_checks": [...],
     "content_checks": [...]
   }
   ```
3. Next pipeline run auto-includes it

### **Workflow: Understanding a Distillation Failure**

1. Check `distillation/results/<date>/round_N/evaluation_results.json`
2. Failed test cases are listed with `hybrid_score` and `failed_checks`
3. Read `key_notes.md` to see Teacher's analysis
4. Debug:
   - If rule failures: Check XML/file structure in output files
   - If LLM Judge failures: Run single test case with `--verbose` to inspect model reasoning
   - If SKILL.md update failed: Check Teacher logs in `teacher.py` error handling

---

## Known Issues & Workarounds

| Issue | Symptom | Workaround |
|-------|---------|-----------|
| **Missing fixture** | Test case `tc_c08` fails with "fixture not found" | Add `tracked_deletion_review.docx` to `test_cases/fixtures/` or skip test |
| **Fixture not passed to agent** | Test cases B, C, D (Read/Edit/Convert) don't receive input `.docx` | Copy fixture to workspace manually in orchestrator before calling `run_agent()` (TODO) |
| **Wrong env var name** | `OPENROUTER_API_KEY` not found | Verify `.env` has exact name; run `echo $OPENROUTER_API_KEY` to check |
| **Teacher API errors** | SKILL.md not updated after round | Check Anthropic key validity; review `teacher.py` error logs |
| **Workspace pollution** | Old agent outputs in workspace | Pipeline cleans workspace before each run (except node_modules, .npm, package.json) |

---

## When to Use Guide

### I need to...

- **Understand the big picture architecture**
  → Read [CLAUDE.md](../CLAUDE.md) Sections 1–2 (Project Overview, Architecture)

- **Debug a scoring failure**
  → Check [context/project_state.md](../context/project_state.md) + [distillation/README.md](../distillation/README.md) scoring section + run `python run.py --dry-run` to isolate the issue

- **Add a new test case**
  → Edit `distillation/test_cases/docx.json` + add fixture if needed; see **Conventions** section above

- **Run evaluation on a new model**
  → `cd skill_evaluation/ && python run_eval.py --skill docx --model <provider>/<model-id>`

- **Understand tool failures in agent execution**
  → Check [skill_runner/docs/](../skill_runner/docs/) (components, lessons_learned) + JSONL logs in `skill_runner/logs/`

- **Optimize the Teacher prompt**
  → Edit `teacher.py` system prompt; see [CLAUDE.md](../CLAUDE.md) Section on Known Issues for context

- **Compare model baselines**
  → Run `python main.py run --skill docx --model anthropic/claude-haiku-4-5 --prompt "..."` to get Claude baseline vs student

---

## Next Steps & Customizations

### Agent Customizations (Now Available)

✅ **All 3 specializations are now active** — See [docs/customizations-guide.md](../docs/customizations-guide.md) for full usage guide and examples.

1. **Create `/create-distillation-task` prompt** (`.prompt/create-distillation-task.md`)
   Guides fast setup & distillation on a new skill with one interactive command

2. **Create `distillation-debugger` agent** (`distillation-debugger.agent.md`)
   Automatically analyzes failed test cases and suggests SKILL.md improvements

3. **Create `skill-evolution` agent** (`.agent.md`)
   Validates skill structure, test cases, and evaluator rules with conventions & checklists

### Example Prompts to Validate Setup

- **"Run a quick distillation on the docx skill with just 2 test cases."**
  → Verifies `.env` setup, skill_runner CLI, orchestrator loop

- **"Add a test case for the xlsx skill that checks cell formatting."**
  → Tests adding to test_cases JSON, understanding schema

- **"Debug why tc_a05 failed in the last round."**
  → Exercises evaluator log analysis, error diagnosis workflow

- **"Improve the docx SKILL.md to handle tracked changes."**
  → Tests skill evolution workflow with conventions

---

## Quick Reference: File Locations

| What | Where |
|------|-------|
| Distillation entry point | `distillation/run.py` |
| Skill executor entry point | `skill_runner/main.py` |
| Pipeline loop | `distillation/orchestrator.py` |
| Scoring engine | `distillation/evaluator/docx_rules.py` |
| Teacher (SKILL rewriter) | `distillation/teacher.py` |
| CLI options & defaults | `distillation/config.yaml`, `skill_runner/config.py` |
| Test cases & fixtures | `distillation/test_cases/docx.json`, `test_cases/fixtures/` |
| SKILL definitions | `skill_runner/skills/<skill_name>/SKILL.md` |
| Execution logs | `skill_runner/logs/*.jsonl` |
| Evaluation results | `distillation/results/<date>/round_N/` |

---

**Last Updated:** 2026-04-15
**Maintained by:** Skill Distillation Team
**For questions:** See CLAUDE.md or context/MEMORY.md
# Copilot Instructions

These instructions guide the GitHub Copilot agent when working in the Skill Distillation project workspace.

## Project Context
This is a **Skill Distillation** system that automatically optimizes Anthropic-style `SKILL.md` definitions for smaller Large Language Models (Student models like Qwen3, Phi-4) using a Teacher model (Claude) and a Hybrid Evaluator. The goal is to improve skill execution **without model fine-tuning**.

## Architecture & Component Boundaries
- **`distillation/`**: The core optimization loop.
  - [`orchestrator.py`](distillation/orchestrator.py): Main loop coordinator.
  - [`teacher.py`](distillation/teacher.py): Calls Claude to rewrite the `SKILL.md`.
  - [`summarizer.py`](distillation/summarizer.py): Analyzes execution logs to generate `key_notes.md` for the teacher.
  - [`evaluator/`](distillation/evaluator/): Contains the Hybrid Evaluator (Rule-based `docx_rules.py` + LLM Judge).
- **`skill_runner/`**: The framework that executes test tasks using the student model via OpenRouter.
  - [`runner/agent_loop.py`](skill_runner/runner/agent_loop.py): Core agentic loop for executing tool calls.
  - [`runner/skill_loader.py`](skill_runner/runner/skill_loader.py): Parses and loads the skill definitions.
- **`skill_evaluation/`**: Standalone evaluation and visualization tools.
- **`skill_runner/skills/`**: Contains the individual skills being distilled. Each contains a `SKILL.md` file and optional `scripts/`.

## Build & Test Commands
- **Install dependencies**: `bash requirements.sh`
- **Run distillation pipeline (example)**:
  ```bash
  cd distillation
  python run.py --skill docx --rounds 5 --test-cases 5
  ```
- **Evaluate a skill manually**:
  ```bash
  cd skill_evaluation
  python run_eval.py --skill docx --model qwen/qwen3-8b
  ```
- **Run tests**:
  ```bash
  cd skill_runner
  python -m pytest tests/
  ```

## Project-Specific Conventions
- **No Fine-Tuning**: The entire system is based on rewriting the `SKILL.md` prompt correctly. Never suggest model fine-tuning.
- **SKILL.md Format**: Each skill must have a `SKILL.md` with an optional YAML frontmatter. The `skill_loader` strips the frontmatter before passing instructions to the model.
- **Evaluator Extensibility**: When adding a new skill (e.g., `xlsx`), you must create a new rule-based evaluator (e.g., `distillation/evaluator/xlsx_rules.py`) mirroring the structure of `docx_rules.py` and register it in `orchestrator.py`.
- **Hybrid Evaluation**: Consists of a Rule-Based check and an LLM Judge check. If the Rule-Based check fails, the final score is automatically 0 (skipping the LLM Judge to save API costs).

## Potential Pitfalls & Environment Issues
- **API Keys Required**: Make sure `skill_runner/.env` contains `OPENROUTER_API_KEY` for the student model inferences. The Claude Teacher requires the `claude` CLI to be logged in globally or `ANTHROPIC_KEY` to be set.
- **Conda Environment**: The distillation pipeline is usually run under a conda environment named `skills` (e.g., using `conda run -n skills python3 run.py`). Ensure dependencies are available in the active environment.
- **Workspace Persistence**: The `skill_runner` cleans the `workspace/` at the start of each run but preserves heavy dependency directories (like `node_modules/`, `.npm/`, `package.json`). Do not assume a completely sterile workspace for package management.

## Key References
- [Main README / Context](README.md)
- [Pipeline Architecture & Configurations](distillation/README.md)
- [Local Agent Run Instructions](skill_runner/README.md)
- [Developer Guidance for Claude](CLAUDE.md)
