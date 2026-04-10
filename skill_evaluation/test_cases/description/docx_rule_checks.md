# Docx Test Case — Rule Checks Reference (Schema v4)

Tài liệu giải thích toàn bộ các field trong `docx.json`, bao gồm ý nghĩa, cách hoạt động, ref tới evaluator, và cách tính điểm.

---

## Kiến trúc tổng quan

### File structure

Một file `.docx` là **ZIP archive** chứa nhiều file XML bên trong:

```
document.docx  (ZIP)
├── word/document.xml           ← toàn bộ nội dung văn bản
├── word/numbering.xml          ← cấu hình danh sách (bullet, số)
├── word/footnotes.xml          ← chú thích cuối trang
├── word/footer1.xml           ← footer
├── word/media/                ← hình ảnh nhúng
├── word/comments.xml          ← comments (nếu có)
└── word/_rels/document.xml.rels ← quan hệ (hyperlink, image)
```

Evaluator giải nén `.docx` vào thư mục tạm, đọc XML, rồi chạy checks.

### Scoring model (Schema v4)

```
hybrid = 0.80 × rule_score + 0.20 × llm_judge_score
```

| Thành phần | Trọng số | Chạy bằng | Phạm vi |
|---|---|---|---|
| `rule_score` | **80%** | `docx_rules.py` — machine | Tất cả checks trong `rule_checks` + `content_checks` |
| `llm_judge_score` | **20%** | `llm_judge.py` — Claude | Off-topic detection + fixture integrity |

### Data model trong JSON

Trong `docx.json`, vẫn giữ **2 dict riêng** (`rule_checks` và `content_checks`) để dễ đọc. Nhưng ở code (`docx_rules.py`), hai dict được **merge thành 1 flat dict** rồi chạy tất cả checks cùng lúc:

```python
all_checks_dict = {**rule_checks, **content_checks}  # merged
checks = self._run_all_checks(output_dir, doc, all_checks_dict)
result.rule_score = _avg(checks)  # 1 avg cho tất cả votes
```

Điều này có nghĩa: mỗi field bất kỳ (dù nằm trong `rule_checks` hay `content_checks`) đều = **1 hoặc nhiều vote**, và `rule_score` = `avg(all votes)`.

### LLM Judge (20%) chỉ còn làm 2 việc

```
LLM Judge nhận: paragraphs (text) + tables (markdown) + image metadata
LLM Judge kiểm tra:
  1. Output có on-topic không (không hallucinate, không đi sai hướng)
  2. Fixture integrity: values_match_fixture, original_text_preserved
LLM Judge KHÔNG còn kiểm tra: keywords, output_format, json_keys, output_is_new_file
```

LLM Judge chạy cho **TẤT CẢ 30 test cases** (không chỉ content_checks). Config `llm_judge_ensemble: 3` trong `config.yaml` (3 Claude calls → lấy median).

---

## Metadata fields (không tính điểm)

| Field | Bắt buộc | Ý nghĩa |
|---|---|---|
| `id` | Có | Định danh duy nhất, ví dụ `tc_a01` |
| `workflow` | Có | `create` / `read` / `edit` / `convert` |
| `name` | Có | Mô tả ngắn test này kiểm tra gì |
| `prompt` | Có | Lệnh chính xác gửi cho student model |
| `expected_behavior` | Có | Mô tả output đúng trông như thế nào |
| `skill_gotcha` | Không | Trỏ đến điểm CRITICAL trong SKILL.md mà test này nhắm vào |
| `fixture_file` | Bắt buộc khi `workflow=read/edit/convert` | File đầu vào |
| `must_have_docx` | Không (default `true`) | Xem Prerequisite Gate bên dưới |

---

## Prerequisite Gate — `must_have_docx`

**Trước khi chạy bất kỳ check nào**, evaluator kiểm tra file output có hợp lệ không.

| Giá trị | Hành vi |
|---|---|
| `true` (mặc định) | File `.docx` phải tồn tại, mở được, và > 1KB. Fail → `rule_score = 0.0` ngay lập tức, bỏ qua mọi check còn lại. |
| `false` | Bỏ qua gate. Dùng khi output **không phải** `.docx` (ví dụ: `tc_b01` → `.md`, `tc_b02` → `.json`). |

