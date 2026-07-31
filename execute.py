#!/usr/bin/env python3
"""Direct workflow executor for DataForge AI v1.0.0"""

import asyncio
import os
import sys
import time
import pandas as pd
from pathlib import Path


async def run_analysis(
    dataset_path: str, output_dir: str | None = None, verbose: bool = False
) -> int:
    """Execute DataForge AI analysis on a dataset.

    Args:
        dataset_path: Path to dataset file (CSV or Parquet).
        output_dir: Output directory for reports and visualizations.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    import sys
    from pathlib import Path

    # Set up environment
    os.environ.setdefault("OPENAI_API_KEY", "sk-dummy-key-for-testing")

    # Add dataforge to path
    sys.path.insert(0, str(Path(__file__).parent))

    try:
        # Import dataforge components
        from dataforge.graph.workflow import create_graph
        from dataforge.core.state import GraphState
        from dataforge.core.logger import StructuredLogger

        # Set up output directory
        dataset_obj = Path(dataset_path)
        if output_dir is None:
            output_dir = str(dataset_obj.parent / "output")
        else:
            output_dir = output_dir

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create state
        state = GraphState(
            input_dataset_path=dataset_path,
            output_dir=output_dir,
        )

        # Initialize logger
        logger = StructuredLogger("cli", output_dir)

        # Create workflow
        workflow = create_graph()

        print(f"DataForge AI v1.0.0")
        print(f"Dataset: {dataset_path}")
        print(f"Output: {output_dir}")
        print(f"Starting analysis...")
        print("")

        # Execute workflow
        start_time = time.time()

        try:
            # Execute workflow with recursion limit
            final_state = await workflow.ainvoke(state, {"recursion_limit": 25})

            duration = time.time() - start_time

            # Print results summary
            steps_completed = final_state.get("steps_completed", [])
            data = final_state.get("data", {})

            print(f"✓ Dataset Loaded")
            print(
                f"✓ Profiling Complete ({len(data.get('profile', {}).get('columns', {}))} columns)"
            )
            print(
                f"✓ Statistics Complete ({len(data.get('statistics', {}).get('descriptive_stats', {}))} columns analyzed)"
            )
            print(
                f"✓ Visualizations Generated ({len(data.get('visualizations', []))} interactive charts)"
            )
            print(f"✓ Report Generated")
            print(f"✓ Workflow Finished")
            print(f"✓ Execution duration: {duration:.2f}s")

            # Check for report
            report = data.get("report")
            if report and report.get("html_path"):
                print(f"\n📊 Analysis complete!")
                print(f"   HTML Report: {report['html_path']}")
                print(f"   JSON Report: {report['json_path']}")
                print(f"   Visualizations: {output_path}/visualizations/")
                print(f"   Logs: {output_path}/execution_*.log")
                return 0
            else:
                print("\n⚠️ Analysis completed but no report generated")
                return 1

        except Exception as e:
            print(f"❌ Error: {e}")
            if verbose:
                import traceback

                traceback.print_exc()
            return 1

    except KeyboardInterrupt:
        print("\n⚠️ Analysis interrupted by user")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python execute.py <dataset_path> [output_dir]")
        print("\nExample:")
        print("  python execute.py datasets/employees.csv")
        print("  python execute.py datasets/products.csv ./output")
        sys.exit(1)

    dataset_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    exit_code = asyncio.run(run_analysis(dataset_path, output_dir))
    sys.exit(exit_code)
