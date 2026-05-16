# Skill Distillation v2

Pipeline chính của đề tài. Chạy song song với `distillation/` (v1, legacy) — v2 là phiên bản đang được nghiên cứu, đo lường và demo cho hội đồng.

> Tóm tắt 1 câu: **viết lại `SKILL.md` qua nhiều vòng để mô hình nhỏ thực thi tốt hơn, không cập nhật trọng số**.

## Khác biệt so với v1

| Khía cạnh | v1 (`distillation/`) | v2 (`distillation_v2/`) |
|---|---|---|
| Student runner | `skill_runner/` (OpenRouter client tự viết, tools tự định nghĩa) | **Claude Code CLI** (`claude -p`) trỏ vào OpenRouter qua `ANTHROPIC_BASE_URL` |
| Student sandbox | Không — share môi trường | **Subprocess sandbox**: env dict explicit, HOME riêng, `claude logout` trước mỗi run |
| Scoring | Rule-based hand-written + LLM Judge (80/20 hybrid) | **100% LLM Judge** với rubric tự sinh; rule-based còn lại chỉ là "file exists / mime check" |
| Rubric | Hard-code `docx_rules.py` cho từng skill | **Sinh tự động** mỗi skill, cache theo `hash(SKILL.md) + hash(test_case_ids)` per workflow |
| Thêm skill mới | Viết `<skill>_rules.py` + đăng ký orchestrator | Chỉ cần thêm test_cases JSON; rubric tự sinh |
| Teacher isolation | Không | Gọi qua `anthropic_env()` context manager, không leak `ANTHROPIC_*` ra parent shell |
| Rollback | Manual | **Gate 1** (validate fixtures) + **Gate 2** (rollback nếu round_avg giảm > 0.10) |
| Resume | Manual | `--resume` từ batch cuối đã có `scores.json` |

## Kết quả thực nghiệm

Đã chạy đầy đủ trên 3 skill từ `anthropics/skills`. Số liệu chính từ `results/stable/<skill>/summary.json`:

| Skill | Rounds | Batch | R1 | Peak (round) | Cuối | Δ R1 → Peak |
|---|---|---|---|---|---|---|
| `docx` | 8 | 5 | 0.793 | **0.921** @ R5 | 0.877 | **+16.2 %** |
| `internal-comms` | 8 | 5 | 0.735 | **0.823** @ R3 | 0.822 | **+11.9 %** |
| `slack-gif-creator` | 10 | 5 | 0.716 | **0.886** @ R9 | 0.865 | **+23.6 %** |

Cả ba skill đều có *peak-then-decline*: score lên đỉnh ở R5 / R3 / R9 rồi suy giảm nhẹ — gợi ý hiện tượng *over-fit rubric ở vòng muộn*, một quan sát hiếm trong literature APO (chi tiết: `../docs/notes/skills_research_vi.md` §5.6).

Stream lại các run này qua dashboard demo: xem `../demo-app/` (`/run` page replay JSONL từng round).

## Mô hình & stack

| Vai trò | Mô hình | Provider |
|---|---|---|
| Student | `google/gemma-4-26b-a4b-it` | OpenRouter |
| Teacher | `anthropic/claude-haiku-4-5` | Anthropic API trực tiếp |
| Judge (ensemble) | `anthropic/claude-haiku-4-5` | Anthropic API |
| Rubric generator | `anthropic/claude-haiku-4-5` | Anthropic API |

Stack: Python 3.12 (conda env `skills`) · Anthropic SDK · OpenRouter · Click + Rich · PyYAML · pytest. Tất cả `python …` lệnh chạy bằng conda env binary — xem `../.claude/rules/python-env.md`.

## Cài đặt

```bash
conda activate skills

# Verify Claude Code CLI có trong $PATH (cần cho student runner)
which claude          # /Users/.../claude
claude --version      # 2.x
```

`.env` ở project root (KHÔNG tạo file riêng trong `distillation_v2/`):