**Ref evaluator:** `docx_rules.py:148-166` — `_run_prerequisite_checks()`

**Ví dụ dùng đúng:**
```json
// tc_b01: pandoc extraction → output là .md, không phải .docx
"must_have_docx": false
```

---

## Tất cả checks — `rule_checks` + `content_checks` (MERGED, 80%)

**Quan trọng:** Trong JSON vẫn tách 2 dict để dễ phân loại. Ở code, chúng được gộp và chạy cùng nhau. Mỗi field bên dưới đều = **1 hoặc nhiều vote** trong `rule_score`.

---

### XML Checks — đọc thẳng từ XML bên trong ZIP

---

#### `xml.contains: ["chuỗi1", "chuỗi2"]`

**Ý nghĩa:** Các chuỗi này **phải xuất hiện** trong file XML mục tiêu.

**Cách hoạt động:** Evaluator đọc nội dung file XML thành string, rồi kiểm tra `chuỗi in nội_dung`. Giống `Ctrl+F`. Mỗi chuỗi trong list = **1 vote độc lập**.

**Ref evaluator:** `docx_rules.py:219-226`
```python
for needle in cd.get("xml.contains") or []:
    ok = needle in doc_xml
```

**Ví dụ:**

| Chuỗi cần có | Kiểm tra điều gì | Ref SKILL.md |
|---|---|---|
| `<w:numFmt` `<w:numId` | Model dùng native Word numbering (không dùng bullet unicode) | Lists section |
| `w:type="dxa"` | Table dùng DXA width, không dùng PERCENTAGE | Tables section |
| `w:type="clear"` | Shading dùng `ShadingType.CLEAR`, không dùng SOLID | Tables section |
| `<w:instrText` `TOC` | Có Table of Contents thật sự trong XML | TOC section |
| `<w:pgSz w:w="12240"` | Page size là US Letter (8.5 inch = 12240 DXA) | Page Size section |
| `w:outlineLvl` `w:val="1"` | Có heading outline level cho ToC | Styles section |
| `<w:cols ` `w:num="2"` | Document có 2-column layout qua section properties | Multi-Column section |
| `w:author="Claude"` | Tracked change ghi đúng tên tác giả | Tracked Changes section |
| `<w:ins ` `<w:del ` | Document có tracked insertions và deletions | Tracked Changes section |
| `<wp:inline` `<a:blip r:embed=` | Có image nhúng đúng cách | Images section |

---

#### `xml.absent: ["chuỗi1", "chuỗi2"]`

**Ý nghĩa:** Các chuỗi này **KHÔNG ĐƯỢC xuất hiện** trong XML. Ngược lại `xml.contains`.

**Cách hoạt động:** Nếu chuỗi **không** tìm thấy → pass (1.0). Nếu tìm thấy → fail (0.0). Mỗi chuỗi = 1 vote.

**Ref evaluator:** `docx_rules.py:228-236`
```python
for needle in cd.get("xml.absent") or []:
    ok = needle not in doc_xml
```

**Ví dụ:**

| Chuỗi cấm | Kiểm tra điều gì | Ref SKILL.md |
|---|---|---|
| `•` `&#x2022;` `&#8226;` | Model không chèn bullet ký tự unicode trực tiếp | Lists: `❌ WRONG: new TextRun("• Item")` |
| `w:type="pct"` | Table không dùng PERCENTAGE width | Tables: `WidthType.PERCENTAGE breaks Google Docs` |
| `w:type="solid"` | Shading không dùng SOLID (gây nền đen) | Tables: `ShadingType.CLEAR not SOLID` |
| `<w:br w:type="page\"/></w:body>` | PageBreak không đứng một mình ngoài Paragraph | Page Breaks: `PageBreak must be in Paragraph` |
| `\n` `&#xA;` | Không dùng newline trong TextRun | Text: `Never use \n` |
| `<w:tbl>` (trong footer) | Footer không dùng table | Headers/Footers: `Never use tables in headers/footers` |
| `<w:ins ` `<w:del ` | Accept tracked changes → output không còn tracked change elements | Accept Changes: `output has no w:ins/w:del` |

