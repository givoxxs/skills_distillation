# Skill Distillation v2

Một phiên bản song song của pipeline distillation — giữ nguyên `distillation/` (v1) và chạy bên cạnh.

## Khác biệt so với v1

| Khía cạnh | v1 | v2 |
|---|---|---|
| **Student runner** | `skill_runner/` (OpenRouter client tự viết, tools tự định nghĩa) | **Claude Code CLI** (`claude -p`) trỏ tới OpenRouter qua `ANTHROPIC_BASE_URL` |
| **Student sandbox** | Không — share môi trường | **Subprocess sandbox**: env dict explicit, HOME riêng, `claude logout` trước |
| **Scoring** | Rule-based hand-written + LLM Judge (80/20 hybrid) | **100% LLM Judge** với rubric tự sinh |
| **Rubric** | Hard-coded `docx_rules.py` cho mỗi skill | **Tự sinh** mỗi skill, cache theo hash(SKILL.md) + hash(test_case_ids) |
| **Thêm skill mới** | Viết `<skill>_rules.py` + đăng ký | Chỉ cần thêm test_cases JSON; rubric sinh tự động |
| **Teacher isolation** | Không | Gọi qua `anthropic_env()` context manager để không leak ANTHROPIC_* |

## Cài đặt

Dùng chung conda env `skills` của v1:

```bash
conda activate skills
# deps (anthropic, click, rich, pyyaml, python-dotenv, python-docx) đã có
```

`claude` binary phải nằm trong `$PATH`:

```bash
which claude     # /Users/.../claude
claude --version # 2.x
```

### Biến môi trường

Sửa `.env` ở project root (KHÔNG tạo file riêng trong `distillation_v2/`):

```
OPENROUTER_API_KEY=sk-or-v1-...   # student model qua OpenRouter
ANTHROPIC_KEY=sk-ant-...          # Teacher + Judge + Rubric Generator
```

> **Lưu ý quan trọng**: v2 thiết kế để KHÔNG đụng vào session Claude Code thật
> trên máy bạn. `ANTHROPIC_BASE_URL` và `ANTHROPIC_API_KEY` chỉ được inject vào
> subprocess `claude` qua env dict explicit; parent shell không thay đổi.

## Sử dụng

```bash
cd distillation_v2/

# Smoke test nhanh: 1 round, 1 test case, Claude Code CLI thật
python run.py --skill docx --rounds 1 --test-cases 1 --verbose

# Dry-run: chạy Student + Judge, bỏ Teacher (không rewrite SKILL.md)
python run.py --skill docx --rounds 1 --test-cases 3 --dry-run --verbose

# Full distillation
python run.py --skill docx --rounds 3 --test-cases 10 --verbose

# Ép sinh lại rubric (bỏ cache)
python run.py --skill docx --regenerate-rubric --rounds 1 --test-cases 3

# Resume từ batch cuối cùng đã xong
python run.py --skill docx --resume
```

## Kiến trúc

```
run.py (CLI, click)
    └─> orchestrator.py
         ├─> rubric_generator.generate_rubric()           # 1 lần/skill
         ├─> LLMOnlyJudge(rubric)                          # judge duy nhất
         │
         └── for round in 1..max_rounds:
              └── for batch in chunks(test_cases, batch_size):
                   ├─> claude_code_runner.run_agent()      # sandbox + stream-json
                   │     ├─> Sandbox (env isolation)
                   │     └─> stream_parser → AgentLogger JSONL
                   ├─> judge.score() → EvalResult          # hybrid = llm_only
                   ├─> summarizer.summarize() (v1 reuse)
                   └─> teacher.rewrite() qua anthropic_env()
```

## Cấu trúc file

```
distillation_v2/
├── run.py                 # CLI entry
├── orchestrator.py        # Main loop
├── config.yaml            # Default config
├── runner/
│   ├── sandbox.py         # Subprocess env isolation
│   ├── anthropic_env.py   # Env-swap context manager
│   ├── stream_parser.py   # stream-json → v1 event schema
│   ├── claude_code_runner.py  # Invoke claude CLI
│   └── config.py          # RunConfigV2
├── evaluator/
│   ├── rubric_generator.py  # Auto-generate per-skill rubric
│   └── llm_only_judge.py    # Score via rubric, no rule checks
├── rubrics/               # Cache cho rubric JSON
├── tests/                 # Offline unit tests (48 test)
└── results/               # Output: DD_MM_YYYY/<skill>/round_N/batch_M/
```

## Chạy tests

```bash
cd distillation_v2/
conda run -n skills python -m pytest tests/ -v
# 48 tests: sandbox (16) + stream_parser (12) + rubric_generator (12) + llm_only_judge (8)
```

## Verify env isolation

Sau khi chạy distillation, parent shell KHÔNG được bị pollute:

```bash
echo "$ANTHROPIC_BASE_URL"   # rỗng (hoặc giữ nguyên giá trị trước khi chạy)
echo "$ANTHROPIC_API_KEY"    # giữ nguyên (hoặc rỗng)
```

Nếu bạn đang có `ANTHROPIC_BASE_URL` trỏ tới OpenRouter trong shell của mình,
orchestrator sẽ REFUSE to start — bỏ nó đi trước:

```bash
unset ANTHROPIC_BASE_URL
```

## Files reused từ v1

Import qua `importlib.util` để tránh collision với v2's `evaluator/` package:

- `distillation/summarizer.py` — analyzes failed test cases → key_notes.md
- `distillation/teacher.py` — Claude rewrites SKILL.md
- `distillation/utils.py` — logging + `write_api_call`, `write_eval_detail`
- `distillation/evaluator/base.py` — `EvalResult`, `CheckResult`
- `distillation/evaluator/llm_judge.py` — reuse `_extract_content()` cho PDF/DOCX/XLSX
- `skill_runner/runner/logger.py` — `AgentLogger` ghi JSONL schema v1

## Debug logs

Log JSONL ra cùng schema v1:

```bash
# Stream-json events → JSONL event log (v1-compatible)
distillation_v2/logs/docx_qwen_qwen3-8b_20260417T....jsonl

# Visualize bằng tool v1
python ../distillation/visualize_log.py logs/docx_*.jsonl
```
