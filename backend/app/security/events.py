"""Security event recording."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import SecurityEvent

log = logging.getLogger("fireguard.security")


def record_event(
    session: Session,
    event_type: str,
    severity: str,
    source: str,
    description: str,
    details: dict[str, Any] | None = None,
    status: str = "open",
    commit: bool = True,
) -> SecurityEvent:
    ev = SecurityEvent(
        event_type=event_type,
        severity=severity,
        source=source[:64],
        description=description,
        status=status,
        details=details or {},
    )
    session.add(ev)
    if commit:
        session.commit()
    else:
        session.flush()
    log.warning("security_event type=%s severity=%s source=%s", event_type, severity, source)
    return ev


def record_event_once(
    session: Session,
    event_type: str,
    severity: str,
    source: str,
    description: str,
    details: dict[str, Any] | None = None,
    window_s: int = 120,
) -> SecurityEvent | None:
    """Like record_event, but skips an identical (type, source) event raised within `window_s` seconds."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    since = datetime.now(UTC) - timedelta(seconds=window_s)
    last = session.scalar(
        select(SecurityEvent)
        .where(
            SecurityEvent.event_type == event_type,
            SecurityEvent.source == source[:64],
            SecurityEvent.created_at >= since,
        )
        .limit(1)
    )
    if last is not None:
        return None
    return record_event(session, event_type, severity, source, description, details, commit=False)
