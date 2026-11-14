import { useState, type FormEvent } from 'react';
import { explainError } from '../lib/errors';
import { useAuth } from '../state/auth';

export function Login() {
  const { login, config, configError, sessionNotice } = useAuth();
  const [u, setU] = useState('commander');
  const [p, setP] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try { await login(u, p); } catch (x) { setErr(explainError(x).body); } finally { setBusy(false); }
  }
  return (
    <main className="login">
      <div className="panel box">
        <div>
          <h1 style={{ fontSize: 38 }}>FIREGUARD<span style={{ color: 'var(--high)' }}>-X</span></h1>
          <div className="note">Adaptive Scientific Intelligence for spacecraft fire safety. Independent prototype, not a NASA product.</div>
        </div>
        {sessionNotice && <div className="errbox">{sessionNotice}</div>}
        {configError != null && <div className="errbox" role="alert">Cannot reach the backend. Is the API running?</div>}
        <form onSubmit={submit}>
          <label><span className="lbl">Username</span><input value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" required /></label>
          <label><span className="lbl">Password</span><input type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" required /></label>
          {err && <div className="errbox" role="alert">{err}</div>}
          <button className="btn primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
        {config?.demo_mode && (
          <div className="demoUsers note">
            Demo mode. Users: {config.demo_users.map((d) => (
              <button key={d.username} type="button" className="btn" style={{ margin: 3 }} onClick={() => { setU(d.username ?? ''); setP(config.demo_password ?? ''); }}>
                {d.username} ({d.role})
              </button>
            ))}
          </div>
        )}
        <div className="note">All mission actions are simulated. A human approves every action.</div>
      </div>
    </main>
  );
}
