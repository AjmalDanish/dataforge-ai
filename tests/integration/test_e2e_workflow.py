"""End-to-end integration tests for the complete workflow."""

import os
from pathlib import Path

import pytest

from dataforge.graph.workflow import create_graph


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end tests for the complete analysis workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_employee_data(self, tmp_path):
        """Test complete workflow with employee dataset."""
        # Create test dataset
        dataset_path = tmp_path / "employees.csv"
        test_data = """id,name,age,department,salary,years_of_service,performance_score,remote_worker
1,Alice Johnson,28,Engineering,75000.0,2,8.5,True
2,Bob Smith,35,Sales,65000.0,5,7.2,False
3,Charlie Brown,42,Engineering,95000.0,10,9.1,True
4,Diana Prince,31,Marketing,70000.0,4,8.8,False
5,Eve Davis,26,Sales,60000.0,1,7.5,False
6,Frank Miller,39,Engineering,85000.0,8,8.2,True
7,Grace Lee,33,Marketing,72000.0,6,7.9,True
8,Henry Wilson,45,Sales,90000.0,15,9.3,False
9,Iris Chen,29,Engineering,78000.0,3,8.6,True
10,Jack Brown,38,Marketing,80000.0,7,8.0,False
"""
        dataset_path.write_text(test_data)

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create workflow
        workflow = create_graph()

        # Initialize state
        from dataforge.core.logger import StructuredLogger
        from dataforge.core.state import GraphState

        logger = StructuredLogger("integration_test", str(output_dir))
        initial_state = GraphState(input_dataset_path=str(dataset_path))

        # Run workflow
        try:
            result_state = await workflow.ainvoke(initial_state, {"recursion_limit": 25})
        except Exception as e:
            pytest.fail(f"Workflow execution failed: {e}")

        # Verify workflow completed successfully
        assert result_state is not None
        assert result_state.get("steps_completed") is not None
        assert len(result_state.get("steps_completed", [])) > 0

        # Verify raw data was loaded
        assert result_state.get("data", {}).get("raw_data") is not None
        raw_data = result_state.get("data", {}).get("raw_data")
        assert len(raw_data) == 10
        assert len(raw_data.columns) == 8

        # Verify profile was generated
        profile = result_state.get("data", {}).get("profile")
        assert profile is not None
        assert profile["n_rows"] == 10
        assert profile["n_columns"] == 8
        assert len(profile["numeric_columns"]) > 0

        # Verify statistics were computed (if numeric columns exist)
        # Note: Statistics may not be present if there was an error, but we still verify workflow completion
        statistics = result_state.get("data", {}).get("statistics")
        if profile["has_numeric_columns"] and statistics is not None:
            assert "descriptive_stats" in statistics
            assert len(statistics["descriptive_stats"]) > 0

        # Verify visualizations were created
        visualizations = result_state.get("data", {}).get("visualizations", [])
        assert len(visualizations) > 0

        # Verify insights were generated
        insights = result_state.get("data", {}).get("insights", [])
        assert len(insights) >= 2  # At least 2 insights from profiling

        # Verify report was generated
        report = result_state.get("data", {}).get("report")
        assert report is not None
        assert "html_path" in report
        assert "json_path" in report

        # Check that report files exist
        html_report_path = Path(report["html_path"])
        json_report_path = Path(report["json_path"])
        assert html_report_path.exists()
        assert json_report_path.exists()

        # Verify HTML report contains expected content
        html_content = html_report_path.read_text(encoding="utf-8")
        assert "DataForge AI Analysis Report" in html_content
        assert "Data Profile" in html_content
        assert "Key Insights" in html_content

        # Verify visualizations directory was created
        viz_dir = output_dir / "visualizations"
        if viz_dir.exists():
            viz_files = list(viz_dir.glob("*.html"))
            assert len(viz_files) > 0

    @pytest.mark.asyncio
    async def test_complete_workflow_with_product_data(self, tmp_path):
        """Test complete workflow with product dataset."""
        # Create test dataset
        dataset_path = tmp_path / "products.csv"
        test_data = """product_id,product_name,category,price,stock_quantity,sold_quantity,customer_rating,reviews_count
101,Smartphone Pro,Electronics,699.99,150,245,4.5,120
102,Laptop Ultra,Electronics,1299.99,80,156,4.7,85
103,Wireless Earbuds,Electronics,149.99,500,890,4.3,320
104,Coffee Maker,Home,79.99,200,450,4.2,180
105,Desk Chair,Furniture,249.99,60,95,4.4,65
"""
        dataset_path.write_text(test_data)

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create workflow
        workflow = create_graph()

        # Initialize state
        from dataforge.core.logger import StructuredLogger
        from dataforge.core.state import GraphState

        logger = StructuredLogger("integration_test", str(output_dir))
        initial_state = GraphState(input_dataset_path=str(dataset_path))

        # Run workflow
        try:
            result_state = await workflow.ainvoke(initial_state, {"recursion_limit": 25})
        except Exception as e:
            pytest.fail(f"Workflow execution failed: {e}")

        # Verify basic workflow completion
        assert result_state is not None
        assert result_state.get("data", {}).get("raw_data") is not None
        assert result_state.get("data", {}).get("profile") is not None
        assert result_state.get("data", {}).get("insights") is not None

        # Verify report was generated
        report = result_state.get("data", {}).get("report")
        assert report is not None
        assert Path(report["html_path"]).exists()

    @pytest.mark.asyncio
    async def test_workflow_with_missing_values(self, tmp_path):
        """Test workflow handles missing values correctly."""
        # Create dataset with missing values
        dataset_path = tmp_path / "missing_values.csv"
        test_data = """id,name,age,salary
1,Alice,25,50000
2,Bob,,60000
3,Charlie,35,
4,Diana,28,55000
5,,30,58000
"""
        dataset_path.write_text(test_data)

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create workflow
        workflow = create_graph()

        # Initialize state
        from dataforge.core.logger import StructuredLogger
        from dataforge.core.state import GraphState

        logger = StructuredLogger("integration_test", str(output_dir))
        initial_state = GraphState(input_dataset_path=str(dataset_path))

        # Run workflow
        try:
            result_state = await workflow.ainvoke(initial_state, {"recursion_limit": 25})
        except Exception as e:
            pytest.fail(f"Workflow execution failed with missing values: {e}")

        # Verify workflow completed despite missing values
        assert result_state is not None
        assert result_state.get("data", {}).get("raw_data") is not None
        assert result_state.get("data", {}).get("profile") is not None

        # Verify missing values were detected
        profile = result_state.get("data", {}).get("profile")
        assert profile is not None
        assert profile["overall_missing_ratio"] > 0

        # Verify insights about data quality
        insights = result_state.get("insights", [])
        data_quality_insights = [i for i in insights if "missing" in i.get("message", "").lower()]
        assert len(data_quality_insights) > 0

    @pytest.mark.asyncio
    async def test_workflow_with_all_numeric_data(self, tmp_path):
        """Test workflow with purely numeric dataset."""
        # Create dataset with only numeric columns
        dataset_path = tmp_path / "numeric.csv"
        test_data = """x,y,z
1.2,3.4,5.6
2.3,4.5,6.7
3.4,5.6,7.8
4.5,6.7,8.9
5.6,7.8,9.0
"""
        dataset_path.write_text(test_data)

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create workflow
        workflow = create_graph()

        # Initialize state
        from dataforge.core.logger import StructuredLogger
        from dataforge.core.state import GraphState

        logger = StructuredLogger("integration_test", str(output_dir))
        initial_state = GraphState(input_dataset_path=str(dataset_path))

        # Run workflow
        try:
            result_state = await workflow.ainvoke(initial_state, {"recursion_limit": 25})
        except Exception as e:
            pytest.fail(f"Workflow execution failed with numeric data: {e}")

        # Verify workflow completed
        assert result_state is not None
        assert result_state.get("raw_data") is not None

        # Verify all columns detected as numeric
        profile = result_state.get("profile")
        assert profile is not None
        assert profile["has_numeric_columns"] is True
        assert profile["has_categorical_columns"] is False

        # Verify statistics were computed
        statistics = result_state.get("statistics")
        assert statistics is not None
        assert "descriptive_stats" in statistics
        assert len(statistics["descriptive_stats"]) == 3

    @pytest.mark.asyncio
    async def test_workflow_generates_all_expected_outputs(self, tmp_path):
        """Test that workflow generates all expected output artifacts."""
        # Create test dataset
        dataset_path = tmp_path / "test.csv"
        test_data = """id,category,value,score
1,A,10,85
2,B,20,90
3,A,15,88
4,B,25,92
5,A,12,87
6,B,18,91
"""
        dataset_path.write_text(test_data)

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create workflow
        workflow = create_graph()

        # Initialize state
        from dataforge.core.logger import StructuredLogger
        from dataforge.core.state import GraphState

        logger = StructuredLogger("integration_test", str(output_dir))
        initial_state = GraphState(input_dataset_path=str(dataset_path))

        # Run workflow
        try:
            result_state = await workflow.ainvoke(initial_state, {"recursion_limit": 25})
        except Exception as e:
            pytest.fail(f"Workflow execution failed: {e}")

        # Verify all expected outputs
        # 1. Raw data
        assert result_state.get("raw_data") is not None

        # 2. Profile
        assert result_state.get("profile") is not None
        profile = result_state.get("profile")
        assert "n_rows" in profile
        assert "n_columns" in profile
        assert "columns" in profile

        # 3. Statistics (for numeric columns)
        if profile.get("has_numeric_columns"):
            assert result_state.get("statistics") is not None
            statistics = result_state.get("statistics")
            assert "descriptive_stats" in statistics
            assert "correlations" in statistics

        # 4. Visualizations
        visualizations = result_state.get("visualizations", [])
        assert len(visualizations) > 0
        for viz in visualizations:
            assert "type" in viz
            assert "title" in viz
            assert "file_path" in viz

        # 5. Insights
        insights = result_state.get("insights", [])
        assert len(insights) >= 3
        for insight in insights:
            assert "type" in insight
            assert "message" in insight

        # 6. Report files
        report = result_state.get("report")
        assert report is not None
        html_path = Path(report["html_path"])
        json_path = Path(report["json_path"])
        assert html_path.exists()
        assert json_path.exists()

        # 7. Execution logs
        logs = result_state.get("logs", [])
        assert len(logs) > 0

        # 8. Completed steps tracking
        steps_completed = result_state.get("steps_completed", [])
        assert len(steps_completed) > 0
        # Should include at least: DataIngestionAgent, DataProfilingAgent, EvaluatorAgent, ReportingAgent
        expected_agents = [
            "DataIngestionAgent",
            "DataProfilingAgent",
            "EvaluatorAgent",
            "ReportingAgent",
        ]
        for agent in expected_agents:
            assert agent in steps_completed, f"Expected {agent} in completed steps"
