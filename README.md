# Skill Distillation for Small Large Language Models via Skill Definition Optimization
## Chắt lọc Kỹ năng cho Mô hình Ngôn ngữ Lớn Nhỏ thông qua Tối ưu Định nghĩa Kỹ năng


**Đề tài Đồ án Tốt nghiệp** • **2026**

---

## Tóm tắt

Đề tài này đề xuất phương pháp **Skill Distillation** (Chưng cất Kỹ năng), sử dụng large model (Teacher) để tự động viết lại file `SKILL.md`, kết hợp với Hybrid Evaluator (Rule-based + LLM Judge), giúp các small model hoặc model khác có thể thực thi được các Agent Skills vốn chỉ hoạt động tốt trên Claude. Toàn bộ quá trình **không cần train, không cần fine-tune** — chỉ cần tối ưu hóa phần mô tả skill mà thôi.

---

## 1. Bối Cảnh

### 1.1. Định nghĩa Skill

Anthropic định nghĩa Skill như một đơn vị hướng dẫn — một file `SKILL.md` mô tả cho model biết: tool này làm gì, khi nào dùng, cần input gì, output trông như thế nào. Model đọc vào → hiểu → thực thi đúng.

Các Skill này được viết và tối ưu hóa cho Claude (Opus, Sonnet). Khi đưa sang model khác — đặc biệt là các small models chỉ có vài tỷ tham số — hiệu quả giảm đáng kể.

### 1.2. Vấn đề cụ thể

| Model | Skill gốc | Kết quả |
|-------|-----------|---------|
| Claude Sonnet/Opus | SKILL.md gốc | ✅ Thực thi đúng |
| Qwen3-8B | SKILL.md gốc | ❌ Gọi sai tool |
| Qwen3.5-4B | SKILL.md gốc | ❌ Điền sai parameter |
| Phi-4-mini-instruct | SKILL.md gốc | ❌ Không biết khi nào dùng |

### 1.3. Nguyên nhân gốc rễ

1. **Skill quá verbose** — model nhỏ bị overwhelm, không extract được thông tin quan trọng
2. **Skill giả định prior knowledge của Claude** — format, cách diễn đạt không tổng quát
3. **Thiếu few-shot examples** — model nhỏ cần ví dụ cụ thể hơn để hiểu cách dùng tool

### 1.4. Câu hỏi nghiên cứu

> Liệu có thể tự động optimize một Skill definition từ large model sang small/other model mà không cần retraining model đó không? Và một Skill đã optimize có mang tính portable — dùng được trên nhiều model không?

---

## 2. Đối Tượng Hướng Đến

| Đối tượng | Vấn đề họ gặp | Lợi ích nhận được |
|-----------|---------------|-------------------|
| Developer xây AI Agent | Muốn dùng model rẻ/nhỏ nhưng vẫn cần chạy được complex skills | Skill tối ưu sẵn cho model nhỏ |
| Researcher LLM Agent | Cần benchmark skill portability across models | Bộ dataset + metric chuẩn hóa |
| Startup AI | Không đủ budget dùng Claude/GPT-4 toàn bộ pipeline | Giảm 60-70% chi phí inference |

---

## 3. Giải Pháp — Skill Distillation

### 3.1. Ẩn dụ cốt lõi

| Ẩn dụ | Thực thể trong hệ thống |
|-------|-------------------------|
| Người thợ xịn | Teacher LLM (Claude Haiku 4.6) |
| Học việc | Student Model (Qwen3-8B, Qwen3.5-4B, Phi-4-mini-instruct) |
| Hướng dẫn làm việc | SKILL.md |
| Bài thử việc | Test tasks (30-50 cases) |
| Đánh giá kết quả | Hybrid Evaluator |

Người thợ không dạy trực tiếp — người thợ viết lại hướng dẫn sao cho học việc đọc vào tự làm được. Nếu học việc làm sai → người thợ sửa lại hướng dẫn → thử lại. Lặp đến khi đúng.

**Điểm quan trọng nhất: Không đụng vào model. Không train. Không fine-tune.** Chỉ thay đổi cách nói chuyện với model đó thông qua tối ưu SKILL.md.

### 3.2. So sánh với DSPy

| Tiêu chí | DSPy | Skill Distillation |
|----------|------|---------------------|
| Focus | Tune prompt cho một task cụ thể | Tune Skill definition cho một model cụ thể |
| Input | Prompt A bất kỳ | SKILL.md / MCP tool description |
| Output | Prompt A* tối ưu hơn | SKILL.md tối ưu — portable, tái sử dụng được |
| Domain | General | Agent / Tool-use specific |
| Granularity | Task-level | Skill-level (tổng quát hơn) |

