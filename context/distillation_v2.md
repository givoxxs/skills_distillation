---
name: Distillation v2 — Current Architecture
description: Pipeline v2 dùng Claude Code CLI + LLM-only judge — kiến trúc hiện tại sau refactor
type: project
---

## Mục tiêu v2

Song song với `distillation/`, giải quyết 2 vấn đề scale của v1:
1. **skill_runner hand-rolled** → **Claude Code CLI** với OpenRouter qua `ANTHROPIC_BASE_URL`.
2. **Rule-based evaluator per-skill** → **LLM-only judge với rubric tự sinh** per skill.

**Why:** Thêm skill mới chỉ cần JSON test cases — không viết thêm `<skill>_rules.py`.

---

## Cấu trúc file hiện tại

```
distillation_v2/
├── run.py              # CLI (click) — entry point
├── pipeline.py         # Main orchestration loop (thay orchestrator.py cũ)
├── config.yaml         # Defaults: models, loop control, sandbox, env
├── stages/
│   ├── student.py      # Claude Code CLI runner — run_student(), _run_once()
│   ├── teacher.py      # Anthropic SDK → rewrite SKILL.md — rewrite()
│   ├── judge.py        # LLM-only judge — Judge.score()
│   ├── rubric_gen.py   # Generate rubric — generate_rubric() với cache
│   └── summarizer.py   # run_log.md generation — make_run_log()
├── runner/
│   ├── sandbox.py      # class Sandbox — env isolation + fresh HOME
│   ├── anthropic_env.py # anthropic_env() context manager cho Teacher/Judge
│   ├── stream_parser.py # stream-json → AgentLogger events
│   ├── config.py       # RunConfigV2 dataclass
│   └── logger.py       # AgentLogger — JSONL log writer
├── evaluator/
│   └── base.py         # EvalResult, CheckResult (dùng chung với v1)
├── utils/
│   ├── __init__.py     # get_logger, write_api_call, write_eval_detail, setup_logging
│   └── rollback.py     # choose_validation_tcs, decide, run_validation
├── test_cases/         # JSON test cases
├── rubrics/            # Cached rubric JSON
├── logs/               # JSONL logs per run
└── tests/              # 63 passing, 1 skipped (live API)
```

**Lưu ý:** Không còn dùng `importlib-by-path` để import v1 modules. v2 là standalone hoàn toàn.

---

## Kiến trúc pipeline (pipeline.py)

```
Round N:
  1. _run_batch() × all batches
     ├── run_student() → _run_once() → _stream_claude()  [stages/student.py]
     ├── Judge.score()                                    [stages/judge.py]
     └── make_run_log()                                   [stages/summarizer.py]
  2. teacher_rewrite() — once per round, reads ALL run_logs  [stages/teacher.py]
  3. choose_validation_tcs() — top-N by score từ round_results
  4. run_validation() + decide() → keep or rollback SKILL.md
  5. Check stopping criteria
```

---

## Skill injection (key design — đã fix)

**Sai (cũ):** copy SKILL.md vào `.claude/commands/<skill>.md`
**Đúng (hiện tại):** `shutil.copytree(skill_dir, ~/.claude/skills/<skill_name>/)` — copy cả folder

Claude Code CLI đọc skills từ `~/.claude/skills/<name>/`, không phải `commands/`.

```python
# stages/student.py: _install_skill_in_sandbox()
skills_dst = claude_dir / "skills" / skill_name
shutil.copytree(skill_dir, skills_dst, dirs_exist_ok=True)
```

**settings.json** inject để force model (tránh haiku/sonnet charges):
```json
{"model": "<student_model>"}
```
→ ghi vào `sandbox_home/.claude/settings.json`

**Source skill:** `~/.claude/skills/` (default trong pipeline.py) — docx-js version.
CLI flag `--skills-dir` override nếu cần.

---

## Claude Code CLI flags dùng trong student

```python
["claude", "--model", model, "-p", prompt, "--bare", "--verbose",
 "--output-format", "stream-json", "--dangerously-skip-permissions",
 "--max-turns", str(config.max_turns)]
```

- `--bare`: bỏ hooks, LSP, plugins → faster, ít tool calls dư
- `--dangerously-skip-permissions`: non-interactive
- `--output-format stream-json`: parse events real-time

---

## Retry logic (student)

```python
_RETRIABLE_STOP_REASONS = {"runner_error", "no_end_event", "cli_exit_1", "cli_exit_2", "timeout"}
```

