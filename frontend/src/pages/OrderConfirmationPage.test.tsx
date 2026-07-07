/**
 * OrderConfirmationPage tests — T-032 / US-011
 *
 * Coverage:
 *  - Renders "Order Confirmed!" heading when valid order state is passed
 *  - Renders the order number prominently
 *  - Renders each line item with name, size, color, quantity, and price
 *  - Renders the order total
 *  - Renders the shipping address
 *  - Renders "Continue Shopping" link pointing to /products
 *  - Renders "View Order History" link for authenticated users
 *  - Does NOT render "View Order History" for guest users
 *  - Redirects to / when no order state is present (direct URL access)
 *  - Accessibility: h1 heading, section landmarks with headings, address element
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockUseAuth = vi.fn();

vi.mock('../stores/authStore', () => ({
  useAuth: () => mockUseAuth(),
}));

import { OrderConfirmationPage } from './OrderConfirmationPage';
import type { ConfirmOrderResponse } from '../api/checkout';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_ORDER: ConfirmOrderResponse = {
  order_id: 'order-uuid-abc',
  order_number: 'ORD-2024-999',
  total_amount: 179.98,
  shipping_address: {
    line1: '42 Boot Lane',
    city: 'Manchester',
    state: 'Greater Manchester',
    postal_code: 'M1 2AB',
  },
  items: [
    {
      product_name: 'Chelsea Boot',
      color: 'tan',
      size: '9',
      quantity: 1,
      unit_price: 129.99,
    },
    {
      product_name: 'Ankle Boot',
      color: 'black',
      size: '8',
      quantity: 1,
      unit_price: 49.99,
    },
  ],
};

const GUEST_AUTH = { user: null, isAuthenticated: false, isLoading: false };
const AUTH_USER = {
  user: {
    id: 'u-1',
    email: 'jane@example.com',
    full_name: 'Jane',
    is_active: true,
    is_superuser: false,
    created_at: '',
    updated_at: '',
  },
  isAuthenticated: true,
  isLoading: false,
};

// ── Render helpers ────────────────────────────────────────────────────────────

/** Render page at /order-confirmation WITH order state */
const renderWithOrder = (order: ConfirmOrderResponse = MOCK_ORDER) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter
        initialEntries={[{ pathname: '/order-confirmation', state: { order } }]}
      >
        <Routes>
          <Route path="/order-confirmation" element={<OrderConfirmationPage />} />
          <Route path="/" element={<div>Home Page</div>} />
          <Route path="/products" element={<div>Products Page</div>} />
          <Route path="/orders" element={<div>Orders Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

/** Render page at /order-confirmation WITHOUT any state (direct URL access) */
const renderWithoutState = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/order-confirmation']}>
        <Routes>
          <Route path="/order-confirmation" element={<OrderConfirmationPage />} />
          <Route path="/" element={<div>Home Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('OrderConfirmationPage (T-032 / US-011)', () => {
  // ── Success heading ─────────────────────────────────────────────────────

  it('renders "Order Confirmed!" h1 heading when order state is present', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(
      screen.getByRole('heading', { level: 1, name: /order confirmed/i })
    ).toBeInTheDocument();
  });

  // ── Order number ────────────────────────────────────────────────────────

  it('renders the order number', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(screen.getByTestId('order-number')).toHaveTextContent('ORD-2024-999');
  });

  // ── Line items ──────────────────────────────────────────────────────────

  it('renders each product name in the items list', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(screen.getByText('Chelsea Boot')).toBeInTheDocument();
    expect(screen.getByText('Ankle Boot')).toBeInTheDocument();
  });

  it('renders item size and color for each line item', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    // size "9" and color "tan" for Chelsea Boot
    expect(screen.getByText(/\/ 9/)).toBeInTheDocument();
    expect(screen.getByText(/\/ tan/)).toBeInTheDocument();
  });

  it('renders item quantity for each line item', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    // Both items have quantity 1 — check ×1 appears twice
    const qty = screen.getAllByText(/×1/);
    expect(qty.length).toBeGreaterThanOrEqual(2);
  });

  it('renders the per-line-item subtotal', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    // Chelsea Boot: 1 × £129.99 → £129.99 (en-GB format)
    expect(screen.getByText('£129.99')).toBeInTheDocument();
    // Ankle Boot: 1 × £49.99 → £49.99
    expect(screen.getByText('£49.99')).toBeInTheDocument();
  });

  // ── Order total ─────────────────────────────────────────────────────────

  it('renders the order total', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(screen.getByTestId('order-total')).toHaveTextContent('£179.98');
  });

  // ── Shipping address ────────────────────────────────────────────────────

  it('renders the shipping address line1', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(screen.getByText('42 Boot Lane')).toBeInTheDocument();
  });

  it('renders city, state and postal code in the shipping address', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(screen.getByText(/Manchester.*Greater Manchester.*M1 2AB/i)).toBeInTheDocument();
  });

  // ── CTA: Continue Shopping ──────────────────────────────────────────────

  it('renders "Continue Shopping" link pointing to /products', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    const link = screen.getByRole('link', { name: /continue shopping/i });
    expect(link).toHaveAttribute('href', '/products');
  });

  // ── CTA: View Order History (authenticated only) ────────────────────────

  it('renders "View Order History" link for authenticated users', () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    renderWithOrder();
    const link = screen.getByRole('link', { name: /view order history/i });
    expect(link).toHaveAttribute('href', '/orders');
  });

  it('does NOT render "View Order History" link for guest users', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(screen.queryByRole('link', { name: /view order history/i })).not.toBeInTheDocument();
  });

  // ── Redirect on missing state ───────────────────────────────────────────

  it('redirects to / when accessed without order state', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithoutState();
    expect(screen.getByText('Home Page')).toBeInTheDocument();
  });

  // ── Items section heading ───────────────────────────────────────────────

  it('renders "Items ordered" section heading', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(
      screen.getByRole('heading', { name: /items ordered/i })
    ).toBeInTheDocument();
  });

  // ── Shipping section heading ─────────────────────────────────────────────

  it('renders "Shipping to" section heading', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    renderWithOrder();
    expect(
      screen.getByRole('heading', { name: /shipping to/i })
    ).toBeInTheDocument();
  });

  // ── Empty items array (edge case) ────────────────────────────────────────

  it('renders correctly when items array is empty (no items section shown)', () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    const emptyItemsOrder: ConfirmOrderResponse = {
      ...MOCK_ORDER,
      items: [],
    };
    renderWithOrder(emptyItemsOrder);
    // heading still present
    expect(
      screen.getByRole('heading', { level: 1, name: /order confirmed/i })
    ).toBeInTheDocument();
    // items heading not shown since items.length === 0
    expect(
      screen.queryByRole('heading', { name: /items ordered/i })
    ).not.toBeInTheDocument();
  });
});
