/**
 * AuthProvider — session persistence and token refresh (T-007 / US-013)
 *
 * Strategy (per ADR-002):
 *   • Access token is kept ONLY in memory (the `authToken` variable inside
 *     api/client.ts). It is NEVER written to localStorage/sessionStorage.
 *   • Refresh token is persisted in localStorage so the session survives page
 *     refresh and new-tab navigation. (ADR-002 prefers httpOnly cookies set
 *     by the server; this localStorage fallback is used until the backend
 *     switches to Set-Cookie, and does NOT expose the short-lived access token.)
 *   • On mount the provider reads the stored refresh token, calls
 *     POST /api/v1/auth/refresh to obtain a new access token, and hydrates
 *     the in-memory auth state. If the refresh fails the stored token is
 *     cleared and the user is treated as unauthenticated.
 *   • The Axios interceptor (api/client.ts) silently repeats this flow on any
 *     401. When it cannot recover it calls the `authFailureHandler` registered
 *     here which clears React state and redirects to /login.
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from 'react';
import { loginApi, registerApi, logoutApi, refreshTokenApi } from '../api/auth';
import { setAuthToken, registerAuthFailureHandler, clearAuthFailureHandler } from '../api/client';
import type { User } from '../types/index';

// ── Storage key ────────────────────────────────────────────────────────────────

const REFRESH_TOKEN_KEY = 'refresh_token';

// ── Context types ──────────────────────────────────────────────────────────────

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterCredentials {
  email: string;
  password: string;
  full_name?: string;
}

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User | null) => void;
  setAccessToken: (token: string | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ── Helpers — persist / clear refresh token ────────────────────────────────────

const storeRefreshToken = (token: string): void => {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
};

const clearRefreshToken = (): void => {
  localStorage.removeItem(REFRESH_TOKEN_KEY);
};

const getStoredRefreshToken = (): string | null =>
  localStorage.getItem(REFRESH_TOKEN_KEY);

// ── AuthProvider ──────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [user, setUserState] = useState<User | null>(null);
  const [accessToken, setAccessTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // ── Session restoration on mount ────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;

    const restoreSession = async (): Promise<void> => {
      const storedRefreshToken = getStoredRefreshToken();

      if (!storedRefreshToken) {
        if (!cancelled) setIsLoading(false);
        return;
      }

      try {
        // Exchange the stored refresh token for a fresh access token.
        const data = await refreshTokenApi(storedRefreshToken);
        if (cancelled) return;

        // refreshTokenApi already calls setAuthToken internally. We also update
        // the React state and register the refresh token with the interceptor.
        setAccessTokenState(data.access_token);
        setAuthToken(data.access_token, storedRefreshToken);
      } catch {
        // Refresh token is invalid or expired — start as unauthenticated.
        if (!cancelled) {
          clearRefreshToken();
          setAuthToken(null, null);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  // ── Auth-failure handler (registered with the Axios interceptor) ─────────────
  //
  // When the interceptor cannot recover from a 401 (e.g. refresh token expired
  // or revoked), it calls this handler so React state is cleared and the user
  // is redirected to /login. Using window.location.replace is intentional here:
  // the interceptor fires outside React's update cycle and navigate() requires a
  // Router context which is not available at this scope level.

  useEffect(() => {
    const handleAuthFailure = (): void => {
      setAccessTokenState(null);
      setUserState(null);
      clearRefreshToken();
      setAuthToken(null, null);
      window.location.replace('/login');
    };

    registerAuthFailureHandler(handleAuthFailure);

    return () => {
      clearAuthFailureHandler();
    };
  }, []);

  // ── setAccessToken (used by consumers that obtain a token outside normal flow) ─

  const setAccessToken = useCallback((token: string | null) => {
    setAccessTokenState(token);
    if (token) {
      setAuthToken(token);
    } else {
      setAuthToken(null);
      clearRefreshToken();
    }
  }, []);

  const setUser = useCallback((newUser: User | null) => {
    setUserState(newUser);
  }, []);

  // ── login ─────────────────────────────────────────────────────────────────────

  const login = useCallback(async (credentials: LoginCredentials): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await loginApi(credentials.email, credentials.password);
      const { access_token, refresh_token, user: loggedInUser } = response;

      setAccessTokenState(access_token);
      setAuthToken(access_token, refresh_token ?? null);
      if (refresh_token) {
        storeRefreshToken(refresh_token);
      }
      setUserState(loggedInUser ?? null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── register ──────────────────────────────────────────────────────────────────

  const register = useCallback(async (credentials: RegisterCredentials): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await registerApi(
        credentials.email,
        credentials.password,
        credentials.full_name
      );
      const { access_token, refresh_token, user: registeredUser } = response;

      if (access_token) {
        setAccessTokenState(access_token);
        setAuthToken(access_token, refresh_token ?? null);
        if (refresh_token) {
          storeRefreshToken(refresh_token);
        }
      }
      setUserState(registeredUser ?? null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── logout ────────────────────────────────────────────────────────────────────

  const logout = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      await logoutApi();
    } catch {
      // Proceed with local logout even if the server call fails.
    } finally {
      setAccessTokenState(null);
      setUserState(null);
      clearRefreshToken();
      setAuthToken(null, null);
      setIsLoading(false);
    }
  }, []);

  // ── Context value ─────────────────────────────────────────────────────────────

  const value: AuthContextValue = {
    user,
    accessToken,
    isAuthenticated: !!accessToken,
    isLoading,
    login,
    register,
    logout,
    setUser,
    setAccessToken,
  };

  return React.createElement(AuthContext.Provider, { value }, children);
}

// ── useAuth ───────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