---

## 4. Kiến Trúc Hệ Thống

### 4.1. Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────────┐
│                    Skill Distillation Pipeline                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │  Skill DB   │───▶│   Target     │───▶│   Skill Analyzer    │ │
│  │ (JSON/MD)   │    │ Model Profile│    │                     │ │
│  └─────────────┘    └─────────────┘    └──────────┬──────────┘ │
│                                                     │            │
│                                                     ▼            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Student   │◀───│   RAG       │◀───│   Teacher LLM       │ │
│  │   Model     │    │  Retriever  │    │   (Rewriter)        │ │
│  └──────┬──────┘    └─────────────┘    └─────────────────────┘ │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Hybrid    │───▶│  Validator  │───▶│  Optimized SKILL.md │ │
│  │  Evaluator  │    │             │    │                     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | Component | Vai trò |
|-------|-----------|---------|
| Input | Skill DB (JSON/Markdown) | Lưu Skill gốc chuẩn hóa |
| Input | Target Model Profile | Thông tin về model nhỏ: context size, weaknesses, format |
| Processing | Skill Analyzer | Phân tích Skill gốc, xác định core intent |
| Processing | RAG Retriever | Query Example DB lấy 3-5 ví dụ liên quan |
| Processing | Teacher LLM (Rewriter) | Rewrite SKILL.md phù hợp target model |
| Processing | Validator | Kiểm tra skill mới có đủ thông tin không |
| Execution | Student Model | Chạy task với skill mới (local via Ollama) |
| Evaluation | Hybrid Evaluator | Chấm điểm output của Student |
| Output | Optimized SKILL.md | File hướng dẫn tối ưu cho target model |

### 4.2. Hybrid Evaluator — Chi tiết

Đây là thành phần quan trọng nhất, gồm 2 lớp kết hợp:

#### Lớp 1 — Rule-based (nhanh, miễn phí)
- Rules được Teacher LLM tự động generate từ Skill gốc (không viết tay)
- Kiểm tra các điều kiện cứng: đúng tool name? có params không? format đúng không?
- Output: Pass / Fail — nếu Fail thì score = 0, không gọi LLM Judge

#### Lớp 2 — LLM Judge (chỉ kích hoạt khi pass Rule check)
- Nhận: task gốc + SKILL.md + output của Student
- Chấm điểm 0-10 theo rubric: chọn đúng tool, params hợp lý, follow workflow đúng không
- Trả về JSON: `{ score, reason }` — reason dùng để Teacher hiểu cần sửa gì

#### Công thức tính điểm cuối

```
Final Score = (Rule Score × 0.4) + (LLM Judge Score × 0.6)
```

- Nếu Rule check Fail → Final Score = 0 (skip LLM Judge để tiết kiệm API call)
- Nếu Rule check Pass → gọi LLM Judge, tính theo công thức trên

### 4.3. So sánh 3 approach

| Tiêu chí | Rule-based | LLM Judge | Hybrid ✅ |
|----------|------------|-----------|-----------|
| Chi phí | Gần 0 | Cao (API call) | Trung bình |
| Tốc độ | Rất nhanh | Chậm | Nhanh |
| Độ chính xác | Cứng nhắc | Linh hoạt | Tốt nhất |
| Handle semantic | ❌ | ✅ | ✅ |
| Explainable | ✅ (rules rõ) | ✅ (có reason) | ✅✅ |
| Phù hợp MVP | ✅ | ⚠️ | ✅✅ |

---

## 5. Vòng Lặp Optimization

Trái tim của hệ thống là **Optimization Loop**:

```
SKILL.md (v0) → Student chạy → Hybrid Evaluator chấm → Teacher nhận feedback → rewrite SKILL.md (v1) → lặp lại → đến khi score đủ tốt → output SKILL.md (v_best)
```

### 5.1. Các bước trong mỗi iteration

| Bước | Thực thể | Hành động |
|------|----------|-----------|
| 1 | System | Inject SKILL.md (v_n) vào system prompt của Student |
| 2 | Student Model | Chạy 30 test tasks, sinh ra tool call outputs |
| 3 | Rule-based | Check nhanh từng output — Pass/Fail |
| 4 | LLM Judge | Chấm điểm semantic cho output đã Pass Rule |
| 5 | Aggregator | Tính Final Score tổng thể cho version này |
| 6 | Teacher LLM | Nhận score + reasons → phân tích điểm yếu → rewrite Skill |
| 7 | System | Lưu SKILL.md (v_n+1) → quay lại bước 1 |

---

