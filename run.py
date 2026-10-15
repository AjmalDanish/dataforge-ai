#!/usr/bin/env python3
"""Convenience entry point: ``python run.py <dataset> [output_dir]``.

Equivalent to ``python -m dataforge analyze <dataset> [-o output_dir]``.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dataforge.presentation.cli import run_cli_analysis  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py <dataset_path> [output_dir]")
        print("Example: python run.py datasets/employees.csv ./output/employees")
        sys.exit(1)
    dataset = Path(sys.argv[1])
    if not dataset.exists():
        print(f"Dataset not found: {dataset}")
        sys.exit(1)
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output") / dataset.stem
    sys.exit(asyncio.run(run_cli_analysis(dataset, output)))
