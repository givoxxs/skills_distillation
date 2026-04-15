# Phân tích Đề Cương ĐATN — Skill Distillation
> Phan Văn Toàn (102220129) — ĐH Bách Khoa Đà Nẵng, 2025–2026
> Người hướng dẫn: TS. Phạm Minh Tuấn

---

## 1. Tóm tắt Ý tưởng

Đề tài đặt ra một câu hỏi cụ thể và thực tế:

> **"Liệu có thể thu hẹp khoảng cách năng lực giữa Small Language Model (SLM) và Large Language Model (LLM) trong bối cảnh agentic tool call, mà không cần fine-tuning?"**

Câu trả lời được đề xuất là **Skill Distillation** — thay vì nén kiến thức vào trọng số mô hình (như Knowledge Distillation truyền thống), đề tài coi file `SKILL.md` (hướng dẫn kỹ năng cho agent) như một **biến tối ưu hóa**. Một Teacher LLM (Claude Haiku) tự động phân tích lỗi của Student SLM, rồi viết lại `SKILL.md` tốt hơn theo từng vòng lặp phản hồi.

**Hai sản phẩm kỹ thuật chính:**

| Thành phần | Vai trò |
|---|---|
| `skill_runner` | Framework Python OSS để bất kỳ LLM nào chạy Anthropic Skills qua agentic loop có sandbox |
| Skill Distillation Pipeline | Vòng lặp Teacher→Student→Evaluator tự động cải thiện SKILL.md |

---

## 2. Điểm mạnh của Ý tưởng

### 2.1. Tính mới và rõ ràng
- Phân biệt sắc nét với Knowledge Distillation truyền thống: **không chạm vào trọng số**, không cần GPU, không cần dữ liệu huấn luyện.
- Coi `SKILL.md` như một *hyperparameter có thể tối ưu hóa* là một framing sáng tạo, rõ ràng, và dễ kiểm chứng thực nghiệm.

### 2.2. Khả năng tái tạo và mở rộng
- Toàn bộ pipeline chạy qua API — không cần phần cứng đặc biệt.
- `skill_runner` được thiết kế độc lập, có thể reuse cho bất kỳ nghiên cứu nào muốn benchmark SLM trên Anthropic Skills.
- Metric SPI (Skill Portability Index) và MSG (Model Skill Gap) là các chỉ số **có thể tái sử dụng** cho các nghiên cứu sau.

### 2.3. Cấu trúc đánh giá nghiêm túc
- Phân tầng kỹ năng (3 tầng) giúp tách biệt auto-eval khỏi human-eval một cách hợp lý.
- Hybrid Evaluator (rule-based 40% + LLM Judge 40% + Human Eval 20%) là thiết kế cân bằng giữa chi phí và độ tin cậy.
- Human Eval blind với Krippendorff's alpha cho Tầng 3 — đây là mức độ nghiêm túc hiếm thấy ở ĐATN cấp cử nhân.

### 2.4. Phạm vi vừa đủ
- 6 skills, ≥160 test cases, ≥5 vòng lặp/skill — đủ để có kết quả thống kê có ý nghĩa mà không bị overscope.
- Thời gian 10 tuần với lịch tuần rõ ràng, sản phẩm từng tuần cụ thể — khả thi.

---

## 3. Điểm cần chú ý / Rủi ro tiềm ẩn

### 3.1. Vòng lặp Teacher có thực sự hội tụ không?
- Stopping criterion định nghĩa rõ (θ_abs = 0.80, Δ < 0.02 trong 3 vòng liên tiếp, max 10 vòng), nhưng **chưa có phân tích lý thuyết hay pilot experiment** để biết Teacher có xu hướng lặp lại lỗi hay không.
- Rủi ro: Teacher "đoán mò" thay vì suy luận từ lỗi cụ thể nếu key-notes summary không đủ thông tin.

**Gợi ý:** Chạy 1–2 vòng pilot trên skill đơn giản nhất (xlsx hoặc docx) trước khi lock thiết kế Teacher Summarization.

### 3.2. LLM Judge có bias không?
- Sử dụng Claude Haiku làm cả Teacher lẫn LLM Judge — có nguy cơ **self-confirmation bias**: Teacher viết SKILL.md theo style mà chính Haiku Judge đánh giá cao, không phải theo hướng SLM thực sự cần.
- Phiên bản v7 đề cập "ensemble N lần → trung vị" nhưng chưa nói rõ N và cách kiểm tra inter-rater agreement cho LLM Judge.

**Gợi ý:** Thử dùng model khác cho LLM Judge (GPT-4o-mini, Gemini Flash) ít nhất một subset để kiểm tra independence.

### 3.3. Human Eval Tầng 3 là bottleneck
- ≥3 người đánh giá × ≥20 cases × 2 skills × ≥5 vòng = **ít nhất 600 lần đánh giá thủ công**.
- Nếu chạy distillation loop song song với Human Eval (như đề cương nói) thì cần đảm bảo người đánh giá không nhận quá nhiều việc cùng lúc.

**Gợi ý:** Giới hạn Human Eval chỉ ở vòng đầu (baseline) và vòng cuối (sau distillation), không mỗi vòng — vẫn đủ để đo delta.

### 3.4. Hai mô hình Student chưa được phân biệt rõ vai trò
- Qwen3-8B là "primary", Qwen3.5-4B là "portability test" — nhưng SPI được tính thế nào nếu SKILL.md tối ưu cho Qwen3-8B lại không tốt hơn cho Qwen3.5-4B?
- Nếu SPI thấp, có nghĩa là distillation overfit vào một model cụ thể — điều này cần được phân tích, không bỏ qua.

### 3.5. Tên đề tài thay đổi giữa các phiên bản
- File cũ: *"Skill Distillation without Fine-Tuning"*
- File v7: *"Skill Distillation for Small Language Models via Skill Definition Optimization"*
- Tên v7 mô tả chính xác hơn và ít gây hiểu lầm hơn ("without fine-tuning" nghe như đặc điểm phụ, trong khi *via Skill Definition Optimization* đặt đúng trọng tâm kỹ thuật).

---

## 4. Nhận xét Tổng thể

Đây là một ý tưởng **tốt, có hướng nghiên cứu rõ ràng, phù hợp với năng lực cử nhân** và có khả năng tạo ra sản phẩm thực sự có giá trị (skill_runner như OSS tool, và metric SPI/MSG có thể tái sử dụng).

| Tiêu chí | Đánh giá |
|---|---|
| Tính mới | ★★★★☆ — Framing mới, chưa thấy trong literature phổ thông |
| Tính khả thi | ★★★★☆ — Phạm vi vừa đủ, không cần GPU, API-only |
| Độ nghiêm túc đánh giá | ★★★★★ — Hybrid Evaluator + Human Eval + inter-rater agreement |
| Rủi ro kỹ thuật | ★★★☆☆ — Teacher bias và Human Eval bottleneck cần quản lý |
| Giá trị thực tiễn | ★★★★★ — skill_runner độc lập, dùng được ngay sau đề tài |

**Kết luận:** Ý tưởng xứng đáng được triển khai. Rủi ro lớn nhất không phải về kỹ thuật mà về **quản lý workload** (Human Eval) và **thiết kế Teacher Summarization** — cần kiểm tra sớm trước khi đầu tư vào toàn bộ pipeline.

---

*Ghi chú: File này tổng hợp từ DE_CUONG_DATN_PhanVanToan_102220129.docx (phiên bản cũ) và DE_CUONG_DATN_PhanVanToan_v7.docx (phiên bản mới nhất). Phiên bản v7 được dùng làm tài liệu tham chiếu chính.*