## 6. Pipeline End-to-End

| Giai đoạn | Việc làm | Output |
|-----------|----------|--------|
| 1. Setup | Thu thập 3-5 SKILL.md gốc, chuẩn hóa sang JSON schema | Skill DB |
| 2. Example DB | Viết tay 30-50 (task, tool_call) pairs, embed vào ChromaDB | Vector DB |
| 3. Baseline | Student + Skill gốc, đo success rate trên 30 test cases | Baseline score ~30% |
| 4. Distillation | Teacher rewrite Skill, RAG inject 3 examples, sinh 5-10 versions | Skill v1...v10 |
| 5. Evaluate | Hybrid Evaluator chấm từng version, chọn version tốt nhất | Best skill version |
| 6. Iterate | Phân tích lỗi, điều chỉnh Teacher prompt, thêm RAG few-shot, chạy lại | Skill v_best |
| 7. Final Eval | So sánh Skill gốc vs Skill distilled trên full test suite | Kết quả ~65-75% |
| 8. Report | Vẽ bảng so sánh, phân tích định tính, viết báo cáo | Paper / Báo cáo |

---

## 7. Tech Stack

| Layer | Công nghệ | Mục đích |
|-------|-----------|-----------|
| Teacher LLM | Claude Haiku 4.6 | Rewrite Skill, generate rules, LLM Judge |
| Student Model | Qwen3-8B, Qwen3.5-4B, Phi-4-mini-instruct | Chạy local via Ollama, miễn phí |
| Skill Format | JSON / Markdown chuẩn hóa | Schema thống nhất cho mọi Skills |
| Vector DB | ChromaDB hoặc FAISS | Lưu và query few-shot examples |
| RAG Engine | LangChain / LlamaIndex | Retrieve examples liên quan |
| Inference | Ollama hoặc HuggingFace Transformers | Chạy student model local |
| Orchestration | Python custom scripts | Điều phối toàn bộ pipeline |
| Experiment tracking | MLflow hoặc W&B (optional) | Theo dõi metrics qua các iterations |

---

## 8. MVP vs Nice-to-have

### 8.1. MVP — Làm trong 6-8 tuần

**Scope của MVP:**
- 2-3 Skills dạng tool-call đơn giản: web search, file reader, calculator
- 3 Student models: Qwen3-8B, Qwen3.5-4B, Phi-4-mini-instruct
- Evaluator: Hybrid (Rule-based auto-gen + LLM Judge)
- Optimization loop: Teacher rewrite → test → iterate
- Output: SKILL.md v_best cho từng target model

### 8.2. Phân loại tính năng

| Tính năng | Loại | Lý do |
|-----------|------|-------|
| Optimization loop cơ bản | ✅ MVP | Core contribution của đề tài |
| Hybrid Evaluator | ✅ MVP | Cần thiết để vòng lặp hoạt động |
| 2-3 Skills tool-call đơn giản | ✅ MVP | Đủ để chứng minh concept |
| 3 student models (Qwen3-8B, Qwen3.5-4B, Phi-4-mini) | ✅ MVP | Đủ để baseline + so sánh |
| RAG few-shot examples | ✅ MVP | Tăng chất lượng distillation đáng kể |
| Cross-model testing (nhiều student) | ✅ MVP | So sánh hiệu quả giữa các model |
| Auto pipeline không cần can thiệp tay | ⏳ Nice-to-have | Nếu còn thời gian |
| Multimodal skills (PPTX, PDF...) | ❌ Out of scope | Cần domain expertise để evaluate |
| Fine-tuning model | ❌ Out of scope | Không phải hướng của đề tài |
| Production deployment | ❌ Out of scope | Đồ án tốt nghiệp, không cần production |

---

## 9. Cấu Trúc Dự Án

```
skill_distillation/
├── README.md                    # File này
├── .gitignore                   # Git ignore
├── requirements.sh              # Script cài đặt môi trường
│
├── skill_evaluation/            # Module đánh giá skill
│   ├── run_eval.py              # Evaluation runner
│   ├── visualize_log.py         # Trực quan hóa log
│   ├── test_cases/              # Thư mục test cases
│   │   ├── web-artifacts-builder.json
│   │   ├── pdf.json
│   │   ├── pptx.json
│   │   ├── docx.json
│   │   ├── algorithmic-art.json
│   │   └── ... (17 skills test cases)
│   │
│   ├── logs/                    # Output log đánh giá
│   │   └── (auto-generated)
│   │
│   └── output/                  # Output và ví dụ skill
│       ├── skills/              # Định nghĩa skill mẫu
│       │   ├── api-testing-monitor/
│       │   │   └── SKILL.md
│       │   ├── data-formatter/
│       │   │   └── SKILL.md
│       │   └── my-first-skill/
│       │       └── SKILL.md
│       │
│       ├── utils_mcp_server.py  # MCP server implementation
│       ├── sqlite_mcp_server.py # SQLite MCP
│       ├── github_mcp_server.py # GitHub MCP
│       └── ... (various MCP servers & tools)
│
└── docs/                        # Tài liệu (mở rộng tùy chọn)
```

