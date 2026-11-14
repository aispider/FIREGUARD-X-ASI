import { useCallback, useState } from 'react';
import { Login } from './components/Login';
import { ErrorBox } from './components/ui';
import { lvColor } from './lib/format';
import { Analytics } from './screens/Analytics';
import { Audit } from './screens/Audit';
import { Council } from './screens/Council';
import { Debate } from './screens/Debate';
import { Evidence } from './screens/Evidence';
import { Mission } from './screens/Mission';
import { Security } from './screens/Security';
import { Trust } from './screens/Trust';
import { Twin } from './screens/Twin';
import { useAuth } from './state/auth';
import { MissionProvider, useMission } from './state/mission';
import type { ScreenKey } from './voice/commands';
import { VoicePanel } from './voice/VoicePanel';

const TABS: [ScreenKey, string][] = [
  ['mission', 'Mission command'], ['twin', 'Fire digital twin'], ['council', 'AI council'], ['evidence', 'Evidence explorer'],
  ['debate', 'AI debate'], ['trust', 'Trust center'], ['security', 'Security center'], ['analytics', 'Risk analytics'], ['audit', 'Audit center'],
];
const SCREENS: Record<ScreenKey, () => JSX.Element> = {
  mission: Mission, twin: Twin, council: Council, evidence: Evidence, debate: Debate, trust: Trust, security: Security, analytics: Analytics, audit: Audit,
};

export function App() {
  const { user } = useAuth();
  if (!user) return <Login />;
  return <MissionProvider><Shell /></MissionProvider>;
}

function Shell() {
  const { user, logout, config } = useAuth();
  const { result, error, retry, loading } = useMission();
  const [screen, setScreen] = useState<ScreenKey>('mission');
  const [drawer, setDrawer] = useState(false);
  const go = useCallback((s: ScreenKey) => { setScreen(s); setDrawer(false); }, []);
  const Screen = SCREENS[screen];
  const chain = result?.chain ?? [];
  const pipeline = [
    { label: 'Scenario', on: !!result }, { label: 'Evidence retrieved', on: (result?.evidence_summary.count ?? 0) > 0 },
    { label: 'Risk model', on: !!result }, { label: 'Seven-agent council', on: !!result },
    { label: 'Red-team challenge', on: !!result }, ...chain.map((c) => ({ label: c.label, on: c.status === 'pass' || c.status === 'sim' })),
  ];

  return (
    <div className="wrap">
      <a className="skip" href="#main">Skip to content</a>
      <header>
        <div className="brand">
          <button className="btn menu-btn" onClick={() => setDrawer(true)} aria-label="Open menu">☰ Menu</button>
          <div><h1>FIREGUARD<span>-X</span></h1><p>Adaptive Scientific Intelligence for spacecraft fire safety · independent prototype, not a NASA product</p></div>
        </div>
        <div className="hstats">
          <div className="hs"><span className="lbl">Risk</span><b style={{ color: lvColor(result?.risk.level) }}>{result ? `${result.risk.level} ${result.risk.score}` : '…'}</b></div>
          <div className="hs"><span className="lbl">Evidence</span><b>{config?.evidence_mode ?? '…'}{result?.evidence_summary.synthetic_only ? ' · SYNTHETIC/DEMO' : ''}</b></div>
          <div className="hs"><span className="lbl">{user?.role}</span><b className="live"><i />{user?.username}</b></div>
          <button className="btn" onClick={logout}>Sign out</button>
        </div>
      </header>
      <div className={`scrim ${drawer ? 'open' : ''}`} onClick={() => setDrawer(false)} />
      <aside className={`side ${drawer ? 'open' : ''}`}>
        <nav className="tabs" aria-label="Screens">
          <p className="ttl">Screens</p>
          <ul>{TABS.map(([k, l]) => (
            <li key={k}><button className="tab-btn" aria-current={screen === k ? 'page' : undefined} aria-selected={screen === k} onClick={() => go(k)}>{l}</button></li>
          ))}</ul>
        </nav>
        <nav className="pipe" aria-label="Mission pipeline">
          <p className="ttl">Mission pipeline</p>
          <ol>{pipeline.map((p, i) => <li key={`${p.label}-${i}`} className={`stage ${p.on ? 'done' : ''}`}><i className="d" />{p.label}</li>)}</ol>
        </nav>
      </aside>
      <main className="main" id="main" aria-busy={loading}>
        {error && <ErrorBox error={error} onRetry={retry} />}
        <Screen />
        <footer className="note">Independent prototype. Not a NASA product and not endorsed by NASA. The risk model and Trust Score are prototype metrics, not NASA-approved. All mission actions are simulated and a human approves each one.</footer>
      </main>
      <VoicePanel go={go} />
    </div>
  );
}
