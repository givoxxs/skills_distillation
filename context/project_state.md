---
name: Project State — Skill Distillation Pipeline
description: Trạng thái build hiện tại, những gì đã xong, những gì còn thiếu
type: project
---

## Đã hoàn thành

### skill_runner/ (COMPLETE)
- `config.py` — `output_dir: str | None`, `input_files: list[str]`
- `runner/agent_loop.py` — `_collect_output_files()`, `_WORKSPACE_PERSISTENT`, `_OUTPUT_EXCLUDE`
- `runner/logger.py` — `AgentLogger` có `__enter__`/`__exit__`/`__del__` (context manager + safety net)
- `main.py` — `--output-dir`, `--input` CLI flags; imports rich.Console/Panel/Table đúng chỗ

### distillation/ (COMPLETE — pipeline chạy được end-to-end)
```
distillation/
├── run.py              # CLI: --skill, -r, -n, -b, --student, --teacher,
│                       #       --no-llm-judge, --dry-run, -v, --runner-verbose, --resume
│                       # Auto-append ngày vào results_dir (DD_MM_YYYY)
├── config.yaml         # Defaults: student=qwen3-8b, teacher=haiku-4-5,
│                       #   batch_size=5, stop_threshold=0.7, max_rounds=3
│                       # llm_judge_weight=0.20 (LIVE — được đọc và wire vào evaluator)
├── orchestrator.py     # Batch loop: fixture copy → run → score → summarize → Teacher
│                       # avg_score dùng hybrid_score (đã fix)
│                       # log_paths lấy từ run_result["log_file"] (đã fix)
│                       # round_key_notes_history: tích lũy key_notes truyền cho Teacher
├── summarizer.py       # JSONL logs → key_notes; avg_score/pass_count dùng hybrid_score
├── teacher.py          # Anthropic SDK → rewrite SKILL.md
│                       # Nhận round_history (2 rounds gần nhất) để không revert fix cũ
├── test_cases/         # ← ĐÃ MOVE từ skill_evaluation/test_cases/ vào đây
│   ├── docx.json       # Schema v4, 32 test cases
│   ├── fixtures/       # 6 fixture files (thiếu tracked_deletion_review.docx)
│   └── description/
├── evaluator/
│   ├── base.py         # EvalResult — hybrid_score property, _rule_weight/_llm_weight
│   ├── docx_rules.py   # DocxEvaluator — schema v4, weights từ config
│   │                   # _avg([]) = 0.0 (đã fix, không còn 1.0)
│   │                   # values_match_fixture: gate check output file exists
│   │                   # original_text_preserved: sample phrases từ fixture
│   └── llm_judge.py    # LLMJudge — ensemble, median scoring
└── results/            # SKILL_round_N.md, round_N/batch_M/scores.json, summary.json
```

### Test cases docx — Schema v4 (distillation/test_cases/docx.json)

**32 test cases** (filter `_comment` objects bằng `if "id" in tc`)

**Scoring hiện tại:**
```
prerequisite gate (must_have_docx) → avg(all checks) = rule_score
hybrid = 0.80 × rule_score + 0.20 × llm_judge_score
LLM judge chỉ chạy khi rule_score > 0
Weights configurable qua config.yaml: llm_judge_weight (default 0.20)
```

**Cấu trúc 5 nhóm (32 cases):**
- **A — Create (13 tests):** tc_a01–tc_a13. Mỗi test target 1 CRITICAL rule SKILL.md
- **B — Read (4 tests):** tc_b01–tc_b04. `must_have_docx: false` cho tc_b01/b02/b04
- **C — Edit (8 tests):** tc_c01–tc_c08. Tracked changes, comments, restore deletions
- **D — Convert (2 tests):** tc_d01 (.doc→.docx), tc_d02 (→images)
- **E — Edge/Regression (5 tests):** tc_e01–tc_e05

**Fixtures hiện có** (`distillation/test_cases/fixtures/`):
- `simple_report.docx`, `contract_draft.docx`, `tracked_review.docx`
- `newsletter_raw.docx`, `data_table.docx`, `legacy_document.doc`
- ⚠️ **MISSING**: `tracked_deletion_review.docx` (cần cho tc_c08)

