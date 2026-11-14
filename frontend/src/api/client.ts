import type { ApiErrorBody } from './types';

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  /** Seconds, from a Retry-After header (429). */
  readonly retryAfter: number | null;
  /** True when no HTTP response was received (backend down, offline, blocked). */
  readonly network: boolean;

  constructor(status: number, detail: string, opts: { retryAfter?: number | null; network?: boolean } = {}) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.retryAfter = opts.retryAfter ?? null;
    this.network = opts.network ?? false;
  }
}

export function isAbortError(e: unknown): boolean {
  return (
    (e instanceof DOMException && e.name === 'AbortError') ||
    (typeof e === 'object' && e !== null && (e as { name?: string }).name === 'AbortError')
  );
}

export function describeError(e: unknown): string {
  if (e instanceof ApiError) return e.network ? `Backend unreachable. ${e.detail}` : e.detail;
  if (e instanceof Error) return e.message;
  return 'Unexpected error';
}

function detailFrom(body: unknown, fallback: string): string {
  if (typeof body === 'object' && body !== null) {
    const d = (body as ApiErrorBody).detail;
    if (typeof d === 'string' && d) return d;
    if (Array.isArray(d) && d.length) {
      return d
        .map((x) => {
          const where = Array.isArray(x.loc) ? x.loc.filter((p) => p !== 'body').join('.') : '';
          return where ? `${where}: ${x.msg ?? 'invalid'}` : (x.msg ?? 'invalid');
        })
        .join('; ');
    }
  }
  return fallback;
}

export interface ClientDeps {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  getToken: () => string | null;
  /** Called once per 401 on an authenticated request, so the app can return to the login screen. */
  onUnauthorized: () => void;
}

export interface RequestOptions {
  signal?: AbortSignal;
  /** Skip the 401 -> logout handler (used by the login call itself). */
  noAuthRedirect?: boolean;
}

export class HttpClient {
  private readonly base: string;
  private readonly fetchImpl: typeof fetch;
  private readonly deps: ClientDeps;

  constructor(deps: ClientDeps) {
    this.deps = deps;
    this.base = deps.baseUrl ?? '/api';
    this.fetchImpl = deps.fetchImpl ?? ((...a) => fetch(...a));
  }

  async request<T>(method: 'GET' | 'POST', path: string, body?: unknown, opts: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    const token = this.deps.getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const init: RequestInit = { method, headers, signal: opts.signal, cache: 'no-store' };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(body);
    }
    let res: Response;
    try {
      res = await this.fetchImpl(`${this.base}${path}`, init);
    } catch (e) {
      if (isAbortError(e)) throw e;
      throw new ApiError(0, 'The request did not reach the FIREGUARD-X backend.', { network: true });
    }
    let parsed: unknown = null;
    const text = await res.text().catch(() => '');
    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = null;
      }
    }
    if (!res.ok) {
      if (res.status === 401 && !opts.noAuthRedirect) this.deps.onUnauthorized();
      const ra = Number(res.headers.get('Retry-After'));
      const fallback =
        res.status === 502 || res.status === 503 || res.status === 504
          ? `Backend unavailable (HTTP ${res.status}).`
          : `Request failed (HTTP ${res.status}).`;
      throw new ApiError(res.status, detailFrom(parsed, fallback), {
        retryAfter: Number.isFinite(ra) && ra > 0 ? ra : null,
        network: res.status === 502 || res.status === 503 || res.status === 504,
      });
    }
    if (parsed === null) throw new ApiError(res.status, 'The backend returned an empty or invalid response.');
    return parsed as T;
  }

  get<T>(path: string, opts?: RequestOptions): Promise<T> {
    return this.request<T>('GET', path, undefined, opts);
  }

  post<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
    return this.request<T>('POST', path, body ?? {}, opts);
  }
}