```env
OPENROUTER_API_KEY=sk-or-v1-...   # Student model qua OpenRouter
ANTHROPIC_KEY=sk-ant-...          # Teacher + Judge + Rubric Generator
```

> **Lưu ý**: v2 KHÔNG đụng vào session Claude Code thật trên máy. `ANTHROPIC_BASE_URL` chỉ inject vào subprocess `claude` qua env dict explicit; parent shell giữ nguyên. Orchestrator sẽ *refuse to start* nếu parent shell đang có `ANTHROPIC_BASE_URL` trỏ tới OpenRouter — `unset` nó trước.

## Sử dụng

```bash
cd distillation_v2

# Smoke test nhanh — 1 round, 1 test case
python run.py --skill docx --rounds 1 --test-cases 1 --verbose

# Dry-run — Student + Judge, BỎ Teacher (không rewrite SKILL.md)
python run.py --skill docx --rounds 1 --test-cases 3 --dry-run --verbose

# Full distillation (rounds & batch_size mặc định lấy từ config.yaml)
python run.py --skill docx --rounds 8 --batch-size 5 --verbose

# Resume từ batch cuối đã có scores.json
python run.py --skill docx --resume

# Bỏ rubric cache, sinh mới
python run.py --skill docx --regenerate-rubric

# Tắt Gate 2 rollback (luôn giữ rewrite mới)
python run.py --skill docx --no-rollback
```

Flag đầy đủ: `python run.py --help`.

## Kiến trúc

```
run.py (CLI · click)
   └── pipeline.py (main loop)
        ├── stages/rubric_gen.py · sinh rubric 1 lần/skill
        ├── stages/judge.py · LLM-only judge, ensemble N=3
        │
        └── for round in 1..max_rounds:
             └── for batch in chunks(test_cases, batch_size):
                  ├── stages/student.py
                  │     └── runner/sandbox.py · spawn `claude` subprocess
                  │            └── runner/stream_parser.py · stream-json → JSONL
                  ├── stages/judge.py · score → eval_detail.jsonl
                  ├── stages/summarizer.py · failure → key_notes.md
                  └── stages/teacher.py · rewrite SKILL.md
                       ├── Gate 1: validate ≥3 rank-6/8 fixtures still pass
                       └── Gate 2: rollback nếu round_avg drop > 0.10
```

Điều kiện dừng (bất kỳ điều nào):
1. `round_avg ≥ stop_threshold` (default 0.70)
2. Hội tụ: `|round_avg − prev| < 0.02` qua 3 round liên tiếp
3. Chạm `max_rounds` (default 10)

## Cấu trúc thư mục

```
distillation_v2/
├── README.md                     # file này
├── run.py                        # CLI entry (click)
├── pipeline.py                   # Main loop
├── config.yaml                   # Defaults (models, rounds, batch_size, thresholds)
├── stages/
│   ├── student.py                # Run Claude Code CLI via sandbox
│   ├── judge.py                  # LLM-only judge + ensemble
│   ├── teacher.py                # Rewrite SKILL.md (anthropic_env isolation)
│   ├── summarizer.py             # key_notes from failures
│   └── rubric_gen.py             # Auto-generate per-skill rubric
├── runner/
│   ├── sandbox.py                # Subprocess env isolation
│   ├── anthropic_env.py          # Env-swap context manager
│   ├── stream_parser.py          # stream-json → v1 event schema
│   ├── logger.py                 # JSONL writer (api_calls, eval_detail)
│   └── config.py                 # RunConfigV2
├── evaluator/
│   └── base.py                   # EvalResult, CheckResult (reused from v1)
├── skills/                       # Symlinked/mirrored skills source
├── test_cases/                   # <skill>.json + fixtures/
├── rubrics/                      # Cached rubric YAML
├── logs/                         # JSONL event logs (per-run)
├── results/                      # DD_MM_YYYY/<skill>/round_N/batch_M/
│   └── stable/<skill>/           # CỐ ĐỊNH số liệu công bố
│       ├── summary.json          # score_history, best_round, rubric_cache_keys
│       ├── SKILL_round_{0..N}.md # Original + sau mỗi round
│       ├── eval_detail.jsonl     # Mỗi dòng: 1 test case đã chấm
│       ├── api_calls.jsonl       # Judge + teacher token + elapsed_s
│       └── run.log
├── tests/                        # pytest (xem dưới)
└── utils/                        # Helpers (converters, formatters)
```