---

## 10. Bắt Đầu Nhanh

### 10.1. Yêu cầu môi trường

- Python 3.10+
- Claude CLI (`npm install -g @anthropic-ai/claude`)
- Ollama (để chạy small model local)

### 10.2. Cài đặt

```bash
# Clone project
git clone <repo-url>
cd skill_distillation

# Cài đặt dependencies
bash requirements.sh

# Hoặc cài thủ công
pip install -r skill_evaluation/output/requirements.txt
```

### 10.3. Chạy đánh giá

```bash
# Liệt kê tất cả skills có sẵn
python skill_evaluation/run_eval.py --list

# Đánh giá tất cả skills với model mặc định
python skill_evaluation/run_eval.py

# Đánh giá với các student models cụ thể
python skill_evaluation/run_eval.py --model qwen3-8B
python skill_evaluation/run_eval.py --model qwen3.5-4B
python skill_evaluation/run_eval.py --model phi-4-mini

# Đánh giá skill cụ thể với model cụ thể
python skill_evaluation/run_eval.py --skill web-artifacts-builder --model qwen3-8B

# Chế độ verbose
python skill_evaluation/run_eval.py --verbose
```

---

## 11. Expected Results

| Metric | Skill gốc (Baseline) | Skill Distilled (Target) |
|--------|---------------------|--------------------------|
| Tool-call success rate | ~30-40% | ~65-75% |
| Parameter accuracy | ~40% | ~70% |
| Token count (skill length) | ~800 tokens | ~300 tokens |
| Latency (per inference) | Cao (context dài) | Thấp hơn 30-40% |
| API cost per eval run | Baseline | Giảm 60-70% (nhờ Hybrid Evaluator) |

---

## 12. Rủi Ro & Cách Xử Lý

| Rủi ro | Xác suất | Cách xử lý |
|--------|----------|------------|
| Student model quá yếu, dù distill tốt vẫn fail | Trung bình | Chọn model có instruction-following tốt hơn (Qwen3-8B thay vì model nhỏ hơn) |
| Skill quá đơn giản sau distill → mất thông tin quan trọng | Cao | Validator check information completeness trước khi test |
| LLM Judge không nhất quán (non-deterministic) | Cao | Chạy mỗi case 3 lần, lấy majority vote |
| Test cases không đủ diverse | Trung bình | Thiết kế test cases cover nhiều tình huống khác nhau từ đầu |
| Teacher LLM tốn nhiều tiền API | Thấp | Hybrid Evaluator giảm 60-70% calls, teacher chỉ gọi khi cần iterate |

---

## 13. Đóng Góp Của Đề Tài

| Layer | Đóng góp | Ý nghĩa |
|-------|----------|---------|
| Concept | "Skill" như một unit độc lập, portable, không phụ thuộc model | New framing chưa được nghiên cứu rõ ràng |
| Dataset | Bộ Skill definitions chuẩn hóa dạng JSON + ví dụ kèm theo | Tái sử dụng được cho nghiên cứu sau |
| Pipeline | Hệ thống tự động optimize Skill từ model A → model B | Không cần train, không cần fine-tune |
| Evaluator | Hybrid Evaluator: Rule-based (auto-gen) + LLM Judge | Vừa rẻ vừa accurate, explainable |
| Benchmark | Metric đo Skill portability across models | Chuẩn đánh giá mới cho Agent Skills |

### Điểm khác biệt với DSPy

DSPy optimize prompt để model nhỏ bắt chước OUTPUT của model lớn.

Đề tài này optimize SKILL DEFINITION để model nhỏ hiểu đúng CÔNG CỤ mình có và dùng được — không dạy nó làm giỏi hơn, dạy nó biết mình có gì và dùng đúng cách.

---

## 14. License

MIT License

---

## 15. Tham Khảo

- [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) - Qwen3 8B Model
- [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) - Qwen3.5 4B Model
- [Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) - Microsoft Phi-4 Mini
- Anthropic Skills Documentation
- DSPy: Declarative Programming for Language Models
- Ollama: Run LLMs locally
- ChromaDB: Vector database for AI applications
