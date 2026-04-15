# Kiến Trúc Hệ Thống

## 1. Kiến trúc tổng quan

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

### Components Table

| Layer | Component | Vai trò |
|-------|-----------|---------|
| Input | Skill DB (JSON/Markdown) | Lưu Skill gốc chuẩn hóa |
| Input | Target Model Profile | Thông tin về model nhỏ: context size, weaknesses, format |
| Processing | Skill Analyzer | Phân tích Skill gốc, xác định core intent |
| Processing | RAG Retriever | Query Example DB lấy 3-5 ví dụ liên quan |
| Processing | Teacher LLM (Rewriter) | Rewrite SKILL.md phù hợp target model |
| Processing | Validator | Kiểm tra skill mới có đủ thông tin không |
| Execution | Student Model | Chạy task với skill mới (via OpenRouter API) |
| Evaluation | Hybrid Evaluator | Chấm điểm output của Student |
| Output | Optimized SKILL.md | File hướng dẫn tối ưu cho target model |

---

## 2. Hybrid Evaluator — Chi tiết

Đây là thành phần quan trọng nhất, gồm 2 lớp kết hợp:

### Lớp 1 — Rule-based (nhanh, miễn phí)
- Rules được Teacher LLM tự động generate từ Skill gốc (không viết tay)
- Kiểm tra các điều kiện cứng: đúng tool name? có params không? format đúng không?
- Output: Pass / Fail — nếu Fail thì score = 0, không gọi LLM Judge

### Lớp 2 — LLM Judge (chỉ kích hoạt khi pass Rule check)
- Nhận: task gốc + SKILL.md + output của Student
- Chấm điểm 0-10 theo rubric: chọn đúng tool, params hợp lý, follow workflow đúng không
- Trả về JSON: `{ score, reason }` — reason dùng để Teacher hiểu cần sửa gì

### Công thức tính điểm cuối

```
⚠️ FLEXIBLE SCORING (tùy test case):

Rule Score = weighted average của các checks liên quan đến test case đó
  - Weights tự động điều chỉnh dựa trên yêu cầu của test case
  - Ví dụ: Test case không yêu cầu "table" → check "has_table" không áp dụng
  - Default threshold để pass: Rule Score ≥ 0.6

LLM Judge Score = 0-10 scale (chỉ gọi nếu Rule Score pass)
  - Semantic quality validation
  - Normalized to 0-1 range

Final Score = (Rule Score × weight_rule) + (LLM Judge Score × weight_llm)
  - Default: weight_rule = 0.80, weight_llm = 0.20
  - Weights có thể tùy chỉnh per evaluator trong config

Nếu Rule check Fail → Final Score = 0 (skip LLM Judge để tiết kiệm API call)
```

---

## 3. So sánh 3 evaluation approaches

| Tiêu chí | Rule-based | LLM Judge | Hybrid ✅ |
|----------|------------|-----------|-----------|
| Chi phí | Gần 0 | Cao (API call) | Trung bình |
| Tốc độ | Rất nhanh | Chậm | Nhanh |
| Độ chính xác | Cứng nhắc | Linh hoạt | Tốt nhất |
| Handle semantic | ❌ | ✅ | ✅ |
| Explainable | ✅ (rules rõ) | ✅ (có reason) | ✅✅ |
| Phù hợp MVP | ✅ | ⚠️ | ✅✅ |
