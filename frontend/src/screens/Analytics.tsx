import { useEffect, useState } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { HeatmapOut, SweepAxis, SweepOut } from '../api/types';
import { Panel } from '../components/ui';
import { useAuth } from '../state/auth';
import { useMission } from '../state/mission';

function SweepChart({ axis, title, unit }: { axis: SweepAxis; title: string; unit: string }) {
  const { api } = useAuth();
  const { scenario } = useMission();
  const [d, setD] = useState<SweepOut | null>(null);
  useEffect(() => {
    const c = new AbortController();
    const t = setTimeout(() => api.sweep(scenario, axis, { signal: c.signal }).then(setD).catch(() => undefined), 300);
    return () => { clearTimeout(t); c.abort(); };
  }, [api, scenario, axis]);
  if (!d) return <div className="skel">Loading…</div>;
  const rows = d.xs.map((x, i) => ({ x, score: d.scores[i] }));
  return (
    <Panel title={title} sub="Dashed lines: MEDIUM 25, HIGH 45, CRITICAL 70 (prototype policy). Shaded: assumed tested range." cls="s6">
      <div style={{ height: 260 }} role="img" aria-label={`${title} chart`}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ left: 0, right: 12, top: 8, bottom: 16 }}>
            <CartesianGrid stroke="#1e2837" />
            <XAxis dataKey="x" stroke="#8996ab" label={{ value: unit, position: 'insideBottom', offset: -8, fill: '#8996ab' }} />
            <YAxis domain={[0, 100]} stroke="#8996ab" />
            <Tooltip contentStyle={{ background: '#0e131c', border: '1px solid #2a3649' }} />
            <ReferenceArea x1={d.envelope[0]} x2={d.envelope[1]} fill="#4fd1c5" fillOpacity={0.07} />
            {[25, 45, 70].map((y) => <ReferenceLine key={y} y={y} stroke="#66768f" strokeDasharray="4 4" />)}
            <ReferenceLine x={d.current} stroke="#ff8a3d" />
            <Line dataKey="score" stroke="#4fd1c5" dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

function colorFor(v: number): string {
  return v < 25 ? '#1f6f50' : v < 45 ? '#8a7a22' : v < 70 ? '#b5611f' : '#b3303d';
}

export function Analytics() {
  const { api } = useAuth();
  const { scenario } = useMission();
  const [h, setH] = useState<HeatmapOut | null>(null);
  useEffect(() => {
    const c = new AbortController();
    const t = setTimeout(() => api.heatmap(scenario, { signal: c.signal }).then(setH).catch(() => undefined), 300);
    return () => { clearTimeout(t); c.abort(); };
  }, [api, scenario]);
  return (
    <div className="grid">
      <SweepChart axis="oxygen_percent" title="Risk against oxygen" unit="oxygen (%)" />
      <SweepChart axis="airflow_cm_s" title="Risk against airflow" unit="airflow (cm/s)" />
      <Panel title="Oxygen × airflow map" sub="Each cell is the prototype risk score. Colours also differ in lightness; values are in the tooltip." cls="s12">
        {h ? (
          <div role="img" aria-label="Risk heat map of oxygen against airflow" style={{ display: 'grid', gridTemplateColumns: `repeat(${h.oxygen.length},1fr)`, gap: 1 }}>
            {[...h.scores].reverse().flatMap((row, ri) => row.map((v, ci) => (
              <div key={`${ri}-${ci}`} title={`O₂ ${h.oxygen[ci]} %, flow ${h.airflow[h.airflow.length - 1 - ri]} cm/s → ${v}`} style={{ background: colorFor(v), height: 16 }} />
            )))}
          </div>
        ) : <div className="skel">Loading…</div>}
        <div className="note">x: oxygen 15–25 %, y: airflow 0–40 cm/s (top = fast).</div>
      </Panel>
    </div>
  );
}
