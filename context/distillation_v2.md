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
  1. _run_batch() × all batches  [parallel=N với ThreadPoolExecutor]
     ├── run_student() → _run_once() → _stream_claude()  [stages/student.py]
     ├── Judge.score()  [temp=0.2, max_gif_frames=3]      [stages/judge.py]
     └── make_run_log()                                   [stages/summarizer.py]
  2. Gate 2: round_avg < prev_avg - 0.10
     → hard rollback: restore SKILL_round_{best_N-1}.md (version TCs đã chạy với)
     → skip Teacher
  3. teacher_rewrite() — once per round, reads ALL run_logs  [temp=0.3]
  4. Gate 1: choose rank-6/7/8 TCs (borderline scores, sensitive to SKILL.md)
     → run_validation() với new SKILL.md
     → decide(): keep nếu val_score >= baseline - 0.10
     → baseline = avg score của TCs đó trong current round (old SKILL.md)
  5. _save_skill_version() → SKILL_round_N.md
  6. Track best: best_skill_snapshot = SKILL_round_{N-1}.md  ← fixed off-by-one
  7. Check stopping criteria (stop_threshold / converge / max_rounds)
```

**no_llm_judge mode:** khi `--no-llm-judge`, `_run_one` skip judge call hoàn toàn, set `llm_judge_score=0.0`. Student vẫn chạy — dùng để test infra không tốn Anthropic API.

---

## Skill injection (key design — đã fix hoàn chỉnh)

**Sai ban đầu (v1):** copy SKILL.md vào `.claude/commands/<skill>.md`
**Fix lần 1:** `shutil.copytree(skill_dir, ~/.claude/skills/<skill_name>/)` — copy cả folder
**Fix lần 2 (session 2026-05-03):** ALSO write `effective_skill_md` → `sandbox.cwd/CLAUDE.md`

**Lý do cần fix lần 2:**
- `.claude/skills/` là feature riêng của Claude Code CLI cho Claude-native models
- Khi routing qua OpenRouter (gemma, qwen), model KHÔNG nhận SKILL.md content từ path đó
- Model trả lời: *"available tools do not include a skill to create Word documents"*
- `cwd/CLAUDE.md` được inject vào system prompt cho **mọi model** bởi Claude Code CLI

```python
# stages/student.py: _install_skill_in_sandbox()
# 1. Copy skill folder → .claude/skills/
skills_dst = claude_dir / "skills" / skill_name
shutil.copytree(skill_dir, skills_dst, dirs_exist_ok=True)
# 2. Write effective_skill_md → cwd/CLAUDE.md (universal injection)
(sandbox.cwd / "CLAUDE.md").write_text(effective_skill_md)
```

**Effective skill md priority:** `working_md` (teacher rewrite) > `skill_dir/SKILL.md` (original)

**settings.json** inject để force model (tránh haiku/sonnet charges):
```json
{"model": "<student_model>", "autoCompactEnabled": false}
```
→ ghi vào `sandbox_home/.claude/settings.json` TRƯỚC khi gọi bất kỳ subprocess nào

**Source skill:** `~/.claude/skills/` (default trong pipeline.py) — docx-js version.
CLI flag `--skills-dir` override nếu cần.

---

## Prompt format (student)

```python
# stages/student.py: _build_prompt()
f"Use skill {skill_name} to: {user_prompt}"
```

**Tiếng Anh** (đã đổi từ tiếng Việt session 2026-05-03). Không dùng `/docx` slash command.

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
  - ⚠️ KHÔNG còn gọi _claude_logout_best_effort() — đã xóa (session 2026-05-03)

list_outputs(): skip node_modules, .npm, __pycache__, .git, hidden dirs
_copy_outputs(): chỉ copy extensions trong _OUTPUT_EXTENSIONS + skip _SKIP_NAMES
```

