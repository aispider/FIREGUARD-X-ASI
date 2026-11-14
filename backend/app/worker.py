"""Ingestion worker: first-start auto-ingest, then polls the database for queued jobs."""

from __future__ import annotations

import logging
import time

from sqlalchemy import select

from app.config import get_settings
from app.db import init_engine, session_factory
from app.models import Document, IngestionJob
from app.services.jobs import run_job

log = logging.getLogger("fireguard.worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = get_settings()
    init_engine()
    if cfg.auto_ingest:
        with session_factory()() as s:
            have = s.scalar(select(Document.id).where(Document.synthetic.is_(False), Document.processing_status == "ingested").limit(1))
            pending = s.scalar(select(IngestionJob.id).where(IngestionJob.status.in_(("queued", "running"))).limit(1))
            if not have and not pending:
                s.add(IngestionJob(requested_by="system", params={"include_web": True}))
                s.commit()
                log.info("auto-ingest job queued")
    while True:
        with session_factory()() as s:
            ids = [j for (j,) in s.execute(select(IngestionJob.id).where(IngestionJob.status == "queued").order_by(IngestionJob.id))]
            for i in ids:
                run_job(s, i)
        time.sleep(3)


if __name__ == "__main__":
    main()
