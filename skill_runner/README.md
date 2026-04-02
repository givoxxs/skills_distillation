# Skill Runner

A Python framework for running Anthropic-style "skills" on small models via OpenRouter. The agent loop gives the model a set of tools (bash, read_file, write_file, etc.) and routes it using a skill-specific system prompt until it calls `end_turn`.

## Prerequisites

- Python 3.11+
- An [OpenRouter](https://openrouter.ai) API key

## Installation

```bash
cd skill_runner/
pip install -r requirements.txt

# Copy and fill in your API key
cp .env.example .env
# Edit .env: OPENROUTER_API_KEY=sk-or-v1-...
```

## CLI Usage

All commands are run from inside `skill_runner/`.

### Run a single task

```bash
python main.py run \
  --skill docx \
  --model qwen/qwen3-8b \
  --output-dir ./outputs/docx/tc_11/round_1 \
  --verbose \
  --prompt "Create a professional cover letter for Sarah Johnson applying to TechCorp."
```

**Option breakdown:**

| Option | Short | Default | Description |
|---|---|---|---|
| `--skill` | `-s` | _(none)_ | Skill folder name inside `skills/`. Omit to run in bare-tools mode (no SKILL.md injected). |
| `--model` | `-m` | `qwen/qwen3-8b` | OpenRouter model ID. Any model available on OpenRouter works (e.g. `anthropic/claude-haiku-4-5`, `qwen/qwen3-14b`). |
| `--prompt` | `-p` | _(required)_ | The task description sent to the model as the first user message. |
| `--output-dir` | | _(none)_ | If set, all files produced in the workspace are copied here after the run — excluding build artifacts (`node_modules/`, `.npm/`, `package.json`, `package-lock.json`). Use this to persist outputs for evaluation or to compare rounds of distillation. Recommended structure: `./outputs/<skill>/<test_case_id>/round_<N>/`. |
| `--input` | `-i` | _(none)_ | Path to an input file to copy into the workspace before the run starts. Can be repeated for multiple files. These files survive the workspace clean. |
| `--max-iterations` | | `20` | Maximum number of agent loop iterations before forcing a stop. Each iteration = one model API call. |
| `--timeout` | | `60` | Bash tool timeout in seconds. Increase for skills that run slow scripts (e.g. LibreOffice, Playwright). |
| `--verbose` | `-v` | off | Print each tool call and its first 200 chars of output in real-time. |
| `--skills-dir` | | `./skills` | Root directory containing skill folders. |
| `--workspace-dir` | | `./workspace` | Working directory the agent writes files to. Cleaned at the start of each run (persistent dirs kept — see below). |
| `--log-dir` | | `./logs` | Directory where JSONL execution logs are written. |

**More examples:**

```bash
# Bare-tools mode (no skill, just raw tools)
python main.py run \
  --prompt "Write a Python script that prints the first 20 Fibonacci numbers" \
  --verbose

# Pass an input file the model can read
python main.py run \
  --skill docx \
  --input ./data/template.docx \
  --prompt "Add a table of contents to the provided document" \
  --output-dir ./outputs/docx/tc_06/round_1

# Use a stronger model as ceiling reference
python main.py run \
  --skill xlsx \
  --model anthropic/claude-haiku-4-5 \
  --output-dir ./outputs/xlsx/tc_01/ceiling \
  --prompt "Create a 3-statement financial model with income statement, balance sheet, cash flow"

# Increase iterations and timeout for heavy tasks
python main.py run \
  --skill webapp-testing \
  --model qwen/qwen3-8b \
  --max-iterations 30 \
  --timeout 120 \
  --output-dir ./outputs/webapp-testing/tc_01/round_1 \
  --prompt "Write a Playwright test for a login form with validation"
```

### Workspace persistence between runs

To avoid reinstalling npm/pip packages on every run, the workspace clean preserves:

```
workspace/
  _skills/          ← skill files copied from skills/<name>/
  .npm/             ← npm cache (persisted)
  node_modules/     ← installed npm packages (persisted)
  package.json      ← (persisted)
  package-lock.json ← (persisted)
```

Everything else (output files, temp scripts) is deleted at the start of each run. When `--output-dir` is set, outputs are copied out **before** the next run's clean.

### Batch evaluation

```bash
# test_cases/pdf.json must be a JSON array of {"prompt": "..."} objects
python main.py eval --skill pdf --models "qwen/qwen3-8b,qwen/qwen3-14b" --test-cases ./test_cases/pdf.json
```

### List available skills

```bash
python main.py list-skills
```

### View logs

```bash
python main.py logs              # last 10 log files
python main.py logs --skill pdf  # filter by skill
python main.py logs --last 5
```

## How Skills Work

Each skill is a folder inside `skills/` with this structure:

```
skills/
└── pdf/
    ├── SKILL.md          # Required: instructions for the model (may have YAML frontmatter)
    ├── FORMS.md          # Optional: reference doc the model can read_file
    ├── REFERENCE.md      # Optional: another reference doc
    ├── scripts/
    │   └── generate.py   # Optional: helper scripts the model can bash-run
    └── LICENSE.txt       # Excluded from the file listing (saves tokens)
```

When a skill is loaded, `skill_runner`:

1. Copies the entire skill folder into `workspace/_skills/<name>/` so the model can access all files.
2. Makes all `.py` and `.sh` scripts executable.
3. Strips YAML frontmatter from `SKILL.md` and injects the body into the system prompt.
4. Lists all skill files (except `LICENSE.txt`) in the system prompt so the model knows what's available without needing to call `list_directory`.

The model is told the exact paths to use:

```
bash: cd /abs/path/to/workspace/_skills/pdf && python scripts/generate.py --output /abs/path/to/workspace/output.pdf
read_file: /abs/path/to/workspace/_skills/pdf/FORMS.md
```

### SKILL.md frontmatter (optional)

```yaml
---
name: PDF Generator
version: 1.2
requires: [reportlab, fpdf2]
---
# Instructions for the model...
```

The frontmatter is parsed into metadata and available programmatically. The body is what the model sees.

## How end_turn Works

`end_turn` is a regular OpenAI function-calling tool. When the model decides its task is complete, it calls:

```json
{"name": "end_turn", "arguments": {"summary": "Created output.pdf with 3 pages"}}
```

The agent loop detects this call, appends the tool result to the message history, sets `stop_reason = "end_turn"`, and breaks out of the loop. This is the clean stop condition — the model is in control of when it is done.

Other stop conditions (handled automatically):
- `natural_stop` — model sends a text reply with no tool calls
- `no_tool_calls` — model responds but calls no tools
- `max_iterations` — safety limit reached (default: 20)
- `api_error` — OpenRouter API failure after retries

## Running Tests

```bash
cd skill_runner/
pip install pytest
pytest tests/ -v
```

Tests are fully offline — they use `tempfile.TemporaryDirectory` and never call the OpenRouter API.

## Project Structure

```
skill_runner/
├── config.py              # RunConfig dataclass (all settings)
├── main.py                # Click CLI (run, eval, list-skills, logs)
├── runner/
│   ├── agent_loop.py      # Core loop: API call → tool dispatch → repeat
│   ├── logger.py          # JSONL structured logging
│   ├── openrouter_client.py  # OpenAI SDK client + retry logic
│   ├── prompt_builder.py  # System prompt construction
│   ├── skill_loader.py    # Skill folder copy + SKILL.md parsing
│   ├── tool_definitions.py   # OpenAI function-calling schemas
│   └── tool_executor.py   # Tool dispatch and security enforcement
├── tools/                 # Standalone tool implementations (importable)
│   ├── bash_tool.py
│   ├── end_turn.py
│   ├── list_directory.py
│   ├── read_file.py
│   ├── str_replace.py
│   └── write_file.py
├── skills/                # Drop skill folders here
├── workspace/             # Agent output files land here
├── logs/                  # JSONL execution logs
└── tests/
    ├── test_agent_loop.py
    ├── test_skill_loader.py
    └── test_tool_executor.py
```