---

#### `xml.absent_pattern: ["regex1", "regex2"]`

**Ý nghĩa:** Regex pattern này **KHÔNG ĐƯỢC match** trong XML. Mạnh hơn `xml.absent` vì dùng regular expression với `re.DOTALL`.

**Cách hoạt động:** `re.compile(pattern, re.DOTALL).search(doc_xml)`. Nếu match → fail. Không match → pass. Mỗi pattern = 1 vote.

> **QUAN TRỌNG:** Phải là **list** `["pattern"]`, không được là string `"pattern"`. String sẽ bị iterate từng ký tự → bugs hoàn toàn.

**Ref evaluator:** `docx_rules.py:238-249`
```python
for pattern in cd.get("xml.absent_pattern") or []:
    ok = re.compile(pattern, re.DOTALL).search(doc_xml) is None
```

**Ví dụ:**

| Pattern | Kiểm tra điều gì | Ref SKILL.md |
|---|---|---|
| `"<w:r>.*<w:commentRangeStart"` | `<w:commentRangeStart>` không được nằm bên trong `<w:r>` | Comments: `commentRangeStart are siblings of <w:r>, never inside` |

Dùng regex khi cần kiểm tra **quan hệ cấu trúc** giữa các XML tags (lồng nhau hay không), không thể làm bằng chuỗi đơn giản.

---

#### `xml.file: "word/document.xml"`

**Ý nghĩa:** Chỉ định **file XML nào** để `xml.contains`, `xml.absent`, `xml.absent_pattern` target vào. Mặc định: `word/document.xml`.

**Cách dùng — override khi cần:**
```json
"xml.file": "word/numbering.xml"   // kiểm tra cấu hình list
"xml.file": "word/footnotes.xml"   // kiểm tra nội dung footnote
```

**Không tính vote** — chỉ là config cho các check XML khác.

---

#### `xml.footer_contains: ["PAGE", "<w:tab/>"]`

**Ý nghĩa:** Các chuỗi này **phải xuất hiện** trong footer XML. Tương tự `xml.contains` nhưng target là `word/footer*.xml` thay vì document.xml.

**Cách hoạt động:** Evaluator glob tất cả `word/footer*.xml`, nối thành 1 string, rồi tìm kiếm substring. Mỗi chuỗi = 1 vote.

**Ref evaluator:** `docx_rules.py:250-259`
```python
footer_xml = "".join(_read_file(f) for f in tmp_dir.glob("word/footer*.xml"))
for needle in cd["xml.footer_contains"]:
    ok = needle in footer_xml
```

**Ví dụ:**

| Chuỗi cần có trong footer | Kiểm tra điều gì | Ref SKILL.md |
|---|---|---|
| `PAGE` | Footer có page number field | Headers/Footers: `TextRun({ children: [PageNumber.CURRENT] })` |
| `<w:tab/>` | Footer dùng tab stop để canh lề (không dùng table) | Headers/Footers: `use tab stops, not tables` |

---

### File Checks — kiểm tra nội dung ZIP

---

#### `file.must_exist: ["word/footnotes.xml", "word/media/"]`

**Ý nghĩa:** Các đường dẫn này **phải tồn tại** bên trong file `.docx` (ZIP).

**Cách hoạt động:**
- Path thường → file phải tồn tại: `(tmp_dir / path).exists()`
- Path kết thúc bằng `/` → thư mục phải tồn tại **và không rỗng**: `target.is_dir() and any(target.iterdir())`

Mỗi path = 1 vote.

**Ref evaluator:** `docx_rules.py:260-273`

**Ví dụ:**

