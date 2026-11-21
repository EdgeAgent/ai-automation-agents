"""Command-line interface for the AI Automation Agents recipes.

Mirrors the Step 1 starter kit's CLI style (Typer + Rich tables). Every
``run`` and ``pipeline`` command executes on fake providers with ``--demo``;
live runs are wired in code with a real provider, so the CLI fails closed
with an explanation instead of silently doing nothing.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from ai_automation_agents import __version__
from ai_automation_agents.demo import run_full_demo, run_pipeline_demo, run_recipe_demo
from ai_automation_agents.router import RECIPES, RECIPES_BY_NAME

app = typer.Typer(no_args_is_help=True, help="Run production-pattern AI agent recipes.")
console = Console()

PIPELINES = ("research-digest", "triage-leads")


def _require_demo(demo: bool) -> None:
    if not demo:
        console.print(
            "The CLI runs recipes on fake providers with --demo. "
            "For live runs, wire a real provider in code — see docs/architecture.md.",
            style="yellow",
        )
        raise typer.Exit(code=1)


@app.command("recipes")
def list_recipes() -> None:
    """List the twelve recipes in build order."""
    table = Table(title="AI Automation Agents — recipes in build order")
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Recipe", style="cyan")
    table.add_column("What it does")
    table.add_column("Provider")
    table.add_column("Sends anything?")
    for recipe in RECIPES:
        table.add_row(
            f"{recipe.number:02d}",
            recipe.name,
            recipe.description,
            recipe.provider,
            recipe.sends,
        )
    console.print(table)


@app.command("run")
def run_recipe(
    name: str = typer.Argument(..., help="Recipe name, e.g. inbox-triage."),
    demo: bool = typer.Option(False, "--demo", help="Run on fake providers with sample data."),
) -> None:
    """Run one recipe's demo end to end."""
    if name not in RECIPES_BY_NAME:
        choices = ", ".join(sorted(RECIPES_BY_NAME))
        raise typer.BadParameter(f"Unknown recipe {name!r}. Available: {choices}")
    _require_demo(demo)
    # markup=False: recipe output contains [source] citations that Rich
    # would otherwise swallow as style tags.
    console.print(run_recipe_demo(name), markup=False)


@app.command("pipeline")
def run_pipeline(
    name: str = typer.Argument(..., help="Pipeline name: research-digest or triage-leads."),
    demo: bool = typer.Option(False, "--demo", help="Run on fake providers with sample data."),
) -> None:
    """Run one reference pipeline end to end."""
    if name not in PIPELINES:
        raise typer.BadParameter(f"Unknown pipeline {name!r}. Available: {', '.join(PIPELINES)}")
    _require_demo(demo)
    console.print(run_pipeline_demo(name), markup=False)


@app.command("demo")
def demo() -> None:
    """Run the headline recipes and both pipelines on fakes, with a summary."""
    console.print(run_full_demo(), markup=False)


@app.command()
def version() -> None:
    """Print the installed ai-automation-agents version."""
    console.print(__version__)
