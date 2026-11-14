import { Bar, Kpi, Panel } from '../components/ui';
import { bandColor } from '../lib/format';
import { useMission } from '../state/mission';

export function Trust() {
  const { result } = useMission();
  if (!result) return <div className="skel">Waiting for the council…</div>;
  const t = result.trust;
  return (
    <div className="grid">
      <Panel title="AI Trust Score" sub={t.note} cls="s5">
        <div className="gaugebox"><div className="kpi"><span className="lbl">Trust</span>
          <span className="v" style={{ color: bandColor(t.band), fontSize: 64 }}>{t.score}<small>/100</small></span><span className="s">{t.band}</span></div></div>
        <div className="verdict" style={{ borderColor: bandColor(t.band), color: bandColor(t.band) }}>{t.verdict}</div>
        <div className="bands note">Bands: 0–49 REJECT · 50–69 LOW CONFIDENCE · 70–84 REVIEW · 85–100 TRUSTED</div>
        <Kpi label="Scientific guardian" value={t.guardian_status} />
      </Panel>
      <Panel title="Score components" sub="Weights are a prototype policy, not NASA-approved." cls="s7">
        {t.components.map((c) => (
          <div className="comp" key={c.key}><span>{c.label}</span><span className="mono">{Math.round(c.weight * 100)}%</span><span className="mono">{Math.round(c.score)}</span><Bar value={c.score} /></div>
        ))}
      </Panel>
      <Panel title="Trust gates" sub="All gates must pass for TRUSTED. 'demo' means passed only with SYNTHETIC/DEMO evidence." cls="s12">
        <ul className="gates">{t.gates.map((g) => (
          <li key={g.key} className={g.status === 'fail' ? 'f' : 'p'}><span className="g">{g.status === 'fail' ? '✕' : g.status === 'demo' ? 'D' : '✓'}</span><span>{g.label}</span><em>{g.value}</em></li>
        ))}</ul>
      </Panel>
    </div>
  );
}
