---
name: Feedback & Corrections
description: Các feedback, correction và preference từ user khi build
type: feedback
---

## Workspace cleanup
Giữ lại `.npm/`, `node_modules/`, `package.json`, `package-lock.json`, `Library/` giữa các runs.
**Why:** tránh reinstall npm mỗi run, tiết kiệm ~30s/run.
**How to apply:** luôn check `_WORKSPACE_PERSISTENT` và `_OUTPUT_EXCLUDE` khi thêm exclude mới.

## Rule-based không nên check content thresholds
Không dùng `min_paragraphs`, `min_word_count` trong rule-based evaluator.
**Why:** task có thể yêu cầu 1 câu, 1 trang — threshold arbitrary là sai.
**How to apply:** rule-based = format only; content adequacy = LLM Judge's job.

## LLM Judge cần context đủ
LLM Judge phải nhận structured checklist từ `prompt` + `expected_behavior`, không chỉ raw text.
Nếu test case có `skill_gotcha` → inject vào judge prompt.
**Why:** score thấp vì Judge không biết technical rule nào đang được test.
**How to apply:** build `_extract_checklist()` + check `skill_gotcha` field.

## Teacher dùng Anthropic SDK, không dùng CLI subprocess
**Why:** `ANTHROPIC_KEY` đã verify hoạt động, SDK sạch hơn subprocess.
**How to apply:** import `anthropic`, load `ANTHROPIC_KEY` từ `.env` root.

## Logging với timestamp + file
Orchestrator nên emit() ra cả stdout và `results/<skill>/run.log` đồng thời, line-buffered.
**Why:** user muốn `tail -f` theo dõi tiến trình trong terminal khác.
**How to apply:** mở file log với `buffering=1`, dùng hàm `emit()` thay `print()`.

## Test case structural checks dùng explicit fields
`rule_checks` object phải explicit (không scan keywords trong `expected_behavior`).
**Why:** keyword scan brittle, false positive/negative. Explicit field chính xác hơn.
**How to apply:** khi viết test case mới, luôn điền `rule_checks` rõ ràng.

## Hybrid weights 80/20 cho docx (configurable)
Rule-based 80%, LLM Judge 20% cho docx.
**Why:** rule_checks trong docx schema v4 là ground truth (binary XML checks). LLM judge chỉ bổ sung semantic signal.
**How to apply:** `llm_judge_weight: 0.20` trong `distillation:` section của config.yaml.

## v2: không đụng vào session Claude Code thật của user
Sandbox cho Claude Code CLI PHẢI dùng `subprocess.Popen(env=sandbox.env)` với dict EXPLICIT — KHÔNG bao giờ `os.environ.copy()`.
**Why:** user đang dùng Claude Code thật với tài khoản Anthropic cá nhân trên cùng máy. Leak `ANTHROPIC_BASE_URL=openrouter` sẽ route Claude Code thật vào OpenRouter → hỏng session và có thể tốn credit sai nơi.
**How to apply:** `Sandbox._build_env()` chỉ whitelist PATH/HOME/TERM/LANG + ANTHROPIC_*. Pre-flight guard từ chối start nếu parent env đã có `ANTHROPIC_BASE_URL ~ openrouter`. Integration test assert parent env không đổi sau khi chạy.

## v2: không xoá v1 — song song codebase
Tạo `distillation_v2/` sibling với `distillation/`, không nested.
**Why:** thesis cần so sánh side-by-side; v2 rủi ro cao (CLI schema drift, rubric quality chưa verify); dễ rollback nếu abandon.
**How to apply:** import v1 modules qua `importlib.util.spec_from_file_location` thay vì copy code. Pre-register shim trong `sys.modules` khi v1 internals có collision tên (vd `evaluator.base`).
Weights tự động tính: `rule_weight = 1 - llm_judge_weight`. Configurable per run qua code, không hardcode.
⚠️ Trước đây từng là 40/60 (thesis spec cũ) — đã đổi và xác nhận 80/20 là đúng.

## Batch size trong distillation
Dùng `config.yaml` cho project-level defaults, CLI flag để override.
**Why:** SKILL.md cải thiện progressive trong round thay vì chờ cả round xong.

## xml.absent_pattern phải là list, không phải string
`xml.absent_pattern` trong rule_checks phải luôn là `["pattern"]`, không bao giờ `"pattern"`.
**Why:** evaluator dùng `for pattern in value` — string bị iterate từng ký tự → 31 votes sai hoàn toàn.
**How to apply:** khi viết test case mới, luôn bọc pattern trong `[]`.

## must_have_docx: false cho workflow read-only
Tất cả test case có workflow `read` hoặc `convert` mà output KHÔNG phải `.docx` phải có `must_have_docx: false`.
**Why:** không có `must_have_docx: false` → prerequisite gate tìm không thấy .docx → rule_score=0 → LLM judge không chạy → hybrid luôn 0.
**How to apply:** tc_b01, tc_b02, tc_b04, tc_d02 và các test tương tự luôn cần flag này.