**Lý do xóa `_claude_logout_best_effort()`:**
- Claude Code CLI v2.1+ không có subcommand `logout`
- `claude logout` bị treat như **user prompt** → gọi default model = `claude-sonnet-4-6`
- Vào thời điểm `__enter__`, `settings.json` chưa được ghi (ghi trong `_install_skill_in_sandbox` sau)
- → Không có model override → sonnet được gọi qua OpenRouter → **~$0.01/TC bị lãng phí**
- Fresh HOME temp dir không có auth gì để clear → gọi logout là vô nghĩa

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

## Validation TC selection — rank 6-8 (updated 09/05)

`choose_validation_tcs()` nhận `round_results: list[EvalResult] | None`, trả về `tuple[list, float]`:
- **`val_tcs`**: rank 6, 7, 8 (index 5:8 sau sort descending by `llm_judge_score`)
  - Không phải top-6 mà là TCs THỨ 6, 7, 8 — "borderline": không trivially easy (top 5 ceiling=1.0) và không luôn fail (bottom)
  - `start = min(5, max(0, len(ranked) - n))` — shift left nếu ít TCs
- **`baseline`**: avg score của chính những TCs đó trong round hiện tại (với old SKILL.md)
- Không có results → random fallback, baseline=0.0

**Gate 1 decide logic:**
```python
keep = val_score >= baseline - gate1_threshold  # default threshold=0.10
```
Baseline được tính từ cùng TCs trong round hiện tại → so sánh apple-to-apple (không phải round trước).

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

## Test coverage (23 unit + 1 integration)

- `test_sandbox.py` (16): env isolation, cleanup, preflight, NODE_PATH
- `test_stream_parser.py` (12): fixtures + edge cases
- `test_rubric_gen.py` (11 + 1 live skipped): cache, parse, normalize
- `test_student.py` (7): build_prompt, skill install (CLAUDE.md injection), retry/skip logic
- `test_rollback.py` (11): top-N selection, decide logic
- `test_converter.py` (1)
- `test_integration_student.py` *(mới — session 2026-05-03)*: chạy real Claude Code CLI end-to-end

**Integration test**: model resolve via `INTEGRATION_MODEL` env, `INTEGRATION_USE_ANTHROPIC=1`, default `google/gemma-4-26b-a4b-it`. Copies output + JSONL logs → `tests/integration_results/<ts>/`.

Run unit tests: `conda run -n skills pytest distillation_v2/tests/ -v`
Run integration: `pytest tests/test_integration_student.py -v -s` (cần API key)

---

## Config priority

```
CLI flag → config.yaml → hardcoded default
```

`skills_dir` default: `~/.claude/skills` (pipeline.py line `Path.home() / ".claude" / "skills"`)

---

## LLM temperature defaults (09/05)

| Component | Default | Lý do |
|---|---|---|
| Judge | 0.2 | Near-deterministic scoring — consistency quan trọng hơn creativity |
| Teacher | 0.3 | Một chút creativity để explore fixes, không quá random |

Config override: `judge_temperature`, `teacher_temperature` trong `config.yaml` hoặc thêm param vào `run_distillation()`.

## GIF frame handling (Judge)

`Judge` có `max_gif_frames=3` (tách riêng khỏi `max_image_pages=10` dùng cho DOCX pages):
- Sample evenly: start / middle / end frames
- Composite lên background color từ GIF palette (tránh transparent → black frames)
- 3 frames đủ cho judge assess "render đúng không" mà không tốn nhiều image tokens

## Known issues / Cần làm tiếp

1. **Scripts copy**: `validate.py` chưa được copy vào sandbox — validate check vẫn không chạy được.
2. **Gemma variance**: score dao động đáng kể giữa các runs (compound non-determinism: Student + Judge + Teacher). Gate 2 giảm regression nhưng không loại bỏ hoàn toàn.
3. **docx bimodal distribution**: nhiều TCs luôn score 1.0 hoặc 0.0 → rank 6-8 thường vẫn ở 1.0 → Gate 1 baseline=1.0 → validation phải đạt ≥0.9 để pass. Ít discriminating hơn so với skills có distribution mịn.
4. **So sánh v1 vs v2** cho thesis writeup.
5. **batch_log_paths** (dead code trong pipeline.py): accumulated nhưng không dùng — harmless.
