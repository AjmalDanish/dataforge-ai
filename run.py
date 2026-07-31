#!/usr/bin/env python3
"""Entry point for running DataForge AI from command line."""

import os
import sys
import time
from pathlib import Path


async def run_analysis(dataset_path: str, output_dir: str | None = None) -> int:
    """Run analysis on dataset.

    Args:
        dataset_path: Path to dataset file.
        output_dir: Output directory for reports and visualizations.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
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

            print(f"[OK] Dataset Loaded")
            print(
                f"[OK] Profiling Complete ({len(data.get('profile', {}).get('columns', {}))} columns)"
            )
            print(
                f"[OK] Statistics Complete ({len(data.get('statistics', {}).get('descriptive_stats', {}))} columns analyzed)"
            )
            print(
                f"[OK] Visualizations Generated ({len(data.get('visualizations', []))} interactive charts)"
            )
            print(f"[OK] Report Generated")
            print(f"[OK] Workflow Finished")
            print(f"[OK] Execution duration: {duration:.2f}s")

            # Check for report
            report = data.get("report")
            if report and report.get("html_path"):
                print(f"\n[SUCCESS] Analysis complete!")
                print(f"   HTML Report: {report['html_path']}")
                print(f"   JSON Report: {report['json_path']}")
                print(f"   Visualizations: {output_path}/visualizations/")
                print(f"   Logs: {output_path}/execution_*.log")
                return 0
            else:
                print("\n[WARNING] Analysis completed but no report generated")
                return 1

        except Exception as e:
            print(f"[ERROR] Error: {e}")
            return 1

    except KeyboardInterrupt:
        print("\n[INFO] Analysis interrupted by user")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py <dataset_path> [output_dir]")
        print("\nExample:")
        print("  python run.py datasets/employees.csv")
        print("  python run.py datasets/products.csv ./output")
        sys.exit(1)

    dataset_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    import asyncio

    exit_code = asyncio.run(run_analysis(dataset_path, output_dir))
    sys.exit(exit_code)
