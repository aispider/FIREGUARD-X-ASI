import { useCallback, useEffect, useState, type FormEvent } from 'react';
import type { DocumentOut, EvidenceItem, ExperimentOut, IngestJobOut } from '../api/types';
import { ErrorBox, Panel, Tag } from '../components/ui';
import { explainError, type FriendlyError } from '../lib/errors';
import { fmtTime, pct, shortHash } from '../lib/format';
import { useAuth } from '../state/auth';

export function Evidence() {
  const { api, can } = useAuth();
  const [exps, setExps] = useState<ExperimentOut[]>([]);
  const [docs, setDocs] = useState<DocumentOut[]>([]);
  const [hits, setHits] = useState<EvidenceItem[] | null>(null);
  const [q, setQ] = useState('oxygen concentration and flame spread');
  const [err, setErr] = useState<FriendlyError | null>(null);
  const [jobs, setJobs] = useState<IngestJobOut[]>([]);

  const load = useCallback(() => {
    Promise.all([api.experiments(), api.documents(), api.ingestJobs()])
      .then(([e, d, j]) => { setExps(e); setDocs(d); setJobs(j); })
      .catch((x) => setErr(explainError(x)));
  }, [api]);
  useEffect(load, [load]);

  async function search(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    try { setHits(await api.searchEvidence({ query: q, limit: 8, experiment: null })); } catch (x) { setErr(explainError(x)); }
  }
  async function ingest() {
    try { await api.ingestRun(true); load(); } catch (x) { setErr(explainError(x)); }
  }
  const official = docs.filter((d) => !d.synthetic).length;

  return (
    <div className="grid">
      {err && <div className="s12"><ErrorBox error={err} onRetry={load} /></div>}
      <Panel title="Experiments" sub={`${docs.length} documents (${official} official NASA, ${docs.length - official} SYNTHETIC/DEMO).`} cls="s12">
        <div className="kpis">{exps.map((e) => (
          <div className="kpi" key={e.key}><span className="lbl">{e.program}</span><b>{e.key}</b><span className="note">{e.name}</span>
            <span className="s">{e.official_documents} official · {e.documents} docs · {e.chunks} chunks</span></div>
        ))}</div>
        <div className="cmdrow">
          <button className="btn" disabled={!can('ingest:run')} title={can('ingest:run') ? '' : 'Needs ingest:run (admin)'} onClick={ingest}>Download official NASA documents</button>
          <span className="note">The worker needs internet access. {jobs[0] ? `Last job #${jobs[0].id}: ${jobs[0].status}. ${JSON.stringify(jobs[0].stats)}` : 'No jobs yet.'}</span>
        </div>
      </Panel>
      <Panel title="Search evidence" sub="Vector search over ingested chunks. Retrieved text is treated as data, never as instructions." cls="s12">
        <form className="searchrow" onSubmit={search}>
          <input aria-label="Search query" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1 }} />
          <button className="btn primary">Search</button>
        </form>
        <div className="chunks">{(hits ?? []).map((h) => (
          <article className="chunk" key={h.chunk_id}>
            <div><b className="mono">{h.chunk_id}</b> <Tag>{h.experiment ?? '—'}</Tag> {h.synthetic && <Tag tone="syn">SYNTHETIC/DEMO</Tag>} {h.status !== 'used' && <Tag tone="bad">{h.status}</Tag>}
              <span className="note"> relevance {pct(h.relevance)}%</span></div>
            <p style={{ margin: 0 }}>{h.text}</p>
            <div className="tags">{h.variables.map((v) => <Tag key={v}>{v}</Tag>)}</div>
            {h.provenance && <div className="prov hash">{h.provenance.source} · {h.provenance.title} · v{h.provenance.version} · sha256 {shortHash(h.provenance.sha256)}</div>}
          </article>
        ))}</div>
      </Panel>
      <Panel title="Provenance" sub="Every document carries its source, version and SHA-256 hash." cls="s12">
        <div className="tw"><table>
          <thead><tr><th>Document</th><th>Source</th><th>Published</th><th>Ver</th><th>Chunks</th><th>SHA-256</th><th>Status</th></tr></thead>
          <tbody>{docs.map((d) => (
            <tr key={d.doc_key}><td>{d.title}<div className="hash">{d.doc_key}{d.source_url && <> · <a className="link" href={d.source_url} target="_blank" rel="noreferrer noopener">source</a></>}</div></td>
              <td>{d.source}{d.synthetic && <> <Tag tone="syn">SYNTHETIC</Tag></>}</td><td>{d.publication_date ?? '—'}</td><td>{d.version}</td><td>{d.chunks}</td>
              <td className="hash">{shortHash(d.current_sha256)}</td><td><Tag tone={d.status === 'verified' ? 'ok' : 'bad'}>{d.status}</Tag> <span className="note">{fmtTime(d.retrieved_at)}</span></td></tr>
          ))}</tbody>
        </table></div>
      </Panel>
    </div>
  );
}
