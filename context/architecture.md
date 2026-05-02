---
name: Architecture Decisions
description: Kiến trúc hệ thống và các quyết định thiết kế quan trọng
type: project
---

## Cấu trúc repo
```
skill_distillation/
├── skill_runner/           # Agent executor — OpenRouter API cho Student SLM (dùng bởi v1)
├── skill_evaluation/       # Test harness (run_eval.py chạy trực tiếp, không qua distillation)
├── distillation/           # v1 pipeline — rule-based evaluator + LLM Judge hybrid
│   ├── config.yaml
│   ├── test_cases/         # docx.json schema v4, fixtures/, description/
│   ├── evaluator/          # base.py, docx_rules.py, llm_judge.py
│   ├── orchestrator.py, summarizer.py, teacher.py, run.py
├── distillation_v2/        # v2 pipeline — Claude Code CLI + LLM-only judge (standalone)
│   ├── config.yaml, run.py, pipeline.py
│   ├── stages/             # student.py, teacher.py, judge.py, rubric_gen.py, summarizer.py
│   ├── runner/             # sandbox.py, anthropic_env.py, stream_parser.py, config.py, logger.py
│   ├── evaluator/          # base.py (EvalResult, CheckResult)
│   ├── utils/              # rollback.py, __init__.py (logging, write_api_call)
│   ├── rubrics/            # cached rubric JSON per (skill, SKILL.md hash, tc_ids hash)
│   └── tests/              # 63 passing, 1 skipped
├── docs/                   # Đề cương + phân tích
├── context/                # MEMORY.md + per-topic context markdown
└── .env                    # ANTHROPIC_KEY + OPENROUTER_API_KEY
```

Chi tiết v2: xem [distillation_v2.md](distillation_v2.md).

## API mapping
| Component | API | Key env var |
|---|---|---|
| Student model (Qwen3-8B) | OpenRouter | `OPENROUTER_API_KEY` |
| Teacher LLM (Claude Haiku) | Anthropic SDK | `ANTHROPIC_KEY` |
| LLM Judge (Claude Haiku) | Anthropic SDK | `ANTHROPIC_KEY` |

⚠️ Env var là `OPENROUTER_API_KEY` (không phải `OPENROUTER_AI_KEY`). `.env` phải load trước check.

## Evaluator design (schema v4 — đã thống nhất)

### Scoring model
```
Step 1: Prerequisite gate (must_have_docx)
  True  → file phải exist, parseable, > 1KB. Fail → rule_score = 0.0
  False → skip gate (read-only output như .md/.json)

Step 2: Format checks
  Mỗi field trong rule_checks = 1+ checks (0.0 hoặc 1.0)
  Vote đầu tiên: no_placeholders (chỉ chạy khi doc is not None)

Step 3: rule_score = avg(all checks)
  _avg([]) = 0.0  ← (đã fix, trước đây = 1.0 gây tc_b04 tự nhận full score)

Step 4: hybrid = rule_weight × rule_score + llm_weight × llm_judge_score
  Mặc định: rule_weight=0.80, llm_weight=0.20
  Configurable qua config.yaml: llm_judge_weight (default 0.20)
  LLM judge chỉ chạy khi rule_score > 0
```

### rule_checks fields (machine-verified → rule_score 80%)
| Field | Vote count | Cơ chế |
|---|---|---|
| `xml.contains: ["str1", "str2"]` | 1/chuỗi | substring search trong target XML |
| `xml.absent: ["str"]` | 1/chuỗi | substring NOT in XML |
| `xml.absent_pattern: ["regex"]` | 1/pattern | regex re.DOTALL NOT match — **phải là list** |
| `xml.file: "word/X.xml"` | 0 (config) | override target XML file |
| `xml.footer_contains: ["str"]` | 1/chuỗi | substring trong word/footer*.xml |
| `file.must_exist: ["path/"]` | 1/path | path trong ZIP; trailing "/" = dir non-empty |
| `validate: true` | 1 | scripts/office/validate.py exit 0 (~1-2s, dùng có chọn lọc) |
| `filename: "name.docx"` | 0 (config) | evaluator ưu tiên tìm file này |
| `style.table/toc/header_footer/list` | 1 each | python-docx DOM check |
| `style.heading_levels: [1, 2]` | 1/cấp | paragraph style == "Heading N" |
| `page.min / page.max` | 1 tổng | đếm `<w:br w:type="page"/>` + 1 (crude) |
| `numbering_references: N` | 1 | distinct w:numId trong numbering.xml |

### content_checks fields (semantic → LLM Judge 20%)
`keywords`, `keywords_absent`, `output_format`, `json_keys_from_fixture`,
`output_is_new_file`, `original_text_preserved`, `values_match_fixture`

- `values_match_fixture` → hiện implement là gate check: output file tồn tại không (numeric verify chưa làm)
- `original_text_preserved` → sample ≤5 phrases từ fixture docx, tìm trong output text

### workflow_checks (informational — NOT in score)
`tool`, `steps` — score cố định 0.5. `_run_workflow_checks()` luôn return `passed=True, score=0.5`.
**Quyết định:** KHÔNG implement actual checking vì signal không giúp ích cho Teacher và log matching có bug cũ.

