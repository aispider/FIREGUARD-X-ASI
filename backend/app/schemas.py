"""API contract. Every response the dashboard renders is defined here."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Level = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Material = Literal["PMMA", "Cotton-fiberglass fabric", "Polyethylene", "Silicone", "Nomex fabric"]
Geometry = Literal["thin_sheet", "cylinder", "thick_slab"]
Gravity = Literal["microgravity", "lunar", "mars", "earth"]
TrustBand = Literal["REJECT", "LOW CONFIDENCE", "REVIEW", "TRUSTED"]
GuardianStatus = Literal["TRUSTED", "REQUIRES REVIEW", "REJECTED"]
GateStatus = Literal["pass", "fail", "demo"]
Severity = Literal["LOW", "MEDIUM", "HIGH"]

INSUFFICIENT_EVIDENCE_TEXT = "INSUFFICIENT EVIDENCE — HUMAN REVIEW REQUIRED."


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- input


class SensorFlags(Strict):
    """Independent sensor corroboration. `None` means the sensor is not reporting."""

    smoke_detected: bool | None = None
    optical_flame_detected: bool | None = None


class ScenarioIn(Strict):
    name: str | None = Field(default=None, max_length=80)
    oxygen_percent: float = Field(20.4, ge=10, le=40)
    airflow_cm_s: float = Field(3.2, ge=0, le=100)
    pressure_kpa: float = Field(101.0, ge=20, le=300)
    temperature_k: float = Field(420.0, ge=200, le=1500)
    external_heating_kw_m2: float = Field(0.0, ge=0, le=100)
    material: Material = "PMMA"
    fuel_geometry: Geometry = "thin_sheet"
    gravity: Gravity = "microgravity"
    sensor_flags: SensorFlags | None = None


class AnalysisRequest(Strict):
    scenario: ScenarioIn
    persist: bool = False


class SweepRequest(Strict):
    scenario: ScenarioIn
    axis: Literal["oxygen_percent", "airflow_cm_s"]


class EvidenceSearchIn(Strict):
    query: str = Field(min_length=2, max_length=300)
    limit: int = Field(8, ge=1, le=25)
    experiment: str | None = Field(default=None, max_length=32)


class PolicyCheckIn(Strict):
    agent: str = Field(max_length=32)
    action: str = Field(max_length=48)


class ScanIn(Strict):
    text: str = Field(max_length=4000)


class DemoDocIn(Strict):
    doc_key: str = Field(max_length=64)


class ApprovalIn(Strict):
    assessment_id: str = Field(max_length=36)
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)
    confirm: bool = False  # approval needs an explicit second confirmation


class IngestIn(Strict):
    ntrs_ids: list[str] | None = Field(default=None, max_length=60)
    include_web: bool = True


class LoginIn(Strict):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


# --------------------------------------------------------------------------- output


class EvidenceRef(Strict):
    source_id: str
    claim: str
    confidence: float = Field(ge=0, le=1)


class Provenance(Strict):
    document_id: str
    title: str
    source: str
    source_url: str | None
    ntrs_id: str | None
    publication_date: str | None
    sha256: str
    retrieved_at: datetime | None
    version: str
    license: str | None
    integrity: Literal["verified", "quarantined"]


class EvidenceItem(Strict):
    chunk_id: str
    experiment: str | None
    text: str
    relevance: float = Field(ge=0, le=1)
    variables: list[str]
    materials: list[str]
    topic: str
    gravity: str
    page: int | None
    synthetic: bool
    status: Literal["used", "excluded_injection", "quarantined"] = "used"
    provenance: Provenance | None = None
    flags: list[str] = Field(default_factory=list)


class AgentIdentity(Strict):
    agent_id: str
    role: str
    version: str
    model: str
    permissions: list[str]
    input_hash: str
    output_hash: str


class AgentOutput(Strict):
    agent: str
    finding: str
    evidence: list[EvidenceRef]
    confidence: float = Field(ge=0, le=1)
    verdict: str
    uncertainties: list[str]
    limitations: list[str]
    recommendation: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CouncilMember(Strict):
    key: str
    code: str
    name: str
    identity: AgentIdentity
    output: AgentOutput
    valid: bool = True


class Consensus(Strict):
    level: Literal["HIGH", "MEDIUM", "LOW"]
    agreement: float
    open_challenges: int


class Driver(Strict):
    name: str
    contribution: float
    share: float


class RiskOut(Strict):
    score: int
    level: Level
    crew_level: Level
    flame_growth: Level
    spread_potential: Level
    extinction_probability: int
    confidence: float
    drivers: list[Driver]
    multiplier: float
    nonlinear_airflow: bool
    in_envelope: bool
    out_of_range: list[str]
    envelope_source: Literal["prototype_assumption", "nasa_observations"]


class Challenge(Strict):
    challenge: str
    severity: Severity
    passed: bool
    category: str


class Gate(Strict):
    key: str
    label: str
    status: GateStatus
    value: str


class TrustComponent(Strict):
    key: str
    label: str
    weight: float
    score: float


class TrustOut(Strict):
    score: int
    band: TrustBand
    guardian_status: GuardianStatus
    components: list[TrustComponent]
    gates: list[Gate]
    all_gates_pass: bool
    insufficient_evidence: bool
    verdict: str
    note: str


class ActionStep(Strict):
    title: str
    detail: str


class ChainLink(Strict):
    key: str
    label: str
    status: Literal["pass", "fail", "wait", "sim"]
    value: str


class DecisionOut(Strict):
    level: Level
    actions: list[ActionStep]
    human_approval_required: bool = True
    simulated_only: bool = True
    insufficient_evidence: bool
    summary: str


class DebateMessage(Strict):
    speaker: Literal["fire", "red", "dat", "grd", "cmdr", "con"]
    label: str
    text: str
    citations: list[str]


class Layers(Strict):
    nasa_evidence: list[str]
    prototype_assumptions: list[str]
    synthetic_values: list[str]


class EvidenceSummary(Strict):
    count: int
    documents: int
    official_documents: int
    synthetic_only: bool
    mode: Literal["official", "mixed", "demo"]
    coverage: float
    material_covered: bool
    excluded: int


class IntegritySummary(Strict):
    ok: bool
    checked: int
    quarantined: list[str]


class AnalysisResult(Strict):
    assessment_id: str | None
    generated_at: datetime
    scenario: ScenarioIn
    risk: RiskOut
    trust: TrustOut
    evidence: list[EvidenceItem]
    evidence_summary: EvidenceSummary
    council: list[CouncilMember]
    consensus: Consensus
    challenges: list[Challenge]
    decision: DecisionOut
    chain: list[ChainLink]
    debate: list[DebateMessage]
    layers: Layers
    integrity: IntegritySummary
    security_flags: dict[str, bool]
    limitations: list[str]


class RiskAssessmentOut(Strict):
    """The compact shape from the project brief, plus the stored ID."""

    id: str
    risk_level: Level
    risk_score: int
    confidence: float
    evidence_count: int
    guardian_status: GuardianStatus
    red_team_status: Literal["PASSED", "CHALLENGED"]
    trust_score: int
    status: str
    drivers: list[str]
    limitations: list[str]


class SimulationOut(Strict):
    scenario: ScenarioIn
    risk: RiskOut
    evidence: list[EvidenceItem]
    layers: Layers
    disclaimer: str


class SweepOut(Strict):
    axis: str
    xs: list[float]
    scores: list[float]
    current: float
    current_score: float
    envelope: list[float]


class HeatmapOut(Strict):
    oxygen: list[float]
    airflow: list[float]
    scores: list[list[float]]
    current: dict[str, float]


class PresetOut(Strict):
    key: str
    name: str
    scenario: ScenarioIn
    synthetic: bool = True
    note: str = ""


class DocumentOut(Strict):
    doc_key: str
    title: str
    experiment: str | None
    source: str
    source_url: str | None
    ntrs_id: str | None
    publication_date: str | None
    document_type: str | None
    center: str | None
    license: str | None
    distribution: str | None
    version: str
    retrieved_at: datetime | None
    expected_sha256: str
    current_sha256: str
    manifest_sha256: str | None
    status: Literal["verified", "quarantined"]
    synthetic: bool
    chunks: int
    bytes: int


class ExperimentOut(Strict):
    key: str
    name: str
    program: str
    description: str
    source_url: str | None
    variables: list[str]
    documents: int
    chunks: int
    official_documents: int


class SecurityEventOut(Strict):
    id: int
    created_at: datetime
    event_type: str
    severity: str
    source: str
    description: str
    status: str


class AuditEntryOut(Strict):
    id: int
    ts: datetime
    username: str
    action: str
    resource: str
    result: str
    hash: str
    prev_hash: str


class AuditOut(Strict):
    chain_ok: bool
    entries: list[AuditEntryOut]
    agent_runs: list[dict[str, Any]]


class IntegrityOut(Strict):
    ok: bool
    checked: int
    quarantined: list[str]
    manifest_ok: bool
    documents: list[DocumentOut]


class ScanOut(Strict):
    detected: bool
    flags: list[str]
    clean_text: str
    severity: Severity | None


class PermissionMatrixOut(Strict):
    agents: list[dict[str, Any]]
    actions: list[str]
    denied_always: list[str]


class PolicyDecisionOut(Strict):
    allowed: bool
    reason: str


class AttackResult(Strict):
    key: str
    name: str
    attack: str
    defense: str
    detail: str
    blocked: bool


class AttackSuiteOut(Strict):
    blocked: int
    total: int
    results: list[AttackResult]


class SimStep(Strict):
    index: int
    title: str
    detail: str
    risk_after: float


class ApprovalOut(Strict):
    assessment_id: str
    decision: str
    allowed: bool
    reason: str
    status: str
    steps: list[SimStep]
    audit_hash: str | None


class TokenOut(Strict):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    username: str
    role: str
    permissions: list[str]


class MeOut(Strict):
    username: str
    role: str
    permissions: list[str]


class AuthConfigOut(Strict):
    demo_mode: bool
    demo_users: list[dict[str, str]]
    demo_password: str | None
    security_demo_enabled: bool
    evidence_mode: str
    llm_enabled: bool
    embedding_provider: str


class IngestJobOut(Strict):
    id: int
    status: str
    requested_by: str
    stats: dict[str, Any]
    log: str
    created_at: datetime
    finished_at: datetime | None


class HealthOut(Strict):
    status: Literal["ok", "degraded"]
    database: bool
    redis: bool
    documents: int
    official_documents: int
    chunks: int
    evidence_mode: str
    version: str


class CouncilOut(Strict):
    council: list[CouncilMember]
    consensus: Consensus
    challenges: list[Challenge]
    trust: TrustOut


class ValidateIn(Strict):
    text: str | None = Field(default=None, max_length=4000)


class ValidateOut(Strict):
    integrity: IntegrityOut
    scan: ScanOut | None


class DemoState(Strict):
    injection_active: bool
    tampered: list[str]
