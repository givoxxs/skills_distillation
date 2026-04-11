"""CLI entry point for the Skill Distillation pipeline.

Usage:
    cd distillation/
    python run.py --skill docx --rounds 3 --test-cases 5 --verbose
    python run.py --skill docx --rounds 5 --batch-size 3 --student qwen/qwen3-8b
    python run.py --skill docx --dry-run
    python run.py --skill docx --no-llm-judge --batch-size 0   # no batching

Config defaults are loaded from config.yaml in this directory.
All CLI flags override the config file.
"""

import json
import logging
import os
import sys
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

_CONFIG_FILE = Path(__file__).parent / "config.yaml"


def _load_config() -> dict:
    """Load config.yaml and return the distillation section."""
    if not _CONFIG_FILE.exists():
        return {}
    with open(_CONFIG_FILE) as f:
        data = yaml.safe_load(f) or {}
    return data.get("distillation", {})


@click.command()
@click.option("--skill", "-s", required=True, help="Skill name (e.g. docx, xlsx).")
@click.option(
    "--rounds",
    "-r",
    default=None,
    type=int,
    help="Max distillation rounds. [config: max_rounds]",
)
@click.option(
    "--batch-size",
    "-b",
    default=None,
    type=int,
    help="Test cases per Teacher feedback cycle within a round. "
    "0 = no batching (teacher once per round). [config: batch_size]",
)
@click.option(
    "--test-cases",
    "-n",
    default=None,
    type=int,
    help="Number of test cases to use (taken from top of file). "
    "Default: all test cases.",
)
@click.option(
    "--student",
    default=None,
    help="OpenRouter model ID for Student. [config: student_model]",
)
@click.option(
    "--teacher",
    default=None,
    help="Claude model ID for Teacher. [config: teacher_model]",
)
@click.option(
    "--test-cases-file",
    default=None,
    help="Path to test cases JSON. "
    "Default: ../skill_evaluation/test_cases/<skill>.json.",
)
@click.option(
    "--results-dir",
    default=None,
    help="Directory to save versioned SKILL.md and scores. [config: results_dir]",
)
@click.option(
    "--skills-dir", default=None, help="Override path to skill_runner/skills/."
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Print orchestrator progress in real-time.",
)
@click.option(
    "--runner-verbose",
    is_flag=True,
    default=False,
    help="Also show skill_runner tool calls (very detailed).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Run eval + summarize, but skip Teacher call.",
)
@click.option(
    "--no-llm-judge",
    is_flag=True,
    default=False,
    help="Skip LLM Judge (rule-based only). Faster and cheaper for debugging.",
)
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="Resume from last completed batch (skip already-finished batches in results_dir).",
)
def main(
    skill,
    rounds,
    batch_size,
    test_cases,
    student,
    teacher,
    test_cases_file,
    results_dir,
    skills_dir,
    verbose,
    runner_verbose,
    dry_run,
    no_llm_judge,
    resume,
):
    """Run the Skill Distillation pipeline for one skill."""
    cfg = _load_config()

    logging_cfg = cfg.get("logging", {})

    # ── Logging setup ─────────────────────────────────────────────────────────
    from utils import setup_logging

    setup_logging(
        level=logging_cfg.get("level", "info"),
        eval_detail=logging_cfg.get("eval_detail", True),
        api_calls=logging_cfg.get("api_calls", True),
        results_dir=results_dir or cfg.get("results_dir", "./results"),
        skill=skill,
        stream=True,
    )

    _log = logging.getLogger("distillation")
    _log.info(
        "OPENROUTER_AI_KEY=%s  ANTHROPIC_KEY=%s",
        "SET" if os.environ.get("OPENROUTER_API_KEY") else "MISSING",
        "SET" if os.environ.get("ANTHROPIC_KEY") else "MISSING",
    )

    # Resolve values: CLI flag → config.yaml → hardcoded fallback
    rounds = rounds if rounds is not None else cfg.get("max_rounds", 10)
    batch_size = batch_size if batch_size is not None else cfg.get("batch_size", 5)
    student = student or cfg.get("student_model", "qwen/qwen3-8b")
    teacher = teacher or cfg.get("teacher_model", "claude-haiku-4-5")
    from datetime import datetime as _dt

    _base_results = results_dir or cfg.get("results_dir", "./results")
    results_dir = str(Path(_base_results) / _dt.now().strftime("%d_%m_%Y"))
    use_llm = not no_llm_judge and cfg.get("use_llm_judge", True)
    llm_judge_ensemble = cfg.get("llm_judge_ensemble", 3)
    llm_judge_weight = cfg.get("llm_judge_weight", 0.20)

    # ── Load test cases ───────────────────────────────────────────────────────
    if test_cases_file is None:
        default = Path(__file__).parent / "test_cases" / f"{skill}.json"
        test_cases_file = str(default)

    tc_path = Path(test_cases_file)
    if not tc_path.exists():
        click.echo(f"[ERROR] Test cases file not found: {tc_path}", err=True)
        sys.exit(1)

    all_cases = [
        tc
        for tc in json.loads(tc_path.read_text()).get("test_cases", [])
        if "id" in tc  # filter _comment objects
    ]
    if not all_cases:
        click.echo(f"[ERROR] No test cases found in {tc_path}", err=True)
        sys.exit(1)

    selected = all_cases[:test_cases] if test_cases else all_cases
    click.echo(
        f"Loaded {len(selected)}/{len(all_cases)} test cases from {tc_path.name}"
    )
    click.echo(
        f"Config: rounds={rounds}  batch_size={batch_size}  student={student}  teacher={teacher}"
    )

    # ── Dry-run mode ──────────────────────────────────────────────────────────
    if dry_run:
        import teacher as teacher_mod

        def _dry_rewrite(skill_md_path, key_notes, model=teacher, **kw):
            click.echo("\n[DRY RUN] Teacher prompt preview:")
            click.echo(key_notes[:800])
            click.echo("...\n[DRY RUN] Skipping Claude call. SKILL.md unchanged.")
            return Path(skill_md_path).read_text()

        teacher_mod.rewrite = _dry_rewrite

    # ── Run pipeline ──────────────────────────────────────────────────────────
    import orchestrator

    if resume:
        click.echo(
            "[RESUME] Skipping batches that already have scores.json in results_dir."
        )

    summary = orchestrator.run_distillation(
        skill=skill,
        test_cases=selected,
        student_model=student,
        teacher_model=teacher,
        max_rounds=rounds,
        batch_size=batch_size,
        stop_threshold=cfg.get("stop_threshold", 0.80),
        converge_delta=cfg.get("converge_delta", 0.02),
        converge_k=cfg.get("converge_k", 3),
        results_dir=results_dir,
        skills_dir=skills_dir,
        test_cases_dir=str(tc_path.parent),
        verbose=verbose,
        runner_verbose=runner_verbose,
        use_llm_judge=use_llm,
        llm_judge_ensemble=llm_judge_ensemble,
        llm_judge_weight=llm_judge_weight,
        resume=resume,
    )

    # ── Print final summary ───────────────────────────────────────────────────
    click.echo("\n" + "=" * 50)
    click.echo("DISTILLATION COMPLETE")
    click.echo("=" * 50)
    click.echo(f"Skill:         {summary['skill']}")
    click.echo(f"Batch size:    {summary['batch_size']}")
    click.echo(f"Rounds run:    {summary['rounds_run']}")
    click.echo(f"Final score:   {summary['final_score']:.3f}")
    click.echo(
        f"Best round:    {summary['best_round']} (score={summary['best_score']:.3f})"
    )
    click.echo("\nScore history:")
    for entry in summary["score_history"]:
        bar = "█" * int(entry["avg_score"] * 20)
        click.echo(
            f"  Round {entry['round']:2d} [{entry['n_batches']} batches]: {entry['avg_score']:.3f} {bar}"
        )
    click.echo(f"\nResults saved to: {Path(results_dir) / skill}")


if __name__ == "__main__":
    main()
