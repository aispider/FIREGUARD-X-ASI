"""All REST endpoints. Permissions are declared per route; see security/rbac.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import DISCLAIMER, run_council
from app.api.deps import limiter, redis_ok
from app.config import get_settings
from app.db import get_session
from app.evidence.observations import observed_ranges
from app.models import (
    AgentRun,
    AuditLog,
    Document,
    EvidenceChunk,
    IngestionJob,
    RiskAssessment,
    Scenario,
    SecurityEvent,
    User,
)
from app.rag.retriever import retrieve, scenario_query, to_item
from app.risk.assumptions import ASSUMPTION_LINES
from app.risk.model import assess
from app.schemas import (
    AnalysisRequest,
    AnalysisResult,
    ApprovalIn,
    ApprovalOut,
    AttackSuiteOut,
    AuditEntryOut,
    AuditOut,
    AuthConfigOut,
    CouncilOut,
    DemoDocIn,
    DemoState,
    DocumentOut,
    EvidenceItem,
    EvidenceSearchIn,
    ExperimentOut,
    HealthOut,
    HeatmapOut,
    IngestIn,
    IngestJobOut,
    IntegrityOut,
    LoginIn,
    MeOut,
    PermissionMatrixOut,
    PolicyCheckIn,
    PolicyDecisionOut,
    PresetOut,
    RiskAssessmentOut,
    ScanIn,
    ScanOut,
    ScenarioIn,
    SecurityEventOut,
    SimulationOut,
    SweepOut,
    SweepRequest,
    TokenOut,
    ValidateIn,
    ValidateOut,
)
from app.security import attack_suite, injection, policy
from app.security.audit import verify_chain, write_audit
from app.security.auth import Principal, create_token, current_principal, require, verify_password
from app.security.events import record_event
from app.security.rbac import permissions_for
from app.services import demo as demo_svc
from app.services import mission
from app.simulation import simulator

router = APIRouter(prefix="/api")


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ------------------------------------------------------------------ public
@router.get("/health", response_model=HealthOut)
def health(session: Session = Depends(get_session)) -> HealthOut:
    return mission.health(session, redis_ok())


@router.get("/auth/config", response_model=AuthConfigOut)
def auth_config() -> AuthConfigOut:
    s = get_settings()
    from app.services.seed import DEMO_USERS

    demo = s.demo_mode
    return AuthConfigOut(
        demo_mode=demo,
        demo_users=[{"username": u, "role": r} for u, r in DEMO_USERS] if demo else [],
        demo_password=s.seed_password if demo else None,
        security_demo_enabled=s.enable_security_demo,
        evidence_mode=s.evidence_mode,
        llm_enabled=s.llm_enabled,
        embedding_provider=s.embedding_provider,
    )


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, session: Session = Depends(get_session)) -> TokenOut:
    d = limiter().hit(f"login:{_ip(request)}", get_settings().login_rate_per_min)
    if not d.allowed:
        record_event(session, "LOGIN_RATE_LIMIT", "MEDIUM", _ip(request), "Too many login attempts.")
        raise HTTPException(429, "Too many attempts", headers={"Retry-After": str(d.retry_after)})
    u = session.scalar(select(User).where(User.username == body.username))
    if u is None or not u.is_active or not verify_password(body.password, u.password_hash):
        write_audit(session, body.username[:64], "auth.login", "api", "denied")
        raise HTTPException(401, "Invalid credentials")
    write_audit(session, u.username, "auth.login", "api", "ok")
    return TokenOut(
        access_token=create_token(u.username, u.role),
        username=u.username,
        role=u.role,
        permissions=permissions_for(u.role),
    )


@router.get("/auth/me", response_model=MeOut)
def me(p: Principal = Depends(current_principal)) -> MeOut:
    return MeOut(username=p.username, role=p.role, permissions=list(p.permissions))


# ------------------------------------------------------------------ scenarios / analysis
@router.get("/scenarios/presets", response_model=list[PresetOut])
def presets(
    _: Principal = Depends(require("simulation:run")), session: Session = Depends(get_session)
) -> list[PresetOut]:
    out = []
    for sc in session.scalars(select(Scenario).where(Scenario.preset.is_(True)).order_by(Scenario.id)):
        p = dict(sc.params)
        key = p.pop("key", sc.name)
        p.pop("name", None)
        out.append(
            PresetOut(
                key=key,
                name=sc.name,
                scenario=ScenarioIn(name=sc.name, **p),
                synthetic=sc.synthetic,
                note="SYNTHETIC/DEMO scenario, not a real mission state.",
            )
        )
    return out


@router.post("/analysis/run", response_model=AnalysisResult)
def analysis_run(
    body: AnalysisRequest,
    request: Request,
    p: Principal = Depends(require("analysis:run")),
    session: Session = Depends(get_session),
) -> AnalysisResult:
    if not limiter().hit(f"analysis:{p.username}", get_settings().analysis_rate_per_min).allowed:
        raise HTTPException(429, "Analysis rate limit")
    if body.persist and not p.can("risk:assess"):
        raise HTTPException(403, "Missing permission: risk:assess")
    return run_council(session, body.scenario, persist=body.persist, actor=p.username)


@router.post("/risk/assess", response_model=RiskAssessmentOut)
def risk_assess(
    body: ScenarioIn, p: Principal = Depends(require("risk:assess")), session: Session = Depends(get_session)
) -> RiskAssessmentOut:
    res = run_council(session, body, persist=True, actor=p.username)
    row = session.get(RiskAssessment, res.assessment_id)
    assert row is not None
    return _assessment_out(row, res)


def _assessment_out(a: RiskAssessment, res: AnalysisResult | None = None) -> RiskAssessmentOut:
    r = AnalysisResult.model_validate(res or a.result)
    return RiskAssessmentOut(
        id=a.id,
        risk_level=a.risk_level,
        risk_score=a.risk_score,
        confidence=a.confidence,
        evidence_count=a.evidence_count,
        guardian_status=a.guardian_status,
        red_team_status=a.red_team_status,
        trust_score=a.trust_score,
        status=a.status,
        drivers=[d.name for d in r.risk.drivers[:3]],
        limitations=r.limitations,
    )


@router.get("/risk/{assessment_id}", response_model=RiskAssessmentOut)
def risk_get(
    assessment_id: str, _: Principal = Depends(require("risk:read")), session: Session = Depends(get_session)
) -> RiskAssessmentOut:
    a = session.get(RiskAssessment, assessment_id)
    if a is None:
        raise HTTPException(404, "Not found")
    return _assessment_out(a)


@router.get("/risk/{assessment_id}/result", response_model=AnalysisResult)
def risk_result(
    assessment_id: str, _: Principal = Depends(require("risk:read")), session: Session = Depends(get_session)
) -> AnalysisResult:
    a = session.get(RiskAssessment, assessment_id)
    if a is None:
        raise HTTPException(404, "Not found")
    return AnalysisResult.model_validate(a.result).model_copy(update={"assessment_id": a.id})


@router.post("/agents/council", response_model=CouncilOut)
def council(
    body: ScenarioIn,
    p: Principal = Depends(require("agents:council")),
    session: Session = Depends(get_session),
) -> CouncilOut:
    r = run_council(session, body, persist=False, actor=p.username)
    return CouncilOut(council=r.council, consensus=r.consensus, challenges=r.challenges, trust=r.trust)


@router.post("/simulation/run", response_model=SimulationOut)
def simulation_run(
    body: ScenarioIn,
    _: Principal = Depends(require("simulation:run")),
    session: Session = Depends(get_session),
) -> SimulationOut:
    risk, _pen, _raw = assess(body, observed=observed_ranges(session) or None)
    cands = retrieve(session, body, limit=6)
    used = [c for c in cands if c.status == "used"]
    from app.agents.orchestrator import _layers

    return SimulationOut(
        scenario=body,
        risk=risk,
        evidence=[to_item(c) for c in cands],
        layers=_layers(used),
        disclaimer=DISCLAIMER,
    )


@router.post("/simulation/sweep", response_model=SweepOut)
def sweep(
    body: SweepRequest,
    _: Principal = Depends(require("simulation:run")),
    session: Session = Depends(get_session),
) -> SweepOut:
    return simulator.sweep(body.scenario, body.axis, observed_ranges(session) or None)


@router.post("/simulation/heatmap", response_model=HeatmapOut)
def heatmap(
    body: ScenarioIn,
    _: Principal = Depends(require("simulation:run")),
    session: Session = Depends(get_session),
) -> HeatmapOut:
    return simulator.heatmap(body, observed_ranges(session) or None)


@router.get("/assumptions", response_model=list[str])
def assumptions(_: Principal = Depends(require("simulation:run"))) -> list[str]:
    return ASSUMPTION_LINES


@router.post("/approvals", response_model=ApprovalOut)
def approvals(
    body: ApprovalIn, p: Principal = Depends(current_principal), session: Session = Depends(get_session)
) -> ApprovalOut:
    if not p.can("approval:decide"):
        raise HTTPException(403, "Missing permission: approval:decide")
    try:
        return mission.decide(session, p, body)
    except LookupError:
        raise HTTPException(404, "Assessment not found") from None


# ------------------------------------------------------------------ evidence
@router.post("/evidence/search", response_model=list[EvidenceItem])
def evidence_search(
    body: EvidenceSearchIn,
    p: Principal = Depends(require("evidence:search")),
    session: Session = Depends(get_session),
) -> list[EvidenceItem]:
    # The query is untrusted text. Instruction-like queries are refused and logged; they are never interpreted.
    sc = injection.scan(body.query)
    if sc.exclude:
        record_event(
            session,
            "PROMPT_INJECTION",
            "MEDIUM",
            p.username,
            "Instruction-like text in a search query was refused.",
            {"flags": sc.flags},
        )
        raise HTTPException(422, "The query contains instruction-like text and was refused.")
    cands = retrieve(session, None, query=body.query, limit=body.limit, experiment=body.experiment)
    return [to_item(c) for c in cands]


@router.get("/evidence/{chunk_id:path}", response_model=EvidenceItem)
def evidence_get(
    chunk_id: str, _: Principal = Depends(require("evidence:read")), session: Session = Depends(get_session)
) -> EvidenceItem:
    from app.rag.retriever import Candidate
    from app.security import integrity

    ch = session.scalar(select(EvidenceChunk).where(EvidenceChunk.chunk_key == chunk_id))
    if ch is None:
        raise HTTPException(404, "Not found")
    d = ch.document
    sc = injection.scan(ch.content)
    status = (
        "quarantined"
        if d.quarantined or not integrity.doc_ok(d)
        else "excluded_injection"
        if sc.exclude
        else "used"
    )
    return to_item(
        Candidate(
            ch, d, d.experiment.key if d.experiment else None, 1.0, 1.0, status, sc.flags, sc.clean_text
        )
    )


@router.get("/experiments", response_model=list[ExperimentOut])
def experiments(
    _: Principal = Depends(require("evidence:read")), session: Session = Depends(get_session)
) -> list[ExperimentOut]:
    return mission.list_experiments(session)


@router.get("/documents", response_model=list[DocumentOut])
def documents(
    _: Principal = Depends(require("evidence:read")), session: Session = Depends(get_session)
) -> list[DocumentOut]:
    return mission.list_documents(session)


# ------------------------------------------------------------------ security
@router.post("/security/validate", response_model=ValidateOut)
def sec_validate(
    body: ValidateIn,
    _: Principal = Depends(require("security:validate")),
    session: Session = Depends(get_session),
) -> ValidateOut:
    rep = mission.integrity_report(session)
    sc = None
    if body.text:
        r = injection.scan(body.text)
        sc = ScanOut(detected=r.detected, flags=r.flags, clean_text=r.clean_text, severity=r.severity)
    return ValidateOut(integrity=rep, scan=sc)


@router.post("/security/scan", response_model=ScanOut)
def sec_scan(body: ScanIn, _: Principal = Depends(require("security:validate"))) -> ScanOut:
    r = injection.scan(body.text)
    return ScanOut(detected=r.detected, flags=r.flags, clean_text=r.clean_text, severity=r.severity)


@router.post("/security/red-team", response_model=AttackSuiteOut)
def red_team(
    p: Principal = Depends(require("security:red_team")), session: Session = Depends(get_session)
) -> AttackSuiteOut:
    res = attack_suite.run_suite(session)
    write_audit(session, p.username, "security.red_team", "local-suite", f"{res.blocked}/{res.total} blocked")
    return res


@router.get("/security/permissions", response_model=PermissionMatrixOut)
def permissions(_: Principal = Depends(require("security:read"))) -> PermissionMatrixOut:
    return PermissionMatrixOut(**policy.matrix())


@router.post("/security/policy-check", response_model=PolicyDecisionOut)
def policy_check(
    body: PolicyCheckIn,
    p: Principal = Depends(require("security:read")),
    session: Session = Depends(get_session),
) -> PolicyDecisionOut:
    d = policy.check(body.agent, body.action)
    if not d.allowed:
        record_event(
            session, "POLICY_DENIED", "MEDIUM", f"agent:{body.agent}", f"{body.agent} denied {body.action}"
        )
    write_audit(
        session,
        p.username,
        "policy.check",
        f"{body.agent}:{body.action}",
        "allowed" if d.allowed else "denied",
    )
    return d


@router.get("/security/events", response_model=list[SecurityEventOut])
def events(
    _: Principal = Depends(require("security:read")), session: Session = Depends(get_session), limit: int = 60
) -> list[SecurityEventOut]:
    rows = session.scalars(select(SecurityEvent).order_by(SecurityEvent.id.desc()).limit(min(limit, 200)))
    return [
        SecurityEventOut(
            id=e.id,
            created_at=e.created_at,
            event_type=e.event_type,
            severity=e.severity,
            source=e.source,
            description=e.description,
            status=e.status,
        )
        for e in rows
    ]


@router.get("/security/integrity", response_model=IntegrityOut)
def integrity_get(
    _: Principal = Depends(require("security:read")), session: Session = Depends(get_session)
) -> IntegrityOut:
    return mission.integrity_report(session)


def _demo_guard() -> None:
    if not get_settings().enable_security_demo:
        raise HTTPException(403, "Security demo is disabled (ENABLE_SECURITY_DEMO=false)")


@router.get("/security/demo/state", response_model=DemoState)
def demo_state(
    _: Principal = Depends(require("security:read")), session: Session = Depends(get_session)
) -> DemoState:
    return demo_svc.state(session)


@router.post("/security/demo/tamper", response_model=DemoState)
def demo_tamper(
    body: DemoDocIn, p: Principal = Depends(require("security:demo")), session: Session = Depends(get_session)
) -> DemoState:
    _demo_guard()
    if not demo_svc.tamper(session, body.doc_key):
        raise HTTPException(404, "Document not found")
    write_audit(session, p.username, "demo.tamper", body.doc_key, "simulated")
    mission.integrity_report(session)  # runs verification, quarantines
    return demo_svc.state(session)


@router.post("/security/demo/restore", response_model=DemoState)
def demo_restore(
    body: DemoDocIn, p: Principal = Depends(require("security:demo")), session: Session = Depends(get_session)
) -> DemoState:
    _demo_guard()
    if not demo_svc.restore(session, body.doc_key):
        raise HTTPException(404, "Document not found")
    write_audit(session, p.username, "demo.restore", body.doc_key, "ok")
    return demo_svc.state(session)


@router.post("/security/demo/inject", response_model=DemoState)
def demo_inject(
    p: Principal = Depends(require("security:demo")), session: Session = Depends(get_session)
) -> DemoState:
    _demo_guard()
    demo_svc.inject(session)
    write_audit(session, p.username, "demo.inject", demo_svc.ATTACK_KEY, "simulated")
    return demo_svc.state(session)


@router.post("/security/demo/clear-injection", response_model=DemoState)
def demo_clear(
    p: Principal = Depends(require("security:demo")), session: Session = Depends(get_session)
) -> DemoState:
    _demo_guard()
    demo_svc.clear(session)
    write_audit(session, p.username, "demo.clear", demo_svc.ATTACK_KEY, "ok")
    return demo_svc.state(session)


# ------------------------------------------------------------------ audit / ingest
@router.get("/audit", response_model=AuditOut)
def audit(
    _: Principal = Depends(require("audit:read")), session: Session = Depends(get_session), limit: int = 60
) -> AuditOut:
    rows = list(session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 200))))
    runs = session.scalars(select(AgentRun).order_by(AgentRun.id.desc()).limit(30))
    return AuditOut(
        chain_ok=verify_chain(session),
        entries=[
            AuditEntryOut(
                id=e.id,
                ts=e.ts,
                username=e.username,
                action=e.action,
                resource=e.resource,
                result=e.result,
                hash=e.hash,
                prev_hash=e.prev_hash,
            )
            for e in rows
        ],
        agent_runs=[
            {
                "agent_id": r.agent_id,
                "role": r.role,
                "version": r.version,
                "model": r.model,
                "input_hash": r.input_hash,
                "output_hash": r.output_hash,
                "confidence": r.confidence,
                "assessment_id": r.assessment_id,
                "created_at": r.created_at.isoformat(),
            }
            for r in runs
        ],
    )


@router.post("/ingest/run", response_model=IngestJobOut)
def ingest_run(
    body: IngestIn, p: Principal = Depends(require("ingest:run")), session: Session = Depends(get_session)
) -> IngestJobOut:
    j = IngestionJob(status="queued", requested_by=p.username, params=body.model_dump())
    session.add(j)
    session.commit()
    write_audit(session, p.username, "ingest.queue", str(j.id), "queued")
    return _job(j)


def _job(j: IngestionJob) -> IngestJobOut:
    return IngestJobOut(
        id=j.id,
        status=j.status,
        requested_by=j.requested_by,
        stats=j.stats or {},
        log=j.log or "",
        created_at=j.created_at,
        finished_at=j.finished_at,
    )


@router.get("/ingest/jobs", response_model=list[IngestJobOut])
def ingest_jobs(
    _: Principal = Depends(require("evidence:read")), session: Session = Depends(get_session)
) -> list[IngestJobOut]:
    return [_job(j) for j in session.scalars(select(IngestionJob).order_by(IngestionJob.id.desc()).limit(10))]


_unused = (Document, scenario_query)