| Path | Kiểm tra điều gì | Ref SKILL.md |
|---|---|---|
| `word/footnotes.xml` | Model đã tạo footnotes đúng cách (file này chỉ tồn tại khi dùng `footnotes:` trong Document + `FootnoteReferenceRun`) | Footnotes section |
| `word/media/` | Model đã nhúng ảnh thật sự vào ZIP (không chỉ reference) | Images section |
| `word/_rels/document.xml.rels` | File relationships tồn tại (luôn có, dùng để xác nhận ZIP hợp lệ + chứa image hyperlinks) | Images XML Reference |
| `word/comments.xml` | Model đã tạo comments đúng cách | Comments section |

---

### Style Checks

---

#### `style.header_footer: true`

**Ý nghĩa:** Document phải có **header hoặc footer có nội dung** (không rỗng).

**Cách hoạt động:** Duyệt tất cả sections, kiểm tra `section.header` hoặc `section.footer` có paragraph nào có text không — 1 vote.

**Tại sao dùng python-docx thay vì XML tag:** Vì header/footer có thể tồn tại trong XML nhưng trống rỗng (không có text). Tag detection không phân biệt được.

**Ref evaluator:** `docx_rules.py:311-318` — `_check_has_header_footer()`

**Ref SKILL.md:** Headers/Footers section. `new Header({...})` và `new Footer({...})`.

---

### Page Count Checks

---

#### `page.min: N` / `page.max: N`

**Ý nghĩa:** Số trang ước tính phải `>= page.min` và `<= page.max`. Dùng 1 trong 2 hoặc cả 2 — chỉ **1 vote tổng**.

**Cách hoạt động (THỰC SỰ THÔ):**
```python
count = doc.element.body.xml.count('w:type="page"') + 1
```
Đếm số explicit page breaks (`<w:br w:type="page"/>`) trong XML, cộng 1. **Không tính word-wrap hay overflow thật sự.**

**Chỉ chính xác khi** model dùng `new Paragraph({ children: [new PageBreak()] })` để phân trang.

**Ref evaluator:** `docx_rules.py:319-329` — `_check_page_count()`

**Ref SKILL.md:** Page Breaks section.
```javascript
// CRITICAL: PageBreak must be inside a Paragraph
new Paragraph({ children: [new PageBreak()] })
```

---

### Numbering Check

---

#### `numbering_references: 2`

**Ý nghĩa:** Phải có đúng **N** numbering references riêng biệt trong `word/numbering.xml`. 1 vote (exact match).

**Cách hoạt động:** Đọc `numbering.xml`, đếm số `<w:num w:numId="...">` distinct.

**Ref evaluator:** `docx_rules.py:331-342` — `_count_numbering_refs()`

**Ref SKILL.md:** Lists section.
```javascript
// Same reference = continues (1,2,3 then 4,5,6)
// Different reference = restarts (1,2,3 then 1,2,3)
```

Dùng để verify model tạo **2 references độc lập** cho 2 numbered lists bắt đầu từ 1 riêng biệt — không dùng chung 1 reference khiến list 2 bắt đầu từ 4.

---

### Validate Check

---

#### `validate: true`

**Ý nghĩa:** Chạy `scripts/office/validate.py` — file phải **pass hoàn toàn** (exit code 0). 1 vote.

**Cách hoạt động:** Subprocess call với timeout 30s. Exit 0 → pass, exit non-zero → fail.

**Ref evaluator:** `docx_rules.py:344-353` — `_check_validate()`

**Ref SKILL.md:** Validation section.
```bash
python scripts/office/validate.py doc.docx
```

**Khi nào dùng:** Test case phức tạp (nhiều sections, tracked changes, comments). Chậm nhất (~1-2s) nên dùng có chọn lọc.

---

### Filename Check

---

#### `filename: "project_report.docx"`

**Ý nghĩa:** Evaluator tìm file có **đúng tên này** trong output directory trước. Nếu không thấy → fallback sang bất kỳ `.docx` nào.

**Không tính vote** — chỉ là config để evaluator biết tìm file nào.

**Ref evaluator:** `docx_rules.py:204-210`

**Dùng khi:** Prompt yêu cầu model lưu file với tên cụ thể.

---

## Content Checks — rules-based (Schema v4, 80%)

