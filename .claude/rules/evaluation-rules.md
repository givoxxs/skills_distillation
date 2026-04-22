---
paths: ["distillation/evaluator/**/*.py", "distillation/test_cases/**/*.json"]
---

# Evaluation & Scoring Rules

## Scoring Model
- `rule_score`: Dynamic average of **only the applicable checks** for a given test case. Checks absent from a test case definition are NOT counted. Pass threshold: ≥ 0.60.
- `llm_judge_score`: Ensemble of N Claude calls (0–10 range, normalized to 0–1). See `distillation/evaluator/llm_judge.py` for ensemble size.
- `hybrid_score` = `(1 - llm_judge_weight) × rule_score + llm_judge_weight × llm_judge_score`. Default weight: 0.20 for LLM judge (set via `llm_judge_weight` in `config.yaml`).

## LLM Judge Skip Rule
NEVER invoke the LLM Judge when `rule_score < 0.60` — the hybrid score is automatically 0 in this case. This is a hard cost-saving gate; do not bypass it even in tests.

## Evaluator Extensibility
- YOU MUST create a new `distillation/evaluator/<skill>_rules.py` (mirroring `docx_rules.py` structure) when adding a new skill to the pipeline.
- YOU MUST register the new evaluator in `distillation/orchestrator.py` — unregistered evaluators silently produce no scores.
- See `distillation/evaluator/docx_rules.py` for the canonical evaluator structure and check type naming conventions.

## Key Data Classes
- `EvalResult` (`distillation/evaluator/base.py`): holds `rule_score`, `llm_judge_score`, `hybrid_score` per test case.
- `CheckResult`: individual check with `name`, `passed`, `score`, `reason` fields.
- NEVER add fields directly to `CheckResult` without updating `base.py` — serialization will silently break.

## Rule Check Types
Test case `rule_checks` use dot-notation types: `xml.contains`, `xml.absent`, `style.*`. `content_checks` are semantic. The `must_have_docx` gate field bypasses content checks if the output `.docx` doesn't exist. See `distillation/test_cases/docx.json` for the full schema with examples.
