import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useCartCount } from './useCartCount';
import type { Cart } from '../types/index';

// ── Mock ──────────────────────────────────────────────────────────────────────

const mockGetCart = vi.fn();

vi.mock('../api/cart', () => ({
  getCart: () => mockGetCart(),
}));

// useCartCount now reads isAuthenticated from useAuth.
// Default to authenticated=true so existing tests continue to exercise the
// cart-fetch path without needing to be rewritten.
vi.mock('../stores/authStore', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const makeCart = (items: Array<{ id: string; quantity: number }>): Cart => ({
  id: 'cart-1',
  user_id: 'user-1',
  session_id: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  items: items.map((item) => ({
    id: item.id,
    cart_id: 'cart-1',
    product_id: 'prod-1',
    variant_id: null,
    quantity: item.quantity,
    unit_price: 100,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  })),
});

// ── Helper ────────────────────────────────────────────────────────────────────

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('useCartCount', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 0 while the cart is loading', () => {
    mockGetCart.mockReturnValue(new Promise(() => {})); // never resolves
    const { result } = renderHook(() => useCartCount(), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBe(0);
  });

  it('returns 0 when the cart is empty', async () => {
    mockGetCart.mockResolvedValue(makeCart([]));
    const { result } = renderHook(() => useCartCount(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current).toBe(0));
  });

  it('returns the total quantity of a single item', async () => {
    mockGetCart.mockResolvedValue(makeCart([{ id: 'item-1', quantity: 3 }]));
    const { result } = renderHook(() => useCartCount(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current).toBe(3));
  });

  it('sums quantities across multiple items', async () => {
    mockGetCart.mockResolvedValue(
      makeCart([
        { id: 'item-1', quantity: 2 },
        { id: 'item-2', quantity: 5 },
        { id: 'item-3', quantity: 1 },
      ])
    );
    const { result } = renderHook(() => useCartCount(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current).toBe(8));
  });

  it('returns 0 when the cart request fails', async () => {
    mockGetCart.mockRejectedValue(new Error('Network error'));
    const { result } = renderHook(() => useCartCount(), {
      wrapper: createWrapper(),
    });
    // Error state — count stays 0
    await waitFor(() => expect(result.current).toBe(0));
  });
});
