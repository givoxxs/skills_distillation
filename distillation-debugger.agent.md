# Distillation Debugger Agent

**Purpose:** Specialized agent for analyzing failed distillation test cases and suggesting SKILL.md improvements.

## Capability

This agent:
1. **Reads evaluation results** from a distillation round
2. **Identifies failure patterns** (rule failures, LLM Judge failures, agent errors)
3. **Extracts key insights** from JSONL logs and key_notes.md
4. **Compares SKILL.md versions** to see what changed
5. **Suggests specific improvements** to prompts, examples, or tool descriptions
6. **Generates next iteration** recommendations

## How to Use

### Examples

**"Debug the failed test cases from round 2 of the docx distillation."**
- → Analyzes `distillation/results/<date>/round_2/`
- → Shows failure breakdown
- → Suggests prompt fixes

**"Why did tc_a05 and tc_c12 fail? What can the teacher improve in the next SKILL.md version?"**
- → Finds specific test cases in latest results
- → Compares SKILL.md diff
- → Recommends specific changes

**"Show me the scoring breakdown for the latest xlsx distillation round and highlight low-performing test cases."**
- → Extracts `evaluation_results.json`
- → Ranks by score
- → Flags patterns (e.g., "all Create workflow cases failed")

**"Compare SKILL.md from round_1 vs round_3 in the docx skill. What improved?"**
- → Diffs versions
- → Shows changes side-by-side
- → Links to scores for those rounds

---

## Analysis Workflow

### Phase 1: Load Results

1. Find latest `distillation/results/<date>/` directory (or ask user for specific date/round)
2. Load `round_N/evaluation_results.json` → parse test case scores
3. Load `round_N/key_notes.md` → extract teacher's analysis
4. Load `round_N/batch_M/docx_qwen_*.jsonl` logs → parse agent failures

### Phase 2: Failure Classification

Categorize failures by type:
- **Rule failures** (XML invalid, file not created, style missing)
  - Rule name, JSON path, expected vs actual
- **LLM Judge failures** (output semantic quality low)
  - Judge's reasoning, score vs threshold
- **Agent loop errors** (tool call failed, max iterations, timeout)
  - Tool name, error message, iteration #

### Phase 3: Pattern Detection

```
If 80% of Create workflow (A) cases pass but 0% of Convert workflow (D) pass:
  → Suggests: SKILL.md missing conversion-specific examples

If rule_score passes but llm_judge fails:
  → Suggests: Output structure correct, but semantic quality low

If agent times out on large files:
  → Suggests: SKILL.md needs optimization for file size handling
```

### Phase 4: Recommendations

