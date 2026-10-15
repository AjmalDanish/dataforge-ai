"""CLI tests (click runner, rule-based path)."""

from click.testing import CliRunner

from dataforge.presentation.cli import cli


def test_analyze_produces_report(tmp_path):
    dataset = tmp_path / "sales.csv"
    dataset.write_text(
        "region,revenue,units\n"
        + "\n".join(f"{['N', 'S'][i % 2]},{100 + i * 7},{i % 9 + 1}" for i in range(30)),
        encoding="utf-8",
    )
    out = tmp_path / "out"

    result = CliRunner().invoke(cli, ["analyze", str(dataset), "-o", str(out), "--no-llm"])

    assert result.exit_code == 0, result.output
    assert "Analysis complete" in result.output
    assert "ReportingAgent" in result.output
    assert (out / "report.html").exists()
    assert (out / "report.pdf").exists()


def test_analyze_failure_exit_code(tmp_path):
    dataset = tmp_path / "empty.csv"
    dataset.write_text("", encoding="utf-8")
    result = CliRunner().invoke(
        cli, ["analyze", str(dataset), "-o", str(tmp_path / "out"), "--no-llm", "--quiet"]
    )
    assert result.exit_code == 1


def test_version_and_providers():
    runner = CliRunner()
    assert "DataForge AI v2.0.0" in runner.invoke(cli, ["version"]).output
    assert "anthropic" in runner.invoke(cli, ["providers"]).output
