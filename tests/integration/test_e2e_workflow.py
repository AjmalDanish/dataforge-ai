"""End-to-end integration tests for the complete v2 workflow."""

import json
from pathlib import Path

import pytest

from dataforge.core.llm import LLMConfig, LLMMessage, LLMProvider, LLMResponse
from dataforge.core.state import GraphState
from dataforge.graph.workflow import run_workflow

EMPLOYEES = """id,name,age,department,salary,years_of_service,performance_score,remote_worker
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
11,Kara Wu,36,Engineering,88000.0,9,8.9,True
12,Liam Ford,27,Sales,58000.0,1,6.9,False
"""

PRODUCTS = """product_id,product_name,category,price,stock_quantity,sold_quantity,customer_rating,reviews_count
1,Laptop Pro,Electronics,1299.99,45,120,4.5,234
2,Wireless Mouse,Electronics,29.99,200,450,4.2,567
3,Office Chair,Furniture,249.99,30,85,4.7,123
4,Standing Desk,Furniture,599.99,15,42,4.6,89
5,USB-C Hub,Electronics,49.99,150,320,4.1,412
6,Bookshelf,Furniture,129.99,25,60,4.3,76
7,Monitor 27in,Electronics,349.99,60,140,4.6,298
8,Desk Lamp,Furniture,39.99,90,210,4.0,154
"""


class FakeLLM(LLMProvider):
    """Deterministic provider: classifies domains and writes narratives."""

    def __init__(self) -> None:
        super().__init__(LLMConfig(provider="fake", model="fake-1", api_key="x"))
        self.calls: list[list[LLMMessage]] = []

    async def generate(self, messages, config=None) -> LLMResponse:
        self.calls.append(messages)
        prompt = messages[-1].content
        if "Which business domain" in prompt:
            content = "retail"
        elif messages[0].role == "system" and "executive" in messages[0].content:
            content = json.dumps(
                {
                    "narrative": "Revenue is concentrated in electronics.",
                    "recommendations": ["Restock top sellers", "Review furniture pricing"],
                }
            )
        else:
            content = "{}"
        return LLMResponse(content=content, model="fake-1", provider="fake")


