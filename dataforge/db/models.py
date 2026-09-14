"""SQLAlchemy ORM models — DataForge AI run history (docs/DATABASE.md).

Portable across SQLite (local dev) and Postgres/Neon (prod): UUIDs stored
as String(36), payloads as JSON. Importing this module requires sqlalchemy.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dataforge.db import Base

__all__ = [
    "Dataset",
    "Run",
    "AgentEvent",
    "KPI",
    "Insight",
    "CleaningDecision",
    "Checkpoint",
    "utcnow_iso",
]


def utcnow_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def new_uuid() -> str:
    """Generate a UUID4 string primary key."""
    return str(uuid.uuid4())


class Dataset(Base):
    """Source file registered for analysis (dedupe via sha256)."""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cols: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    runs: Mapped[list[Run]] = relationship(back_populates="dataset")


class Run(Base):
    """One analysis execution over a dataset."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    dataset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("datasets.id"), nullable=True
    )
    business_domain: Mapped[str | None] = mapped_column(String(32), nullable=True)
    domain_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    current_phase: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    steps_completed: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    steps_skipped: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    quality_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    quality_errors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    report_html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )

    dataset: Mapped[Dataset | None] = relationship(back_populates="runs")
    events: Mapped[list[AgentEvent]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_runs_status_created", "status"),)


class AgentEvent(Base):
    """One agent execution within a run (mirrors GraphState agent_history)."""

    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    agent: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    run: Mapped[Run] = relationship(back_populates="events")

    __table_args__ = (Index("ix_agent_events_run_created", "run_id"),)


class KPI(Base):
    """Discovered Key Performance Indicator for a run."""

    __tablename__ = "kpis"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend: Mapped[str | None] = mapped_column(String(16), nullable=True)
    benchmark_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_kpis_run", "run_id"),)


class Insight(Base):
    """Ranked business insight for a run."""

    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    supporting_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    business_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_insights_run_rank", "run_id", "rank"),)


class CleaningDecision(Base):
    """Auditable data-cleaning decision for a run."""

    __tablename__ = "cleaning_decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    issue: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    rows_affected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_cleaning_run", "run_id"),)


class Checkpoint(Base):
    """Latest resumable GraphState snapshot for a run."""

    __tablename__ = "checkpoints"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    )
    state_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    parquet_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