## Bugs đã fix (session 2026-04-11)

### distillation/evaluator/docx_rules.py
1. **`_avg([]) = 1.0 → 0.0`** — tc_b04 không còn tự động nhận score 1.0
2. **`values_match_fixture` implement** — gate check output file exists
3. **`original_text_preserved` implement** — sample phrases từ fixture kiểm tra trong output
4. **`DocxEvaluator._rule_weight/_llm_weight` class attrs** — resume có thể đọc đúng weights
5. **`result._rule_weight/llm_weight`** — dùng `self._rule_weight` thay vì hardcode 0.80/0.20
6. **`llm_judge_weight` từ config** — `__init__` nhận param, tính `1 - llm_judge_weight`

### distillation/orchestrator.py
7. **`avg_score` dùng `hybrid_score`** — stopping criterion nhất quán
8. **`prev_avg` dùng `hybrid_score`** — convergence check đúng
9. **`_save_batch_scores` avg dùng `hybrid_score`**
10. **Resume restore weights** — `_rule_weight/_llm_weight` từ evaluator class attr
11. **`_find_latest_log` xóa** — dùng `run_result["log_file"]` thay thế
12. **`round_key_notes_history`** — tích lũy key_notes, truyền vào Teacher
13. **`test_cases_dir` path** — dùng `Path(__file__).parent / "test_cases"` thay path cũ

### distillation/summarizer.py
14. **`avg_score` + `pass_count` dùng `hybrid_score`**
15. **`prev_avg` dùng `hybrid_score`**

### distillation/teacher.py
16. **`round_history` param** — thêm section "Previous Round Error Analyses" vào prompt
17. Truncate mỗi history entry 800 chars, lấy tối đa 2 rounds gần nhất

### distillation/run.py
18. **`load_dotenv`** — thêm ở đầu file (trước đây không có → key luôn MISSING)
19. **`OPENROUTER_AI_KEY` → `OPENROUTER_API_KEY`** trong log check
20. **`llm_judge_weight`** — đọc từ config, truyền vào `run_distillation()`
21. **`results_dir` auto-date** — append `DD_MM_YYYY` tự động
22. **test_cases default path** — `Path(__file__).parent / "test_cases"`

### skill_runner/runner/logger.py
23. **`AgentLogger.__enter__/__exit__/__del__`** — đóng file handle đúng cách khi exception

### skill_runner/runner/tool_executor.py + tool_definitions.py
24. **`str_replace` xóa hoàn toàn** — gây infinite loop với small model, dead code

### distillation/config.yaml
25. **`llm_judge_weight` move** — từ `logging:` sang `distillation:` section (đúng chỗ)
26. **`results_dir`** — đổi về `"./results"` (ngày tự động thêm trong code)

### Cấu trúc
27. **`skill_evaluation/test_cases/` → `distillation/test_cases/`** — hợp lý hơn về tổ chức
28. **`skill_evaluation/run_eval.py`** — update `TEST_CASES_DIR` path

## Known Issues còn lại

### ✅ tracked_deletion_review.docx — ĐÃ TẠO (session 2026-04-11)
`tc_c08` fixture tạo bằng `make_tracked_deletion_review.py` (trong cùng thư mục fixtures/).
3 paragraphs, mỗi cái có 1 `<w:del w:author="Jane">` với delText: "March 15th", "attached budget proposal", "are required to".

### 🟡 workflow_checks không thực sự check gì
`_run_workflow_checks()` luôn trả về `passed=True, score=0.5` — chỉ là documentation.
Quyết định: **không implement** vì signal không giúp ích cho Teacher và log matching có bug cũ.

## Cần làm tiếp

1. ✅ Fixture `tracked_deletion_review.docx` đã tạo (3 tracked deletions by Jane)
2. Chạy full pipeline: `cd distillation && python run.py --skill docx --rounds 3 --verbose`
3. Phân tích kết quả baseline với schema v4 + 32 test cases
4. Nâng cấp evaluator cho xlsx, slack-gif-creator (nếu cần)