## Tests

```bash
cd ..   # repo root
/opt/anaconda3/envs/skills/bin/pytest distillation_v2/tests -q

# Hoặc qua Makefile của demo-app
cd demo-app && make test-pipeline
```

| Suite | Tests | Status |
|---|---|---|
| `test_sandbox.py` | 16 | ✅ pass |
| `test_stream_parser.py` | 12 | ✅ pass |
| `test_rubric_gen.py` | 12 | ✅ pass |
| `test_student.py` | 8 | ✅ pass |
| `test_converter.py` | 6 | ✅ pass |
| `test_integration_student.py` | 1 | ⏭ skipped (cần Claude CLI) |
| **`test_rollback.py`** | 11 | ⚠️ **fail — legacy API drift** (`decide()` chữ ký không khớp) |

**Tổng: 54 pass, 11 fail, 1 skipped (trên 66 tests).** Fail trong `test_rollback.py` là known issue do refactor `rollback.decide()`; cần align signature lại — ngoài scope giai đoạn này.

## Verify env isolation

Sau khi chạy distillation, parent shell KHÔNG được bị pollute:

```bash
echo "$ANTHROPIC_BASE_URL"   # rỗng (hoặc giữ nguyên giá trị ban đầu)
echo "$ANTHROPIC_API_KEY"    # giữ nguyên
```

Nếu shell hiện tại đang có `ANTHROPIC_BASE_URL` trỏ tới OpenRouter, gỡ trước khi chạy:

```bash
unset ANTHROPIC_BASE_URL
```

## Tích hợp với `../demo-app/`

`demo-app/backend/` đọc trực tiếp `results/stable/<skill>/`:

- `summary.json` → Overview KPI + sparkline + learning curve.
- `SKILL_round_*.md` → side-by-side diff giữa các round.
- `eval_detail.jsonl` → Test case explorer (26-27 entries / round, real rule_checks + judge rationale).
- `api_calls.jsonl` → `/run` page replay token counts thật cho judge + teacher.

Pipeline KHÔNG nên ghi vào `results/stable/` trong quá trình chạy. Đó là *snapshot công bố*, được sao chép thủ công từ kết quả run mới khi nào đẹp.

## Files reused từ v1

Import qua `importlib.util` để tránh collision với `evaluator/` package:

- `distillation/summarizer.py` — analyzes failed test cases → key_notes.md
- `distillation/utils.py` — `write_api_call`, `write_eval_detail` helpers
- `distillation/evaluator/base.py` — `EvalResult`, `CheckResult`
- `distillation/evaluator/llm_judge.py` — reuse `_extract_content()` cho PDF/DOCX/XLSX

## Debug

JSONL event log có cùng schema v1 — tái sử dụng visualize tool của v1:

```bash
# Latest run log
ls -t distillation_v2/logs/*.jsonl | head -1

# Visualize
python ../distillation/visualize_log.py distillation_v2/logs/<latest>.jsonl
```

## Tham khảo

- `../docs/notes/skills_research_vi.md` — khảo cứu literature (APO, LLM-as-Judge, SLM failure modes)
- `../.claude/rules/pipeline-rules.md` — orchestration + batching + resume rules
- `../.claude/rules/evaluation-rules.md` — scoring model (rule + LLM judge + hybrid)
- `../.claude/rules/agent-execution-rules.md` — agent loop + workspace + OpenRouter
- `../README.md` — overview repo cấp cao + thông tin hồ sơ ĐATN
