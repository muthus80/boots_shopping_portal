/**
 * T-007 — Silent token refresh interceptor (US-013)
 *
 * Tests for the Axios response interceptor in api/client.ts:
 *   1. Passes through successful responses unchanged
 *   2. On 401 with no refresh token: fires authFailureHandler immediately
 *   3. On 401 with a refresh token: calls axios.post to /auth/refresh and retries
 *   4. On refresh failure: fires authFailureHandler and rejects
 *   5. On refresh success: Authorization header updated with new token
 *   6. setAuthToken correctly sets / clears the module-level token + header
 *   7. registerAuthFailureHandler / clearAuthFailureHandler wiring
 *   8. Non-401 errors pass through without refresh attempt
 */

import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ── Import the real client module ────────────────────────────────────────────
// We import once at the top level. Each test suite uses beforeEach to
// clear mock state; the module-level let vars (authToken, refreshTokenValue,
// isRefreshing, failedQueue) are reset indirectly by calling setAuthToken.

import {
  apiClient,
  setAuthToken,
  registerAuthFailureHandler,
  clearAuthFailureHandler,
} from './client';

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('api/client — setAuthToken (T-007)', () => {
  afterEach(() => {
    // Clean up headers after each test
    setAuthToken(null, null);
    clearAuthFailureHandler();
  });

  it('adds Bearer Authorization header when a token is provided', () => {
    setAuthToken('my-access-token');

    expect(apiClient.defaults.headers.common['Authorization']).toBe(
      'Bearer my-access-token'
    );
  });

  it('removes Authorization header when token is null', () => {
    setAuthToken('my-access-token');
    setAuthToken(null);

    expect(apiClient.defaults.headers.common['Authorization']).toBeUndefined();
  });

  it('stores the refresh token without throwing', () => {
    // The refresh token is module-private; we verify it's used in interceptor tests.
    expect(() => setAuthToken('at', 'rt')).not.toThrow();
  });
});

describe('api/client — authFailureHandler wiring (T-007)', () => {
  afterEach(() => {
    setAuthToken(null, null);
    clearAuthFailureHandler();
  });

  it('registerAuthFailureHandler stores the callback (no throw)', () => {
    const handler = vi.fn();
    expect(() => registerAuthFailureHandler(handler)).not.toThrow();
  });

  it('clearAuthFailureHandler removes the callback (no throw)', () => {
    const handler = vi.fn();
    registerAuthFailureHandler(handler);
    expect(() => clearAuthFailureHandler()).not.toThrow();
  });
});

describe('api/client — response interceptor passthrough (T-007)', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(apiClient);
    setAuthToken(null, null);
    clearAuthFailureHandler();
  });

  afterEach(() => {
    mock.restore();
    setAuthToken(null, null);
    clearAuthFailureHandler();
  });

  it('passes 200 responses through unchanged', async () => {
    mock.onGet('/api/v1/products').reply(200, { items: [] });

    const response = await apiClient.get('/api/v1/products');

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ items: [] });
  });

  it('does not attempt refresh for 500 errors', async () => {
    setAuthToken('at', 'rt');
    const axiosPostSpy = vi.spyOn(axios, 'post');
    mock.onGet('/api/v1/products').reply(500, { detail: 'Server error' });

    await expect(apiClient.get('/api/v1/products')).rejects.toThrow();

    // axios.post (the refresh call) should NOT have been triggered
    const refreshCalls = axiosPostSpy.mock.calls.filter(
      (c) => typeof c[0] === 'string' && (c[0] as string).includes('/auth/refresh')
    );
    expect(refreshCalls).toHaveLength(0);

    axiosPostSpy.mockRestore();
  });

  it('passes through network errors without a refresh attempt', async () => {
    setAuthToken('at', 'rt');
    const axiosPostSpy = vi.spyOn(axios, 'post');
    mock.onGet('/api/v1/products').networkError();

    await expect(apiClient.get('/api/v1/products')).rejects.toThrow();

    const refreshCalls = axiosPostSpy.mock.calls.filter(
      (c) => typeof c[0] === 'string' && (c[0] as string).includes('/auth/refresh')
    );
    expect(refreshCalls).toHaveLength(0);

    axiosPostSpy.mockRestore();
  });
});

