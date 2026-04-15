# AI Agent Customizations Guide

**Ngày tạo:** 15/04/2026
**Mục đích:** Hướng dẫn sử dụng 3 customizations mới cho AI agent Copilot khi làm việc trên Skill Distillation project.

---

## 📋 Tóm Tắt 3 Customizations

Đã tạo 3 file customizations để tăng năng suất AI agent trên dự án này:

| # | File | Loại | Mục Đích |
|----|------|------|---------|
| 1 | `.prompt/create-distillation-task.md` | Prompt Guide | Setup & chạy distillation rounds một cách interactive |
| 2 | `distillation-debugger.agent.md` | Agent Guide | Phân tích và debug lỗi từ distillation results |
| 3 | `.agent.md` | Agent Guide | Conventions để evolve SKILL.md, test cases, evaluators |

---

## 1️⃣ Create Distillation Task (`.prompt/create-distillation-task.md`)

### Mục đích
Guided workflow giúp bạn **nhanh chóng setup & chạy distillation** mà không cần nhớ lệnh.

### Cách dùng
Yêu cầu AI agent (Copilot) theo một trong các cách sau:

#### **A. Quick setup (default parameters)**
```
"Run a quick distillation on the docx skill with 2 test cases."
```
→ Agent sẽ hỏi bạn vài câu hỏi rồi tự động chạy:
```bash
cd distillation/
python run.py --skill docx --rounds 1 --test-cases 2 --verbose
```

#### **B. Custom models**
```
"Set up a 2-round distillation on docx skill, using qwen/qwen3-14b as student and claude-sonnet-4 as teacher."
```
→ Agent xác nhận lệnh rồi chạy với models cụ thể

#### **C. Dry-run (test infrastructure)**
```
"Dry-run the docx pipeline to test infrastructure without teacher rewrite."
```
→ Chạy nhanh để test setup, bỏ qua Teacher API calls

#### **D. No LLM Judge (faster, cheaper)**
```
"Run rule-based scoring only on docx: 1 round, 5 test cases, no LLM Judge."
```
→ Chỉ dùng rule checks, không gọi Claude LLM Judge