Generate specific suggestions:
1. **Prompt rewrites** (if Teacher hasn't addressed issue):
   - "Add explicit step-by-step examples for tc_c12 (tracked deletions)"
   - "Clarify when to use Table of Contents vs manual structure"

2. **Tool descriptor improvements**:
   - "The `write_file` tool description misses mention of file encoding"
   - "Add note about LibreOffice compatibility for .docx generation"

3. **Rule check tuning**:
   - "Current XML XPath is too strict; 3 edge cases failed"
   - "Consider loosening content_quality threshold from 0.7 to 0.6"

4. **Test case additions**:
   - "Missing test case for: Create docx with complex table + embedded images"
   - "No edge case for: Handle corrupted input files gracefully"

---

## Output Structure

```
## Distillation Analysis: docx skill, Round 2

### Summary
- Total test cases: 5
- Passed: 3 (60%)
- Failed: 2 (40%)
- Avg hybrid score: 0.65
- Status: Below threshold (need round 3)

### Failure Breakdown

#### Failed: tc_a05 (Create docx with complex formatting)
- Rule Score: 0.40 (FAILED)
- LLM Judge Score: 0.75
- Hybrid Score: 0.54
- **Why:** XML style tags missing; agent didn't apply bold + italic formatting
- **Root Cause:** SKILL.md example doesn't show nested formatting syntax
- **Fix:** Add example: "Bold + italic: <w:rPr><w:b/><w:i/></w:rPr>"
- **Confidence:** High (clear pattern; teacher should catch in next round)

#### Failed: tc_c12 (Edit docx, track deletions)
- Rule Score: 0.20 (FAILED)
- LLM Judge Score: 0.50
- Hybrid Score: 0.38
- **Why:** Tracked changes not used; deletions permanent
- **Root Cause:** SKILL.md doesn't explain track_changes workflow
- **Fix:** Add: "When editing, use w:del + w:delInst tags for tracked deletions"
- **Confidence:** Very High (known issue from key_notes.md)

#### Passed: tc_a01, tc_a03, tc_b07 (100% pass rate for Read/Create workflows)
- **Pattern:** Sequential file operations work well
- **Implication:** Agent understands basic tool calling

### SKILL.md Changes (Round 1 → Round 2)

```diff
- "Use the write_file tool to create files"
+ "Use the write_file tool to create .docx files with proper XML structure
+   Example for bold text: <w:r><w:rPr><w:b/></w:rPr><w:t>Bold</w:t></w:r>"

- "Apply formatting as needed"
+ "Apply formatting using specific XML tags:
+   - Bold: <w:b/>
+   - Italic: <w:i/>
+   - Underline: <w:u val='single'/>"
```

### Recommendations for Round 3

1. **High Priority** (blocking multiple test cases):
   - [ ] Add explciit tracked_changes example (fixes tc_c12)
   - [ ] Clarify nested formatting syntax (fixes tc_a05)

2. **Medium Priority** (edge cases):
   - [ ] Mention file size limits and optimization tips
   - [ ] Add error recovery example: "If write_file fails, use python-docx library"

3. **Low Priority** (nice-to-have):
   - [ ] Add reference to LibreOffice validation tool
   - [ ] Link to Official MS Word XML spec

4. **Test Case Improvements**:
   - [ ] Add tc_a09: Complex formatting + images + tables in one doc
   - [ ] Add tc_b09: Read and validate complex docx structure
   - [ ] Add tc_d06: Convert PDF → DOCX with formatting preservation

### Stopping Criteria Status

| Criterion | Status |
|-----------|--------|
| Threshold (≥0.70 avg hybrid) | ❌ Avg: 0.65 (need improvement) |
| Convergence (delta < 0.02 for 3 rounds) | ⏳ Round 2 of 3 (continue) |
| Max rounds (≥3) | ⏳ Currently on 2 (more room) |

**Recommendation:** Continue to Round 3; patterns are clear and teacher can address.

---

## Next Steps (Suggested Prompts)

- **"Apply the recommendations from this debug session and run round 3 of docx distillation."**
  → Auto-executes: `python run.py --skill docx --rounds 1 --start-from-round 3 -n 5`

- **"Add the suggested test cases to distillation/test_cases/docx.json"**
  → Creates: tc_a09, tc_b09, tc_d06 with proper rule/content checks

- **"Show me the teacher's key_notes.md from round 2 — what did Claude identify?"**
  → Returns: Full markdown analysis from teacher

- **"Compare all 3 rounds: show me the score progression for each test case."**
  → Generates: Spreadsheet view of tc_* scores across rounds
```

---

## Implementation Details

### Data Sources

1. **evaluation_results.json** (per round)
   ```json
   {
     "test_cases": [
       {
         "test_case_id": "tc_a05",
         "prompt": "...",
         "rule_score": 0.40,
         "llm_judge_score": 0.75,
         "hybrid_score": 0.54,
         "passed": false,
         "rule_checks": [{...}],
         "failed_checks": [{...}]
       }
     ]
   }
   ```

2. **JSONL logs** (agent execution traces)
   ```jsonl
   {"step": 1, "tool": "write_file", "input": {...}, "output": "...", "status": "success"}
   {"step": 2, "tool": "bash", "input": "cd ...", "output": "error: ...", "status": "failed"}
   ```

3. **key_notes.md** (teacher's analysis)
   - Extracted failure patterns
   - Teacher's observations
   - Suggested improvements

### Error Handling

| Scenario | Response |
|----------|----------|
| No results found | "No distillation results found. Suggest running distillation first." |
| Malformed evaluation_results.json | "Results file corrupted. Ask user to re-run round." |
| JSONL logs incomplete | "Agent logs incomplete (interrupted run?). Analyze available data." |
| Both rounds have improvements | "Converging well. Continue or stop based on threshold." |

---

## Agent Configuration

```yaml
name: distillation-debugger
description: >
  Analyzes failed test cases from distillation rounds.
  Identifies patterns, suggests SKILL.md improvements,
  and recommends next steps.
tools:
  - read_file (evaluation_results.json, key_notes.md, JSONL logs, SKILL.md)
  - grep_search (find patterns in logs)
  - semantic_search (compare prompts, find similar failures)
limitations:
  - Cannot modify files (read-only analysis)
  - Focuses on last completed round (can query others if specified)
  - Scoring formula assumed fixed (0.80 rule + 0.20 LLM)
```

---

**Related:** See `.github/copilot-instructions.md` for pipeline overview and `/create-distillation-task.prompt.md` for running new distillations.
