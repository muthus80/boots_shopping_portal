import { apiClient, setAuthToken } from './client';
import { User } from '../types/index';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const loginApi = async (credentials: LoginRequest): Promise<AuthResponse> => {
  const formData = new URLSearchParams();
  formData.append('username', credentials.email);
  formData.append('password', credentials.password);

  const response = await apiClient.post<AuthResponse>('/api/v1/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  const { access_token } = response.data;
  setAuthToken(access_token);

  return response.data;
};

export const registerApi = async (data: RegisterRequest): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>('/api/v1/auth/register', data);

  const { access_token } = response.data;
  setAuthToken(access_token);

  return response.data;
};

export const logoutApi = async (): Promise<void> => {
  try {
    await apiClient.post('/api/v1/auth/logout');
  } finally {
    setAuthToken(null);
  }
};

export const refreshTokenApi = async (refreshToken: string): Promise<RefreshTokenResponse> => {
  const response = await apiClient.post<RefreshTokenResponse>('/api/v1/auth/refresh', {
    refresh_token: refreshToken,
  });

  const { access_token } = response.data;
  setAuthToken(access_token);

  return response.data;
};