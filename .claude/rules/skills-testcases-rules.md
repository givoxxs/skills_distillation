---
paths: ["skill_runner/skills/**", "distillation/test_cases/**"]
---

# Skills & Test Cases Rules

## SKILL.md Format
- Each skill lives in `skill_runner/skills/<skill_name>/SKILL.md`.
- SKILL.md may have optional YAML frontmatter. The `skill_loader` (`skill_runner/runner/skill_loader.py`) strips frontmatter before passing instructions to the model.
- NEVER embed code in SKILL.md that should be in `scripts/` — executable helpers go in `skill_runner/skills/<skill_name>/scripts/`.

## Test Case Schema
Test cases are JSON arrays in `distillation/test_cases/<skill>.json`. Each entry requires:
- `test_case_id`: format `tc_<workflow><number>` where workflow ∈ {A=Create, B=Read, C=Edit, D=Convert, E=Edge} (e.g., `tc_a01`, `tc_e05`)
- `rule_checks`: array of XML/style check objects (dot-notation types)
- `content_checks`: array of semantic checks
- `must_have_docx`: boolean gate

NEVER reuse test case IDs across skills — IDs must be globally unique within a skill's JSON file.

## Fixtures
Input fixtures for workflows B, C, D live in `distillation/test_cases/fixtures/`. YOU MUST add a fixture file before creating a test case that references it — a missing fixture causes the test case to error at runtime, not at load time.

## Adding a New Test Case
1. Add the fixture to `distillation/test_cases/fixtures/` (if needed for workflows B/C/D).
2. Append the entry to `distillation/test_cases/<skill>.json`.
3. The next pipeline run auto-includes it — no registration step required.

## Skill Count
`skill_runner/skills/` currently contains 17 skill folders. The primary distillation target is `docx`. When adding a new distillable skill, ALSO create its evaluator (see `evaluation-rules.md`).