async def _run(tmp_path: Path, csv: str, name: str = "data.csv", **kwargs) -> GraphState:
    dataset = tmp_path / name
    dataset.write_text(csv, encoding="utf-8")
    out = tmp_path / "output"
    state = GraphState(input_dataset_path=str(dataset), output_dir=str(out))
    return await run_workflow(state, **kwargs)


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Full pipeline runs on small in-memory datasets."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_employee_data(self, tmp_path):
        events: list[dict] = []

        async def collect(event: dict) -> None:
            events.append(event)

        final = await _run(tmp_path, EMPLOYEES, on_event=collect)

        steps = final.steps_completed
        for agent in (
            "DataValidationAgent",
            "DataCleaningAgent",
            "SchemaDetectionAgent",
            "BusinessDomainDetectionAgent",
            "DataProfilingAgent",
            "KPIDiscoveryAgent",
            "StatisticalAnalysisAgent",
            "InsightGenerationAgent",
            "VisualizationAgent",
            "EvaluatorAgent",
            "ReportingAgent",
        ):
            assert agent in steps, f"{agent} did not run"
        assert [s for s in steps if s != "PlannerAgent"][-1] == "ReportingAgent"
        assert final.steps_skipped == []
        assert final.current_phase == 7
        assert final.end_time is not None

        cleaned = final.get("cleaned_data")
        assert len(cleaned) == 12
        assert final.get("business_domain") == "hr"
        assert final.get("profile")["n_rows"] == 12
        assert len(final.get("statistics")["descriptive_stats"]) > 0
        assert len(final.get("discovered_kpis")) > 0
        assert len(final.get("business_insights")) > 0
        assert final.get("evaluation")["passed"] is True

        report = final.get("report")
        html = Path(report["html_path"]).read_text(encoding="utf-8")
        assert "Executive Summary" in html
        assert json.loads(Path(report["json_path"]).read_text(encoding="utf-8"))
        assert report["pdf_available"] is True
        assert Path(report["pdf_path"]).read_bytes()[:4] == b"%PDF"

        viz_dir = tmp_path / "output" / "visualizations"
        charts = list(viz_dir.glob("*.html"))
        assert charts
        # Charts share one plotly bundle instead of embedding ~5 MB each.
        assert (viz_dir / "plotly.min.js").exists()
        assert all(c.stat().st_size < 500_000 for c in charts)

        # One event per agent step, in pipeline order, no planner noise.
        assert [e["agent"] for e in events] == [s for s in steps if s != "PlannerAgent"]
        assert all(e["success"] for e in events)
        phases = [e["phase"] for e in events]
        assert phases == sorted(phases)

    @pytest.mark.asyncio
    async def test_complete_workflow_with_product_data(self, tmp_path):
        final = await _run(tmp_path, PRODUCTS)
        assert "ReportingAgent" in final.steps_completed
        assert final.get("business_domain") == "retail"
        assert Path(final.get("report")["html_path"]).exists()

    @pytest.mark.asyncio
    async def test_workflow_with_missing_values(self, tmp_path):
        csv = "id,name,age,salary\n" + "\n".join(
            f"{i},Person {i},{'' if i % 4 == 0 else 20 + i},{'' if i % 5 == 0 else 1000 * i}"
            for i in range(1, 21)
        )
        final = await _run(tmp_path, csv)
        assert "ReportingAgent" in final.steps_completed
        assert final.get("raw_data").isna().sum().sum() > 0
        assert final.get("cleaning_report") is not None

    @pytest.mark.asyncio
    async def test_workflow_with_all_numeric_data(self, tmp_path):
        csv = "x,y,z\n" + "\n".join(f"{i},{i * 2 + 1},{(i * 7) % 11}" for i in range(1, 25))
        final = await _run(tmp_path, csv)
        profile = final.get("profile")
        assert profile["has_numeric_columns"] is True
        assert profile["has_categorical_columns"] is False
        assert "descriptive_stats" in final.get("statistics")
        assert "ReportingAgent" in final.steps_completed

    @pytest.mark.asyncio
    async def test_llm_provider_drives_domain_and_narrative(self, tmp_path):
        llm = FakeLLM()
        csv = "a,b,c\n" + "\n".join(f"{i},{i * 3},{i % 4}" for i in range(1, 30))
        final = await _run(tmp_path, csv, llm_provider=llm)

        # Rule-based detection has no signal here, so the LLM breaks the tie.
        assert final.get("business_domain") == "retail"
        assert final.get("domain_detection_method") == "llm"
        assert final.get("executive_narrative")["recommendations"] == [
            "Restock top sellers",
            "Review furniture pricing",
        ]
        html = Path(final.get("report")["html_path"]).read_text(encoding="utf-8")
        assert "Revenue is concentrated in electronics." in html
        assert "Recommended Actions" in html

    @pytest.mark.asyncio
    async def test_report_escapes_hostile_column_names(self, tmp_path):
        csv = '"<script>alert(1)</script>",amount\n' + "\n".join(
            f"x{i},{i * 10}" for i in range(1, 15)
        )
        final = await _run(tmp_path, csv)
        html = Path(final.get("report")["html_path"]).read_text(encoding="utf-8")
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    @pytest.mark.asyncio
    async def test_unreadable_file_ends_without_report(self, tmp_path):
        final = await _run(tmp_path, "", name="empty.csv")
        assert "ReportingAgent" not in final.steps_completed
        assert final.get("cleaned_data") is None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("fmt", ["xlsx", "json", "parquet"])
async def test_non_csv_formats(tmp_path, fmt):
    import io

    import pandas as pd

    frame = pd.read_csv(io.StringIO(PRODUCTS))
    path = tmp_path / f"products.{fmt}"
    {"xlsx": lambda: frame.to_excel(path, index=False),
     "json": lambda: frame.to_json(path, orient="records"),
     "parquet": lambda: frame.to_parquet(path)}[fmt]()

    final = await run_workflow(GraphState(input_dataset_path=str(path), output_dir=str(tmp_path / "o")))
    assert "ReportingAgent" in final.steps_completed
    assert len(final.get("cleaned_data")) == 8


@pytest.mark.integration
@pytest.mark.asyncio
async def test_text_column_with_one_date_is_not_destroyed(tmp_path):
    csv = "note,amount\n2021-01-05,10\n" + "\n".join(f"free text {i},{i}" for i in range(20))
    final = await _run(tmp_path, csv)
    assert final.get("cleaned_data")["note"].notna().all()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_writes_only_to_output_dir(tmp_path, monkeypatch):
    """Containers run with a read-only working dir: nothing may be created in cwd."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    dataset = tmp_path / "data.csv"
    dataset.write_text(EMPLOYEES, encoding="utf-8")

    final = await run_workflow(
        GraphState(input_dataset_path=str(dataset), output_dir=str(tmp_path / "out"))
    )

    assert "ReportingAgent" in final.steps_completed
    assert list(cwd.iterdir()) == []
