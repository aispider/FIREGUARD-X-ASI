/**
 * TypeScript mirror of backend/app/schemas.py. Keep in lock-step with the pydantic models.
 * Timestamps arrive as ISO-8601 strings.
 */

export type Level = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type Material = 'PMMA' | 'Cotton-fiberglass fabric' | 'Polyethylene' | 'Silicone' | 'Nomex fabric';
export type Geometry = 'thin_sheet' | 'cylinder' | 'thick_slab';
export type Gravity = 'microgravity' | 'lunar' | 'mars' | 'earth';
export type TrustBand = 'REJECT' | 'LOW CONFIDENCE' | 'REVIEW' | 'TRUSTED';
export type GuardianStatus = 'TRUSTED' | 'REQUIRES REVIEW' | 'REJECTED';
export type GateStatus = 'pass' | 'fail' | 'demo';
export type Severity = 'LOW' | 'MEDIUM' | 'HIGH';

export const INSUFFICIENT_EVIDENCE_TEXT = 'INSUFFICIENT EVIDENCE — HUMAN REVIEW REQUIRED.';

export const MATERIALS: readonly Material[] = [
  'PMMA',
  'Cotton-fiberglass fabric',
  'Polyethylene',
  'Silicone',
  'Nomex fabric',
];
export const GEOMETRIES: readonly Geometry[] = ['thin_sheet', 'cylinder', 'thick_slab'];
export const GRAVITIES: readonly Gravity[] = ['microgravity', 'lunar', 'mars', 'earth'];

// ----------------------------------------------------------------------------- input

export interface SensorFlags {
  smoke_detected: boolean | null;
  optical_flame_detected: boolean | null;
}

export interface ScenarioIn {
  name: string | null;
  oxygen_percent: number;
  airflow_cm_s: number;
  pressure_kpa: number;
  temperature_k: number;
  external_heating_kw_m2: number;
  material: Material;
  fuel_geometry: Geometry;
  gravity: Gravity;
  sensor_flags: SensorFlags | null;
}

export interface AnalysisRequest {
  scenario: ScenarioIn;
  persist: boolean;
}

export type SweepAxis = 'oxygen_percent' | 'airflow_cm_s';

export interface SweepRequest {
  scenario: ScenarioIn;
  axis: SweepAxis;
}

export interface EvidenceSearchIn {
  query: string;
  limit: number;
  experiment?: string | null;
}

export interface PolicyCheckIn {
  agent: string;
  action: string;
}

export interface ScanIn {
  text: string;
}

export interface DemoDocIn {
  doc_key: string;
}

export interface ApprovalIn {
  assessment_id: string;
  decision: 'approve' | 'reject';
  note?: string | null;
  confirm: boolean;
}

export interface IngestIn {
  ntrs_ids?: string[] | null;
  include_web: boolean;
}

export interface LoginIn {
  username: string;
  password: string;
}

// ----------------------------------------------------------------------------- output

export interface EvidenceRef {
  source_id: string;
  claim: string;
  confidence: number;
}

export type Integrity = 'verified' | 'quarantined';

export interface Provenance {
  document_id: string;
  title: string;
  source: string;
  source_url: string | null;
  ntrs_id: string | null;
  publication_date: string | null;
  sha256: string;
  retrieved_at: string | null;
  version: string;
  license: string | null;
  integrity: Integrity;
}

export type EvidenceStatus = 'used' | 'excluded_injection' | 'quarantined';

export interface EvidenceItem {
  chunk_id: string;
  experiment: string | null;
  text: string;
  relevance: number;
  variables: string[];
  materials: string[];
  topic: string;
  gravity: string;
  page: number | null;
  synthetic: boolean;
  status: EvidenceStatus;
  provenance: Provenance | null;
  flags: string[];
}

export interface AgentIdentity {
  agent_id: string;
  role: string;
  version: string;
  model: string;
  permissions: string[];
  input_hash: string;
  output_hash: string;
}

