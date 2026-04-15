# Create Distillation Task

**Purpose:** Interactive guided workflow for setting up and running distillation experiments on skill definitions.

## Capability

Helps you quickly initialize and execute a distillation pipeline round by asking clarifying questions about:
- Which skill to optimize (docx, xlsx, pptx, etc.)
- How many rounds and test cases
- Which student/teacher models
- Advanced options (dry-run, LLM Judge only, verbosity)

Then **automatically generates and executes** the appropriate command.

## How to Use

Simply ask for a distillation task with your parameters:

### Examples

**"Run a quick distillation on the docx skill with 2 test cases."**
- → Guided questions about rounds, models
- → Confirms command + executes

**"Set up a 5-round distillation on xlsx skill, using qwen/qwen3-14b as student."**
- → Confirms models, asks about LLM Judge, test cases
- → Generates & runs: `python run.py --skill xlsx --rounds 5 --test-cases 10 --student qwen/qwen3-14b`

**"Dry-run the docx pipeline to test infrastructure without teacher rewrite."**
- → Quick infrastructure validation
- → Runs: `python run.py --skill docx --dry-run --test-cases 3`

---

## Workflow Steps

1. **Parse request** — Extract skill name, rounds, test-cases if mentioned
2. **Ask clarifying questions** for any missing parameters:
   - Skill name (if not specified)
   - Number of rounds (default: 3)
   - Test cases per round (default: 5)
   - Student model (default: qwen/qwen3-8b)
   - Teacher model (default: claude-haiku-4-5)
   - Options: dry-run, no-llm-judge, verbose
3. **Confirm command** with user
4. **Execute** from `distillation/` directory
5. **Monitor output** and report results
6. **Display results location** (results/<date>/round_N/)

---

## Parameters Reference

| Parameter | Default | Options |
|-----------|---------|---------|
| `--skill` | _(required)_ | docx, xlsx, pptx, pdf, etc. |
| `--rounds` | 3 | 1-10 |
| `--test-cases` | 5 | 1-30 |
| `--student` | qwen/qwen3-8b | Any OpenRouter model ID |
| `--teacher` | claude-haiku-4-5 | claude-opus-4-1, claude-sonnet-4 |
| `--dry-run` | off | Skip teacher rewrite; test infrastructure |
| `--no-llm-judge` | off | Rule-based scoring only (faster) |
| `--verbose` | off | Enable detailed logging |

---

## Questions to Ask User

```
1. Which skill would you like to optimize?
   → Options: List available skills from skill_runner/skills/

2. How many rounds should the distillation run?
   → Default: 3 (suggest 1-2 for testing, 3-5 for optimization)

3. How many test cases per round?
   → Default: 5 (suggest 3 for quick iteration, 10+ for thorough evaluation)

4. Which student model?
   → Default: qwen/qwen3-8b (Qwen 3-8B is fastest & cheapest)
   → Option: qwen/qwen3-14b (better quality, slower)
   → Option: anthropic/claude-haiku-4-5 (quality baseline)

5. Which teacher model?
   → Default: claude-haiku-4-5 (fast & cheap)
   → Option: claude-sonnet-4 (higher quality rewrites)
   → Option: claude-opus-4-1 (best quality, most expensive)

6. Do you want to run in dry-run mode?
   → Useful for: Testing infrastructure, debugging without Teacher API calls
   → Will skip: SKILL.md rewriting, LLM Judge scoring

7. Do you want to enable LLM Judge scoring?
   → Default: enabled (0.20 weight in hybrid score)
   → Disable for: Faster iterations, cost savings

8. Enable verbose logging?
   → Shows: Each tool call, model responses, scoring details
```

---

## Next Steps After Execution

1. **Check results:** `ls distillation/results/`
2. **Analyze scores:** View `round_1/evaluation_results.json`
3. **Review key notes:** `cat round_1/key_notes.md`
4. **Compare rounds:** `diff round_1/SKILL.md round_2/SKILL.md`
5. **Continue optimization:** `"Run another distillation round on docx with the new SKILL.md"`

---

## Error Handling

| Error | Likely Cause | Suggested Fix |
|-------|-------------|---------------|
| `OPENROUTER_API_KEY not found` | Missing `.env` or wrong var name | Verify: `echo $OPENROUTER_API_KEY` is set |
| `Anthropic key not found` | Missing `ANTHROPIC_KEY` | Ensure `.env` has `ANTHROPIC_KEY=sk-ant-...` |
| `Skill not found: xyz` | Typo or skill doesn't exist | Run `python main.py list-skills` to see available |
| `Model not available on OpenRouter` | Invalid model ID | Check openrouter.ai/models for valid IDs |
| `Test case file not found` | Missing `distillation/test_cases/<skill>.json` | Create test_cases file or use existing skill |

---

## Related Commands

After your distillation task:

- **"Compare the student model vs Claude baseline on test case tc_a05"**
  → Use skill_runner directly to benchmark

- **"Debug why tc_c12 failed in round 2"**
  → Use distillation-debugger agent

- **"Add a new test case for the xlsx skill"**
  → Edit `distillation/test_cases/xlsx.json`

- **"Tune the scoring weights (increase LLM Judge percentage)"**
  → Edit `distillation/config.yaml`

---

## Implementation Notes

- Always run from `distillation/` directory before executing `python run.py`
- API calls are billed per test case per round (student + teacher + judges)
- Results are versioned by date: `results/<DD_MM_YYYY>/round_N/`
- Dry-run (~2–3 min per round) for quick internal testing
- Full run (~10–15 min per round + scoring) depends on # test cases & models

---

**Related:** See `.github/copilot-instructions.md` for full command reference and known issues.