## Test case schema v4
```json
{
  "id": "tc_a01",
  "workflow": "create|read|edit|convert",
  "must_have_docx": true,        // false cho read-only output
  "fixture_file": "fixtures/x.docx",
  "skill_gotcha": "SKILL.md CRITICAL: ...",
  "name": "Short description",
  "prompt": "...",
  "expected_behavior": "...",
  "rule_checks": {
    "xml.contains": ["<w:numFmt"],
    "xml.absent": ["•", "&#x2022;"],
    "xml.absent_pattern": ["<w:r>.*<w:commentRangeStart"],  // list, không phải string
    "xml.file": "word/document.xml",
    "xml.footer_contains": ["PAGE", "<w:tab/>"],
    "file.must_exist": ["word/footnotes.xml", "word/media/"],
    "validate": true,
    "filename": "report.docx",
    "style.table": true,
    "style.toc": true,
    "style.header_footer": true,
    "style.list": true,
    "style.heading_levels": [1, 2],
    "page.min": 2,
    "page.max": 5,
    "numbering_references": 2
  },
  "content_checks": { "keywords": ["Design"], "output_format": "json" },
  "workflow_checks": { "tool": "pandoc", "steps": ["unpack.py", "pack.py"] }
}
```
_comment objects trong array → filter bằng `if "id" in tc`.

## Distillation batch loop
```
Round N:
  Split test_cases → batches (batch_size từ config.yaml hoặc -b CLI)
  For each batch:
    Run student → Score → Summarize → Teacher → Update SKILL.md
  avg_score = avg(hybrid_score) — dùng hybrid_score, KHÔNG phải rule_score
  Check stopping criteria
  round_key_notes_history tích lũy → Teacher nhận 2 rounds gần nhất
```
SKILL.md cập nhật progressive trong round — batch sau hưởng lợi từ batch trước.

## Config priority
```
CLI flag → config.yaml → hardcoded fallback
```

## config.yaml structure (distillation section)
```yaml
distillation:
  student_model: qwen/qwen3-8b
  teacher_model: claude-haiku-4-5
  max_rounds: 3
  batch_size: 5
  stop_threshold: 0.7
  results_dir: "./results"          # date tự động append trong code (DD_MM_YYYY)
  use_llm_judge: true
  llm_judge_ensemble: 3
  llm_judge_weight: 0.20            # ← PHẢI nằm trong distillation: section
```

## Stopping criteria (config.yaml)
- `stop_threshold: 0.7` — dừng khi avg **hybrid_score** ≥ 0.7
- `converge_delta: 0.02` + `converge_k: 3`
- `max_rounds: 10`

## Workspace persistence
Giữ lại: `_skills/`, `.npm/`, `node_modules/`, `package.json`, `package-lock.json`, `Library/`
Copy sang output_dir: exclude toàn bộ trên.

## Tools available trong agent loop
`bash`, `read_file`, `write_file`, `list_directory`, `end_turn`
**str_replace đã bị xóa hoàn toàn** — gây infinite loop với small model, là dead code.

## Text extraction cho content checks

`_run_content_checks` dùng `_extract_all_text(output_dir, doc, cd)`:

```python
# Nếu doc exists VÀ không có search_output_files → đọc doc.paragraphs (python-docx)
# Nếu doc is None HOẶC search_output_files=True → fallback đọc .md/.txt/.json từ output_dir
```

Dùng `search_output_files: true` trong `content_checks` khi workflow output không phải .docx (pandoc → .md):
```json
"content_checks": { "keywords": ["..."], "search_output_files": true }
```

## python-docx usage trong evaluator

python-docx dùng cho:
- `doc.paragraphs[i].text` — keyword check, no_placeholders check
- `doc.sections[i].header/footer` — style.header_footer check

XML/ZIP checks (`xml.contains`, `xml.absent`, `validate`, ...) dùng `zipfile` trực tiếp, KHÔNG qua python-docx.

**Dependencies:** `python-docx>=1.1.0` — đã thêm vào pyproject.toml, requirements.sh, skill_runner/requirements.txt.

## SKILL.md version — docx-js (đã đồng bộ)

`skill_runner/skills/docx/SKILL.md` đã được cập nhật sang **docx-js** (Node.js) — đồng bộ với `anthropic_skills/skills/docx/`.
`distillation/test_cases/docx.json` cũng viết cho docx-js → không còn mismatch.

Toàn bộ skills trong `skill_runner/skills/` đã được cập nhật với version mới từ `anthropic_skills/`.

⚠️ Kết quả 11_04_2026 chạy với version python-docx cũ → scores thấp một phần do mismatch này, không phản ánh đúng khả năng thực tế của pipeline.

## Fixture handling

`orchestrator.py` copy `fixture_file` vào workspace và inject path vào prompt (đã implement).
Evaluator dùng `fixture_file` cho: `original_text_preserved`, `json_keys_from_fixture`, `output_is_new_file`.

## Teacher retry logic

`teacher.py` retry 529 OverloadedError với delays [3, 6, 15]s (tổng 4 lần).
Chỉ catch `status_code == 529` — lỗi khác raise ngay.

## Skill tiers
- Tier 1 (auto eval): slack-gif-creator, xlsx, docx
- Tier 2 (exit code): webapp-testing
- Tier 3 (human eval): frontend-design, algorithmic-art
