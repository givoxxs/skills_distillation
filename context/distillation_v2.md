---
name: Distillation v2 — Parallel Pipeline
description: Pipeline v2 song song với v1, dùng Claude Code CLI + LLM-only judge, implemented 2026-04-17
type: project
---

## Mục tiêu v2 (không xoá v1)

Song song với `distillation/`, giải quyết 2 vấn đề scale của v1:
1. **skill_runner hand-rolled** → thay bằng **Claude Code CLI** (binary `claude`) với OpenRouter làm backend qua `ANTHROPIC_BASE_URL`.
2. **Rule-based evaluator per-skill** → thay bằng **LLM-only judge với rubric tự sinh** cho mỗi skill (cache theo hash SKILL.md + test case ids).

**Why:** Thêm skill mới giờ chỉ cần JSON test cases — không phải viết thêm `<skill>_rules.py`. Demo dễ dàng cho nhiều skill trong thesis.

## Quyết định kiến trúc đã chốt (qua AskUserQuestion)

- **Layout**: `distillation_v2/` sibling với `distillation/` (không nested).
- **Sandbox**: subprocess + env dict explicit + fresh HOME (không Docker, không sandbox-exec).
  - Lý do: user đang dùng Claude Code thật trên máy, KHÔNG được leak `ANTHROPIC_BASE_URL=openrouter` ra parent shell.
  - Pre-flight guard: refuse start nếu parent env đã có `ANTHROPIC_BASE_URL` trỏ tới openrouter.
- **API keys**: chung 1 `ANTHROPIC_KEY` cho Judge + Teacher. Isolation qua `anthropic_env()` context manager (os.environ swap + restore).
- **Skill injection**: inline SKILL.md trong prompt tới Claude Code (không dùng `.claude/CLAUDE.md` file).

## Files tạo mới (15 files, ~2,000 LOC)

```
distillation_v2/
├── run.py                        # CLI (click) — mirror v1 flags + --regenerate-rubric
├── orchestrator.py               # Main loop — reuse v1 summarizer/teacher/utils
├── config.yaml                   # Defaults: sandbox, env, rubric, student cfg
├── README.md                     # User-facing doc (tiếng Việt)
├── runner/
│   ├── sandbox.py                # class Sandbox (context mgr, env isolation)
│   ├── anthropic_env.py          # anthropic_env() context mgr cho Teacher/Judge
│   ├── stream_parser.py          # Claude Code stream-json → v1 AgentLogger events
│   ├── claude_code_runner.py     # run_agent() — cùng return shape như v1
│   └── config.py                 # RunConfigV2 dataclass
├── evaluator/
│   ├── rubric_generator.py       # generate_rubric() — cache theo sha256(SKILL.md + tc_ids)
│   └── llm_only_judge.py         # LLMOnlyJudge — rule_weight=0, llm_weight=1
├── rubrics/                      # Cache per-skill JSON
├── logs/                          # JSONL logs khớp v1 schema
└── tests/                        # 48 tests offline (pytest)
```

## Import pattern: importlib-by-path

v2 `evaluator/` package collide với v1 `distillation/evaluator/` (cùng tên). Solution: load v1 modules qua `importlib.util.spec_from_file_location` bằng absolute path. Trong `orchestrator.py` còn phải pre-register v1's `evaluator` package trong `sys.modules` trước khi load `summarizer.py` (vì summarizer có `from evaluator.base import EvalResult`), rồi xoá shim trước khi import v2.

**Why:** tránh copy v1 code — keep summarizer/teacher/utils/llm_judge `_extract_content` reusable as-is.

## Rubric generator

- **Input prompt**: skill name + full SKILL.md + 3-5 test cases (`prompt` + `expected_behavior`).
- **System prompt**: yêu cầu 4-8 criteria, weights sum = 1.0, pass_threshold mỗi criterion.
- **Cache key**: `sha256(SKILL.md)[:12] + "_" + sha256(sorted tc_ids)[:12]`.
- **Cache path**: `distillation_v2/rubrics/{skill}_{key}.json`.
- **Invalidate**: khi SKILL.md thay đổi (Teacher rewrite) hoặc test set đổi. Flag `--regenerate-rubric` bypass cache.
- **Auto-normalize**: weights được re-scale để sum = 1.0 nếu LLM trả về lệch.

