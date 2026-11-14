"""Hash-chained audit log. Editing or deleting history breaks the chain."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.models.tables import utcnow
from app.security.hashing import sha256_hex

GENESIS = "0" * 64
_ADVISORY_LOCK_ID = 727_001


def _entry_hash(prev: str, ts_iso: str, username: str, action: str, resource: str, result: str) -> str:
    return sha256_hex("|".join([prev, ts_iso, username, action, resource, result]))


def write_audit(
    session: Session,
    username: str,
    action: str,
    resource: str,
    result: str,
    details: dict[str, Any] | None = None,
    commit: bool = True,
) -> AuditLog:
    if session.get_bind().dialect.name == "postgresql":
        # Serialize writers so two requests cannot chain from the same predecessor.
        session.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": _ADVISORY_LOCK_ID})
    last = session.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev = last.hash if last else GENESIS
    ts = utcnow().replace(microsecond=0)
    entry = AuditLog(
        ts=ts,
        username=username[:64],
        action=action[:64],
        resource=resource[:160],
        result=result[:64],
        details=details or {},
        prev_hash=prev,
        hash=_entry_hash(prev, ts.isoformat(), username[:64], action[:64], resource[:160], result[:64]),
    )
    session.add(entry)
    if commit:
        session.commit()
    else:
        session.flush()
    return entry


def verify_chain(session: Session) -> bool:
    prev = GENESIS
    for e in session.scalars(select(AuditLog).order_by(AuditLog.id.asc())):
        ts = e.ts.replace(microsecond=0)
        ts = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)
        expected = _entry_hash(prev, ts.isoformat(), e.username, e.action, e.resource, e.result)
        if e.prev_hash != prev or e.hash != expected:
            return False
        prev = e.hash
    return True