**Tất cả các field bên dưới đã được chuyển sang rules-based** trong `docx_rules.py`. Không còn chạy qua LLM Judge. Mỗi field = **1 hoặc nhiều vote** trong `rule_score`.

---

### `keywords: ["chuỗi1", "chuỗi2"]`

**Ý nghĩa:** Các từ/cụm từ này **phải xuất hiện** trong extracted paragraph text. Mỗi keyword = 1 vote độc lập.

**Cách hoạt động:**
```python
all_text = " ".join(p.text for p in doc.paragraphs)  # paragraphs only
for kw in cd.get("keywords") or []:
    ok = kw in all_text
```

**Lưu ý:** Chỉ kiểm tra paragraph text, không bao gồm table cell text (LLM Judge kiểm tra table content qua markdown extraction).

**Ref evaluator:** `docx_rules.py:358-364`

**Ví dụ:**
```json
// tc_a01: kiểm tra 5 items trong bullet list
"keywords": ["Design", "Develop", "Test", "Deploy", "Monitor"]
// → 5 votes, mỗi keyword tìm thấy = 1.0, không tìm thấy = 0.0
```

---

### `keywords_absent: ["chuỗi1"]`

**Ý nghĩa:** Các từ/cụm từ này **KHÔNG ĐƯỢC xuất hiện** trong extracted paragraph text. Mỗi keyword = 1 vote.

**Ref evaluator:** `docx_rules.py:366-372`

**Ví dụ:**
```json
// tc_c01: sau khi replace 'Company' → 'Acme Corp'
"keywords": ["Acme Corp"],
"keywords_absent": ["Company"]
```

---

### `output_format: "json"`

**Ý nghĩa:** Output directory phải chứa ít nhất 1 file có extension tương ứng. 1 vote.

**Cách hoạt động:**
```python
ok = bool(list(output_dir.rglob(f"*.{fmt}")))
```

**Ref evaluator:** `docx_rules.py:374-380`

**Ví dụ:**

| `output_format` | Dùng khi | Ví dụ |
|---|---|---|
| `"json"` | Đọc table → output JSON | `tc_b02` |
| `"jpg"` | Chuyển docx → images | `tc_d02` |
| `"md"` | Pandoc extraction | `tc_b01` |

---

### `json_keys_from_fixture: true`

**Ý nghĩa:** Keys của JSON output phải khớp với header row của fixture table. 1 vote.

**Cách hoạt động:**
1. Load fixture `.docx` → extract table[0] header cells
2. Load output `.json` → extract keys
3. So sánh: `json_keys == fixture_header_keys` → pass

**Cần:** `fixture_file` phải có trong test case.

**Ref evaluator:** `docx_rules.py:382-402`

**Ví dụ:**
```json
// tc_b02: fixture table có header [Name, Department, Salary]
// Output JSON phải có keys ["Name", "Department", "Salary"]
"fixture_file": "fixtures/simple_report.docx",
"content_checks": {
  "output_format": "json",
  "json_keys_from_fixture": true
}
```

---

### `output_is_new_file: true`

**Ý nghĩa:** Output `.docx` filename phải khác fixture filename. 1 vote.

**Cách hoạt động:**
```python
fixture_name = Path(fixture_file).name
ok = any(f.name != fixture_name for f in output_dir.rglob("*.docx"))
```

**Dùng khi:** Task yêu cầu tạo file mới, không phải sửa fixture gốc. Ví dụ: `tc_b03` (đọc rồi tạo summary doc mới).

**Ref evaluator:** `docx_rules.py:404-411`

---

## LLM Judge — Semantic Checks (20%)

LLM Judge nhận output đã extract và chạy Claude để đánh giá:

```
_extract_docx output:
  ├── paragraphs → [Title] text, [Normal] text với style
  ├── tables     → markdown table lines
  ├── headers/footers → [Header-0] / [Footer-0] lines
  └── images     → [IMAGE] format=png, size=2500 bytes, rId=rId10
```

### 2 fields vẫn còn qua LLM Judge

