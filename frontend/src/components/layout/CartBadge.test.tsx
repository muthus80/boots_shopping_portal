/**
 * Cart badge integration tests for SiteHeader (T-023 / US-009)
 *
 * These tests verify that the cart icon in the SiteHeader shows the correct
 * item count badge when the cart contains items, and hides it when empty.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SiteHeader } from './SiteHeader';
import type { Cart, User } from '../../types/index';

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockGetCart = vi.fn();
const mockGetCategories = vi.fn();

vi.mock('../../api/cart', () => ({
  getCart: () => mockGetCart(),
}));

vi.mock('../../api/categories', () => ({
  getCategories: () => mockGetCategories(),
}));

const defaultUser: User = {
  id: 'u1',
  email: 'test@example.com',
  full_name: 'Test User',
  is_active: true,
  is_superuser: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

vi.mock('../../stores/authStore', () => ({
  useAuth: () => ({
    user: defaultUser,
    accessToken: 'token',
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    setUser: vi.fn(),
    setAccessToken: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const makeCart = (items: Array<{ id: string; quantity: number }>): Cart => ({
  id: 'cart-1',
  user_id: 'u1',
  session_id: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  items: items.map((item) => ({
    id: item.id,
    cart_id: 'cart-1',
    product_id: 'prod-1',
    variant_id: null,
    quantity: item.quantity,
    unit_price: 120,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  })),
});

const renderHeader = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <SiteHeader />
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('SiteHeader — cart badge (T-023)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCategories.mockResolvedValue([]);
  });

  it('does not show the badge when the cart is empty', async () => {
    mockGetCart.mockResolvedValue(makeCart([]));
    renderHeader();
    // Wait for queries to resolve, then confirm no badge
    await waitFor(() => {
      expect(screen.queryByTestId('cart-badge')).not.toBeInTheDocument();
    });
  });

  it('shows the badge with the correct count when cart has items', async () => {
    mockGetCart.mockResolvedValue(
      makeCart([
        { id: 'item-1', quantity: 2 },
        { id: 'item-2', quantity: 1 },
      ])
    );
    renderHeader();
    await waitFor(() => {
      const badge = screen.getByTestId('cart-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent('3');
    });
  });

  it('shows 1 on the badge for a single item with quantity 1', async () => {
    mockGetCart.mockResolvedValue(makeCart([{ id: 'item-1', quantity: 1 }]));
    renderHeader();
    await waitFor(() => {
      expect(screen.getByTestId('cart-badge')).toHaveTextContent('1');
    });
  });

  it('caps the badge at 99+ for very large counts', async () => {
    mockGetCart.mockResolvedValue(makeCart([{ id: 'item-1', quantity: 150 }]));
    renderHeader();
    await waitFor(() => {
      expect(screen.getByTestId('cart-badge')).toHaveTextContent('99+');
    });
  });

  it('cart link aria-label includes item count when cart is non-empty', async () => {
    mockGetCart.mockResolvedValue(makeCart([{ id: 'item-1', quantity: 2 }]));
    renderHeader();
    await waitFor(() => {
      const cartLink = screen.getByRole('link', { name: /shopping cart/i });
      expect(cartLink).toHaveAttribute('aria-label', 'Shopping cart, 2 items');
    });
  });

  it('cart link aria-label is "Shopping cart" when cart is empty', async () => {
    mockGetCart.mockResolvedValue(makeCart([]));
    renderHeader();
    await waitFor(() => {
      const cartLink = screen.getByRole('link', { name: /shopping cart/i });
      expect(cartLink).toHaveAttribute('aria-label', 'Shopping cart');
    });
  });

  it('cart link aria-label uses singular "item" for exactly 1 item', async () => {
    mockGetCart.mockResolvedValue(makeCart([{ id: 'item-1', quantity: 1 }]));
    renderHeader();
    await waitFor(() => {
      const cartLink = screen.getByRole('link', { name: /shopping cart/i });
      expect(cartLink).toHaveAttribute('aria-label', 'Shopping cart, 1 item');
    });
  });

  it('does not show the badge when the cart request fails', async () => {
    mockGetCart.mockRejectedValue(new Error('Network error'));
    renderHeader();
    await waitFor(() => {
      expect(screen.queryByTestId('cart-badge')).not.toBeInTheDocument();
    });
  });
});
