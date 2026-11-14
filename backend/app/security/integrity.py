"""Document integrity: SHA-256 manifest, verification, quarantine, restore.

The manifest (data/manifests/manifest.json) is an independent record of each document's hash, sealed when the
document is ingested. Verification compares three values: the hash stored on the document row, the hash of the
text now in effect (original, or the simulated tamper overlay used by the Security Center demo) and the
manifest entry. Any mismatch quarantines the document; quarantined documents never feed evidence.
"""

from __future__ import annotations

import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Document
from app.security.hashing import sha256_hex


def _manifest_path() -> Path:
    p = get_settings().data_dir / "manifests"
    p.mkdir(parents=True, exist_ok=True)
    return p / "manifest.json"


@contextmanager
def _locked() -> Iterator[None]:
    lock = _manifest_path().with_suffix(".lock")
    with open(lock, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def load_manifest() -> dict[str, dict]:
    p = _manifest_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def seal(doc: Document) -> None:
    with _locked():
        m = load_manifest()
        m[doc.doc_key] = {
            "sha256": doc.sha256,
            "source": doc.source,
            "source_url": doc.source_url,
            "version": doc.version,
            "bytes": doc.byte_length,
            "synthetic": doc.synthetic,
            "retrieved_at": doc.retrieved_at.isoformat() if doc.retrieved_at else None,
        }
        tmp = _manifest_path().with_suffix(".tmp")
        tmp.write_text(json.dumps(m, indent=2, sort_keys=True))
        tmp.replace(_manifest_path())


def effective_text(doc: Document) -> str:
    return doc.tamper_overlay if doc.tamper_overlay is not None else doc.content_text


def current_hash(doc: Document) -> str:
    return sha256_hex(effective_text(doc))


def doc_ok(doc: Document, manifest: dict[str, dict] | None = None) -> bool:
    m = manifest if manifest is not None else load_manifest()
    entry = m.get(doc.doc_key)
    cur = current_hash(doc)
    return cur == doc.sha256 and (entry is None or entry.get("sha256") == cur)


def verify_all(session: Session, quarantine: bool = True) -> tuple[list[Document], list[str], bool]:
    """Returns (documents, newly_quarantined_keys, manifest_ok)."""
    manifest = load_manifest()
    docs = list(session.scalars(select(Document).order_by(Document.doc_key)))
    newly: list[str] = []
    manifest_ok = True
    for d in docs:
        ok = doc_ok(d, manifest)
        entry = manifest.get(d.doc_key)
        if entry is not None and entry.get("sha256") != d.sha256:
            manifest_ok = False
        if not ok and not d.quarantined and quarantine:
            d.quarantined = True
            d.processing_status = "quarantined"
            newly.append(d.doc_key)
    if newly:
        session.commit()
    return docs, newly, manifest_ok


def restore(session: Session, doc_key: str) -> bool:
    d = session.scalar(select(Document).where(Document.doc_key == doc_key))
    if d is None:
        return False
    d.tamper_overlay = None
    if doc_ok(d):
        d.quarantined = False
        d.processing_status = "ingested"
    session.commit()
    return True