| Field | Mô tả |
|---|---|
| `values_match_fixture` | Computed values phải khớp fixture (không hallucinate số) |
| `original_text_preserved` | Tất cả text gốc còn nguyên sau edit |

**Ref evaluator:** `llm_judge.py` — `_extract_checklist()`, `_build_judge_prompt()`

### Phần còn lại — LLM Judge làm off-topic detection

LLM Judge không kiểm tra keywords hay output_format nữa. Thay vào đó, nó kiểm tra:

```
1. Output có on-topic không (đúng yêu cầu trong prompt)
2. Fixture integrity:
   - Computed values match fixture data (values_match_fixture)
   - All original text preserved (original_text_preserved)
3. fixture_verdict: PASS | FAIL | N/A
```

### Cấu hình

```yaml
# config.yaml
llm_judge_ensemble: 3     # 3 Claude calls → lấy median (default)
llm_judge_weight: 0.20   # trọng số LLM Judge trong hybrid
```

Set `llm_judge_ensemble: 1` trong config để tiết kiệm chi phí khi test.

---

## `workflow_checks` — Process checks (không tính điểm)

Chỉ **ghi log** để debug, không ảnh hưởng `rule_score` hay `hybrid_score`. Score cố định `0.5` (informational).

| Field | Ý nghĩa | Ví dụ |
|---|---|---|
| `tool` | Tool nào phải được dùng trong workflow | `"pandoc"`, `"comment.py"`, `"accept_changes.py"`, `"soffice.py"` |
| `steps` | Các bước workflow theo thứ tự | `["unpack.py", "str_replace", "pack.py --original"]` |

**Ref evaluator:** `docx_rules.py:416-429` — `_run_workflow_checks()`

---

## Cách tính điểm — Tóm tắt

```
hybrid_score = 0.80 × rule_score + 0.20 × llm_judge_score
```

### Bước 1 — Prerequisite Gate

```
must_have_docx = true:
  File không tồn tại?  → rule_score = 0.0  (dừng luôn)
  File corrupt?         → rule_score = 0.0  (dừng luôn)
  File < 1KB?          → rule_score = 0.0  (dừng luôn)
  → OK → chạy tiếp bước 2

must_have_docx = false:
  → Bỏ qua gate, chạy tiếp bước 2 luôn
```

### Bước 2 — Tất cả votes (rule_checks + content_checks merged)

```
rule_score = avg(TẤT CẢ votes)

Vote đầu tiên (luôn có): no_placeholders
  → Không được có "[INSERT", "[YOUR ", "[NAME]", "TBD", "TODO" trong text

Rồi mới đến tất cả fields đã khai báo:
  xml.contains           → 1 vote / chuỗi
  xml.absent             → 1 vote / chuỗi
  xml.absent_pattern     → 1 vote / pattern
  xml.footer_contains    → 1 vote / chuỗi
  file.must_exist        → 1 vote / path
  style.header_footer    → 1 vote
  page.min/max           → 1 vote (tổng)
  numbering_references   → 1 vote
  validate               → 1 vote
  ── content_checks (giờ rules-based) ──
  keywords               → 1 vote / keyword
  keywords_absent        → 1 vote / keyword
  output_format          → 1 vote
  json_keys_from_fixture → 1 vote
  output_is_new_file     → 1 vote
```

### Bước 3 — rule_score

```
rule_score = sum(votes_passed) / sum(votes_total)

Ví dụ tc_a01 (bullet list):
  no_placeholders  ✓  → 1/1
  xml_has:w:numFmt ✓  → 1/1
  xml_has:w:numId  ✓  → 1/1
  xml_has:w:numPr  ✓  → 1/1
  xml_absent:•      ✓  → 1/1
  xml_absent:&#x2022 ✓ → 1/1
  xml_absent:&#8226  ✓ → 1/1
  keyword:Design    ✓  → 1/1
  keyword:Develop   ✓  → 1/1
  keyword:Test      ✓  → 1/1
  keyword:Deploy    ✓  → 1/1
  keyword:Monitor   ✓  → 1/1
  = 12/12 votes = rule_score 1.0

Ví dụ tc_c01 (replace Company → Acme Corp):
  no_placeholders  ✓  → 1/1
  validate          ✓  → 1/1
  keyword:Acme Corp ✓  → 1/1
  kw_absent:Company ✓  → 1/1
  = 4/4 votes = rule_score 1.0
```

