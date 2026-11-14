"""Evidence retrieval: pgvector cosine search (SQL on PostgreSQL, Python elsewhere) plus a transparent rerank.

Safety rules applied here:
* chunks of quarantined documents are returned with status 'quarantined' and never used;
* every candidate is re-scanned for instruction-like text at retrieval time (not only at ingestion);
  high-severity hits are 'excluded_injection', lower ones are scrubbed;
* retrieved text is data: it is only ever shown or cited, never executed or obeyed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from app.models import Document, EvidenceChunk, Experiment
from app.rag.embeddings import cosine, get_embedder
from app.schemas import EvidenceItem, Provenance, ScenarioIn
from app.security import injection, integrity

GRAVITY_MATCH = {
    "microgravity": {"microgravity"},
    "lunar": {"reduced"},
    "mars": {"reduced"},
    "earth": {"normal"},
}
CANDIDATES = 48


@dataclass
class Candidate:
    chunk: EvidenceChunk
    doc: Document
    experiment: str | None
    similarity: float
    relevance: float = 0.0
    status: str = "used"
    flags: list[str] = field(default_factory=list)
    text: str = ""


def scenario_query(s: ScenarioIn) -> str:
    grav = {
        "microgravity": "microgravity",
        "lunar": "reduced gravity lunar",
        "mars": "reduced gravity martian",
        "earth": "normal gravity",
    }[s.gravity]
    geom = {"thin_sheet": "thin sheet", "cylinder": "cylinder", "thick_slab": "thick slab"}[s.fuel_geometry]
    return (
        f"flame spread extinction {s.material} {geom} oxygen concentration {s.oxygen_percent:g} percent "
        f"airflow flow velocity pressure temperature external heating {grav} spacecraft fire safety"
    )


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def _nearest(
    session: Session, vec: list[float], n: int, experiment: str | None
) -> list[tuple[EvidenceChunk, float]]:
    if session.get_bind().dialect.name == "postgresql":
        sql = "SELECT id, 1 - (embedding <=> CAST(:v AS vector)) AS sim FROM evidence_chunks WHERE embedding IS NOT NULL"
        params: dict = {"v": _vector_literal(vec), "n": n}
        if experiment:
            sql += " AND document_id IN (SELECT d.id FROM documents d JOIN experiments e ON e.id=d.experiment_id WHERE e.key=:exp)"
            params["exp"] = experiment
        sql += " ORDER BY embedding <=> CAST(:v AS vector) LIMIT :n"
        rows = session.execute(text(sql), params).all()
        sims = {r.id: float(r.sim) for r in rows}
        if not sims:
            return []
        chunks = {c.id: c for c in session.scalars(select(EvidenceChunk).where(EvidenceChunk.id.in_(sims)))}
        return [(chunks[i], sims[i]) for i in sims if i in chunks]
    q = select(EvidenceChunk).where(EvidenceChunk.embedding.is_not(None))
    if experiment:
        q = q.join(Document).join(Experiment).where(Experiment.key == experiment)
    scored = [(c, cosine(vec, c.embedding or [])) for c in session.scalars(q)]
    scored.sort(key=lambda t: -t[1])
    return scored[:n]


def _relevance(s: ScenarioIn | None, c: EvidenceChunk, sim: float) -> float:
    # Hash embeddings give small cosines for a long query vs a short passage; 0.15 maps a good lexical match to ~1.
    base = max(0.0, min(1.0, sim / 0.15))
    if s is None:
        return round(base, 3)
    want = {"oxygen", "airflow", "pressure", "temperature", "geometry"}
    if s.external_heating_kw_m2 > 0:
        want.add("heating")
    var = len(want & set(c.variables)) / len(want)
    mat = 1.0 if s.material in c.materials else (0.4 if not c.materials else 0.0)
    grav = 1.0 if c.gravity in GRAVITY_MATCH[s.gravity] else (0.5 if c.gravity == "unspecified" else 0.2)
    return round(max(0.0, min(1.0, 0.55 * base + 0.25 * var + 0.10 * mat + 0.10 * grav)), 3)


def retrieve(
    session: Session,
    scenario: ScenarioIn | None = None,
    query: str | None = None,
    limit: int = 8,
    experiment: str | None = None,
) -> list[Candidate]:
    q = query or (scenario_query(scenario) if scenario else "")
    if not q.strip():
        return []
    vec = get_embedder().embed([q])[0]
    near = _nearest(session, vec, CANDIDATES, experiment)
    manifest = integrity.load_manifest()
    doc_ids = {c.document_id for c, _ in near}
    # Demo attack candidates are always surfaced so the Security Center can show the defence working.
    attack = [
        c
        for c in session.scalars(
            select(EvidenceChunk).join(Document).where(Document.doc_key.like("DEMO-attack%"))
        )
    ]
    doc_ids |= {c.document_id for c in attack}
    docs = (
        {
            d.id: d
            for d in session.scalars(
                select(Document).options(joinedload(Document.experiment)).where(Document.id.in_(doc_ids))
            )
        }
        if doc_ids
        else {}
    )
    seen = {c.id for c, _ in near}
    pairs = near + [(c, 0.5) for c in attack if c.id not in seen]
    out: list[Candidate] = []
    for ch, sim in pairs:
        d = docs.get(ch.document_id)
        if d is None:
            continue
        scan = injection.scan(ch.content)
        status, txt = "used", scan.clean_text
        if d.quarantined or not integrity.doc_ok(d, manifest):
            status = "quarantined"
        elif scan.exclude:
            status = "excluded_injection"
        flags = sorted(set(scan.flags) | set(ch.injection_flags))
        out.append(
            Candidate(
                ch,
                d,
                d.experiment.key if d.experiment else None,
                sim,
                _relevance(scenario, ch, sim),
                status,
                flags,
                txt,
            )
        )
    out.sort(key=lambda c: -c.relevance)
    used = [c for c in out if c.status == "used"][:limit]
    blocked = [c for c in out if c.status != "used"][:6]
    return sorted(used + blocked, key=lambda c: -c.relevance)


def to_item(c: Candidate) -> EvidenceItem:
    d = c.doc
    prov = Provenance(
        document_id=d.doc_key,
        title=d.title,
        source=d.source,
        source_url=d.source_url,
        ntrs_id=d.ntrs_id,
        publication_date=d.publication_date,
        sha256=d.sha256,
        retrieved_at=d.retrieved_at,
        version=d.version,
        license=d.license,
        integrity="quarantined" if c.status == "quarantined" else "verified",
    )
    shown = (
        c.text
        if c.status == "used"
        else (
            "[excluded: instruction-like content]"
            if c.status == "excluded_injection"
            else "[quarantined: integrity check failed]"
        )
    )
    return EvidenceItem(
        chunk_id=c.chunk.chunk_key,
        experiment=c.experiment,
        text=shown[:1200],
        relevance=c.relevance,
        variables=list(c.chunk.variables),
        materials=list(c.chunk.materials),
        topic=c.chunk.topic,
        gravity=c.chunk.gravity,
        page=c.chunk.page,
        synthetic=c.chunk.synthetic,
        status=c.status,
        provenance=prov,
        flags=c.flags,
    )
