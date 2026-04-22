---
paths: ["distillation/**/*.py", "distillation/config.yaml", "distillation/run.py"]
---

# Pipeline & Orchestration Rules

## Architecture Flow
The pipeline has a strict layered flow: `run.py` (CLI entry) → `orchestrator.py` (main loop) → `skill_runner` (agent exec) + `evaluator/` (scoring) + `summarizer.py` (failure analysis) → `teacher.py` (SKILL.md rewrite). See `distillation/orchestrator.py` for the exact call sequence.

## Batching & Round Structure
- The Teacher (`teacher.py`) is invoked **per batch**, not per round — SKILL.md is progressively rewritten multiple times within a single round.
- If `batch_size=0` or `batch_size >= len(test_cases)`, the Teacher is called once per round (no intra-round batching).
- NEVER invoke the Teacher outside of the orchestrator's batch loop — doing so breaks the resume/replay model.

## Resume Support
- `_is_batch_complete()` in `orchestrator.py` checks for existing `scores.json` in the output dir.
- YOU MUST preserve this idempotency guarantee when modifying the orchestrator — completed batches must always be skipped on re-run.

## Stopping Criteria
Three conditions stop the pipeline — any one being met is sufficient:
1. `stop_threshold`: average hybrid score ≥ configured value (default 0.70)
2. Convergence: score delta < 0.02 for 3 consecutive rounds
3. `max_rounds` reached

See `distillation/config.yaml` for all default values. CLI flags always override config.yaml.

## Results Layout
Each batch writes output to `distillation/results/DD_MM_YYYY/round_<N>/batch_<M>/`. See `distillation/orchestrator.py` for the exact path-building logic. NEVER hardcode date-based paths in tests.

## Configuration Conventions
- All pipeline defaults live in `distillation/config.yaml`.
- The `RunConfig` dataclass in `skill_runner/config.py` governs single-agent-run params.
- IMPORTANT: Do not duplicate config values between `config.yaml` and `RunConfig` — the orchestrator is responsible for bridging the two.
