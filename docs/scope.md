# Project Scope: MVP vs Nice-to-have

## 1. MVP — Core Scope (6-8 weeks)

The Minimum Viable Product focuses on demonstrating the core concept:

### MVP Deliverables

- **2-3 Skills** với dạng tool-call đơn giản: web search, file reader, calculator
- **3 Student models**: Qwen3-8B, Qwen3.5-4B, Phi-4-mini-instruct
- **Evaluator**: Hybrid (Rule-based auto-gen + LLM Judge)
- **Optimization loop**: Teacher rewrite → test → iterate
- **Output**: SKILL.md v_best cho từng target model

### MVP Success Criteria

- [ ] Baseline score (skill gốc): ~30-40% success rate
- [ ] Distilled score: ~65-75% success rate
- [ ] Convergence trong 3-5 rounds
- [ ] Reproducible results across 3+ models
- [ ] Documentation & evaluation metrics

---

## 2. Feature Classification

| Tính năng | Loại | Lý do | Độ ưu tiên |
|-----------|------|-------|-----------|
| Optimization loop cơ bản | ✅ MVP | Core contribution của đề tài | **CRITICAL** |
| Hybrid Evaluator | ✅ MVP | Cần thiết để vòng lặp hoạt động | **CRITICAL** |
| 2-3 Skills tool-call đơn giản | ✅ MVP | Đủ để chứng minh concept | **HIGH** |
| 3 student models (Qwen3-8B, Qwen3.5-4B, Phi-4-mini) | ✅ MVP | Đủ để baseline + so sánh | **HIGH** |
| RAG few-shot examples | ✅ MVP | Tăng chất lượng distillation đáng kể | **HIGH** |
| Cross-model testing (nhiều student) | ✅ MVP | So sánh hiệu quả giữa các model | **HIGH** |
| Auto pipeline không cần can thiệp tay | ⏳ Nice-to-have | Nếu còn thời gian | MEDIUM |
| Multimodal skills (PPTX, PDF...) | ❌ Out of scope | Cần domain expertise để evaluate | LOW |
| Fine-tuning model | ❌ Out of scope | Không phải hướng của đề tài | N/A |
| Production deployment | ❌ Out of scope | Đồ án tốt nghiệp, không cần production | N/A |

---

## 3. Nice-to-have Features (If time permits)

### 3.1 Extended Skills
- PPTX, PDF, XLSX skills (multimodal)
- API testing & mocking skills
- Require domain-specific evaluation rules

### 3.2 Enhanced RAG
- Semantic search over example DB
- Auto-generated few-shot prompts
- LangChain integration for retrieval

### 3.3 Advanced Analytics
- Visualization dashboard for round metrics
- Baseline vs distilled comparisons
- Error pattern analysis

### 3.4 Production Readiness
- API endpoint for skill optimization
- Batch processing pipeline
- Cost tracking & optimization

### 3.5 Model Expansion
- Support for more student models (Gemma, LLaMA, etc.)
- Cross-org model compatibility testing
- Benchmark suite for portability metrics

---

## 4. Known Constraints & Risks

### Timeframe Constraint
- 6-8 weeks for MVP completion
- 2-3 weeks for setup + infrastructure
- 3-5 weeks for core development
- 1 week for testing & documentation

### Budget Constraint (API Costs)
- Teacher LLM (Claude) calls: ~$0.05 per call × 50 iterations = ~$2.50 per skill
- Student model inference: ~$0.01 per test × 30 tests × 5 rounds = ~$1.50 per skill
- LLM Judge calls: ~$0.02 × 30 tests × 5 rounds = ~$3 per skill
- **Estimated total**: ~$7-10 per skill (manageable for thesis scope)

### Model Availability
- OpenRouter must support target models (Qwen3-8B, Phi-4, etc.)
- Teacher requires Claude Haiku 4.5 or higher
- Student model performance varies significantly

---

## 5. Success Metrics

### Primary Metrics
1. **Success rate improvement**: Baseline 30-40% → Target 65-75%
2. **Prompt efficiency**: Token count reduction of 30-50%
3. **Portability**: SKILL.md works on 3+ different models

### Secondary Metrics
1. **Convergence speed**: Reach 0.70 score within 3-5 rounds
2. **Cost efficiency**: 60-70% reduction in evaluation API calls
3. **Stability**: Consistency across multiple runs

### Publication Metrics
1. **Reproducibility**: Full documentation + code release
2. **Benchmark dataset**: 30-50 standardized test cases per skill
3. **Novel contribution**: Comparison to DSPy & other baselines

---

## 6. Dependency Tree

```
MVP Completion
├── Core Infrastructure
│   ├── Orchestrator (distillation/orchestrator.py)
│   ├── Teacher (distillation/teacher.py)
│   ├── Hybrid Evaluator (rule-based + LLM Judge)
│   └── Test cases & fixtures
├── CLI & UX
│   ├── run.py (distillation entry point)
│   ├── main.py (skill_runner entry point)
│   └── Rich formatting
├── Integration
│   ├── OpenRouter API (Student models)
│   ├── Anthropic API (Teacher LLM)
│   └── Logging & results tracking
└── Testing & Documentation
    ├── Unit tests (pytest)
    ├── README & docs
    └── Evaluation results

Optional Extensions (Phase 2)
├── RAG Integration (LangChain)
├── Dashboard (Visualization)
├── Production API
└── Extended model support
```

---

## 7. Timeline Estimate

| Week | Focus | Deliverable |
|------|-------|------------|
| 1-2 | Setup & Infra | Repository, CLI framework, API clients |
| 3-4 | Core Loop | Orchestrator, Teacher, basic Evaluator |
| 5 | Hybrid Evaluator | Rule-based + LLM Judge integration |
| 6 | Cross-model Testing | Test on 3 student models |
| 7 | Optimization | Refine prompts, improve metrics |
| 8 | Docs & Papers | Write thesis, benchmark results |
