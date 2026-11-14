"""Ingestion pipeline: metadata -> rights check -> download -> text -> quality -> hash -> chunk/scan/tag/embed -> seal.

Every step is logged to the job log. A document that fails any gate is recorded with an error and is not used
as evidence. Retrieved text is data: it is scanned for instruction-like content before it is ever shown to an agent.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.evidence import ntrs
from app.evidence.catalog import DEMO_EXPERIMENT, EXPERIMENTS, WEB_PAGES, ExperimentSpec, experiment_by_key
from app.evidence.chunker import chunk_text
from app.evidence.tagger import tag_gravity, tag_materials, tag_topic, tag_variables
from app.evidence.webpages import html_to_text, pdf_to_text
from app.models import Document, EvidenceChunk, Experiment
from app.rag.embeddings import get_embedder
from app.security import injection, integrity
from app.security.audit import write_audit
from app.security.hashing import sha256_hex

log = logging.getLogger("fireguard.ingest")
Logger = Callable[[str], None]

MIN_TEXT_CHARS = 600
# Terms that make a record plausibly relevant to spacecraft fire safety / combustion.
RELEVANCE_TERMS = ("flame", "fire", "combustion", "flammab", "ignition", "microgravity", "burn")


def ensure_experiment(session: Session, spec: ExperimentSpec) -> Experiment:
    exp = session.scalar(select(Experiment).where(Experiment.key == spec.key))
    if exp is None:
        exp = Experiment(key=spec.key)
        session.add(exp)
    exp.name, exp.program, exp.description = spec.name, spec.program, spec.description
    exp.source_url, exp.variables = spec.source_url, list(spec.variables)
    session.flush()
    return exp


def relevance_ok(text: str, spec: ExperimentSpec | None = None) -> bool:
    low = text.lower()
    hits = sum(low.count(t) for t in RELEVANCE_TERMS)
    return hits >= 5


def store_document(
    session: Session,
    *,
    doc_key: str,
    experiment: Experiment | None,
    title: str,
    source: str,
    text: str,
    source_url: str | None = None,
    ntrs_id: str | None = None,
    meta_fields: dict[str, Any] | None = None,
    byte_sha: str | None = None,
    byte_length: int | None = None,
    synthetic: bool = False,
    extra_meta: dict[str, Any] | None = None,
    actor: str = "system",
) -> tuple[Document, int, str]:
    """Upsert a document and rebuild its chunks. Returns (doc, chunk_count, action)."""
    m = meta_fields or {}
    digest = sha256_hex(text)
    doc = session.scalar(select(Document).where(Document.doc_key == doc_key))
    action = "created"
    if doc is None:
        doc = Document(doc_key=doc_key, version="1")
        session.add(doc)
    elif doc.sha256 == digest and not doc.quarantined and doc.processing_status == "ingested":
        return doc, len(doc.chunks), "unchanged"
    else:
        action = "updated"
        doc.version = str(int(doc.version or "1") + 1) if doc.sha256 != digest else doc.version
        session.execute(delete(EvidenceChunk).where(EvidenceChunk.document_id == doc.id))
    doc.experiment_id = experiment.id if experiment else None
    doc.title, doc.source, doc.source_url, doc.ntrs_id = title[:512], source, source_url, ntrs_id
    doc.document_type, doc.publication_date = m.get("document_type"), m.get("date")
    doc.center, doc.license, doc.distribution = m.get("center"), m.get("license"), m.get("distribution")
    doc.retrieved_at = datetime.now(UTC)
    doc.sha256, doc.source_bytes_sha256 = digest, byte_sha
    doc.byte_length = byte_length if byte_length is not None else len(text.encode())
    doc.content_text, doc.tamper_overlay = text, None
    doc.synthetic, doc.quarantined, doc.processing_status, doc.error = synthetic, False, "ingested", None
    doc.meta = extra_meta or {}
    session.flush()

    raw = chunk_text(text)
    embedder = get_embedder()
    clean_texts: list[str] = []
    scans = []
    for rc in raw:
        sc = injection.scan(rc.text)
        scans.append(sc)
        clean_texts.append(sc.clean_text)
    vectors = embedder.embed(clean_texts) if clean_texts else []
    for i, (rc, sc, vec) in enumerate(zip(raw, scans, vectors, strict=True)):
        session.add(
            EvidenceChunk(
                chunk_key=f"{doc_key}#{i:03d}",
                document_id=doc.id,
                ordinal=i,
                page=rc.page,
                content=sc.clean_text,
                content_hash=sha256_hex(sc.clean_text),
                embedding=vec,
                variables=tag_variables(sc.clean_text),
                materials=tag_materials(sc.clean_text),
                topic=tag_topic(sc.clean_text),
                gravity=tag_gravity(sc.clean_text),
                injection_flags=sc.flags,
                synthetic=synthetic,
                meta={"embedder": embedder.name},
            )
        )
    session.flush()
    integrity.seal(doc)
    write_audit(
        session,
        actor,
        "ingest.document",
        doc_key,
        action,
        {"sha256": digest, "chunks": len(raw)},
        commit=False,
    )
    session.commit()
    return doc, len(raw), action


def _record_failure(
    session: Session, doc_key: str, title: str, source: str, err: str, url: str | None, ntrs_id: str | None
) -> None:
    doc = session.scalar(select(Document).where(Document.doc_key == doc_key))
    if doc is None:
        doc = Document(
            doc_key=doc_key,
            title=title[:512],
            source=source,
            source_url=url,
            ntrs_id=ntrs_id,
            sha256=sha256_hex(""),
            content_text="",
        )
        session.add(doc)
    doc.processing_status, doc.error = "failed", err[:1000]
    session.commit()


def ingest_ntrs_record(
    session: Session, ntrs_id: str, spec: ExperimentSpec, say: Logger, actor: str = "system"
) -> str:
    doc_key = f"NTRS-{ntrs_id}"
    try:
        rec = ntrs.get_record(ntrs_id)
    except Exception as e:  # noqa: BLE001
        say(f"{doc_key}: metadata failed ({e})")
        return "failed"
    meta = ntrs.record_meta(rec)
    if str(rec.get("distribution", "PUBLIC")).upper() not in ("PUBLIC", ""):
        say(f"{doc_key}: skipped (distribution {rec.get('distribution')})")
        return "skipped"
    text, raw_sha, n_bytes = "", None, None
    link = ntrs.pdf_link(rec)
    if link:
        try:
            f = ntrs.safe_get(link, accept="application/pdf")
            raw_sha, n_bytes = sha256_hex(f.content), len(f.content)
            text = pdf_to_text(f.content)
            (get_settings().data_dir / "raw" / "ntrs").mkdir(parents=True, exist_ok=True)
            (get_settings().data_dir / "raw" / "ntrs" / f"{ntrs_id}.pdf").write_bytes(f.content)
        except Exception as e:  # noqa: BLE001
            say(f"{doc_key}: PDF failed ({e}); using abstract only")
    if len(text) < MIN_TEXT_CHARS and meta["abstract"]:
        text = f"{meta['title']}\n\n{meta['abstract']}"
        say(f"{doc_key}: using abstract text")
    if len(text) < MIN_TEXT_CHARS // 2:
        _record_failure(
            session,
            doc_key,
            meta["title"] or doc_key,
            "NASA NTRS",
            "no usable text",
            f"{get_settings().ntrs_base_url}/citations/{ntrs_id}",
            ntrs_id,
        )
        say(f"{doc_key}: no usable text")
        return "failed"
    if not relevance_ok(f"{meta['title']} {text}", spec):
        say(f"{doc_key}: skipped (not about combustion or fire safety)")
        return "skipped"
    exp = ensure_experiment(session, spec)
    _, n, action = store_document(
        session,
        doc_key=doc_key,
        experiment=exp,
        title=meta["title"] or doc_key,
        source="NASA NTRS",
        text=text,
        source_url=f"{get_settings().ntrs_base_url}/citations/{ntrs_id}",
        ntrs_id=ntrs_id,
        meta_fields=meta,
        byte_sha=raw_sha,
        byte_length=n_bytes,
        actor=actor,
        extra_meta={"pdf_url": link},
    )
    say(f"{doc_key}: {action}, {n} chunks")
    return action


def ingest_web(session: Session, key: str, exp_key: str, url: str, say: Logger, actor: str = "system") -> str:
    spec = experiment_by_key(exp_key)
    try:
        f = ntrs.safe_get(url, accept="text/html,application/pdf")
        if "pdf" in f.content_type.lower():
            title, text = url, pdf_to_text(f.content)
        else:
            title, text = html_to_text(f.content)
    except Exception as e:  # noqa: BLE001
        say(f"{key}: fetch failed ({e})")
        return "failed"
    if len(text) < MIN_TEXT_CHARS or not relevance_ok(text, spec):
        say(f"{key}: skipped (too short or not relevant)")
        return "skipped"
    exp = ensure_experiment(session, spec) if spec else None
    _, n, action = store_document(
        session,
        doc_key=key,
        experiment=exp,
        title=title or key,
        source="NASA web",
        text=text,
        source_url=f.url,
        meta_fields={"document_type": "web page"},
        byte_sha=sha256_hex(f.content),
        byte_length=len(f.content),
        actor=actor,
    )
    say(f"{key}: {action}, {n} chunks")
    return action


def run_ingestion(
    session: Session,
    ntrs_ids: list[str] | None = None,
    include_web: bool = True,
    say: Logger | None = None,
    actor: str = "system",
) -> dict[str, int]:
    say = say or (lambda m: log.info(m))
    stats = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0, "failed": 0}

    def tally(a: str) -> None:
        stats[a if a in stats else "failed"] += 1

    seen: set[str] = set()
    for spec in EXPERIMENTS:
        ensure_experiment(session, spec)
    if ntrs_ids:
        # Explicit request: only these records, filed under general spacecraft fire safety unless in the catalog.
        for rid in ntrs_ids:
            if rid in seen or not rid.isdigit():
                continue
            seen.add(rid)
            owner = next((s for s in EXPERIMENTS if rid in s.ntrs_ids), experiment_by_key("SFS"))
            assert owner is not None
            tally(ingest_ntrs_record(session, rid, owner, say, actor))
    else:
        for spec in EXPERIMENTS:
            ids = list(spec.ntrs_ids)
            for q in spec.queries:
                try:
                    ids += [str(r.get("id", "")) for r in ntrs.search(q, 6) if str(r.get("id", "")).isdigit()]
                except Exception as e:  # noqa: BLE001
                    say(f"search '{q}' failed ({e})")
            for rid in ids:
                if rid in seen:
                    continue
                seen.add(rid)
                tally(ingest_ntrs_record(session, rid, spec, say, actor))
    if include_web:
        for key, exp_key, url in WEB_PAGES:
            tally(ingest_web(session, key, exp_key, url, say, actor))
    return stats


def ensure_demo_experiment(session: Session) -> Experiment:
    return ensure_experiment(session, DEMO_EXPERIMENT)
