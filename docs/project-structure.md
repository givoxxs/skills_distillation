# Project Structure

## Directory Layout

```
skill_distillation/
│
├── 📄 README.md                    # Quick start guide
├── 📄 CLAUDE.md                    # Architecture reference
├── 📄 LICENSE                      # MIT License + dependencies
├── 📄 .env.example                 # Environment template
├── 📄 requirements.sh              # Dependency installation script
├── 📄 pyproject.toml               # Python packaging config
│
├── 📁 docs/                        # Extended documentation
│   ├── architecture.md             # System design (this you are reading)
│   ├── pipeline.md                 # Optimization loop & flow
│   ├── tech-stack.md               # Technologies & dependencies
│   ├── scope.md                    # MVP vs nice-to-have features
│   ├── results-and-risks.md        # Expected results & risks
│   ├── project-structure.md        # (this file)
│   ├── setup.md                    # Detailed setup (coming soon)
│   ├── customizations-guide.md     # AI agent customizations
│   └── ...
│
├── 📁 distillation/                # 🔄 Main optimization pipeline
│   ├── run.py                      # CLI entry point (python run.py --skill docx)
│   ├── orchestrator.py             # Main loop: batch scheduling, stopping criteria
│   ├── teacher.py                  # Claude-based SKILL.md rewriter
│   ├── summarizer.py               # Analyzes execution logs → key_notes.md
│   ├── utils.py                    # Logging, API call tracking
│   ├── config.yaml                 # Default params (rounds, thresholds, models)
│   │
│   ├── evaluator/                  # Scoring engine
│   │   ├── base.py                 # Protocol definitions
│   │   ├── docx_rules.py           # Rule-based evaluator for DOCX
│   │   ├── llm_judge.py            # Claude semantic judge (ensemble)
│   │   └── __init__.py
│   │
│   ├── test_cases/                 # Test case definitions
│   │   ├── docx.json               # 30-40 test cases + scoring rules
│   │   ├── xlsx.json
│   │   ├── fixtures/               # Input files for testing
│   │   │   └── sample_docx.docx
│   │   └── description/
│   │
│   ├── results/                    # Versioned output per date
│   │   └── 15_04_2026/
│   │       ├── round_1/
│   │       │   ├── evaluation_results.json
│   │       │   ├── key_notes.md    # Teacher's error analysis
│   │       │   ├── SKILL.md.v1     # Rewritten by Teacher
│   │       │   └── ...
│   │       ├── round_2/
│   │       └── round_3/
│   │
│   └── README.md                   # Pipeline documentation
│
├── 📁 skill_runner/                # Agent executor (OpenRouter integration)
│   ├── main.py                     # CLI: (python main.py run --skill docx --prompt "...")
│   ├── config.py                   # RunConfig dataclass
│   ├── requirements.txt            # Python dependencies
│   │
│   ├── runner/                     # Core agent loop implementation
│   │   ├── agent_loop.py           # Main agentic loop with tool calling
│   │   ├── openrouter_client.py    # OpenRouter API client wrapper
│   │   ├── skill_loader.py         # Parses SKILL.md + injects into prompt
│   │   ├── prompt_builder.py       # Constructs system + user prompts
│   │   ├── tool_definitions.py     # Tool schema definitions
│   │   ├── tool_executor.py        # Execute bash/file tools
│   │   ├── logger.py               # JSONL execution logger
│   │   └── __init__.py
│   │
│   ├── tools/                      # Tool implementations
│   │   ├── bash_executor.py        # Bash command execution
│   │   ├── file_manager.py         # Read/write files
│   │   ├── list_directory.py       # Directory listing
│   │   └── __init__.py
│   │
│   ├── skills/                     # SKILL.md definitions
│   │   ├── docx/
│   │   │   ├── SKILL.md            # Instructions for DOCX skill
│   │   │   └── scripts/            # Helper scripts
│   │   ├── xlsx/
│   │   ├── pptx/
│   │   └── ... (18+ official skills from Anthropic)
│   │
│   ├── workspace/                  # Agent's working directory
│   │   ├── node_modules/           # Preserved across runs
│   │   ├── package.json            # Preserved across runs
│   │   └── ...output files...      # Cleaned before each run
│   │
│   ├── logs/                       # JSONL execution logs
│   │   ├── docx_qwen_qwen3-8b_20260415T075943.jsonl
│   │   ├── docx_qwen_qwen3-8b_20260415T080243.jsonl
│   │   └── ... (one per run)
│   │
│   ├── tests/                      # Unit tests (offline)
│   │   ├── test_agent_loop.py
│   │   ├── test_skill_loader.py
│   │   ├── test_tool_executor.py
│   │   └── ...
│   │
│   ├── docs/                       # Detailed docs
│   │   ├── overview.md
│   │   ├── components.md
│   │   ├── usage.md
│   │   ├── workflow.md
│   │   └── lessons_learned.md
│   │
│   ├── README.md                   # Skill runner documentation
│   └── .gitignore                  # Ignore local files
│
├── 📁 skill_evaluation/            # Batch evaluation harness
│   ├── run_eval.py                 # Evaluation orchestrator
│   ├── visualize_log.py            # Log visualization tool
│   ├── viewer.html                 # Web viewer for results
│   │
│   ├── test_cases/                 # Test case definitions
│   │   ├── docx.json
│   │   ├── xlsx.json
│   │   ├── webapp-testing.json
│   │   └── ...
│   │
│   ├── logs/                       # Evaluation results
│   │   └── (auto-generated)
│   │
│   ├── scripts/                    # Helper scripts
│   └── README.md
│
├── 📁 anthropic_skills/            # 📦 Git submodule
│   ├── skills/                     # Anthropic's official skill library
│   │   ├── docx/
│   │   ├── xlsx/
│   │   ├── pptx/
│   │   ├── pdf/
│   │   ├── web-artifacts-builder/
│   │   └── ... (18+ skills)
│   │
│   ├── spec/                       # Official specification
│   │   └── agent-skills-spec.md
│   │
│   └── template/
│       └── SKILL.md                # Template for new skills
│
├── 📁 context/                     # Project context & metadata
│   ├── architecture.md             # Component boundaries
│   ├── feedback.md                 # Design decisions log
│   ├── project_state.md            # Build status, known issues
│   ├── user_profile.md             # Users & personas
│   └── MEMORY.md                   # Index to all materials
│
└── 📁 .github/                     # GitHub configuration
    └── copilot-instructions.md     # AI agent bootstrap guide
```

