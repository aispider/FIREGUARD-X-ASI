import { ApiError } from '../api/client';

export interface FriendlyError {
  title: string;
  body: string;
  kind: 'network' | 'auth' | 'forbidden' | 'rate' | 'server' | 'other';
}

/** Plain-words explanation of an API failure, shown in the error banner. */
export function explainError(e: unknown): FriendlyError {
  if (e instanceof ApiError) {
    if (e.network) {
      return {
        kind: 'network',
        title: 'Cannot reach the FIREGUARD-X backend',
        body: 'The request did not get an answer. The API may be starting up, stopped, or your network is offline. Nothing on screen is being updated. Check that the backend is running, then retry.',
      };
    }
    if (e.status === 401) {
      return {
        kind: 'auth',
        title: 'Your session is not valid',
        body: 'The backend did not accept your sign-in token. It may have expired. Please sign in again.',
      };
    }
    if (e.status === 403) {
      return {
        kind: 'forbidden',
        title: 'Your role is not allowed to do that',
        body: `${e.detail} Ask a commander or administrator if you need this permission.`,
      };
    }
    if (e.status === 429) {
      const wait = e.retryAfter ? ` Try again in about ${e.retryAfter} seconds.` : ' Wait a moment and try again.';
      return {
        kind: 'rate',
        title: 'Too many requests',
        body: `The backend is rate limiting this session to protect itself.${wait}`,
      };
    }
    if (e.status >= 500) {
      return { kind: 'server', title: 'The backend reported a problem', body: `${e.detail} The values on screen may be out of date.` };
    }
    return { kind: 'other', title: 'The request was rejected', body: e.detail };
  }
  if (e instanceof Error) return { kind: 'other', title: 'Something went wrong', body: e.message };
  return { kind: 'other', title: 'Something went wrong', body: 'Unexpected error.' };
}
