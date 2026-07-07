import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { loginApi, registerApi, logoutApi } from '../api/auth';
import { setAuthToken } from '../api/client';
import type { User } from '../types/index';

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

const ACCESS_TOKEN_KEY = 'access_token';

export function AuthProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [user, setUserState] = useState<User | null>(null);
  const [accessToken, setAccessTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const storedToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (storedToken) {
      setAccessTokenState(storedToken);
      setAuthToken(storedToken);
    }
    setIsLoading(false);
  }, []);

  const setAccessToken = useCallback((token: string | null) => {
    setAccessTokenState(token);
    if (token) {
      localStorage.setItem(ACCESS_TOKEN_KEY, token);
      setAuthToken(token);
    } else {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      setAuthToken(null);
    }
  }, []);

  const setUser = useCallback((newUser: User | null) => {
    setUserState(newUser);
  }, []);

  const login = useCallback(async (credentials: LoginCredentials): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await loginApi(credentials.email, credentials.password);
      const { access_token, user: loggedInUser } = response;
      setAccessToken(access_token);
      setUserState(loggedInUser ?? null);
    } finally {
      setIsLoading(false);
    }
  }, [setAccessToken]);

  const register = useCallback(async (credentials: RegisterCredentials): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await registerApi(credentials.email, credentials.password, credentials.full_name);
      const { access_token, user: registeredUser } = response;
      setAccessToken(access_token);
      setUserState(registeredUser ?? null);
    } finally {
      setIsLoading(false);
    }
  }, [setAccessToken]);

  const logout = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      await logoutApi();
    } catch {
      // Proceed with local logout even if server call fails
    } finally {
      setAccessToken(null);
      setUserState(null);
      setIsLoading(false);
    }
  }, [setAccessToken]);

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

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}