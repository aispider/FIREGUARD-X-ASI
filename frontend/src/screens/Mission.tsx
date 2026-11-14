import { useState } from 'react';
import { GEOMETRIES, GRAVITIES, MATERIALS, type ScenarioIn } from '../api/types';
import { Bar, Kpi, Panel, Tag } from '../components/ui';
import { GEOMETRY_LABEL, GRAVITY_LABEL } from '../lib/enums';
import { explainError } from '../lib/errors';
import { lvColor, pct } from '../lib/format';
import { useAuth } from '../state/auth';
import { useMission } from '../state/mission';
import type { ApprovalOut } from '../api/types';

type NumKey = 'oxygen_percent' | 'airflow_cm_s' | 'pressure_kpa' | 'temperature_k' | 'external_heating_kw_m2';
const SLIDERS: { k: NumKey; label: string; min: number; max: number; step: number; unit: string }[] = [
  { k: 'oxygen_percent', label: 'Oxygen', min: 15, max: 30, step: 0.1, unit: '%' },
  { k: 'airflow_cm_s', label: 'Airflow', min: 0, max: 60, step: 0.1, unit: 'cm/s' },
  { k: 'pressure_kpa', label: 'Pressure', min: 40, max: 160, step: 1, unit: 'kPa' },
  { k: 'temperature_k', label: 'Temperature', min: 250, max: 700, step: 5, unit: 'K' },
  { k: 'external_heating_kw_m2', label: 'External heating', min: 0, max: 40, step: 0.5, unit: 'kW/m²' },
];