export interface AgentOutput {
  agent: string;
  finding: string;
  evidence: EvidenceRef[];
  confidence: number;
  verdict: string;
  uncertainties: string[];
  limitations: string[];
  recommendation: string | null;
  payload: Record<string, unknown>;
}

export interface CouncilMember {
  key: string;
  code: string;
  name: string;
  identity: AgentIdentity;
  output: AgentOutput;
  valid: boolean;
}

export interface Consensus {
  level: 'HIGH' | 'MEDIUM' | 'LOW';
  agreement: number;
  open_challenges: number;
}

export interface Driver {
  name: string;
  contribution: number;
  share: number;
}

export interface RiskOut {
  score: number;
  level: Level;
  crew_level: Level;
  flame_growth: Level;
  spread_potential: Level;
  extinction_probability: number;
  confidence: number;
  drivers: Driver[];
  multiplier: number;
  nonlinear_airflow: boolean;
  in_envelope: boolean;
  out_of_range: string[];
  envelope_source: 'prototype_assumption' | 'nasa_observations';
}

export interface Challenge {
  challenge: string;
  severity: Severity;
  passed: boolean;
  category: string;
}

export interface Gate {
  key: string;
  label: string;
  status: GateStatus;
  value: string;
}

export interface TrustComponent {
  key: string;
  label: string;
  /** Fraction 0-1. */
  weight: number;
  /** 0-100. */
  score: number;
}

export interface TrustOut {
  score: number;
  band: TrustBand;
  guardian_status: GuardianStatus;
  components: TrustComponent[];
  gates: Gate[];
  all_gates_pass: boolean;
  insufficient_evidence: boolean;
  verdict: string;
  note: string;
}

export interface ActionStep {
  title: string;
  detail: string;
}

export type ChainStatus = 'pass' | 'fail' | 'wait' | 'sim';

export interface ChainLink {
  key: string;
  label: string;
  status: ChainStatus;
  value: string;
}

export interface DecisionOut {
  level: Level;
  actions: ActionStep[];
  human_approval_required: boolean;
  simulated_only: boolean;
  insufficient_evidence: boolean;
  summary: string;
}

export type DebateSpeaker = 'fire' | 'red' | 'dat' | 'grd' | 'cmdr' | 'con';

export interface DebateMessage {
  speaker: DebateSpeaker;
  label: string;
  text: string;
  citations: string[];
}

export interface Layers {
  nasa_evidence: string[];
  prototype_assumptions: string[];
  synthetic_values: string[];
}

export type EvidenceMode = 'official' | 'mixed' | 'demo';

export interface EvidenceSummary {
  count: number;
  documents: number;
  official_documents: number;
  synthetic_only: boolean;
  mode: EvidenceMode;
  coverage: number;
  material_covered: boolean;
  excluded: number;
}

export interface IntegritySummary {
  ok: boolean;
  checked: number;
  quarantined: string[];
}

export interface AnalysisResult {
  assessment_id: string | null;
  generated_at: string;
  scenario: ScenarioIn;
  risk: RiskOut;
  trust: TrustOut;
  evidence: EvidenceItem[];
  evidence_summary: EvidenceSummary;
  council: CouncilMember[];
  consensus: Consensus;
  challenges: Challenge[];
  decision: DecisionOut;
  chain: ChainLink[];
  debate: DebateMessage[];
  layers: Layers;
  integrity: IntegritySummary;
  security_flags: Record<string, boolean>;
  limitations: string[];
}

export interface SweepOut {
  axis: string;
  xs: number[];
  scores: number[];
  current: number;
  current_score: number;
  envelope: number[];
}

export interface HeatmapOut {
  oxygen: number[];
  airflow: number[];
  /** scores[airflowIndex][oxygenIndex] */
  scores: number[][];
  current: Record<string, number>;
}

export interface PresetOut {
  key: string;
  name: string;
  scenario: ScenarioIn;
  synthetic: boolean;
  note: string;
}

