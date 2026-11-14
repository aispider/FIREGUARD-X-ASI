/** Permission-gating helpers. The backend is the authority; the UI only hides or disables what a role cannot do. */

export type Permission =
  | 'evidence:read'
  | 'evidence:search'
  | 'simulation:run'
  | 'analysis:run'
  | 'risk:read'
  | 'risk:assess'
  | 'agents:council'
  | 'security:read'
  | 'security:validate'
  | 'security:red_team'
  | 'security:demo'
  | 'audit:read'
  | 'approval:decide'
  | 'ingest:run'
  | 'admin:users';

export function can(permissions: readonly string[] | null | undefined, needed: Permission): boolean {
  return !!permissions && permissions.includes(needed);
}

export function canAll(permissions: readonly string[] | null | undefined, needed: readonly Permission[]): boolean {
  return needed.every((p) => can(permissions, p));
}

export interface Gate {
  allowed: boolean;
  /** Human-readable reason used as a title/tooltip when the control is disabled. */
  reason: string;
}

const LABELS: Record<Permission, string> = {
  'evidence:read': 'read evidence',
  'evidence:search': 'search evidence',
  'simulation:run': 'run simulations',
  'analysis:run': 'run analyses',
  'risk:read': 'read stored assessments',
  'risk:assess': 'store assessments',
  'agents:council': 'run the council',
  'security:read': 'read security data',
  'security:validate': 'validate integrity',
  'security:red_team': 'run the attack suite',
  'security:demo': 'use the security demo controls',
  'audit:read': 'read the audit log',
  'approval:decide': 'approve or reject actions',
  'ingest:run': 'ingest official NASA documents',
  'admin:users': 'administer users',
};

/** Gate for one permission, optionally also requiring the server-side security demo switch. */
export function gate(
  permissions: readonly string[] | null | undefined,
  needed: Permission,
  extra?: { ok: boolean; reason: string },
): Gate {
  if (!can(permissions, needed)) {
    return { allowed: false, reason: `Your role cannot ${LABELS[needed]} (needs ${needed}).` };
  }
  if (extra && !extra.ok) return { allowed: false, reason: extra.reason };
  return { allowed: true, reason: '' };
}
