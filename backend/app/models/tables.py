"""SQLAlchemy models. One table per concept in the project brief."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, EmbeddingType, JSONType


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    permissions: Mapped[list[str]] = mapped_column(JSONType, default=list)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(ForeignKey("roles.name"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # BASS-II, SoFIE, ACME, Saffire
    program: Mapped[str] = mapped_column(String(64), default="NASA microgravity combustion")
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    variables: Mapped[list[str]] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    documents: Mapped[list[Document]] = relationship(back_populates="experiment")


class Document(Base):
    """One source document, with its provenance record."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(64))  # "NASA NTRS", "NASA web", "SYNTHETIC/DEMO"
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ntrs_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    document_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    center: Mapped[str | None] = mapped_column(String(64), nullable=True)
    license: Mapped[str | None] = mapped_column(String(128), nullable=True)
    distribution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version: Mapped[str] = mapped_column(String(16), default="1")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sha256: Mapped[str] = mapped_column(String(64))  # of content_text (UTF-8), sealed at ingestion
    source_bytes_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_length: Mapped[int] = mapped_column(Integer, default=0)
    content_text: Mapped[str] = mapped_column(Text, default="")
    # Security demo only: a simulated edit layered over the original text. The original is never modified.
    tamper_overlay: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(24), default="ingested")
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    experiment: Mapped[Experiment | None] = relationship(back_populates="documents")
    chunks: Mapped[list[EvidenceChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Observation(Base):
    """A numeric observation (for example a row from a NASA PSI data export)."""

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id"), nullable=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    variable: Mapped[str] = mapped_column(String(48), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32), default="")
    condition: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"
    __table_args__ = (Index("ix_evidence_chunks_document_ord", "document_id", "ordinal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)  # the citable evidence ID
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType, nullable=True)
    variables: Mapped[list[str]] = mapped_column(JSONType, default=list)
    materials: Mapped[list[str]] = mapped_column(JSONType, default=list)
    topic: Mapped[str] = mapped_column(String(32), default="general")
    gravity: Mapped[str] = mapped_column(String(24), default="unspecified")
    injection_flags: Mapped[list[str]] = mapped_column(JSONType, default=list)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    params: Mapped[dict[str, Any]] = mapped_column(JSONType)
    preset: Mapped[bool] = mapped_column(Boolean, default=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario: Mapped[dict[str, Any]] = mapped_column(JSONType)
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(16))
    crew_level: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    trust_score: Mapped[int] = mapped_column(Integer)
    trust_band: Mapped[str] = mapped_column(String(24))
    guardian_status: Mapped[str] = mapped_column(String(24))
    red_team_status: Mapped[str] = mapped_column(String(24))
    evidence_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="pending_approval")
    result: Mapped[dict[str, Any]] = mapped_column(JSONType)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    agent_runs: Mapped[list[AgentRun]] = relationship(back_populates="assessment")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("risk_assessments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32))
    version: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(64))
    permissions: Mapped[list[str]] = mapped_column(JSONType, default=list)
    input_hash: Mapped[str] = mapped_column(String(64))
    output_hash: Mapped[str] = mapped_column(String(64))
    output: Mapped[dict[str, Any]] = mapped_column(JSONType)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assessment: Mapped[RiskAssessment | None] = relationship(back_populates="agent_runs")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    severity: Mapped[str] = mapped_column(String(12))
    source: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open")
    details: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AuditLog(Base):
    """Hash-chained audit trail: each row stores the hash of the previous row."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    username: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    resource: Mapped[str] = mapped_column(String(160))
    result: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("risk_assessments.id", ondelete="CASCADE"), index=True
    )
    username: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    policy: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    simulated_steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    requested_by: Mapped[str] = mapped_column(String(64), default="system")
    params: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    stats: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    log: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
