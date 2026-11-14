import { useEffect, useRef } from 'react';
import { Kpi, Panel } from '../components/ui';
import { GRAVITY_G } from '../lib/enums';
import { lvColor } from '../lib/format';
import { useMission } from '../state/mission';

/** Stylised flame. Spherical without buoyancy (microgravity), teardrop with gravity. Illustration, not a simulation. */
export function Twin() {
  const { result, scenario } = useMission();
  const ref = useRef<HTMLCanvasElement>(null);
  const score = (result?.risk.score ?? 0) / 100;
  const g = GRAVITY_G[scenario.gravity];

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext('2d');
    if (!ctx) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let raf = 0;
    let t = 0;
    const draw = () => {
      const w = (c.width = c.clientWidth * devicePixelRatio);
      const h = (c.height = c.clientHeight * devicePixelRatio);
      ctx.clearRect(0, 0, w, h);
      const cx = w * 0.5, base = h * 0.7;
      const r = Math.min(w, h) * (0.04 + 0.2 * score);
      ctx.fillStyle = '#7a8aa3'; // fuel sample
      ctx.fillRect(w * 0.2, base, w * 0.6, Math.max(4, (scenario.fuel_geometry === 'thin_sheet' ? 6 : scenario.fuel_geometry === 'cylinder' ? 16 : 24) * devicePixelRatio));
      if (score > 0.02) {
        const wob = reduce ? 0 : Math.sin(t / 7) * r * 0.06;
        for (const [k, col] of [[1, 'rgba(255,90,40,.55)'], [0.7, 'rgba(255,170,60,.7)'], [0.4, 'rgba(255,240,180,.9)']] as const) {
          ctx.beginPath();
          const rx = r * k * (1 - 0.35 * g) + wob;
          const ry = r * k * (1 + 1.4 * g);
          ctx.ellipse(cx, base - ry * (0.9 + 0.3 * g), rx, ry, 0, 0, Math.PI * 2);
          ctx.fillStyle = col;
          ctx.fill();
        }
      }
      t += 1;
      if (!reduce) raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [score, g, scenario.fuel_geometry]);

  return (
    <div className="grid">
      <Panel title="Fire digital twin" sub="Illustration driven by the risk score and gravity. Not a CFD simulation." cls="s8">
        <div className="stagebox" style={{ minHeight: 360 }}>
          <canvas ref={ref} role="img" aria-label={`Flame illustration, risk ${result?.risk.level ?? 'unknown'}`} style={{ width: '100%', height: 360 }} />
          <span className="chip tl">{scenario.material}</span>
          <span className="chip tr">{scenario.gravity}</span>
          <span className="chip bl" style={{ color: lvColor(result?.risk.level) }}>{result?.risk.level ?? '…'}</span>
        </div>
      </Panel>
      <Panel title="Readouts" cls="s4">
        <div className="kpis">
          <Kpi label="Flame growth" value={result?.risk.flame_growth ?? '…'} level={result?.risk.flame_growth} />
          <Kpi label="Spread potential" value={result?.risk.spread_potential ?? '…'} level={result?.risk.spread_potential} />
          <Kpi label="Extinction" value={result?.risk.extinction_probability ?? '…'} small="%" />
          <Kpi label="Multiplier" value={result?.risk.multiplier ?? '…'} small="×" />
        </div>
      </Panel>
    </div>
  );
}
