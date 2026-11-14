"""The council: retrieve evidence, assess risk, run seven agents, challenge, score trust, decide.

Flow: integrity check -> retrieve -> risk model -> scientist/data/fire/safety -> red team -> trust -> guardian
-> commander. The trust gate and the decision are computed from facts, not from agent prose, so a manipulated
agent output cannot raise a score. Outputs are validated; an invalid agent is excluded and lowers consensus.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents import decision as dec
from app.agents.base import AGENT_SPECS, Context, identity
from app.agents.llm import narrate
from app.agents.roles import ROLE_FUNCS
from app.config import get_settings
from app.evidence.observations import observed_ranges
from app.models import AgentRun, RiskAssessment
from app.rag.retriever import Candidate, retrieve, to_item
from app.risk import assumptions as A
from app.risk.model import assess
from app.schemas import (
    AnalysisResult,
    Consensus,
    CouncilMember,
    IntegritySummary,
    Layers,
    ScenarioIn,
)
from app.security import integrity
from app.security import trust as T
from app.security.audit import write_audit
from app.security.events import record_event, record_event_once
from app.security.policy import PermissionDenied, ToolBroker
from app.security.validation import validate_output

DISCLAIMER = "Prototype model. Simulated analysis only. Not NASA-approved. A human must approve every action."


def _integrity(session: Session) -> tuple[IntegritySummary, int]:
    docs, newly, _ = integrity.verify_all(session)
    docs = [d for d in docs if not d.doc_key.startswith("DEMO-attack")]
    q = [d.doc_key for d in docs if d.quarantined]
    for k in newly:
        record_event(
            session,
            "INTEGRITY_FAIL",
            "HIGH",
            "data-guard",
            f"{k} failed its SHA-256 integrity check and was quarantined.",
            {"doc": k},
        )
    return IntegritySummary(ok=not q, checked=len(docs), quarantined=q), len(q)


def _layers(used: list[Candidate]) -> Layers:
    nasa = sorted({f"{c.doc.doc_key}: {c.doc.title}" for c in used if not c.chunk.synthetic})
    synth = sorted({f"{c.chunk.chunk_key}: {c.doc.title}" for c in used if c.chunk.synthetic})
    return Layers(
        nasa_evidence=nasa[:12], prototype_assumptions=list(A.ASSUMPTION_LINES), synthetic_values=synth[:12]
    )


def run_council(
    session: Session,
    scenario: ScenarioIn,
    *,
    persist: bool = False,
    actor: str = "system",
    suppression: float = 0.0,
) -> AnalysisResult:
    settings = get_settings()
    mode = settings.evidence_mode
    integ, quarantined_docs = _integrity(session)

    cands = retrieve(session, scenario, limit=8)
    used = [c for c in cands if c.status == "used"]
    blocked = [c for c in cands if c.status != "used"]
    inj_excluded = [c for c in blocked if c.status == "excluded_injection"]
    for c in inj_excluded:
        record_event_once(
            session,
            "PROMPT_INJECTION",
            "HIGH",
            c.doc.doc_key,
            "Instruction-like text in retrieved evidence was excluded.",
            {"chunk": c.chunk.chunk_key, "flags": c.flags},
        )

    obs = observed_ranges(session)
    risk, pen, _raw = assess(scenario, suppression=suppression, observed=obs or None)
    stats = T.evidence_stats(scenario, used, len(blocked), mode)
    challenges = T.red_team(scenario, risk, pen, stats, quarantined_docs, len(inj_excluded), mode)

    ctx = Context(
        scenario=scenario,
        risk=risk,
        pen=pen,
        used=used,
        stats=stats,
        challenges=challenges,
        broker=ToolBroker(),
        mode=mode,
    )
    allowed_ids = {c.chunk.chunk_key for c in used}
    members: dict[str, CouncilMember] = {}
    invalid = 0

    def run_agent(key: str) -> None:
        nonlocal invalid
        spec = next(a for a in AGENT_SPECS if a.key == key)
        try:
            out = ROLE_FUNCS[key](ctx)
        except PermissionDenied as e:
            record_event(session, "POLICY_DENIED", "HIGH", f"agent:{key}", str(e), commit=False)
            raise
        model_name = "rule-based-v1"
        if settings.llm_enabled and key in ("scientist", "data", "fire", "safety"):
            text = narrate(key, {"finding": out.finding, "verdict": out.verdict})
            if text:
                out = out.model_copy(update={"finding": text})
                model_name = f"{settings.openai_model}+rules"
        errs = validate_output(out, allowed_ids)
        if errs:
            invalid += 1
            record_event(
                session, "AGENT_OUTPUT_INVALID", "MEDIUM", f"agent:{key}", "; ".join(errs), commit=False
            )
        members[key] = CouncilMember(
            key=key,
            code=spec.code,
            name=spec.name,
            identity=identity(spec, ctx, out, model_name),
            output=out,
            valid=not errs,
        )

    for k in ("scientist", "data", "fire", "safety", "red"):
        run_agent(k)
    cons: Consensus = T.consensus(risk, sum(1 for c in challenges if not c.passed), invalid)
    trust = T.compute_trust(
        risk=risk,
        pen=pen,
        st=stats,
        challenges=challenges,
        cons=cons,
        quarantined_docs=quarantined_docs,
        mode=mode,
    )
    ctx.trust = trust
    decision = dec.decide(risk, trust)
    ctx.decision = decision
    run_agent("guardian")
    run_agent("commander")

    conf = round(0.5 * max(0.0, min(1.0, (stats.quality - pen * 0.5) / 100)) + 0.5 * cons.agreement, 2)
    risk = risk.model_copy(update={"confidence": conf})
    ordered = [members[a.key] for a in AGENT_SPECS]

    limitations = [DISCLAIMER, "The Trust Score is a prototype metric, not NASA-approved."]
    if stats.summary.synthetic_only:
        limitations.append("All evidence is SYNTHETIC/DEMO; official NASA documents have not been ingested.")
    if risk.out_of_range:
        limitations.append("Extrapolating beyond the tested envelope: " + ", ".join(risk.out_of_range) + ".")
    if not stats.material_covered:
        limitations.append(f"No retrieved evidence mentions {scenario.material}.")

    top_drivers = [d.name.lower() for d in risk.drivers[:3]]
    result = AnalysisResult(
        assessment_id=None,
        generated_at=datetime.now(UTC),
        scenario=scenario,
        risk=risk,
        trust=trust,
        evidence=[to_item(c) for c in cands],
        evidence_summary=stats.summary,
        council=ordered,
        consensus=cons,
        challenges=challenges,
        decision=decision,
        chain=dec.chain_for(trust, decision),
        debate=dec.debate(risk, trust, challenges, [c.chunk.chunk_key for c in used], top_drivers),
        layers=_layers(used),
        integrity=integ,
        security_flags={
            "injection_detected": bool(inj_excluded),
            "quarantined": quarantined_docs > 0,
            "out_of_envelope": bool(risk.out_of_range),
            "insufficient_evidence": trust.insufficient_evidence,
            "synthetic_only": stats.summary.synthetic_only,
        },
        limitations=limitations,
    )
    if persist:
        aid = str(uuid.uuid4())
        session.add(
            RiskAssessment(
                id=aid,
                scenario=scenario.model_dump(mode="json"),
                risk_score=risk.score,
                risk_level=risk.level,
                crew_level=risk.crew_level,
                confidence=conf,
                trust_score=trust.score,
                trust_band=trust.band,
                guardian_status=trust.guardian_status,
                red_team_status="PASSED"
                if all(c.passed or c.severity == "LOW" for c in challenges)
                and not any((not c.passed) and c.severity == "HIGH" for c in challenges)
                else "CHALLENGED",
                evidence_count=stats.summary.count,
                status="pending_approval" if not trust.insufficient_evidence else "insufficient_evidence",
                result=result.model_dump(mode="json"),
                created_by=actor,
            )
        )
        session.flush()
        for m in ordered:
            session.add(
                AgentRun(
                    assessment_id=aid,
                    agent_id=m.identity.agent_id,
                    role=m.identity.role,
                    version=m.identity.version,
                    model=m.identity.model,
                    permissions=m.identity.permissions,
                    input_hash=m.identity.input_hash,
                    output_hash=m.identity.output_hash,
                    output=m.output.model_dump(mode="json"),
                    confidence=m.output.confidence,
                )
            )
        write_audit(
            session,
            actor,
            "risk.assess",
            aid,
            f"{risk.level}/{trust.band}",
            {"trust": trust.score},
            commit=False,
        )
        result = result.model_copy(update={"assessment_id": aid})
    session.commit()
    return result