export function Mission() {
  const { scenario, setScenario, presets, result, loading, persist } = useMission();
  const { api, can } = useAuth();
  const [approval, setApproval] = useState<ApprovalOut | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const approveGate = { allowed: can('approval:decide'), reason: can('approval:decide') ? '' : 'Your role cannot approve actions (needs approval:decide).' };

  async function act(decision: 'approve' | 'reject') {
    setMsg(null);
    try {
      const stored = result?.assessment_id ? result : await persist();
      if (!stored?.assessment_id) return setMsg('Could not store the assessment. Your role may not allow it.');
      const r = await api.approve({ assessment_id: stored.assessment_id, decision, note: null, confirm: decision === 'reject' || confirming });
      setApproval(r);
      setConfirming(false);
      if (!r.allowed && r.reason.includes('confirm')) setConfirming(true);
    } catch (e) { setMsg(explainError(e).body); }
  }

  const r = result?.risk;
  return (
    <div className="grid">
      <Panel title="Scenario" sub="Move a control and the council re-runs. Presets are SYNTHETIC/DEMO scenarios.">
        <div className="presets">
          {presets.map((p) => (
            <button key={p.key} className="btn" onClick={() => { setScenario(p.scenario); setApproval(null); }}>{p.name}</button>
          ))}
        </div>
        <div className="controls">
          {SLIDERS.map((s) => (
            <div className="ctl" key={s.k}>
              <div className="row"><label className="lbl" htmlFor={s.k}>{s.label}</label><output>{scenario[s.k]} {s.unit}</output></div>
              <input id={s.k} type="range" min={s.min} max={s.max} step={s.step} value={scenario[s.k]}
                onChange={(e) => setScenario({ [s.k]: Number(e.target.value) } as Partial<ScenarioIn>)} />
            </div>
          ))}
          <Select label="Fuel" value={scenario.material} opts={MATERIALS.map((m) => [m, m])} on={(v) => setScenario({ material: v as ScenarioIn['material'] })} />
          <Select label="Geometry" value={scenario.fuel_geometry} opts={GEOMETRIES.map((m) => [m, GEOMETRY_LABEL[m]])} on={(v) => setScenario({ fuel_geometry: v as ScenarioIn['fuel_geometry'] })} />
          <Select label="Gravity" value={scenario.gravity} opts={GRAVITIES.map((m) => [m, GRAVITY_LABEL[m]])} on={(v) => setScenario({ gravity: v as ScenarioIn['gravity'] })} />
        </div>
      </Panel>

      {r && result && (
        <>
          <Panel cls="s12">
            <div className="kpis" aria-busy={loading}>
              <Kpi label="Fire risk" value={r.score} small="/100" level={r.level} sub={r.level} />
              <Kpi label="Crew risk" value={r.crew_level} level={r.crew_level} />
              <Kpi label="Extinction chance" value={r.extinction_probability} small="%" />
              <Kpi label="Confidence" value={pct(r.confidence)} small="%" sub={r.in_envelope ? 'inside tested envelope' : 'extrapolating'} />
              <Kpi label="AI trust" value={result.trust.score} small="/100" sub={result.trust.band} />
              <Kpi label="Evidence" value={result.evidence_summary.count} sub={`${result.evidence_summary.official_documents} official docs`} />
            </div>
            {result.evidence_summary.synthetic_only && <div className="note"><Tag tone="syn">SYNTHETIC/DEMO</Tag> All evidence is demonstration text. Run the NASA ingestion to use official documents.</div>}
          </Panel>

          <Panel title="Recommendation" cls="s7" sub={result.decision.summary}>
            <div className="decision" style={{ borderColor: lvColor(result.decision.level) }}>
              <div className="big" style={{ color: lvColor(result.decision.level) }}>{result.decision.insufficient_evidence ? 'INSUFFICIENT EVIDENCE' : result.decision.level}</div>
              <ol style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>{result.decision.actions.map((a) => <li key={a.title}><b>{a.title}</b><div className="note">{a.detail}</div></li>)}</ol>
              <div className="note">Simulated only. A human must approve. The AI never commands a spacecraft.</div>
            </div>
            <div className="chain">{result.chain.map((c) => <div key={c.key} className={`stepl ${c.status}`}><span className="lbl">{c.label}</span><b>{c.value}</b></div>)}</div>
            <div className="cmdrow">
              <button className="btn primary" disabled={!approveGate.allowed || result.decision.insufficient_evidence} title={approveGate.reason} onClick={() => act('approve')}>
                {confirming ? 'Confirm approval (simulate)' : 'Approve (simulate)'}
              </button>
              <button className="btn" disabled={!approveGate.allowed} title={approveGate.reason} onClick={() => act('reject')}>Reject</button>
            </div>
            {msg && <div className="errbox">{msg}</div>}
            {approval && (
              <div className="note" role="status">
                <b>{approval.allowed ? approval.status : 'Blocked'}.</b> {approval.reason}
                {approval.steps.map((s) => <div key={s.index} className="mono">{s.index}. {s.title} → risk {s.risk_after}</div>)}
              </div>
            )}
          </Panel>

          <Panel title="What drives the risk" cls="s5">
            <div className="drv">{r.drivers.map((d) => (
              <div className="r" key={d.name}><span>{d.name}</span><Bar value={d.share * 100} color={lvColor(r.level)} /><span className="v">{pct(d.share)}%</span></div>
            ))}</div>
            {r.nonlinear_airflow && <div className="note">Airflow is in a nonlinear regime. Cut it in stages.</div>}
            {r.out_of_range.length > 0 && <div className="note" style={{ color: 'var(--high)' }}>Outside the tested envelope: {r.out_of_range.join(', ')}.</div>}
          </Panel>

          <Panel title="Evidence layers" sub="NASA evidence, prototype assumptions and synthetic values are kept apart." cls="s12">
            <div className="layers">
              <Layer title="NASA evidence" items={result.layers.nasa_evidence} empty="None ingested yet." />
              <Layer title="Prototype assumptions" items={result.layers.prototype_assumptions} />
              <Layer title="SYNTHETIC/DEMO values" items={result.layers.synthetic_values} empty="None used." />
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}

function Layer({ title, items, empty }: { title: string; items: string[]; empty?: string }) {
  return <div className="layer"><span className="lbl">{title}</span>{items.length ? <ul>{items.map((i) => <li key={i}>{i}</li>)}</ul> : <span className="note">{empty}</span>}</div>;
}

function Select({ label, value, opts, on }: { label: string; value: string; opts: [string, string][]; on: (v: string) => void }) {
  const id = `sel-${label}`;
  return (
    <div className="ctl"><label className="lbl" htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => on(e.target.value)}>{opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
    </div>
  );
}
