"""Command-line interface for DataForge AI."""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

import click

from dataforge import __version__
from dataforge.core.llm import LLMProviderFactory
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState
from dataforge.infrastructure.llm_providers import llm_from_env
from dataforge.shared.config import get_output_dir

__all__ = ["main", "cli", "run_cli_analysis"]


@click.group()
@click.version_option(version=__version__, prog_name="dataforge")
def cli() -> None:
    """DataForge AI - Autonomous Business Intelligence Engine."""


async def _print_event(event: dict[str, Any]) -> None:
    mark = "OK " if event["success"] else "ERR"
    click.echo(
        f"  [{mark}] phase {event['phase']}  {event['agent']:<32} "
        f"{event['duration_s']:>6.2f}s  {str(event['message'])[:90]}"
    )


async def run_cli_analysis(
    dataset_path: Path,
    output_dir: Path,
    use_llm: bool = True,
    query: str | None = None,
    verbose: bool = True,
) -> int:
    """Run one analysis and print a summary. Returns a process exit code."""
    from dataforge.graph.workflow import run_workflow

    output_dir.mkdir(parents=True, exist_ok=True)
    state = GraphState(
        input_dataset_path=str(dataset_path),
        input_query=query,
        output_dir=str(output_dir),
    )
    logger = StructuredLogger(state.execution_id, str(output_dir))
    llm = llm_from_env() if use_llm else None

    click.echo(f"DataForge AI v{__version__}")
    click.echo(f"Dataset: {dataset_path}")
    click.echo(f"Output:  {output_dir}")
    click.echo(
        f"LLM:     {llm.provider_name} / {llm.config.model}"
        if llm
        else "LLM:     off (rule-based; set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable)"
    )
    click.echo("")

    start = time.time()
    final = await run_workflow(
        state, llm_provider=llm, on_event=_print_event if verbose else None, logger=logger
    )
    duration = time.time() - start

    report = final.get("report") or {}
    click.echo("")
    if "ReportingAgent" in final.steps_completed and report.get("html_path"):
        domain = final.get("business_domain") or "general"
        click.echo(f"Analysis complete in {duration:.1f}s  (domain: {domain})")
        click.echo(f"  KPIs:           {len(final.get('discovered_kpis') or [])}")
        click.echo(f"  Insights:       {len(final.get('business_insights') or [])}")
        click.echo(f"  Visualizations: {len(final.get('visualizations') or [])}")
        click.echo(f"  HTML report:    {report['html_path']}")
        click.echo(f"  JSON report:    {report['json_path']}")
        if report.get("pdf_path"):
            click.echo(f"  PDF report:     {report['pdf_path']}")
        if final.steps_skipped:
            click.echo(f"  Skipped:        {', '.join(final.steps_skipped)}")
        click.echo(f"  Logs:           {logger.export_logs()}")
        return 0

    click.echo("Analysis did not complete.", err=True)
    for entry in final.agent_history:
        result = (entry.metadata or {}).get("result", {})
        if not result.get("success", True):
            click.echo(f"  - {entry.agent_name}: {entry.message or result.get('error')}", err=True)
    return 1


@cli.command()
@click.argument("dataset_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory (default: ./output/<dataset_name>)",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["anthropic", "openai"]),
    default=None,
    help="LLM provider (default: first one with an API key in the environment)",
)
@click.option("--model", "-m", type=str, default=None, help="LLM model override")
@click.option("--no-llm", is_flag=True, help="Run the deterministic rule-based path only")
@click.option("--query", "-q", type=str, default=None, help="Optional business question")
@click.option("--quiet", is_flag=True, help="Hide per-agent progress")
def analyze(
    dataset_path: Path,
    output: Path | None,
    provider: str | None,
    model: str | None,
    no_llm: bool,
    query: str | None,
    quiet: bool,
) -> None:
    """Analyze a dataset autonomously.

    DATASET_PATH: CSV, Excel, Parquet or JSON file.
    """
    if provider:
        os.environ["LLM_PROVIDER"] = provider
    if model:
        os.environ["LLM_MODEL"] = model
    output_dir = output or get_output_dir(str(dataset_path))
    try:
        code = asyncio.run(
            run_cli_analysis(dataset_path, output_dir, not no_llm, query, not quiet)
        )
    except KeyboardInterrupt:
        click.echo("Interrupted.", err=True)
        code = 130
    except Exception as e:
        click.echo(f"Workflow execution failed: {type(e).__name__}: {e}", err=True)
        code = 1
    sys.exit(code)


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo(f"DataForge AI v{__version__}")
    click.echo(f"Python {sys.version}")


@cli.command()
def providers() -> None:
    """List available LLM providers."""
    click.echo("Available LLM providers:")
    for name in LLMProviderFactory.list_providers():
        click.echo(f"  - {name}")


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
