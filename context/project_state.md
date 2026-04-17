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

**30 test cases** — bỏ tc_a13 (hyperlinks, quá phức tạp) và tc_c07 (tracked para deletion, 0/3 rounds)

**Scoring hiện tại:**
```
prerequisite gate (must_have_docx) → avg(all checks) = rule_score
hybrid = 0.80 × rule_score + 0.20 × llm_judge_score
LLM judge chỉ chạy khi rule_score > 0
Weights configurable qua config.yaml: llm_judge_weight (default 0.20)
```

**Cấu trúc 5 nhóm (30 cases):**
- **A — Create (12 tests):** tc_a01–tc_a12 (bỏ tc_a13)
- **B — Read (4 tests):** tc_b01–tc_b04. `must_have_docx: false` cho tc_b01/b02/b04
  - tc_b01: thêm `search_output_files: true` → keyword check đọc .md output thay vì doc.paragraphs
- **C — Edit (7 tests):** tc_c01–tc_c06, tc_c08 (bỏ tc_c07)
  - tc_c05: bỏ keyword check (comment text không trong document.xml), chỉ giữ `file.must_exist: ["word/comments.xml"]`
- **D — Convert (2 tests):** tc_d01 (.doc→.docx), tc_d02 (→images)
- **E — Edge/Regression (5 tests):** tc_e01–tc_e05

**Fixtures hiện có** (`distillation/test_cases/fixtures/`):
- `simple_report.docx`, `contract_draft.docx`, `tracked_review.docx`
- `newsletter_raw.docx`, `data_table.docx`, `legacy_document.doc`
- `tracked_deletion_review.docx` ✅ đã tạo (3 tracked deletions by Jane)

## Kết quả distillation 11_04_2026 (3 rounds, 32 test cases)

| Round | Avg hybrid | Ghi chú |
|-------|-----------|---------|
| R1 | 0.448 | baseline |
| R2 | 0.391 | **regression** — Teacher over-rewrote SKILL.md |
| R3 | 0.473 | phục hồi một phần |

**Per-group best score:**
- A (Create): 0.687, 10/12 passing
- B (Read): 0.353, 2/4 — tc_b01 luôn fail do keyword check sai (fixed)
- C (Edit): 0.488, 3/7 — tc_c05 luôn 0.60 do check sai (fixed)
- D (Convert): 0.685, 1/2
- E (Edge): 0.603, 3/5

**⚠️ Nguyên nhân gốc rễ: SKILL.md mismatch (đã fix)**
- Lúc chạy 11_04: `skill_runner/skills/docx/SKILL.md` là version **python-docx** (Python)
- `docx.json` test cases viết cho **docx-js** (Node.js) → fundamental mismatch
- **Đã fix**: `skill_runner/skills/` đã sync toàn bộ skills mới từ `anthropic_skills/` → docx SKILL.md giờ là docx-js
- Kết quả 11_04 không phản ánh đúng tiềm năng thực tế vì chạy với SKILL.md sai

**Nguyên nhân thất bại cụ thể:**
1. `validate_passes` fail → model dùng python-docx generate sai OOXML structure (không phải docx-js)
2. Numbered list: model dùng python-docx style thay vì `LevelFormat.BULLET` + `<w:numPr>`
3. TOC: model không dùng `HeadingLevel` enum của docx-js → thiếu `<w:instrText>`
4. tc_b01: keyword check đọc sai nguồn (fixed session 15_04)
5. tc_c05: keyword check sai kỹ thuật (comment text ≠ document.xml) (fixed session 15_04)

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

## Bugs đã fix (session 2026-04-15)

### distillation/teacher.py
29. **Retry 529 OverloadedError** — delays [3, 6, 15]s, tổng 4 lần thử trước khi raise.
    Catch `anthropic.APIStatusError` với `status_code == 529`, các lỗi khác raise ngay.

### distillation/evaluator/docx_rules.py
30. **`_extract_all_text()`** — method mới. Khi `doc is None` hoặc `search_output_files=True`:
    fallback đọc text từ `.md`, `.txt`, `.json` files trong output_dir.
    `_run_content_checks` dùng method này thay vì `"..." if doc else ""`.

### distillation/test_cases/docx.json
31. **Bỏ tc_a13** (hyperlinks + bookmarks — 0/3 rounds, quá phức tạp)
32. **Bỏ tc_c07** (tracked paragraph deletion — 0/3 rounds)
33. **tc_b01** — thêm `"search_output_files": true` trong `content_checks`
34. **tc_c05** — bỏ keyword check, giữ chỉ `file.must_exist: ["word/comments.xml"]`

### requirements (python-docx thiếu)
35. **pyproject.toml** — thêm `python-docx>=1.1.0` vào `dependencies`
36. **requirements.sh** — thêm `pip install python-docx>=1.1.0`
37. **skill_runner/requirements.txt** — thêm `python-docx>=1.1.0`

### skill_runner/runner/agent_loop.py (session 15_04)
38. **`_trim_messages()`** — trim message history, giữ 4 turns gần nhất, tóm tắt turns cũ.
    Giảm token O(n²) → O(1) cho long-running agent loops.
39. **`r'"command"\s*:\s*"'`** — fix SyntaxWarning `\s` trong regular string.

### distillation/evaluator/docx_rules.py (session 15_04)
40. **validate error output** — tăng từ 200 → 800 chars để Teacher thấy full XSD error.

### distillation/run.py (session 15_04)
41. **results_dir date bug** — compute dated `results_dir` TRƯỚC khi gọi `setup_logging()`.
    Trước: api_calls.jsonl/eval_detail.jsonl ghi vào `results/docx/`, không phải `results/DD_MM/docx/`.

## distillation_v2/ (NEW — 2026-04-17, end-to-end verified)

Pipeline song song, KHÔNG xoá v1. Xem chi tiết: [distillation_v2.md](distillation_v2.md).

**Khác biệt vs v1:**
- Student: `skill_runner/` → **Claude Code CLI** (`claude -p --output-format stream-json`) trỏ tới OpenRouter qua `ANTHROPIC_BASE_URL`.
- Evaluator: rule-based `docx_rules.py` → **LLM-only judge** với rubric **tự sinh** per-skill (cache theo hash SKILL.md + tc_ids).
- Sandbox: subprocess + env dict explicit + fresh HOME, KHÔNG leak `ANTHROPIC_BASE_URL` ra parent shell.
- Teacher isolation: gọi qua `anthropic_env()` context manager.
- Reuse v1 modules (summarizer, teacher, utils, evaluator.base, llm_judge._extract_content) qua `importlib.util` by path (tránh namespace collision).

**Tests**: 48/48 pass offline (sandbox 16, stream_parser 12, rubric 12, judge 8).

**Smoke live 2026-04-17**: 1 round × 1 tc với `--dry-run` — rubric sinh 7 criteria, Claude Code chạy qwen3-8b 41s, judge score 0.21, parent env không leak.

## Cần làm tiếp

1. ✅ Fixture `tracked_deletion_review.docx` đã tạo
2. ✅ Kết quả 11_04 đã phân tích, bugs đã fix
3. Chạy lại pipeline v1 với 30 test cases sau fix: `python run.py --skill docx --verbose`
4. Theo dõi xem tc_b01, tc_c05 có cải thiện không
5. **v2**: test Teacher loop (bỏ `--dry-run`) để verify không leak env qua rewrite call
6. **v2**: so sánh v1 vs v2 trên cùng test set cho thesis writeup
