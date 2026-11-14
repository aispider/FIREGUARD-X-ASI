import type { ReactNode } from 'react';
import type { FriendlyError } from '../lib/errors';
import { lvClass } from '../lib/format';
import type { Level } from '../api/types';

export function Panel({ title, sub, children, cls = 's12' }: { title?: string; sub?: string; children: ReactNode; cls?: string }) {
  return (
    <section className={`panel ${cls}`}>
      {title && (
        <div>
          <h2>{title}</h2>
          {sub && <div className="note">{sub}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Kpi({ label, value, sub, level, small }: { label: string; value: ReactNode; sub?: ReactNode; level?: Level; small?: string }) {
  return (
    <div className="kpi">
      <span className="lbl">{label}</span>
      <span className={`v ${level ? lvClass(level) : ''}`}>{value}{small && <small>{small}</small>}</span>
      {sub && <span className="s">{sub}</span>}
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: FriendlyError; onRetry?: () => void }) {
  return (
    <div className="errbox" role="alert">
      <div><b>{error.title}</b><div className="note">{error.body}</div></div>
      {onRetry && <button className="btn" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Loading({ what = 'Loading' }: { what?: string }) {
  return <div className="skel" role="status">{what}…</div>;
}

export function Bar({ value, color }: { value: number; color?: string }) {
  return <div className="bar" aria-hidden="true"><i style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color ?? 'var(--accent)' }} /></div>;
}

export function Tag({ children, tone }: { children: ReactNode; tone?: 'syn' | 'ok' | 'bad' }) {
  const color = tone === 'syn' ? 'var(--med)' : tone === 'bad' ? 'var(--crit)' : tone === 'ok' ? 'var(--low)' : 'var(--muted)';
  return <span className="tag" style={{ color, borderColor: color }}>{children}</span>;
}
