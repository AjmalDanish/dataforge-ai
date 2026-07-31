#!/usr/bin/env python3
"""Entry point for running DataForge AI from command line."""

import sys
import asyncio

from pathlib import Path

# Try to import from the dataforge package
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from dataforge.presentation.cli import analyze_sync as run_analysis
    from dataforge.core.state import GraphState
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure dataforge is installed or run with: python -m dataforge")
    sys.exit(1)


async def run_cli_analysis(dataset_path: str) -> int:
    """Run CLI analysis workflow."""
    import sys
    from pathlib import Path
    from dataforge.presentation.cli import analyze
    import click

    dataset_path_obj = Path(dataset_path)

    # Create click context to run analyze function synchronously
    from click.testing import CliRunner

    @click.command()
    @click.argument(
        "dataset_path",
        type=click.Path(exists=True),
        required=True,
    )
    @click.option(
        "--output",
        "-o",
        type=click.Path(path_type=Path),
        default=None,
    )
    @click.option(
        "--verbose",
        "-v",
        is_flag=True,
    )
    def analyze_sync(dataset_path, output, verbose) -> int:
        """Synchronous wrapper."""
        return 0

    runner = CliRunner()
    result = runner.invoke(
        analyze_sync,
        [str(dataset_path), "--output", output or None] + (["--verbose"] if verbose else []),
        standalone_mode=False,
        catch_exceptions=False,
    )

    return result.exit_code or 0


def run_analysis(dataset_path: str) -> int:
    """Run analysis on dataset synchronously.

    Args:
        dataset_path: Path to dataset file.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    import os
    import sys
    from pathlib import Path

    # Set working directory to repository root
    os.chdir(Path(__file__).parent)

    dataset_path_obj = Path(dataset_path)

    if not dataset_path_obj.exists():
        click.echo(f"Error: Dataset not found: {dataset_path}", err=True)
        return 1

    # Set up minimal environment for execution
    if os.getenv("OPENAI_API_KEY") is None:
        # Allow mock execution for demonstration without API keys
        os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"

    return asyncio.run(run_cli_analysis(dataset_path))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py <dataset_path>")
        print("Example: python run.py datasets/employees.csv")
        sys.exit(1)

    dataset_path = sys.argv[1]
    exit_code = run_analysis(dataset_path)
    sys.exit(exit_code)