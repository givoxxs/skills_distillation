"""
Skill Runner CLI

Usage examples:

    # Run a specific skill with a specific model
    python main.py run --skill pdf --model qwen/qwen3-8b --prompt "Create a PDF titled 'Hello World'"

    # Run without a skill (bare tools)
    python main.py run --model qwen/qwen3-8b --prompt "Create a file hello.txt with 'Hello World'"

    # Run batch evaluation
    python main.py eval --skill pdf --models qwen/qwen3-8b,qwen/qwen3-14b --test-cases ./test_cases/pdf.json

    # List available skills
    python main.py list-skills

    # Show recent logs
    python main.py logs --skill pdf
"""

import json
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

load_dotenv()

console = Console()


@click.group()
def cli() -> None:
    """Skill Runner — run Anthropic-style skills on small models via OpenRouter."""


@cli.command()
@click.option(
    "--skill",
    "-s",
    default=None,
    help="Skill name (folder in ./skills/). Omit for bare tools.",
)
@click.option(
    "--model",
    "-m",
    default="qwen/qwen3-8b",
    show_default=True,
    help="OpenRouter model ID.",
)
@click.option("--prompt", "-p", required=True, help="Task prompt for the model.")
@click.option(
    "--input",
    "-i",
    "input_files",
    multiple=True,
    help="Input file(s) to copy into workspace before run. Can be repeated.",
)
@click.option(
    "--max-iterations",
    default=20,
    show_default=True,
    help="Maximum agent loop iterations.",
)
@click.option(
    "--timeout", default=60, show_default=True, help="Bash tool timeout (seconds)."
)
@click.option(
    "--verbose", "-v", is_flag=True, default=False, help="Show tool calls in real-time."
)
@click.option("--skills-dir", default="./skills", show_default=True)
@click.option("--workspace-dir", default="./workspace", show_default=True)
@click.option("--log-dir", default="./logs", show_default=True)
@click.option(
    "--output-dir",
    default=None,
    help="Copy output files here after run (for evaluation). E.g. ./outputs/docx/tc_01/round_1",
)
def run(
    skill: str | None,
    model: str,
    prompt: str,
    input_files: tuple[str, ...],
    max_iterations: int,
    timeout: int,
    verbose: bool,
    skills_dir: str,
    workspace_dir: str,
    log_dir: str,
    output_dir: str | None,
) -> None:
    """Run a single task with the agent."""
    import shutil
    from config import RunConfig
    from runner.agent_loop import run_agent

    config = RunConfig(
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        model=model,
        max_iterations=max_iterations,
        bash_timeout=timeout,
        verbose=verbose,
        skills_dir=skills_dir,
        workspace_dir=workspace_dir,
        log_dir=log_dir,
        output_dir=output_dir,
    )

    # Copy input files into workspace BEFORE agent_loop cleans it.
    # agent_loop._clean_workspace preserves files listed in config.input_files.
    if input_files:
        ws = Path(workspace_dir)
        ws.mkdir(parents=True, exist_ok=True)
        for src in input_files:
            src_path = Path(src)
            if not src_path.exists():
                console.print(f"[bold red]Input file not found:[/bold red] {src}")
                sys.exit(1)
            dest = ws / src_path.name
            shutil.copy2(src_path, dest)
            if verbose:
                console.print(f"[dim]Copied input:[/dim] {src_path.name} → workspace/")
        config.input_files = [Path(f).name for f in input_files]

    try:
        result = run_agent(
            user_prompt=prompt,
            skill_name=skill,
            model=model,
            config=config,
        )
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    # Display result summary
    table = Table(title="Run Result", show_header=False)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value")
    table.add_row("Stop reason", result["stop_reason"])
    table.add_row("Iterations", str(result["iterations"]))
    table.add_row("Duration", f"{result['duration_seconds']}s")
    table.add_row("Prompt tokens", str(result["token_usage"]["prompt"]))
    table.add_row("Completion tokens", str(result["token_usage"]["completion"]))
    if result.get("output_files"):
        table.add_row("Output files", "\n".join(result["output_files"]))
    console.print(table)

    # Show final assistant message if any
    for msg in reversed(result["messages"]):
        if msg["role"] == "assistant" and msg.get("content"):
            console.print(Panel(msg["content"][:500], title="Final message"))
            break


