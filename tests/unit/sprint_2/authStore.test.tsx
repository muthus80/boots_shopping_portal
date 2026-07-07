/**
 * T-007: Session persistence and token refresh logic (US-013)
 *
 * Covers:
 *  - Session is restored on page load when a valid refresh token is stored
 *  - Stale/invalid refresh token is cleared and user stays unauthenticated
 *  - No stored token → provider mounts as unauthenticated without API calls
 *  - login() stores the refresh token and sets the access token in memory
 *  - logout() clears stored tokens and resets auth state
 *  - register() stores the refresh token when the server returns one
 *  - Auth failure handler clears state and redirects to /login
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './authStore';
import * as clientModule from '../api/client';
import * as authApiModule from '../api/auth';

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('../api/auth', () => ({
  loginApi: vi.fn(),
  registerApi: vi.fn(),
  logoutApi: vi.fn(),
  refreshTokenApi: vi.fn(),
}));

vi.mock('../api/client', () => ({
  setAuthToken: vi.fn(),
  registerAuthFailureHandler: vi.fn(),
  clearAuthFailureHandler: vi.fn(),
  apiClient: { post: vi.fn(), get: vi.fn(), defaults: { headers: { common: {} } } },
}));

const mockRefreshTokenApi = vi.mocked(authApiModule.refreshTokenApi);
const mockLoginApi = vi.mocked(authApiModule.loginApi);
const mockLogoutApi = vi.mocked(authApiModule.logoutApi);
const mockRegisterApi = vi.mocked(authApiModule.registerApi);
const mockSetAuthToken = vi.mocked(clientModule.setAuthToken);
const mockRegisterAuthFailureHandler = vi.mocked(clientModule.registerAuthFailureHandler);
const mockClearAuthFailureHandler = vi.mocked(clientModule.clearAuthFailureHandler);

// ── localStorage stub ─────────────────────────────────────────────────────────

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get store() {
      return store;
    },
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// ── window.location.replace stub ──────────────────────────────────────────────

const mockLocationReplace = vi.fn();
Object.defineProperty(window, 'location', {
  value: { ...window.location, replace: mockLocationReplace },
  writable: true,
});

// ── Test consumer component ───────────────────────────────────────────────────

const TestConsumer: React.FC = () => {
  const { user, accessToken, isAuthenticated, isLoading } = useAuth();
  return (
    <div>
      <span data-testid="loading">{isLoading ? 'loading' : 'ready'}</span>
      <span data-testid="authenticated">{isAuthenticated ? 'yes' : 'no'}</span>
      <span data-testid="token">{accessToken ?? 'none'}</span>
      <span data-testid="user">{user ? user.email : 'none'}</span>
    </div>
  );
};

const renderWithProvider = () =>
  render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  );

// ── Helpers ───────────────────────────────────────────────────────────────────

const MOCK_USER = {
  id: 'u1',
  email: 'jane@example.com',
  full_name: 'Jane Doe',
  is_active: true,
  is_superuser: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// ── Setup / Teardown ──────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  localStorageMock.clear();
});

afterEach(() => {
  vi.resetAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AuthProvider — session restoration on mount', () => {
  it('shows loading while restoring session, then ready', async () => {
    // No stored token → resolves immediately as unauthenticated
    renderWithProvider();

    // Initially loading or immediately ready (depends on microtask timing)
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('ready');
    });
  });

  it('stays unauthenticated when no refresh token is stored', async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('ready');
    });

    expect(screen.getByTestId('authenticated').textContent).toBe('no');
    expect(mockRefreshTokenApi).not.toHaveBeenCalled();
  });

  it('restores session when a valid refresh token is stored', async () => {
    localStorageMock.setItem('refresh_token', 'stored-rt');

    mockRefreshTokenApi.mockResolvedValueOnce({
      access_token: 'new-at',
      token_type: 'bearer',
      expires_in: 1800,
    });

    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('ready');
    });

    expect(mockRefreshTokenApi).toHaveBeenCalledWith('stored-rt');
    expect(screen.getByTestId('authenticated').textContent).toBe('yes');
    expect(screen.getByTestId('token').textContent).toBe('new-at');
  });

  it('clears stored token and stays unauthenticated when refresh fails', async () => {
    localStorageMock.setItem('refresh_token', 'expired-rt');

    mockRefreshTokenApi.mockRejectedValueOnce(new Error('Token expired'));

    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('ready');
    });

    expect(screen.getByTestId('authenticated').textContent).toBe('no');
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    expect(mockSetAuthToken).toHaveBeenCalledWith(null, null);
  });

  it('registers an auth failure handler on mount', () => {
    renderWithProvider();
    expect(mockRegisterAuthFailureHandler).toHaveBeenCalledOnce();
    expect(typeof mockRegisterAuthFailureHandler.mock.calls[0][0]).toBe('function');
  });

  it('clears the auth failure handler on unmount', () => {
    const { unmount } = renderWithProvider();
    unmount();
    expect(mockClearAuthFailureHandler).toHaveBeenCalled();
  });
});

describe('AuthProvider — auth failure handler', () => {
  it('clears state and redirects to /login when handler is invoked', async () => {
    // Set up a stored refresh token and restored session.
    localStorageMock.setItem('refresh_token', 'stored-rt');
    mockRefreshTokenApi.mockResolvedValueOnce({
      access_token: 'new-at',
      token_type: 'bearer',
      expires_in: 1800,
    });

    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId('authenticated').textContent).toBe('yes');
    });

    // Retrieve the handler registered with the interceptor and invoke it.
    const handler = mockRegisterAuthFailureHandler.mock.calls[0][0];
    act(() => {
      handler();
    });

    await waitFor(() => {
      expect(screen.getByTestId('authenticated').textContent).toBe('no');
    });

    expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    expect(mockSetAuthToken).toHaveBeenCalledWith(null, null);
    expect(mockLocationReplace).toHaveBeenCalledWith('/login');
  });
});

describe('AuthProvider — login', () => {
  it('stores refresh token in localStorage on successful login', async () => {
    mockLoginApi.mockResolvedValueOnce({
      access_token: 'at-login',
      refresh_token: 'rt-login',
      token_type: 'bearer',
    });

    // Mount with no stored token
    const LoginTrigger: React.FC = () => {
      const { login, isAuthenticated } = useAuth();
      return (
        <div>
          <span data-testid="authenticated">{isAuthenticated ? 'yes' : 'no'}</span>
          <button
            onClick={() => login({ email: 'jane@example.com', password: 'Password1' })}
          >
            Login
          </button>
        </div>
      );
    };

    const { getByRole, getByTestId } = render(
      <AuthProvider>
        <LoginTrigger />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(getByTestId('authenticated').textContent).toBe('no');
    });

    await act(async () => {
      getByRole('button', { name: 'Login' }).click();
    });

    await waitFor(() => {
      expect(getByTestId('authenticated').textContent).toBe('yes');
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'rt-login');
    expect(mockSetAuthToken).toHaveBeenCalledWith('at-login', 'rt-login');
  });
});

describe('AuthProvider — logout', () => {
  it('clears tokens and resets auth state on logout', async () => {
    localStorageMock.setItem('refresh_token', 'stored-rt');
    mockRefreshTokenApi.mockResolvedValueOnce({
      access_token: 'new-at',
      token_type: 'bearer',
      expires_in: 1800,
    });
    mockLogoutApi.mockResolvedValueOnce(undefined);

    const LogoutTrigger: React.FC = () => {
      const { logout, isAuthenticated } = useAuth();
      return (
        <div>
          <span data-testid="authenticated">{isAuthenticated ? 'yes' : 'no'}</span>
          <button onClick={() => logout()}>Logout</button>
        </div>
      );
    };

    const { getByRole, getByTestId } = render(
      <AuthProvider>
        <LogoutTrigger />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(getByTestId('authenticated').textContent).toBe('yes');
    });

    await act(async () => {
      getByRole('button', { name: 'Logout' }).click();
    });

    await waitFor(() => {
      expect(getByTestId('authenticated').textContent).toBe('no');
    });

    expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    expect(mockSetAuthToken).toHaveBeenLastCalledWith(null, null);
  });

  it('still clears local state when logout API call fails', async () => {
    localStorageMock.setItem('refresh_token', 'stored-rt');
    mockRefreshTokenApi.mockResolvedValueOnce({
      access_token: 'new-at',
      token_type: 'bearer',
      expires_in: 1800,
    });
    mockLogoutApi.mockRejectedValueOnce(new Error('Network error'));

    const LogoutTrigger: React.FC = () => {
      const { logout, isAuthenticated } = useAuth();
      return (
        <div>
          <span data-testid="authenticated">{isAuthenticated ? 'yes' : 'no'}</span>
          <button onClick={() => logout()}>Logout</button>
        </div>
      );
    };

    const { getByRole, getByTestId } = render(
      <AuthProvider>
        <LogoutTrigger />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(getByTestId('authenticated').textContent).toBe('yes');
    });

    await act(async () => {
      getByRole('button', { name: 'Logout' }).click();
    });

    await waitFor(() => {
      expect(getByTestId('authenticated').textContent).toBe('no');
    });

    expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
  });
});

describe('AuthProvider — register', () => {
  it('stores refresh token in localStorage when register returns one', async () => {
    mockRegisterApi.mockResolvedValueOnce({
      access_token: 'at-reg',
      refresh_token: 'rt-reg',
      token_type: 'bearer',
      user: MOCK_USER,
    });

    const RegisterTrigger: React.FC = () => {
      const { register, isAuthenticated } = useAuth();
      return (
        <div>
          <span data-testid="authenticated">{isAuthenticated ? 'yes' : 'no'}</span>
          <button
            onClick={() =>
              register({ email: 'jane@example.com', password: 'Password1', full_name: 'Jane Doe' })
            }
          >
            Register
          </button>
        </div>
      );
    };

    const { getByRole, getByTestId } = render(
      <AuthProvider>
        <RegisterTrigger />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(getByTestId('authenticated').textContent).toBe('no');
    });

    await act(async () => {
      getByRole('button', { name: 'Register' }).click();
    });

    await waitFor(() => {
      expect(getByTestId('authenticated').textContent).toBe('yes');
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'rt-reg');
  });
});
