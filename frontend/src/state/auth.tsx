import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { HttpClient, isAbortError } from '../api/client';
import { makeApi, type Api } from '../api/endpoints';
import type { AuthConfigOut } from '../api/types';
import { can, type Permission } from '../lib/permissions';
import { clearSession, currentToken, loadSession, saveSession, type SessionUser } from '../lib/session';

interface AuthCtx {
  api: Api;
  user: SessionUser | null;
  can: (p: Permission) => boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  /** Set when a 401 sent the person back to the login screen. */
  sessionNotice: string | null;
  /** Public backend configuration (demo users, evidence mode). Null until loaded or if unreachable. */
  config: AuthConfigOut | null;
  configError: unknown;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children, client }: { children: ReactNode; client?: HttpClient }) {
  const [user, setUser] = useState<SessionUser | null>(() => loadSession()?.user ?? null);
  const [notice, setNotice] = useState<string | null>(null);
  const [config, setConfig] = useState<AuthConfigOut | null>(null);
  const [configError, setConfigError] = useState<unknown>(null);
  const logoutRef = useRef<(msg?: string) => void>(() => undefined);

  const http = useMemo(
    () =>
      client ??
      new HttpClient({
        getToken: currentToken,
        onUnauthorized: () => logoutRef.current('Your session expired. Please sign in again.'),
      }),
    [client],
  );
  const api = useMemo(() => makeApi(http), [http]);

  const logout = useCallback((msg?: string) => {
    clearSession();
    setUser(null);
    setNotice(msg ?? null);
  }, []);
  logoutRef.current = logout;

  const login = useCallback(
    async (username: string, password: string) => {
      const t = await api.login(username, password);
      const u: SessionUser = { username: t.username, role: t.role, permissions: t.permissions };
      saveSession({ token: t.access_token, user: u });
      setNotice(null);
      setUser(u);
    },
    [api],
  );

  // Re-validate a stored session on load (permissions may have changed, token may have expired).
  useEffect(() => {
    const s = loadSession();
    if (!s) return;
    const ctl = new AbortController();
    api
      .me({ signal: ctl.signal })
      .then((m) => {
        const u: SessionUser = { username: m.username, role: m.role, permissions: m.permissions };
        saveSession({ token: s.token, user: u });
        setUser(u);
      })
      .catch((e: unknown) => {
        if (!isAbortError(e)) {
          /* 401 already handled by the client; other failures keep the stored session */
        }
      });
    return () => ctl.abort();
  }, [api]);

  useEffect(() => {
    const ctl = new AbortController();
    api
      .authConfig({ signal: ctl.signal })
      .then((c) => {
        setConfig(c);
        setConfigError(null);
      })
      .catch((e: unknown) => {
        if (!isAbortError(e)) setConfigError(e);
      });
    return () => ctl.abort();
  }, [api]);

  const value = useMemo<AuthCtx>(
    () => ({
      api,
      user,
      can: (p) => can(user?.permissions, p),
      login,
      logout: () => logout(),
      sessionNotice: notice,
      config,
      configError,
    }),
    [api, user, login, logout, notice, config, configError],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAuth outside AuthProvider');
  return c;
}

export type { AuthConfigOut };
