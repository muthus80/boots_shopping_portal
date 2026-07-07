import { apiClient, setAuthToken } from './client';
import type { User } from '../types/index';

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
  user?: User;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

/**
 * POST /api/v1/auth/login
 * Returns JWT tokens.
 */
export const loginApi = async (email: string, password: string): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>('/api/v1/auth/login', {
    email,
    password,
  });

  const { access_token } = response.data;
  setAuthToken(access_token);

  return response.data;
};

/**
 * POST /api/v1/auth/register
 * Creates a new user account. The server may return an access_token for
 * automatic login after registration; if not, the caller should redirect
 * to /login.
 */
export const registerApi = async (
  email: string,
  password: string,
  full_name?: string
): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>('/api/v1/auth/register', {
    email,
    password,
    ...(full_name ? { full_name } : {}),
  });

  if (response.data.access_token) {
    setAuthToken(response.data.access_token);
  }

  return response.data;
};

/**
 * POST /api/v1/auth/logout
 * Revokes the refresh token server-side and clears local auth state.
 */
export const logoutApi = async (): Promise<void> => {
  try {
    await apiClient.post('/api/v1/auth/logout');
  } finally {
    setAuthToken(null);
  }
};

/**
 * POST /api/v1/auth/refresh
 * Issues a new access token from a valid refresh token.
 */
export const refreshTokenApi = async (refreshToken: string): Promise<RefreshTokenResponse> => {
  const response = await apiClient.post<RefreshTokenResponse>('/api/v1/auth/refresh', {
    refresh_token: refreshToken,
  });

  const { access_token } = response.data;
  setAuthToken(access_token);

  return response.data;
};
