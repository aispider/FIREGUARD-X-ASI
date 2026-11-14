import type { HttpClient, RequestOptions } from './client';
import type {
  AnalysisResult,
  ApprovalIn,
  ApprovalOut,
  AttackSuiteOut,
  AuditOut,
  AuthConfigOut,
  DemoState,
  DocumentOut,
  EvidenceItem,
  EvidenceSearchIn,
  ExperimentOut,
  HealthOut,
  HeatmapOut,
  IngestJobOut,
  IntegrityOut,
  MeOut,
  PermissionMatrixOut,
  PolicyDecisionOut,
  PresetOut,
  ScanOut,
  ScenarioIn,
  SecurityEventOut,
  SweepAxis,
  SweepOut,
  TokenOut,
  ValidateOut,
} from './types';

type O = RequestOptions;

/** One typed method per backend route used by the UI. */
export function makeApi(c: HttpClient) {
  return {
    health: (o?: O) => c.get<HealthOut>('/health', o),
    authConfig: (o?: O) => c.get<AuthConfigOut>('/auth/config', o),
    login: (username: string, password: string, o?: O) =>
      c.post<TokenOut>('/auth/login', { username, password }, { ...o, noAuthRedirect: true }),
    me: (o?: O) => c.get<MeOut>('/auth/me', o),
    presets: (o?: O) => c.get<PresetOut[]>('/scenarios/presets', o),
    analyze: (scenario: ScenarioIn, persist: boolean, o?: O) =>
      c.post<AnalysisResult>('/analysis/run', { scenario, persist }, o),
    /** Stored assessment as a full AnalysisResult (the bare /risk/{id} route returns a summary only). */
    riskResult: (id: string, o?: O) => c.get<AnalysisResult>(`/risk/${encodeURIComponent(id)}/result`, o),
    sweep: (scenario: ScenarioIn, axis: SweepAxis, o?: O) => c.post<SweepOut>('/simulation/sweep', { scenario, axis }, o),
    heatmap: (scenario: ScenarioIn, o?: O) => c.post<HeatmapOut>('/simulation/heatmap', scenario, o),
    approve: (body: ApprovalIn, o?: O) => c.post<ApprovalOut>('/approvals', body, o),
    searchEvidence: (body: EvidenceSearchIn, o?: O) => c.post<EvidenceItem[]>('/evidence/search', body, o),
    evidence: (chunkId: string, o?: O) => c.get<EvidenceItem>(`/evidence/${encodeURIComponent(chunkId)}`, o),
    experiments: (o?: O) => c.get<ExperimentOut[]>('/experiments', o),
    documents: (o?: O) => c.get<DocumentOut[]>('/documents', o),
    ingestRun: (includeWeb: boolean, o?: O) => c.post<IngestJobOut>('/ingest/run', { include_web: includeWeb }, o),
    ingestJobs: (o?: O) => c.get<IngestJobOut[]>('/ingest/jobs', o),
    permissions: (o?: O) => c.get<PermissionMatrixOut>('/security/permissions', o),
    policyCheck: (agent: string, action: string, o?: O) =>
      c.post<PolicyDecisionOut>('/security/policy-check', { agent, action }, o),
    securityEvents: (limit = 60, o?: O) => c.get<SecurityEventOut[]>(`/security/events?limit=${limit}`, o),
    integrity: (o?: O) => c.get<IntegrityOut>('/security/integrity', o),
    demoState: (o?: O) => c.get<DemoState>('/security/demo/state', o),
    demoTamper: (docKey: string, o?: O) => c.post<DemoState>('/security/demo/tamper', { doc_key: docKey }, o),
    demoRestore: (docKey: string, o?: O) => c.post<DemoState>('/security/demo/restore', { doc_key: docKey }, o),
    demoInject: (o?: O) => c.post<DemoState>('/security/demo/inject', {}, o),
    demoClearInjection: (o?: O) => c.post<DemoState>('/security/demo/clear-injection', {}, o),
    scan: (text: string, o?: O) => c.post<ScanOut>('/security/scan', { text }, o),
    redTeam: (o?: O) => c.post<AttackSuiteOut>('/security/red-team', {}, o),
    validate: (text: string | null, o?: O) => c.post<ValidateOut>('/security/validate', { text }, o),
    audit: (limit = 80, o?: O) => c.get<AuditOut>(`/audit?limit=${limit}`, o),
  };
}

export type Api = ReturnType<typeof makeApi>;
