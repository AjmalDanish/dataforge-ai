"""Executive PDF report rendering (reportlab, pure Python — no system libraries)."""

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

__all__ = ["pdf_available", "render_executive_pdf"]

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    _REPORTLAB = True
except ImportError:  # pragma: no cover - optional dependency
    _REPORTLAB = False


def pdf_available() -> bool:
    """Whether PDF rendering is possible in this environment."""
    return _REPORTLAB


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return str(value)


def render_executive_pdf(
    path: Path,
    metadata: dict[str, Any],
    executive_summary: dict[str, Any],
    kpis: list[dict[str, Any]],
    business_insights: list[dict[str, Any]],
) -> Path:
    """Write a concise executive PDF (summary, KPIs, findings, actions) to ``path``."""
    if not _REPORTLAB:
        raise RuntimeError("reportlab is not installed")

    styles = getSampleStyleSheet()
    body = styles["BodyText"]

    def para(text: Any, style: Any = body) -> "Paragraph":
        return Paragraph(escape(str(text)), style)

    generated = str(metadata.get("generated_at", ""))[:19].replace("T", " ")
    story: list[Any] = [
        para("DataForge AI — Executive Report", styles["Title"]),
        para(
            f"Domain: {metadata.get('business_domain', 'general')}  ·  "
            f"{_fmt(metadata.get('total_rows', 0))} rows × "
            f"{_fmt(metadata.get('total_columns', 0))} columns  ·  Generated {generated}",
            styles["Italic"],
        ),
        Spacer(1, 6 * mm),
        para("Executive Summary", styles["Heading2"]),
        para(executive_summary.get("headline", "")),
    ]
    if executive_summary.get("narrative"):
        story += [Spacer(1, 2 * mm), para(executive_summary["narrative"])]

    if kpis:
        rows = [["KPI", "Value", "Trend"]] + [
            [para(k.get("name", "")), _fmt(k.get("value", "")), str(k.get("trend", "stable"))]
            for k in kpis[:12]
        ]
        table = Table(rows, colWidths=[95 * mm, 45 * mm, 30 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8d1dc")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f3f6f9")],
                    ),
                ]
            )
        )
        story += [Spacer(1, 5 * mm), para("Key Metrics", styles["Heading2"]), table]

    if business_insights:
        items = []
        for bi in business_insights[:10]:
            text = (
                f"<b>{escape(str(bi.get('title', '')))}</b> "
                f"[{escape(str(bi.get('severity', 'info')))}] — "
                f"{escape(str(bi.get('summary', '')))}"
            )
            if bi.get("business_action"):
                text += f"<br/><i>Action: {escape(str(bi['business_action']))}</i>"
            items.append(ListItem(Paragraph(text, body)))
        story += [
            Spacer(1, 5 * mm),
            para("Findings", styles["Heading2"]),
            ListFlowable(items, bulletType="1"),
        ]

    recommendations = executive_summary.get("recommendations") or []
    if recommendations:
        story += [
            Spacer(1, 5 * mm),
            para("Recommended Actions", styles["Heading2"]),
            ListFlowable([ListItem(para(r)) for r in recommendations], bulletType="bullet"),
        ]

    path = Path(path)
    SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title="DataForge AI Executive Report",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    ).build(story)
    return path