Thêm check mới (C2): nếu `stop_reason == "end_turn"` nhưng `output_files == []` (Gemma hallucination pattern — claim success không tạo file) → `stop_reason = "runner_error: no_output_files"` → retriable.

Max retries: 3 (configurable `max_retry_per_tc`). Sau khi hết → `make_skip_result()` (score=0).

---

## Sandbox mechanics

```
Sandbox.__enter__:
  - Preflight: raise SandboxError nếu parent env có ANTHROPIC_BASE_URL ~ openrouter
  - mkdir {tmp_root}/{name}-{uuid8}/{home, cwd}
  - Build env EXPLICIT (không copy os.environ):
      PATH, HOME, TERM, LANG, ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL (if set)
      NODE_PATH = os.environ.get("NODE_PATH", "/usr/local/lib/node_modules")  ← hardcoded default
      NVM_DIR, NVM_BIN, SHELL (nếu có trong parent)
  - Best-effort claude logout (timeout 10s)

list_outputs(): skip node_modules, .npm, __pycache__, .git, hidden dirs
_copy_outputs(): chỉ copy extensions trong _OUTPUT_EXTENSIONS + skip _SKIP_NAMES
```

`NODE_PATH=/usr/local/lib/node_modules` → `require('docx')` hoạt động không cần `npm install` per run. Package docx@9.6.1 đã cài globally.

---

## Teacher system prompt (rewritten)

Prompt mới có sections rõ ràng: ## Context, ## Your Task, ## Rules (What MUST do / MUST NOT do).

Key rules:
- **Fix failures** trực tiếp từ run_logs
- **Preserve** những gì đã pass
- **Common Mistakes section** + fallback strategies
- **NO self-check loops** (confuse small models)
- **No 80% length guard** — shorter is acceptable nếu tăng clarity

Không còn sanity check "reject nếu new SKILL.md < 80% old length" trong pipeline.py.

---

## Validation TC selection (H5)

`choose_validation_tcs()` giờ nhận `round_results: list[EvalResult] | None`:
- Có results → top-N by `hybrid_score` (stable, deterministic)
- Không có results → random fallback

---

## Rubric generator

- **Cache key**: `sha256(SKILL.md)[:12] + "_" + sha256(sorted tc_ids)[:12]`
- **Cache path**: `distillation_v2/rubrics/{skill}_{key}.json`
- **Criteria**: 4–8 criteria, weights sum = 1.0 (auto-normalize nếu LLM trả lệch)
- **Invalidate**: flag `--regenerate-rubric` hoặc `watch_skill_hash=true`

---

## Stream parser

| stream-json type | event |
|---|---|
| `system.init` | `cli_init` |
| `assistant.content[tool_use]` | `tool_call` (tăng iteration) |
| `assistant.content[text]` | `assistant_text` |
| `user.content[tool_result]` | `tool_result` |
| `result.subtype=success` | `end` |
| `result.subtype!=success` | `api_error` + `end` |

---

## Gemma 4 26B hallucination pattern

Model nhận Skill tool → `"Launching skill: docx"` → claim success, iters=1, không tạo file.
→ C2 fix xử lý case này bằng cách treat end_turn + no output = retriable.

Token cost: ~68K base tokens/run = ~62K CLI system prompt + 6.5K SKILL.md.
→ `--bare` giảm overhead, `settings.json` tránh haiku/sonnet charges qua OpenRouter.

---

## Test coverage (63 passing, 1 skipped)

- `test_sandbox.py` (16): env isolation, cleanup, preflight, NODE_PATH
- `test_stream_parser.py` (12): fixtures + edge cases
- `test_rubric_gen.py` (11 + 1 live skipped): cache, parse, normalize
- `test_student.py` (7): build_prompt, skill install, retry/skip logic
- `test_rollback.py` (11): top-N selection, decide logic
- `test_converter.py` (1)

Run: `conda run -n skills pytest distillation_v2/tests/ -v`

---

## Config priority

```
CLI flag → config.yaml → hardcoded default
```

`skills_dir` default: `~/.claude/skills` (pipeline.py line `Path.home() / ".claude" / "skills"`)

---

## Known issues / Cần làm tiếp

1. **Scripts copy**: SKILL.md có `python scripts/office/validate.py` — scripts chưa được copy vào `sandbox.cwd/`. Hiện tại bỏ qua (validate không chạy được trong sandbox).
2. **Gemma variance**: cùng SKILL.md, round 1→2 score dao động 0.66→0.42. Cần nhiều rounds hơn để đánh giá trend thực tế.
3. **So sánh v1 vs v2** cho thesis writeup: chạy cùng test set, report chênh lệch score.