**Ví dụ**: docx rubric đầu tiên có 7 criteria: File Validity, Task Completion, Correct Numbering, Native Word Formatting, Not Text Substitution, Clean Structure, Output in Right Location.

## LLM-only judge

- Reuse `_extract_content()` từ v1's `llm_judge.py` (handles docx/pdf/xlsx/txt).
- Prompt = rubric JSON + test_case prompt + expected_behavior + extracted content.
- Response JSON: `{criteria:[{name,score,reason}], overall, verdict}`.
- Ensemble N calls → `statistics.median(overalls)`.
- Map vào `EvalResult`: `_rule_weight=0.0, _llm_weight=1.0` → `hybrid_score == llm_judge_score`. Summarizer và stopping criteria v1 chạy không đổi.

## Sandbox mechanics

```
Sandbox.__enter__:
  - Preflight: raise nếu parent env có ANTHROPIC_BASE_URL ~ openrouter.ai
  - mkdir {tmp_root}/{name}-{uuid8}/{home,cwd}
  - Build env dict explicit: PATH, HOME, TERM, LANG, ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL
    + PRESERVE NODE_PATH/NVM_*/SHELL từ parent (Claude Code shells out to node)
    + KHÔNG dùng os.environ.copy() — tránh leak biến khác
  - Best-effort `claude logout` trong sandbox HOME (timeout 10s, ignore exit code)

Sandbox.__exit__:
  - shutil.rmtree trừ khi (keep_on_fail=True AND có exception)
```

## Stream parser

Map Claude Code `--output-format stream-json` sang v1 `AgentLogger` events:

| Stream-json type | v1 event |
|---|---|
| `system.init` | `cli_init` (thay thế `start` — `start` gọi trước khi stream) |
| `assistant.content[tool_use]` | `tool_call` (tăng iteration) |
| `assistant.content[text]` | `assistant_text` (v2-only, không có trong v1) |
| `user.content[tool_result]` | `tool_result` |
| `result.subtype!="success"` | `api_error` + `end` |
| `result.subtype="success"` | `end` |

Unknown type → log + skip (schema drift defensive, không crash).

## Smoke test 2026-04-17 (verified live)

Command: `python run.py --skill docx --rounds 1 --test-cases 1 --dry-run --verbose`

- Rubric sinh tự động: 7 criteria, cached.
- Claude Code CLI (v2.1.112) chạy qwen3-8b qua OpenRouter trong sandbox.
- 2 iterations (Write script.py → Bash python script.py), 41s wall.
- Output: `output.docx` + `script.py` copied tới `results/17_04_2026/docx/round_1/batch_1/tc_a01/`.
- Judge score: 0.21 (fail — qwen3-8b nhầm `scripts/office/validate.py` không tồn tại trong sandbox).
- **Parent env không leak**: `ANTHROPIC_BASE_URL` vẫn unset sau khi chạy.
- JSONL log khớp schema v1: `start → cli_init → tool_call/tool_result × N → assistant_text → end`.

## Test coverage (48 tests offline)

- `test_sandbox.py` (16): env isolation, cleanup, preflight guard, file listing.
- `test_stream_parser.py` (12): 3 fixture transcripts + edge cases + unknown types.
- `test_rubric_generator.py` (12): cache key stability, cache invalidation, JSON parse + weight normalization.
- `test_llm_only_judge_smoke.py` (8): empty output, mocked API call, EvalResult mapping.

Run: `conda run -n skills python -m pytest distillation_v2/tests/ -v`.

## Known gaps / next steps

1. **Smoke chưa test Teacher loop** — `--dry-run` bỏ qua. Cần test Teacher rewrite trong `anthropic_env()` context (expected: không leak env qua rewrite call).
2. **qwen3-8b nhầm path validate.py** — trong v1 có workspace script, v2 sandbox chưa copy. Cần đánh giá xem có cần copy `skill_runner/workspace/scripts/` hay không, hay để LLM Judge đánh giá output.docx trực tiếp (preferred cho v2 để giảm complexity).
3. **So sánh v1 vs v2** — chạy cùng test set, report chênh lệch score cho thesis writeup.
