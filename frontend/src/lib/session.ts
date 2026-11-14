/** Bearer token held in memory and mirrored to sessionStorage (every access guarded; storage may be blocked). */

const KEY = 'fgx-session';

export interface SessionUser {
  username: string;
  role: string;
  permissions: string[];
}

export interface StoredSession {
  token: string;
  user: SessionUser;
}

let memory: StoredSession | null = null;

function isStoredSession(v: unknown): v is StoredSession {
  if (typeof v !== 'object' || v === null) return false;
  const o = v as Record<string, unknown>;
  const u = o.user as Record<string, unknown> | undefined;
  return (
    typeof o.token === 'string' &&
    typeof u === 'object' &&
    u !== null &&
    typeof u.username === 'string' &&
    typeof u.role === 'string' &&
    Array.isArray(u.permissions)
  );
}

export function loadSession(): StoredSession | null {
  if (memory) return memory;
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (isStoredSession(parsed)) {
      memory = parsed;
      return parsed;
    }
  } catch {
    /* storage unavailable or corrupt: behave as logged out */
  }
  return null;
}

export function saveSession(s: StoredSession): void {
  memory = s;
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* in-memory only */
  }
}

export function clearSession(): void {
  memory = null;
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

export function currentToken(): string | null {
  return memory?.token ?? loadSession()?.token ?? null;
}
