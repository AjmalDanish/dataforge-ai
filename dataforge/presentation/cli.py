"""Command-line interface bootstrap for DataForge AI."""

import sys
from pathlib import Path
from typing import Any

import click

from dataforge.core.llm import LLMConfig, LLMProviderFactory
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState

# Import providers to register them
from dataforge.infrastructure.llm_providers import AnthropicProvider, OpenAIProvider
from dataforge.shared.config import get_output_dir, settings
from dataforge.shared.errors import ConfigurationError, DataForgeError

__all__ = ["main"]


@click.group()
@click.version_option(version="0.1.0", prog_name="dataforge")
def cli() -> None:
    """DataForge AI - Autonomous Multi-Agent Data Science Platform."""
    pass


@cli.command()
@click.argument(
    "dataset_path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
)
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
    type=click.Choice(["openai", "anthropic"]),
    default=None,
    help=f"LLM provider (default: {settings.llm_provider})",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default=None,
    help=f"LLM model (default: {settings.llm_model})",
)
@click.option(
    "--query",
    "-q",
    type=str,
    default=None,
    help="Optional query for targeted analysis",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
def analyze(
    dataset_path: Path,
    output: Path | None,
    provider: str | None,
    model: str | None,
    query: str | None,
    verbose: bool,
) -> None:
    """Analyze a dataset autonomously.

    DATASET_PATH: Path to the dataset file (CSV or Parquet).
    """
    try:
        # Determine output directory
        if output is None:
            output_dir = get_output_dir(str(dataset_path))
        else:
            output_dir = output
            output_dir.mkdir(parents=True, exist_ok=True)

        click.echo(f"DataForge AI v{settings.app_version}")
        click.echo(f"Dataset: {dataset_path}")
        click.echo(f"Output: {output_dir}")
        click.echo("")

        # Create initial state
        state = GraphState(
            input_dataset_path=str(dataset_path),
            input_query=query,
            output_dir=str(output_dir),
        )

        # Initialize logger
        logger = StructuredLogger(state.execution_id, str(output_dir))

        logger.info("Starting DataForge analysis", dataset=str(dataset_path))

        # Configure LLM
        llm_config = LLMConfig(
            provider=provider or settings.llm_provider,
            model=model or settings.llm_model,
            api_key=_get_api_key(provider or settings.llm_provider),
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
        )

        logger.info(
            "LLM configured",
            provider=llm_config.provider,
            model=llm_config.model,
        )

        # Create LLM provider
        llm_provider = LLMProviderFactory.create(llm_config)

        logger.info("LLM provider created", provider=llm_provider.provider_name)

        # TODO: Execute workflow (will be implemented in next phase)
        click.echo("⚠ Infrastructure is complete. Workflow execution coming in next phase.")

        # Export logs
        log_file = logger.export_logs()
        logger.info("Logs exported", log_file=str(log_file))

        click.echo("")
        click.echo(f"✓ Logs saved to: {log_file}")

    except ConfigurationError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except DataForgeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo(f"DataForge AI v{settings.app_version}")
    click.echo(f"Python {sys.version}")


@cli.command()
def providers() -> None:
    """List available LLM providers."""
    click.echo("Available LLM providers:")
    for provider in LLMProviderFactory.list_providers():
        click.echo(f"  - {provider}")


def _get_api_key(provider: str) -> str | None:
    """Get API key for provider from environment or settings.

    Args:
        provider: Provider name.

    Returns:
        API key or None.
    """
    import os

    if provider == "openai":
        return os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    elif provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
    return None


def main() -> None:
    """Main entry point for the CLI."""
    cli()
