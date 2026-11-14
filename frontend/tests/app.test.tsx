import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';
import { AuthProvider } from '../src/state/auth';

describe('App', () => {
  it('shows the login screen when signed out and states it is a prototype', () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('offline'))));
    render(<AuthProvider><App /></AuthProvider>);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeTruthy();
    expect(screen.getByText(/not a nasa product/i)).toBeTruthy();
  });
});
