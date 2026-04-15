# Skill Distillation for Small Large Language Models

**Đề tài Đồ án Tốt nghiệp 2026**

---

## What is this?

A **Skill Distillation** system that automatically optimizes Anthropic-style `SKILL.md` definitions for Small Large Language Models (Student models like Qwen3-8B, Phi-4) using a Teacher model (Claude) and a Hybrid Evaluator.

**Key Innovation**: Optimize how models understand tools — **without training or fine-tuning**. Just rewrite the skill definition.

```
SKILL.md (gốc) + Qwen3-8B → 30% success rate ❌
  ↓ Skill Distillation (Teacher rewrites SKILL.md)
SKILL.md (optimized) + Qwen3-8B → 70% success rate ✅
```

---

## Who needs this?

| User | Problem | Solution |
|------|---------|----------|
| **AI Developer** | Want cheap models but skills fail | Pre-optimized SKILL.md files |
| **Researcher** | Benchmark skill portability | Standardized test suite + metrics |
| **Startup** | Can't afford Claude on every call | Distilled skills work on Qwen3-8B |

---

## How does it work?

1. **Teacher (Claude)** reads which test cases failed
2. **Teacher** rewrites SKILL.md to be clearer for small models
3. **Student (Qwen3-8B)** executes tasks with new SKILL.md
4. **Evaluator (Hybrid)** scores performance
5. **Loop** repeats until score is good enough (~70%)

No gradient updates. No fine-tuning. Just smarter prompt writing.

---

## Quick Start

### Requirements

- Python 3.11+
- API Keys:
  - `OPENROUTER_API_KEY` from [openrouter.ai](https://openrouter.ai) (student models)
  - `ANTHROPIC_KEY` from [console.anthropic.com](https://console.anthropic.com) (teacher)

### Setup

```bash
git clone --recurse-submodules https://github.com/givoxxs/skills_distillation.git
cd skill_distillation

# Option 1: Conda (recommended)
conda create -n skills python=3.11 -y
conda activate skills
bash requirements.sh

# Option 2: Direct pip
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Edit .env with your API keys
```

### Run Distillation

```bash
cd distillation
python run.py --skill docx --rounds 3 --test-cases 5 --verbose
# ✅ Output: results/DATE/round_3/SKILL.md (optimized)
```

### Run Single Task

```bash
cd skill_runner
python main.py run --skill docx --prompt "Create a report on Q1 sales"
```

---

## Documentation

**For detailed information, see:**

| Document | Content |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | System design & Hybrid Evaluator |
| [docs/pipeline.md](docs/pipeline.md) | Optimization loop & end-to-end flow |
| [docs/tech-stack.md](docs/tech-stack.md) | Technologies used |
| [docs/scope.md](docs/scope.md) | MVP vs nice-to-have features |
| [docs/results-and-risks.md](docs/results-and-risks.md) | Expected results & risk mitigation |
| [docs/project-structure.md](docs/project-structure.md) | Directory layout & key files |
| [docs/contribution-and-insights.md](docs/contribution-and-insights.md) | Research contributions vs DSPy, implications |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | Setup with conda environment |
| [CLAUDE.md](CLAUDE.md) | Architecture for AI agents |

---

## Project Structure

```
skill_distillation/
├── distillation/                  # 🔄 Optimization pipeline (run.py)
├── skill_runner/                  # 🤖 Agent executor (main.py)
├── skill_evaluation/              # 📊 Batch evaluation
├── anthropic_skills/              # 📦 Git submodule (Anthropic skills)
├── docs/                          # 📖 Extended documentation
├── context/                       # 📚 Project context
├── pyproject.toml                 # 📦 Python packaging
├── requirements.sh                # ⚙️ Dependency installer
└── README.md                      # This file
```

**See [docs/project-structure.md](docs/project-structure.md) for detailed layout.**

---

## Commands

### Distillation Pipeline

```bash
cd distillation/

# Standard 3-round distillation with 5 test cases
python run.py --skill docx --rounds 3 --test-cases 5 --verbose

# Dry-run (no API calls, test infrastructure)
python run.py --skill docx --dry-run --test-cases 3
```

### Skill Executor

```bash
cd skill_runner/

# Run single task
python main.py run --skill docx --prompt "Create a report"

# List available skills
python main.py list-skills
```

---

## License

**MIT License** — Personal thesis project (Givoxxs, 2026)