### Bước 4 — Hybrid Score

```
hybrid = 0.80 × rule_score + 0.20 × llm_judge_score

LLM Judge chỉ chạy khi rule_score > 0 (không chạy khi file không tồn tại)

Ví dụ:
  rule_score = 0.83, llm_judge_score = 0.90
  hybrid = 0.80×0.83 + 0.20×0.90 = 0.664 + 0.180 = 0.844
```

### Stopping criteria (distillation/config.yaml)

```
stop_threshold: 0.80   → dừng khi avg hybrid >= 0.80
converge_delta: 0.02  → dừng sau 3 rounds cải thiện < 0.02
max_rounds: 10         → hard cap
llm_judge_ensemble: 3 → 3 Claude calls/test case (set 1 để tiết kiệm)
```

---

## Schema v4 vs v3 — Thay đổi chính

| Thay đổi | v3 (cũ) | v4 (mới) |
|---|---|---|
| hybrid weights | `0.40 × rule + 0.60 × llm` | `0.80 × rule + 0.20 × llm` |
| `content_checks.keywords` | LLM Judge (60%) | **Rules-based** (80%) |
| `content_checks.output_format` | LLM Judge | **Rules-based** |
| `content_checks.json_keys` | LLM Judge | **Rules-based** |
| `content_checks.output_is_new_file` | LLM Judge | **Rules-based** |
| `content_checks.values_match_fixture` | LLM Judge | **LLM Judge (20%)** |
| `content_checks.original_text_preserved` | LLM Judge | **LLM Judge (20%)** |
| `style.table` | python-docx DOM | **`xml.contains: ["<w:tbl>"]`** |
| `style.toc` | python-docx DOM | **`xml.contains: ["<w:instrText", "TOC"]`** |
| `style.list` | python-docx DOM | **`xml.contains: ["<w:numPr"]`** |
| `style.heading_levels` | python-docx DOM | **`xml.contains: ["w:outlineLvl"]`** |
| LLM Judge image handling | base64 image blob | **Image metadata (format, size, rId)** |
| Data model in JSON | 2 dicts riêng | 2 dicts riêng (đọc dễ), **gộp ở code** |

---

## Quick reference — khi nào dùng field nào

| Muốn kiểm tra... | Dùng field |
|---|---|
| Model dùng đúng XML tag/attribute | `xml.contains` |
| Model không dùng cách bị cấm | `xml.absent` |
| Cấu trúc lồng nhau trong XML | `xml.absent_pattern` |
| Nội dung trong footer | `xml.footer_contains` |
| File phụ được tạo (footnotes, media, comments) | `file.must_exist` |
| Header/footer có nội dung (không trống) | `style.header_footer` |
| Số trang (chỉ khi dùng explicit PageBreak) | `page.min` / `page.max` |
| Hai list numbered độc lập | `numbering_references` |
| File XML hợp lệ hoàn toàn | `validate` |
| Tên file output cụ thể | `filename` |
| Output không phải .docx | `must_have_docx: false` |
| Từ khoá có trong nội dung paragraph | `keywords` |
| Từ khoá KHÔNG có trong nội dung | `keywords_absent` |
| Output có đúng extension file | `output_format` |
| JSON keys khớp fixture table headers | `json_keys_from_fixture` |
| Output là file mới, không phải fixture | `output_is_new_file` |
| Giá trị tính toán đúng fixture (semantic) | `values_match_fixture` (LLM Judge 20%) |
| Text gốc còn nguyên sau edit (semantic) | `original_text_preserved` (LLM Judge 20%) |
| Model có đi đúng hướng, không hallucinate | LLM Judge 20% (off-topic detection) |
| Quy trình đúng (pandoc, unpack...) | `workflow_checks.tool/steps` |