## Phân biệt xml.contains vs style.* checks
- `xml.contains` → verify **exact format / API usage** (attribute values, specific tags)
- `style.*` → verify **sự tồn tại** của element (có table không, có list không...)
**How to apply:** dùng cả hai khi cần (tc_a03: xml.contains ["<w:instrText"] + style.toc).
Không dùng style.* khi cần kiểm tra attribute value cụ thể → dùng xml.contains.

## validate: true — dùng có chọn lọc
Chỉ thêm `validate: true` cho test case phức tạp (sections, tracked changes, comments, images).
Không cần cho test chỉ check 1-2 attribute đơn giản.
**Why:** validate.py chậm ~1-2s/file, chạy với 32 test cases × nhiều rounds = tốn kém.
**How to apply:** mặc định không có validate; thêm khi test có complex XML structure.

## str_replace tool đã bị xóa hoàn toàn — không tái tạo
`str_replace` đã bị remove khỏi tool_executor.py, tool_definitions.py, và file str_replace.py đã delete.
**Why:** user test thực tế thấy tool này gây infinite loop với small model (qwen3-8b).
**How to apply:** không define lại str_replace trong bất kỳ context nào. Agent chỉ dùng: bash, read_file, write_file, list_directory, end_turn.

## workflow_checks KHÔNG implement actual checking
`_run_workflow_checks()` chỉ return `passed=True, score=0.5` — không check gì cả.
**Why:** signal không giúp ích cho Teacher (tool usage information), và log matching approach cũ có bug.
**How to apply:** workflow_checks trong docx.json chỉ có giá trị tài liệu hóa. Không implement thêm.

## Stopping criterion và avg_score phải dùng hybrid_score
Tất cả avg_score, pass_count, convergence check trong orchestrator và summarizer phải dùng `hybrid_score`, KHÔNG phải `rule_score`.
**Why:** stopping criterion nhất quán với metric thực tế được report. Rule_score và hybrid_score có thể diverge đáng kể.
**How to apply:** luôn dùng `result.hybrid_score` khi aggregate scores.

## load_dotenv phải gọi trước khi check env vars
`run.py` phải có `load_dotenv(Path(__file__).parent.parent / ".env")` ở đầu file, trước mọi `os.environ.get()`.
**Why:** không có load_dotenv → `.env` không được đọc → key luôn báo MISSING dù file tồn tại.
**How to apply:** pattern chuẩn: `load_dotenv` ở top-level module scope, không trong function.

## results_dir không hardcode ngày
`config.yaml` chỉ lưu base path `"./results"`. Code tự append `DD_MM_YYYY`.
**Why:** hardcode ngày trong config phải sửa tay mỗi ngày.
**How to apply:** `results_dir = str(Path(_base_results) / _dt.now().strftime("%d_%m_%Y"))` trong run.py.
⚠️ Phải compute dated path TRƯỚC khi gọi `setup_logging()` — nếu không api_calls.jsonl ghi sai thư mục.

## keyword check cho non-docx output (workflow read)
Khi workflow output là .md/.txt (pandoc), KHÔNG dùng keyword check đơn thuần — `doc=None` → `all_text=""` → luôn fail.
**Why:** `doc.paragraphs` chỉ đọc được .docx, không đọc .md output.
**How to apply:** thêm `"search_output_files": true` trong `content_checks` → evaluator fallback đọc .md/.txt/.json.

## check comment text bằng file.must_exist, không phải keyword
Comment text trong docx nằm trong `word/comments.xml`, KHÔNG phải `document.xml`.
**Why:** `doc.paragraphs` chỉ parse body text, không parse comments.xml — keyword check luôn fail.
**How to apply:** dùng `"file.must_exist": ["word/comments.xml"]` thay vì keyword để verify comment đã được tạo.

## Teacher retry delays cho 529
Retry delays cho 529 OverloadedError: **[3, 6, 15]s** — không dùng 30/60/120s (quá dài không cần thiết).
**Why:** 529 overloaded thường chỉ cần vài giây, không phải hàng phút.
**How to apply:** `delays = [3, 6, 15]` trong `_call_api`, catch `anthropic.APIStatusError` với `status_code == 529`.

## Test cases phải match SKILL.md technology
`docx.json` test cases viết cho **docx-js** (Node.js). SKILL.md dùng trong pipeline phải là docx-js version (`~/.claude/skills/docx/`), KHÔNG phải python-docx version.
**Why:** mismatch gây ra toàn bộ kết quả sai — model học python-docx API nhưng bị evaluate bằng docx-js XML structure.
**How to apply:** `skills_dir` default trong pipeline.py trỏ tới `~/.claude/skills`. Trước khi chạy skill mới, verify test cases và SKILL.md cùng technology stack.