### Kết quả
Sau khi chạy xong:
- ✅ Kết quả lưu trong: `distillation/results/<DD_MM_YYYY>/round_1/`
- 📊 File đánh giá: `evaluation_results.json` (chứa scores)
- 📝 Phân tích: `key_notes.md` (teacher's observations)
- 📄 SKILL cập nhật: `SKILL.md` (phiên bản mới)
- 📋 Logs: `batch_1/docx_qwen_qwen3-8b_*.jsonl`

### Khi nào dùng?
✅ Bạn muốn chạy distillation nhanh mà không cần gõ command
✅ Lần đầu chạy, cần confirm parameters
✅ Testing infrastructure trước khi chạy full pipeline

---

## 2️⃣ Distillation Debugger (`distillation-debugger.agent.md`)

### Mục đích
**Phân tích failure patterns** từ distillation results và đưa ra specific recommendations để improve SKILL.md.

### Cách dùng
Sau khi distillation chạy xong, yêu cầu AI agent:

#### **A. Phân tích round cụ thể**
```
"Debug the failed test cases from round 2 of the docx distillation."
```
→ Agent sẽ:
1. Đọc `evaluation_results.json` từ round 2
2. Phân loại failures: rule failures vs LLM Judge failures vs agent errors
3. Tìm patterns ("80% test case A pass, but 0% test case D pass" → missing examples)
4. Suggest specific fixes cho SKILL.md

#### **B. So sánh SKILL.md versions**
```
"Compare SKILL.md from round_1 vs round_2. What improved? Why did round_2 get better scores?"
```
→ Hiển thị diff + phân tích impact của từng change

#### **C. Xem failure breakdown**
```
"Show me the scoring breakdown for the latest docx distillation. Which test cases failed and why?"
```
→ Bảng ranking test cases by score + failure categories

#### **D. Identify patterns**
```
"Are there patterns in the failures? (e.g., all Create tests pass, but Convert tests fail)"
```
→ Phát hiện gaps trong SKILL.md

### Kết quả
Agent trả về:
- 📊 Failed test cases + root causes
- 🔍 Pattern detection ("missing examples for workflow D")
- ✨ Specific recommendations ("Add tracked_changes example")
- 📈 Stopping criteria status (threshold reached? converged?)

### Khi nào dùng?
✅ Distillation vừa chạy xong, cần check failures
✅ Không hiểu tại sao test case nào đó fail
✅ Muốn biết teacher nên improve cái gì để round tiếp theo tốt hơn

---

## 3️⃣ Skill Evolution Agent (`.agent.md`)

### Mục đích
**Specialized conventions & workflow** giúp AI agent làm việc trên SKILL.md, test cases, evaluators đúng cách.

### Cách dùng
Yêu cầu AI agent theo một trong các workflow:

#### **Workflow A: Optimize existing SKILL.md**
```
"Improve the docx SKILL.md to handle tracked changes and nested formatting.
 Add test cases that verify both features work."
```
→ Agent sẽ:
1. Đọc hiện tại SKILL.md
2. Thêm examples cho tracked changes + nested formatting
3. Tạo 2 test cases mới
4. Update version number + timestamp

#### **Workflow B: Create new test case**
```
"Add a test case for docx that checks if the agent can create a document with:
 - Bold + italic text
 - A 3-column table
 - A bulleted list"
```
→ Agent sẽ:
1. Tạo JSON test case với rule_checks (XML XPath) + content_checks (keywords)
2. Assign workflow type (A, B, C, D, E)
3. Estimate difficulty level

#### **Workflow C: Create new skill**
```
"Create a new xlsx skill from scratch:
 - SKILL.md covering create/read/edit/convert workflows
 - Test cases (20-30 comprehensive cases)
 - Evaluator rules (xlsx_rules.py)"
```
→ Agent sẽ:
1. Gen SKILL.md với structure template
2. Gen test_cases/xlsx.json
3. Gen evaluator/xlsx_rules.py
4. Register evaluator trong orchestrator.py

#### **Workflow D: Review & improve evaluator**
```
"Review the docx_rules.py evaluator. Are the checks too strict? Add more lenient alternatives."
```
→ Agent sẽ audit rules và suggest improvements

### File Structure Reference
Agent's guideline cho SKILL.md:
```yaml
---
name: docx
version: 1.0
description: Create, read, edit, and convert Word documents
models_tested:
  - qwen/qwen3-8b (score: 0.72)
  - anthropic/claude-haiku-4-5 (baseline: 0.95)
---

# Skill: [Name]

## Overview
[clear description - max 2000 chars]

## Tools Available
[list with constraints]

## Before You Start
[prerequisites, pitfalls]

## Step-by-Step Examples
[3-5 complete, runnable examples]

## Common Tasks
[troubleshooting, edge cases]
```

### Quality Checklist
Trước khi commit changes, agent check:
- [ ] SKILL.md ≤ 2000 chars
- [ ] Examples đầy đủ, runnable
- [ ] Test cases có clear rule_checks
- [ ] Evaluator rules không ambiguous
- [ ] Version number + timestamp updated
- [ ] Fixtures tracked (not in .gitignore)

### Khi nào dùng?
✅ Bạn muốn improve một SKILL.md hiện tại
✅ Cần thêm test cases đó đủ challenging
✅ Muốn tạo skill mới (xlsx, pptx, etc.)
✅ Refactor evaluator rules để fix false positives/negatives

---

## 🔗 Cách Kết Nối 3 Customizations

```
👤 User: "Run a 1-round distillation on docx"
    ↓
1️⃣ create-distillation-task.prompt.md
   (interactive setup, generate command)
    ↓
📊 Pipeline runs → results in distillation/results/
    ↓
👤 User: "Why did tc_a05 fail?"
    ↓
2️⃣ distillation-debugger.agent.md
   (analyze failures, suggest fixes)
    ↓
👤 User: "Update SKILL.md with those suggestions"
    ↓
3️⃣ .agent.md
   (enforce conventions, quality checklist)
    ↓
✅ SKILL.md v2 committed
```

---

## 📚 Các Prompt Ví Dụ

### Scenario 1: Quick experiment
```
"Run a dry-run distillation on docx skill with 3 test cases.
 I want to test the infrastructure without API costs."
```
→ Uses: `create-distillation-task.prompt.md`

### Scenario 2: Analyze failure
```
"The distillation just finished. tc_a05 and tc_c12 failed.
 What do they have in common? What should the teacher fix?"
```
→ Uses: `distillation-debugger.agent.md`

### Scenario 3: Evolve skill
```
"Based on the debug analysis, add 2 new examples to docx SKILL.md
 showing how to handle tracked changes and complex nested formatting."
```
→ Uses: `.agent.md` + conventions

### Scenario 4: Add test case
```
"Create a challenging test case for docx:
 - Workflow: Convert
 - Content: Convert a multi-page PDF with complex formatting to DOCX
 - Verify: Images preserved, table layouts correct, formatting close"
```
→ Uses: `.agent.md` for structure + quality checks

### Scenario 5: Create new skill
```
"Create a new pptx skill from scratch. Cover:
 - Creating presentations with slides, speaker notes
 - Adding images, shapes, text boxes
 - Applying themes and formatting
 Include evaluator rules and 25 test cases."
```
→ Uses: `.agent.md` guidelines for structure

---

## 📖 Reference Liên Kết

- **[.github/copilot-instructions.md](../.github/copilot-instructions.md)**
  → Full command reference + architecture overview

- **[CLAUDE.md](../CLAUDE.md)**
  → Deep architectural dive, data flow, known issues

- **[distillation/README.md](../distillation/README.md)**
  → Pipeline mechanics, mermaid diagrams

- **[skill_runner/README.md](../skill_runner/README.md)**
  → Skill executor CLI options, workspace persistence

- **[skill_runner/docs/](../skill_runner/docs/)**
  → Components, lessons_learned, detailed workflow

---

## 🎯 Típ & Tricks

### Tip 1: Combine customizations
```
# One-shot workflow
"Run a 1-round distillation on xlsx, analyze the failures,
 and suggest SKILL.md improvements."
→ Chạy distillation + debug in one go
```

### Tip 2: Use dry-run for fast iteration
```
# Test infrastructure first
"Dry-run for 2 test cases to verify everything works,
 then run full round with 10 test cases."
→ Avoid wasting API budget
```

### Tip 3: Benchmark before & after
```
"Compare a single test case (tc_a05) on:
 - qwen/qwen3-8b with original SKILL.md
 - qwen/qwen3-8b with new SKILL.md
 Show me the improvement."
→ Validate SKILL improvements objectively
```

### Tip 4: Leverage distillation-debugger for insights
```
"Analyze all 3 rounds of docx distillation.
 Did the scores improve each round?
 What patterns did the teacher identify?"
→ Understand optimization trajectory
```

---

## ⚠️ Common Mistakes

| Mistake | Solution |
|---------|----------|
| "Run distillation on xlsx but I haven't created test_cases/xlsx.json yet" | Create test cases first using `.agent.md` workflow |
| "Used model that's not on OpenRouter (e.g., 'gpt-4')" | Check openrouter.ai/models for valid IDs |
| "SKILL.md is 5000+ chars; teacher takes forever" | Trim to ≤2000 chars; move verbose examples to separate file |
| "Test case has no rule_checks; evaluator always returns high score" | Define specific XPath/property checks in rule_checks array |
| "Forgot to update version number in SKILL.md" | Agent will remind you in quality checklist |

---

## 🚀 Next Steps

1. **Try Customization #1:**
   Ask: `"Run a quick 1-round distillation on docx with 3 test cases"`

2. **After distillation, try Customization #2:**
   Ask: `"Debug the results. Which test cases failed and why?"`

3. **Then try Customization #3:**
   Ask: `"Based on the debug analysis, improve the docx SKILL.md"`

4. **For next iteration:**
   Repeat steps 1-3 with updated SKILL.md

---

**Last Updated:** 2026-04-15
**For questions:** See `.github/copilot-instructions.md` or `CLAUDE.md`
