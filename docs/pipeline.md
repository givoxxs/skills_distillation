# Optimization Pipeline & End-to-End Flow

## 1. Vòng Lặp Optimization

Trái tim của hệ thống là **Optimization Loop** (vòng lặp tối ưu):

```
SKILL.md (v0)
  ↓
Student chạy test tasks
  ↓
Hybrid Evaluator chấm
  ↓
Teacher nhận feedback
  ↓
rewrite SKILL.md (v1)
  ↓
lặp lại → đến khi score đủ tốt
  ↓
output SKILL.md (v_best)
```

### Các bước trong mỗi iteration

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

## 2. Pipeline End-to-End

Quy trình hoàn chỉnh từ setup đến final evaluation:

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

## 3. Stopping Criteria

Pipeline dừng khi một trong các điều kiện được thỏa:

1. **Average score ≥ stop_threshold** (mặc định 0.70)
   - Nếu điểm trung bình trên tất cả test cases ≥ 0.70, dừng và xuất kết quả

2. **Convergence: Score delta < 0.02 cho 3 rounds liên tiếp**
   - Nếu 3 rounds gần đây đều cải thiện < 2%, có thể model đã đạt plateau

3. **max_rounds được chạy**
   - Mặc định 3-5 rounds, nếu chạy tới giới hạn thì dừng

---

## 4. Key Metrics Tracked per Round

```json
{
  "round": 1,
  "timestamp": "2026-04-15T10:30:00Z",
  "skill_version": "v1",
  "test_results": {
    "total_tests": 30,
    "passed": 22,
    "failed": 8,
    "avg_score": 0.68,
    "rule_score_avg": 0.72,
    "llm_judge_avg": 0.62
  },
  "errors": [
    {
      "test_id": "tc_a01",
      "error": "Wrong tool selected",
      "severity": "high"
    }
  ],
  "convergence": {
    "delta_vs_prev": 0.08,
    "consecutive_low_deltas": 0
  }
}
```

This data is used by Teacher to understand what needs fixing in the next iteration.
