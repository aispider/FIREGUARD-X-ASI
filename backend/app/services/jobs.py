"""Ingestion jobs: created by the API, executed by the worker (or inline when Redis is absent)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.evidence.ingest import run_ingestion
from app.evidence.observations import load_psi_csvs
from app.models import IngestionJob

QUEUE = "fgx:ingest"


def run_job(session: Session, job_id: int) -> None:
    job = session.get(IngestionJob, job_id)
    if job is None or job.status not in ("queued", "running"):
        return
    job.status, job.started_at = "running", datetime.now(UTC)
    session.commit()
    lines: list[str] = []

    def say(m: str) -> None:
        lines.append(m)

    try:
        p = job.params or {}
        stats = run_ingestion(
            session, p.get("ntrs_ids"), p.get("include_web", True), say=say, actor=job.requested_by
        )
        stats["observations"] = load_psi_csvs(session, say=say)
        job.status = "done"
        job.stats = stats
    except Exception as e:  # noqa: BLE001
        session.rollback()
        job = session.get(IngestionJob, job_id)
        assert job is not None
        job.status = "failed"
        lines.append(f"error: {e}")
    job.log = "\n".join(lines)[-8000:]
    job.finished_at = datetime.now(UTC)
    session.commit()
