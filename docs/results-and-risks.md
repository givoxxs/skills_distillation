# Results & Risk Management

## 1. Expected Results

### Performance Improvements

| Metric | Skill gốc (Baseline) | Skill Distilled (Target) | Improvement |
|--------|---------------------|--------------------------|-------------|
| Tool-call success rate | ~30-40% | ~65-75% | +75-100% |
| Parameter accuracy | ~40% | ~70% | +75% |
| Token count (skill length) | ~800 tokens | ~300 tokens | -62% |
| Latency (per inference) | Cao (context dài) | Thấp hơn 30-40% | -30-40% |
| API cost per eval run | Baseline | Giảm 60-70%* | -60-70% |

*Due to Hybrid Evaluator reducing LLM Judge calls on failed cases

---

## 2. Risk Analysis & Mitigation

### 2.1 High-Priority Risks

| Risk | Xác suất | Impact | Mitigation Strategy |
|------|----------|--------|----------------------|
| Student model quá yếu, dù distill tốt vẫn fail | Trung bình (40%) | HIGH | Chọn model có instruction-following tốt hơn (Qwen3-8B thay vì model nhỏ hơn); perform baseline testing first |
| Skill mất thông tin quan trọng sau distill | Cao (60%) | CRITICAL | Validator check information completeness trước khi test; compare SKILL.md versions |
| LLM Judge không nhất quán (non-deterministic) | Cao (60%) | MEDIUM | Chạy mỗi case 3 lần, lấy majority vote; log all judge calls |
| Test cases không đủ diverse | Trung bình (45%) | MEDIUM | Thiết kế test cases cover A-E workflows từ đầu; add edge cases |

### 2.2 Medium-Priority Risks

| Risk | Xác suất | Impact | Mitigation |
|------|----------|--------|-----------|
| Teacher LLM tốn nhiều tiền API | Thấp (20%) | LOW | Hybrid Evaluator giảm 60-70% calls; set daily budget alerts |
| Submodule update gây conflict | Thấp (15%) | MEDIUM | Document submodule commit version; test compatibility |
| OpenRouter API rate limits | Trung bình (35%) | MEDIUM | Implement exponential backoff; queue management |
| False negatives in Rule-based scoring | Trung bình (40%) | MEDIUM | Manual review of failed cases; adjust rule thresholds |

### 2.3 Low-Priority Risks

| Risk | Xác suất | Impact | Mitigation |
|------|----------|--------|-----------|
| Documentation becoming outdated | Cao (70%) | LOW | Auto-generate docs from code; version control docs |
| Reproducibility issues across runs | Thấp (10%) | MEDIUM | Fix random seeds; document environment setup |
| Conflicting model families' strengths | Trung bình (30%) | LOW | Run separate distillation per model family |

---

## 3. Failure Mode Analysis (FMEA)

### Scenario 1: Teacher produces worse SKILL.md

**Symptom**: Score decreases instead of increases after Teacher rewrite

**Root Causes**:
- Teacher prompt not specific enough
- Losing context of passing test cases
- Over-optimization for failures

**Prevention**:
- ✅ Rule #1 in SYSTEM_PROMPT: "PRESERVE passing cases"
- ✅ Include round_history in prompt for context
- ✅ Validate SKILL.md completeness before evaluation

**Recovery**:
- Track best score seen so far; revert if worse
- Log all Teacher prompts & outputs
- Manual review of changes

---

### Scenario 2: All test cases fail despite distillation

**Symptom**: Final score < 0.30, no improvement over baselines

**Root Causes**:
- Student model fundamentally unable to execute task
- SKILL.md misalignment with model's training data
- Test cases do not represent real use cases

**Prevention**:
- Run baseline first; skip if baseline < 0.15
- Check model instruction-following capabilities
- Diversify test cases during setup phase

**Recovery**:
- Switch to larger student model
- Simplify SKILL.md format
- Rewrite test cases to match model's strengths

---

### Scenario 3: Cost explosion from API calls

**Symptom**: API bills exceed budget before MVP completion

**Root Causes**:
- Too many LLM Judge calls on failed cases
- Inefficient prompt design causing retries
- OpenRouter rate limiting causing backoff delays

**Prevention**:
- ✅ Hybrid Evaluator (skip LLM Judge on failures)
- ✅ Cost tracking per round
- ✅ Circuit breaker for expensive operations

**Recovery**:
- Disable LLM Judge temporarily (use Rule-based only)
- Reduce batch size or test count
- Use local models for some evaluation

---

## 4. Quality Checkpoints

### Pre-Distillation Checklist

- [ ] Test cases review: 30-50 cases, diverse, realistic?
- [ ] Baseline measurement: Skill gốc works on >= 30% of tests?
- [ ] SKILL.md completeness: All required sections present?
- [ ] Student model selection: Instruction-following verified?
- [ ] API keys validated: OpenRouter & Anthropic working?

### Post-Round Checkpoint

- [ ] Score changed < 2% consecutively 3 times? (convergence)
- [ ] All failed cases documented?
- [ ] Teacher prompt was applied correctly?
- [ ] SKILL.md changes logged?

### Pre-Publication Checkpoint

- [ ] Reproducibility test: Multiple runs give same results?
- [ ] Documentation complete: All sections covered?
- [ ] Results significant: 50%+ improvement rate?
- [ ] Code reviewed: No obvious bugs/issues?

---

## 5. Comparison to Baselines

### vs DSPy

| Aspect | DSPy | Skill Distillation |
|--------|------|---------------------|
| Optimization target | Prompt A | Skill definition |
| Reusability | Task-specific | Model-portable |
| Cost per optimization | Low | Higher (LLM Judge) |
| Learning curve | Steep (DSL) | Lower (CLI) |

### vs Few-shot Learning

| Aspect | Few-shot | Skill Distillation |
|--------|----------|---------------------|
| Examples required | 5-10 | 0 (auto-generated) |
| Performance ceiling | Model's limit | Higher via rewriting |
| Adaptation speed | Manual | Automated |

### vs Fine-tuning

| Aspect | Fine-tuning | Skill Distillation |
|--------|-------------|---------------------|
| Model modification | YES | NO |
| Training time | Hours-days | Minutes |
| Data requirement | 100s-1000s samples | None |
| Cost | High (compute) | Low (API calls) |
| Portability | Fixed model | Multiple models |

---

## 6. Success Stories (Theoretical Examples)

### Example 1: Simple Tool-call (Web Search)

```
Baseline (Qwen3-8B + SKILL.md gốc): 32% success (wrong tool choice)
Round 1: 55% (add examples, clarify tool)
Round 2: 68% (emphasize when to use)
Round 3: 72% (refine parameters)
✅ CONVERGED - Output optimized SKILL.md
```

### Example 2: Complex Workflow (File Processing)

```
Baseline (Qwen3.5-4B + SKILL.md gốc): 28% success (parameter errors)
Round 1: 45% (add step-by-step guide)
Round 2: 62% (RAG inject examples)
Round 3: 68% (fix edge cases)
Round 4: 70% (convergence)
✅ CONVERGED - 2.5x improvement
```

### Example 3: Fails to Converge

```
Baseline (Phi-4-mini + SKILL.md gốc): 15% success (model too weak)
Round 1: 22% (add examples)
Round 2: 24% (improve clarity)
Round 3: 23% (small improvement)
❌ STOPPED - Below viability threshold
→ Recommend using larger model
```
