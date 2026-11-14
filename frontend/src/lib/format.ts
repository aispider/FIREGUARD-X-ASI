import type { Level, TrustBand } from '../api/types';

export const LEVELS: readonly Level[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
export const LEVEL_COLORS = ['var(--low)', 'var(--med)', 'var(--high)', 'var(--crit)'] as const;

export function lvIdx(l: Level | null | undefined): number {
  const i = l ? LEVELS.indexOf(l) : -1;
  return i < 0 ? 0 : i;
}
export const lvClass = (l: Level | null | undefined): string => `lv${lvIdx(l)}`;
export const lvColor = (l: Level | null | undefined): string => LEVEL_COLORS[lvIdx(l)] ?? 'var(--fg)';

export function bandClass(b: TrustBand): string {
  return b === 'TRUSTED' ? 'lv0' : b === 'REVIEW' ? 'lv1' : b === 'LOW CONFIDENCE' ? 'lv2' : 'lv3';
}
export function bandColor(b: TrustBand): string {
  return b === 'TRUSTED' ? 'var(--low)' : b === 'REVIEW' ? 'var(--med)' : b === 'LOW CONFIDENCE' ? 'var(--high)' : 'var(--crit)';
}

export { GEOMETRY_LABEL, GRAVITY_LABEL } from './enums';

export const shortHash = (h: string | null | undefined, n = 12): string => (h ? `${h.slice(0, n)}…` : '—');

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace('T', ' ').slice(0, 19) + 'Z';
}

export const pct = (x: number): number => Math.round(x * 100);
export const clamp = (x: number, a: number, b: number): number => Math.max(a, Math.min(b, x));

/** Sentence-case a snake/upper identifier for display. */
export const humanize = (s: string): string => s.replace(/[_:]/g, ' ').toLowerCase();