@cli.command()
@click.option("--skill", "-s", required=True, help="Skill name to evaluate.")
@click.option("--models", "-m", required=True, help="Comma-separated model IDs.")
@click.option(
    "--test-cases",
    "-t",
    required=True,
    type=click.Path(exists=True),
    help="JSON file with test cases.",
)
@click.option("--verbose", "-v", is_flag=True, default=False)
def eval(skill: str, models: str, test_cases: str, verbose: bool) -> None:
    """Batch evaluation: run multiple models on a skill's test cases."""
    from config import RunConfig
    from runner.agent_loop import run_agent

    with open(test_cases, encoding="utf-8") as f:
        cases = json.load(f)

    model_list = [m.strip() for m in models.split(",")]
    all_results = []

    for model in model_list:
        for i, case in enumerate(cases):
            console.print(
                f"[bold]Model:[/bold] {model} | [bold]Case {i + 1}/{len(cases)}:[/bold] {case['prompt'][:80]}"
            )
            config = RunConfig(
                api_key=os.getenv("OPENROUTER_API_KEY", ""),
                model=model,
                verbose=verbose,
            )
            try:
                result = run_agent(
                    user_prompt=case["prompt"],
                    skill_name=skill,
                    model=model,
                    config=config,
                )
                result["test_case"] = case
                all_results.append(result)
                console.print(
                    f"  → {result['stop_reason']} in {result['iterations']} iterations"
                )
            except Exception as e:
                console.print(f"  [red]FAILED:[/red] {e}")

    # Summary table
    table = Table(title="Eval Summary")
    table.add_column("Model")
    table.add_column("Stop reason")
    table.add_column("Iterations")
    table.add_column("Duration(s)")
    for r in all_results:
        table.add_row(
            r["model"],
            r["stop_reason"],
            str(r["iterations"]),
            str(r["duration_seconds"]),
        )
    console.print(table)


@cli.command("list-skills")
@click.option("--skills-dir", default="./skills", show_default=True)
def list_skills(skills_dir: str) -> None:
    """List all available skill folders."""
    skills_path = Path(skills_dir)
    if not skills_path.exists():
        console.print(f"[red]Skills directory not found:[/red] {skills_dir}")
        sys.exit(1)

    table = Table(title="Available Skills")
    table.add_column("Skill", style="cyan")
    table.add_column("Files")
    table.add_column("Has scripts")

    for d in sorted(skills_path.iterdir()):
        if not d.is_dir():
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        files = list(d.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        has_scripts = "yes" if any(d.rglob("*.py")) or any(d.rglob("*.sh")) else "no"
        table.add_row(d.name, str(file_count), has_scripts)

    console.print(table)


@cli.command()
@click.option("--skill", "-s", default=None, help="Filter by skill name.")
@click.option("--log-dir", default="./logs", show_default=True)
@click.option("--last", default=10, show_default=True, help="Show last N log files.")
def logs(skill: str | None, log_dir: str, last: int) -> None:
    """Show recent log files."""
    log_path = Path(log_dir)
    if not log_path.exists():
        console.print("[red]No logs directory found.[/red]")
        return

    all_logs = sorted(
        log_path.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True
    )
    if skill:
        all_logs = [f for f in all_logs if f.name.startswith(skill + "_")]

    for log_file in all_logs[:last]:
        console.print(f"\n[bold cyan]{log_file.name}[/bold cyan]")
        with open(log_file, encoding="utf-8") as fh:
            for line in fh:
                record = json.loads(line)
                event = record.get("event", "")
                if event == "start":
                    console.print(
                        f"  [green]START[/green] model={record.get('model')} skill={record.get('skill')}"
                    )
                elif event == "end":
                    console.print(
                        f"  [blue]END[/blue] stop_reason={record.get('stop_reason')} iterations={record.get('iterations')} duration={record.get('duration_seconds')}s"
                    )
                elif event == "tool_call":
                    console.print(
                        f"  [yellow]TOOL[/yellow] [{record.get('iteration')}] {record.get('tool')}"
                    )
                elif event == "api_error":
                    console.print(f"  [red]ERROR[/red] {record.get('error')}")


if __name__ == "__main__":
    cli()