## Test case quality over quantity
Bỏ test case nếu: 0/3 rounds pass VÀ yêu cầu kỹ năng quá advanced cho SLM 8B.
**Why:** test case không bao giờ pass = không có signal cho Teacher = lãng phí token và thời gian.
**How to apply:** sau mỗi 3 rounds, review test cases có hybrid=0.0 xuyên suốt → cân nhắc bỏ hoặc đơn giản hóa.

## v2: skill injection dùng shutil.copytree, không copy từng file
Copy cả folder `skill_dir/` → `sandbox_home/.claude/skills/<skill_name>/`.
**Why:** Claude Code CLI đọc skills từ `~/.claude/skills/<name>/` (cả folder), không phải `~/.claude/commands/<name>.md`.
**How to apply:** `shutil.copytree(skill_dir, claude_dir / "skills" / skill_name, dirs_exist_ok=True)`.

## v2: settings.json bắt buộc để tránh haiku/sonnet charges
Inject `{"model": "<student_model>"}` vào `sandbox_home/.claude/settings.json` trước mỗi run.
**Why:** Claude Code CLI dùng haiku/sonnet cho auto-compaction mặc định. Khi `ANTHROPIC_BASE_URL=openrouter`, tất cả internal calls đều route qua OpenRouter → tốn tiền không mong muốn.
**How to apply:** `_install_skill_in_sandbox()` luôn ghi settings.json khi model được pass.

## v2: teacher prompt không được có ±% length constraint
Không dùng "shorter by ±20%" hay guard 80% trong pipeline.
**Why:** small model dễ hiểu nhầm "shorter is better" thành cắt bớt nội dung quan trọng. Guard 80% cũng block teacher cải thiện skill bằng cách tái cấu trúc ngắn gọn hơn.
**How to apply:** teacher system prompt chỉ nói "shorter is acceptable if it improves clarity" — không số cụ thể. Pipeline.py không reject output dựa trên độ dài.

## conda env cho tests
Dùng `conda run -n skills pytest ...` để chạy tests trong project này.
**Why:** python3 global là 3.14, không có pytest. Env `skills` có đầy đủ dependencies.
**How to apply:** `conda run -n skills pytest distillation_v2/tests/ -v`

## Temperature: không về 0, giữ chút creativity
Teacher=0.3, Judge=0.2 — không dùng temperature=0.
**Why:** Judge=0 ok về mặt determinism nhưng Anthropic API không accept 0 chính xác trên một số model. Teacher=0 làm mất khả năng explore fix mới (overfits vào pattern đã biết). 0.3 là điểm cân bằng.
**How to apply:** `teacher_temperature=0.3`, `judge_temperature=0.2` trong config.yaml / run_distillation() params.

## Parallel=5 là mặc định hợp lý cho production runs
`--parallel 5` tốt cho API rate limit của OpenRouter với gemma-4-26b.
**Why:** sequential (=1) quá chậm; parallel=10+ có thể hit rate limit. 5 là sweet spot.
**How to apply:** `--parallel 5` khi chạy production. Default config giữ `parallel=1` để an toàn.

## Test cases: cắt xuống 20-25 khi có redundancy
Khi một skill có >25 TCs và nhiều cái test cùng pattern → cắt bớt.
**Why:** token tốn kém, mỗi TC thêm ~68K base tokens. 20 TCs coverage tốt + tiết kiệm.
**How to apply:** giữ TCs có workflow khác nhau và edge cases quan trọng. Xóa duplicates cùng workflow type.
Đã cắt: internal-comms (33→25), slack-gif-creator/xlsx/webapp-testing (30→20).

## Gate 1 rollback: dùng rank 6-8 TCs, không phải top-6
Validation TCs phải là TCs THỨ 6, 7, 8 (index 5:8 sorted desc) — không phải top-6.
**Why:** top-5 TCs thường ceiling ở 1.0 → baseline=1.0 → Gate 1 pass threshold quá cao → false negatives. Bottom TCs luôn fail → không sensitive. Rank 6-8 là "borderline" → nhạy cảm với SKILL.md quality.
**How to apply:** `choose_validation_tcs` select `ranked[5:8]`, baseline từ cùng round (không phải round trước).

## Gate 2: so sánh với round gần nhất, không phải round tốt nhất
Gate 2 check `round_avg < prev_avg - threshold` — dùng round ngay trước, không phải best round.
**Why:** so sánh với best round quá strict (score dao động tự nhiên). So sánh với prev round detect regression tức thời tốt hơn.
**How to apply:** `gate2_delta = round_avg - prev_avg`. Threshold=0.10.

## best_skill_snapshot là SKILL_round_{N-1}.md không phải SKILL_round_N.md
Khi round N đạt best score, snapshot restore phải là `SKILL_round_{N-1}.md` (cái TCs đã chạy với), không phải `SKILL_round_N.md` (Teacher output của round N).
**Why:** `SKILL_round_N.md` là Teacher rewrite chưa được verify bởi batches. `SKILL_round_{N-1}.md` là version đã produce best score thực tế.
**How to apply:** `best_skill_snapshot = results_path / f"SKILL_round_{round_n - 1}.md"` (đã fix 09/05).