describe('api/client — 401 with no refresh token (T-007)', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(apiClient);
    // Ensure no refresh token is stored
    setAuthToken(null, null);
  });

  afterEach(() => {
    mock.restore();
    setAuthToken(null, null);
    clearAuthFailureHandler();
  });

  it('fires authFailureHandler and rejects when no refresh token is present', async () => {
    const handler = vi.fn();
    registerAuthFailureHandler(handler);

    mock.onGet('/api/v1/protected').reply(401, { detail: 'Unauthorized' });

    await expect(apiClient.get('/api/v1/protected')).rejects.toThrow();

    expect(handler).toHaveBeenCalledOnce();
  });

  it('clears the auth token when 401 fires with no refresh token', async () => {
    // Set an access token but no refresh token
    setAuthToken('stale-at');
    registerAuthFailureHandler(vi.fn());

    mock.onGet('/api/v1/protected').reply(401);

    await expect(apiClient.get('/api/v1/protected')).rejects.toThrow();

    expect(apiClient.defaults.headers.common['Authorization']).toBeUndefined();
  });
});

describe('api/client — 401 with refresh token (T-007)', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(apiClient);
    clearAuthFailureHandler();
  });

  afterEach(() => {
    mock.restore();
    setAuthToken(null, null);
    clearAuthFailureHandler();
  });

  it('calls axios.post /auth/refresh and retries the original request', async () => {
    setAuthToken('old-at', 'valid-rt');

    let callCount = 0;
    mock.onGet('/api/v1/protected').reply(() => {
      callCount += 1;
      return callCount === 1 ? [401, { detail: 'Unauthorized' }] : [200, { data: 'ok' }];
    });

    // Spy on axios.post (the underlying refresh call uses base axios, not apiClient)
    const axiosPostSpy = vi.spyOn(axios, 'post').mockResolvedValueOnce({
      data: { access_token: 'new-at', token_type: 'bearer', expires_in: 1800 },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    });

    const response = await apiClient.get('/api/v1/protected');

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ data: 'ok' });
    expect(callCount).toBe(2);

    // The refresh endpoint was called
    expect(axiosPostSpy).toHaveBeenCalledOnce();
    const [url, body] = axiosPostSpy.mock.calls[0];
    expect(url).toContain('/api/v1/auth/refresh');
    expect(body).toEqual({ refresh_token: 'valid-rt' });

    axiosPostSpy.mockRestore();
  });

  it('updates the Authorization header on the default client after refresh', async () => {
    setAuthToken('old-at', 'valid-rt');

    let callCount = 0;
    mock.onGet('/api/v1/protected').reply(() => {
      callCount += 1;
      return callCount === 1 ? [401] : [200, {}];
    });

    vi.spyOn(axios, 'post').mockResolvedValueOnce({
      data: { access_token: 'new-at', token_type: 'bearer' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    });

    await apiClient.get('/api/v1/protected');

    expect(apiClient.defaults.headers.common['Authorization']).toBe('Bearer new-at');

    vi.restoreAllMocks();
  });

  it('fires authFailureHandler and rejects when the refresh call fails', async () => {
    setAuthToken('old-at', 'expired-rt');

    mock.onGet('/api/v1/protected').reply(401, { detail: 'Unauthorized' });

    // Simulate the refresh endpoint returning 401
    vi.spyOn(axios, 'post').mockRejectedValueOnce(
      Object.assign(new Error('Refresh failed'), { response: { status: 401 } })
    );

    const handler = vi.fn();
    registerAuthFailureHandler(handler);

    await expect(apiClient.get('/api/v1/protected')).rejects.toThrow();

    expect(handler).toHaveBeenCalledOnce();

    vi.restoreAllMocks();
  });

  it('clears the auth token when the refresh call fails', async () => {
    setAuthToken('old-at', 'expired-rt');

    mock.onGet('/api/v1/protected').reply(401);

    vi.spyOn(axios, 'post').mockRejectedValueOnce(
      Object.assign(new Error('Refresh failed'), { response: { status: 401 } })
    );

    registerAuthFailureHandler(vi.fn());

    await expect(apiClient.get('/api/v1/protected')).rejects.toThrow();

    expect(apiClient.defaults.headers.common['Authorization']).toBeUndefined();

    vi.restoreAllMocks();
  });
});
