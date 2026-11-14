import { useCallback, useEffect, useState } from 'react';
import type { AuditOut } from '../api/types';
import { ErrorBox, Kpi, Panel } from '../components/ui';
import { explainError, type FriendlyError } from '../lib/errors';
import { fmtTime, shortHash } from '../lib/format';
import { useAuth } from '../state/auth';

export function Audit() {
  const { api } = useAuth();
  const [a, setA] = useState<AuditOut | null>(null);
  const [err, setErr] = useState<FriendlyError | null>(null);
  const load = useCallback(() => api.audit(80).then(setA).catch((x) => setErr(explainError(x))), [api]);
  useEffect(() => { void load(); }, [load]);
  return (
    <div className="grid">
      {err && <div className="s12"><ErrorBox error={err} onRetry={load} /></div>}
      <Panel title="Audit log" sub="Each entry stores the hash of the one before it. Editing history breaks the chain." cls="s12">
        <div className="kpis"><Kpi label="Hash chain" value={a ? (a.chain_ok ? 'INTACT' : 'BROKEN') : '…'} sub={`${a?.entries.length ?? 0} recent entries`} /></div>
        <div className="tw"><table><thead><tr><th>#</th><th>Time</th><th>User</th><th>Action</th><th>Resource</th><th>Result</th><th>Hash</th></tr></thead>
          <tbody>{a?.entries.map((e) => <tr key={e.id}><td>{e.id}</td><td>{fmtTime(e.ts)}</td><td>{e.username}</td><td>{e.action}</td><td>{e.resource}</td><td>{e.result}</td><td className="hash">{shortHash(e.hash, 10)}</td></tr>)}</tbody></table></div>
      </Panel>
      <Panel title="Agent runs" sub="Identity, model and input/output hashes for each stored assessment." cls="s12">
        <div className="tw"><table><thead><tr><th>Agent</th><th>Version</th><th>Model</th><th>Input</th><th>Output</th></tr></thead>
          <tbody>{a?.agent_runs.map((r, i) => <tr key={i}><td>{String(r.agent_id)}</td><td>{String(r.version)}</td><td>{String(r.model)}</td><td className="hash">{shortHash(String(r.input_hash))}</td><td className="hash">{shortHash(String(r.output_hash))}</td></tr>)}</tbody></table></div>
      </Panel>
    </div>
  );
}