export interface DocumentOut {
  doc_key: string;
  title: string;
  experiment: string | null;
  source: string;
  source_url: string | null;
  ntrs_id: string | null;
  publication_date: string | null;
  document_type: string | null;
  center: string | null;
  license: string | null;
  distribution: string | null;
  version: string;
  retrieved_at: string | null;
  expected_sha256: string;
  current_sha256: string;
  manifest_sha256: string | null;
  status: Integrity;
  synthetic: boolean;
  chunks: number;
  bytes: number;
}

export interface ExperimentOut {
  key: string;
  name: string;
  program: string;
  description: string;
  source_url: string | null;
  variables: string[];
  documents: number;
  chunks: number;
  official_documents: number;
}

export interface SecurityEventOut {
  id: number;
  created_at: string;
  event_type: string;
  severity: string;
  source: string;
  description: string;
  status: string;
}

export interface AuditEntryOut {
  id: number;
  ts: string;
  username: string;
  action: string;
  resource: string;
  result: string;
  hash: string;
  prev_hash: string;
}

export interface AgentRunRow {
  agent_id: string;
  role: string;
  version: string;
  model: string;
  input_hash: string;
  output_hash: string;
  confidence: number;
  assessment_id: string | null;
  created_at: string;
}

export interface AuditOut {
  chain_ok: boolean;
  entries: AuditEntryOut[];
  /** Backend declares dict[str, Any]; the keys below are what routes.py currently emits. */
  agent_runs: Array<Partial<AgentRunRow> & Record<string, unknown>>;
}

export interface IntegrityOut {
  ok: boolean;
  checked: number;
  quarantined: string[];
  manifest_ok: boolean;
  documents: DocumentOut[];
}

export interface ScanOut {
  detected: boolean;
  flags: string[];
  clean_text: string;
  severity: Severity | null;
}

export interface PermissionAgentRow {
  key: string;
  name: string;
  role: string;
  grants: Record<string, boolean>;
}

export interface PermissionMatrixOut {
  agents: Array<Partial<PermissionAgentRow> & Record<string, unknown>>;
  actions: string[];
  denied_always: string[];
}

export interface PolicyDecisionOut {
  allowed: boolean;
  reason: string;
}

export interface AttackResult {
  key: string;
  name: string;
  attack: string;
  defense: string;
  detail: string;
  blocked: boolean;
}

export interface AttackSuiteOut {
  blocked: number;
  total: number;
  results: AttackResult[];
}

export interface SimStep {
  index: number;
  title: string;
  detail: string;
  risk_after: number;
}

export interface ApprovalOut {
  assessment_id: string;
  decision: string;
  allowed: boolean;
  reason: string;
  status: string;
  steps: SimStep[];
  audit_hash: string | null;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  username: string;
  role: string;
  permissions: string[];
}

export interface MeOut {
  username: string;
  role: string;
  permissions: string[];
}

export interface AuthConfigOut {
  demo_mode: boolean;
  demo_users: Array<Record<string, string>>;
  demo_password: string | null;
  security_demo_enabled: boolean;
  evidence_mode: string;
  llm_enabled: boolean;
  embedding_provider: string;
}

export interface IngestJobOut {
  id: number;
  status: string;
  requested_by: string;
  stats: Record<string, unknown>;
  log: string;
  created_at: string;
  finished_at: string | null;
}

export interface HealthOut {
  status: 'ok' | 'degraded';
  database: boolean;
  redis: boolean;
  documents: number;
  official_documents: number;
  chunks: number;
  evidence_mode: string;
  version: string;
}

export interface CouncilOut {
  council: CouncilMember[];
  consensus: Consensus;
  challenges: Challenge[];
  trust: TrustOut;
}

export interface ValidateIn {
  text?: string | null;
}

export interface ValidateOut {
  integrity: IntegrityOut;
  scan: ScanOut | null;
}

export interface DemoState {
  injection_active: boolean;
  tampered: string[];
}

/** FastAPI error body. */
export interface ApiErrorBody {
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
}
