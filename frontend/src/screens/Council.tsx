import { Panel, Tag } from '../components/ui';
import { pct, shortHash } from '../lib/format';
import { useMission } from '../state/mission';

export function Council() {
  const { result } = useMission();
  if (!result) return <div className="skel">Waiting for the council…</div>;
  return (
    <div className="grid">
      <Panel title="AI council" sub={`Seven agents. Consensus ${result.consensus.level} (${pct(result.consensus.agreement)}%). ${result.consensus.open_challenges} open challenge(s).`}>
        <div className="council">
          {result.council.map((m) => (
            <article key={m.key} className={`ag ${m.key === 'red' ? 'red' : m.key === 'guardian' ? 'vio' : ''}`}>
              <div className="top"><div className="g">{m.code}</div><div><h3>{m.name}</h3><div className="vd">{m.output.verdict} · {pct(m.output.confidence)}%</div></div></div>
              <p style={{ margin: 0 }}>{m.output.finding}</p>
              {m.output.recommendation && <div className="note">Recommends: {m.output.recommendation}</div>}
              <div className="cites">{m.output.evidence.map((e) => <Tag key={e.source_id}>{e.source_id}</Tag>)}</div>
              {m.output.uncertainties.length > 0 && <ul className="note">{m.output.uncertainties.slice(0, 3).map((u) => <li key={u}>{u}</li>)}</ul>}
              <div className="meta">
                <span>agent</span><span>{m.identity.agent_id} v{m.identity.version}</span>
                <span>model</span><span>{m.identity.model}</span>
                <span>may</span><span>{m.identity.permissions.join(', ')}</span>
                <span>input</span><span>{shortHash(m.identity.input_hash)}</span>
                <span>output</span><span>{shortHash(m.identity.output_hash)}</span>
                <span>valid</span><span>{m.valid ? 'yes' : 'NO — excluded'}</span>
              </div>
            </article>
          ))}
        </div>
      </Panel>
      <Panel title="Red-team challenges" cls="s12">
        <ul className="gates">{result.challenges.map((c) => (
          <li key={c.challenge} className={c.passed ? 'p' : 'f'}><span className="g">{c.passed ? '✓' : '!'}</span><span>{c.challenge}</span><em>{c.severity} · {c.category}</em></li>
        ))}</ul>
      </Panel>
    </div>
  );
}