---

## Key Files at a Glance

### Entry Points

| File | Purpose | Usage |
|------|---------|-------|
| `distillation/run.py` | Start optimization pipeline | `python run.py --skill docx --rounds 3 -n 5` |
| `skill_runner/main.py` | Execute single task | `python main.py run --skill docx --prompt "..."` |
| `skill_evaluation/run_eval.py` | Batch evaluation | `python run_eval.py --skill docx --model qwen/qwen3-8b` |

### Configuration

| File | Purpose |
|------|---------|
| `distillation/config.yaml` | Pipeline defaults (rounds, thresholds, models) |
| `skill_runner/config.py` | RunConfig dataclass (programmatic) |
| `.env.example` | API key template |

### Skills & Test Cases

| Path | Content |
|------|---------|
| `skill_runner/skills/<skill>/SKILL.md` | Skill definition |
| `distillation/test_cases/<skill>.json` | Test cases + evaluation rules |
| `distillation/test_cases/fixtures/` | Input files for testing |

### Logs & Results

| Path | Purpose |
|------|---------|
| `skill_runner/logs/*.jsonl` | Execution logs (one per run) |
| `distillation/results/<date>/round_*/` | Evaluation results + SKILL versions |
| `skill_evaluation/logs/` | Batch evaluation results |

---

## Typical Workflow

1. **Setup**: `cd distillation && python run.py --skill docx --dry-run -n 3`
2. **Run optimization**: `python run.py --skill docx --rounds 3 --test-cases 5`
3. **Check results**: `ls results/<date>/round_*/evaluation_results.json`
4. **View improved SKILL**: `cat results/<date>/round_3/SKILL.md.v3`
5. **Evaluate on new model**: `cd ../skill_evaluation && python run_eval.py --skill docx --model qwen/qwen3-8b`
