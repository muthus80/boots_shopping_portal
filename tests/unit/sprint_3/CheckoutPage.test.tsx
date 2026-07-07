/**
 * CheckoutPage tests — T-030 / US-011
 *
 * Coverage:
 *  - Loading state shows spinner while cart is fetching
 *  - Error state shows ErrorMessage with retry button
 *  - Empty cart shows empty-state UI with Browse Boots link
 *  - Guest path: identity step is shown first
 *  - Guest path: validates email before advancing
 *  - Guest path: advances to shipping after valid email
 *  - Authenticated path: skips identity step, shows shipping directly
 *  - Authenticated path: shows "signed in as" banner
 *  - Shipping step: validates required fields
 *  - Shipping step: advances to payment after valid submission
 *  - Shipping step: back navigation works
 *  - Confirmation step: renders order details
 *  - Accessibility: step indicator landmark, form labels, aria-required
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ── Mocks (set up BEFORE importing the component) ─────────────────────────────

const mockGetCart = vi.fn();
const mockCreatePaymentIntent = vi.fn();
const mockConfirmOrder = vi.fn();
const mockUseAuth = vi.fn();

// Mock Stripe so tests never hit a real Stripe instance
vi.mock('@stripe/stripe-js', () => ({
  loadStripe: vi.fn().mockResolvedValue({
    confirmCardPayment: vi.fn(),
  }),
}));

vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  CardElement: () => <div data-testid="card-element">Card Element</div>,
  useStripe: vi.fn().mockReturnValue({
    confirmCardPayment: vi.fn().mockResolvedValue({
      paymentIntent: { status: 'succeeded' },
      error: null,
    }),
  }),
  useElements: vi.fn().mockReturnValue({
    getElement: vi.fn().mockReturnValue({}),
  }),
}));

vi.mock('../api/cart', () => ({
  getCart: () => mockGetCart(),
}));

vi.mock('../api/checkout', () => ({
  createPaymentIntent: (...args: unknown[]) => mockCreatePaymentIntent(...args),
  confirmOrder: (...args: unknown[]) => mockConfirmOrder(...args),
}));

vi.mock('../stores/authStore', () => ({
  useAuth: () => mockUseAuth(),
}));

import React from 'react';
import { CheckoutPage } from './CheckoutPage';
import type { Cart, CartItem, Product } from '../types/index';
import type { ConfirmOrderResponse } from '../api/checkout';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_PRODUCT: Product = {
  id: 'prod-1',
  name: 'Trail Boot',
  slug: 'trail-boot',
  description: 'A trail boot.',
  category_id: 'cat-1',
  brand: 'TestBrand',
  base_price: 89.99,
  sale_price: null,
  image_url: null,
  images: [],
  is_active: true,
  is_featured: false,
  average_rating: null,
  review_count: 0,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const MOCK_CART_ITEM: CartItem = {
  id: 'item-1',
  cart_id: 'cart-1',
  product_id: 'prod-1',
  variant_id: null,
  quantity: 1,
  unit_price: 89.99,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  product: MOCK_PRODUCT,
};

const MOCK_CART: Cart = {
  id: 'cart-1',
  user_id: null,
  session_id: 'session-abc',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  items: [MOCK_CART_ITEM],
};

const MOCK_ORDER: ConfirmOrderResponse = {
  order_id: 'order-uuid-1',
  order_number: 'ORD-2024-001',
  total_amount: 89.99,
  shipping_address: {
    line1: '123 Main St',
    city: 'New York',
    state: 'NY',
    postal_code: '10001',
  },
  items: [
    {
      product_name: 'Trail Boot',
      color: 'black',
      size: '10',
      quantity: 1,
      unit_price: 89.99,
    },
  ],
};

const GUEST_AUTH = { user: null, isAuthenticated: false, isLoading: false };
const AUTH_USER = {
  user: { id: 'u-1', email: 'jane@example.com', full_name: 'Jane', is_active: true, is_superuser: false, created_at: '', updated_at: '' },
  isAuthenticated: true,
  isLoading: false,
};

// ── Render helper ─────────────────────────────────────────────────────────────

const renderPage = () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/checkout']}>
        <Routes>
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order-confirmation" element={<div data-testid="order-confirmation-page">Order Confirmation Page</div>} />
          <Route path="/products" element={<div>Products Page</div>} />
          <Route path="/cart" element={<div>Cart Page</div>} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('CheckoutPage (T-030 / US-011)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: guest user with items in cart
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    mockGetCart.mockResolvedValue(MOCK_CART);
  });

  // ── Loading ─────────────────────────────────────────────────────────────

  it('renders a loading spinner while the cart is fetching', () => {
    mockGetCart.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });

  // ── Error ───────────────────────────────────────────────────────────────

  it('renders an error message when the cart request fails', async () => {
    mockGetCart.mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('renders a retry button on cart error', async () => {
    mockGetCart.mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry loading/i })).toBeInTheDocument();
    });
  });

  // ── Empty cart ──────────────────────────────────────────────────────────

  it('renders empty-cart state when the cart has no items', async () => {
    mockGetCart.mockResolvedValue({ ...MOCK_CART, items: [] });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/your cart is empty/i)).toBeInTheDocument();
    });
  });

  it('renders a Browse Boots link when cart is empty', async () => {
    mockGetCart.mockResolvedValue({ ...MOCK_CART, items: [] });
    renderPage();
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /browse boots/i });
      expect(link).toHaveAttribute('href', '/products');
    });
  });

  // ── Guest path — identity step ──────────────────────────────────────────

  it('shows the identity step first for guest users', async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/how would you like to check out/i)
      ).toBeInTheDocument();
    });
  });

  it('renders the guest email input on the identity step', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    });
  });

  it('shows validation error when guest tries to continue with empty email', async () => {
    const user = userEvent.setup();
    renderPage();

    // Wait for identity step to appear
    await screen.findByText(/how would you like to check out/i);

    // Click "Continue as Guest" without filling in email
    await user.click(screen.getByRole('button', { name: /continue as guest/i }));

    await waitFor(() => {
      expect(screen.getByText(/email address is required/i)).toBeInTheDocument();
    });
  });

  it('shows validation error for an invalid email format', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/how would you like to check out/i);

    await user.type(screen.getByLabelText(/email address/i), 'not-an-email');
    // Trigger blur to fire onBlur validation
    fireEvent.blur(screen.getByLabelText(/email address/i));

    await waitFor(() => {
      expect(screen.getByText(/valid email address/i)).toBeInTheDocument();
    });
  });

  it('advances to the shipping step after entering a valid guest email', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/how would you like to check out/i);

    await user.type(screen.getByLabelText(/email address/i), 'guest@example.com');
    await user.click(screen.getByRole('button', { name: /continue as guest/i }));

    await waitFor(() => {
      expect(screen.getByText(/shipping address/i)).toBeInTheDocument();
    });
  });

  it('renders a Sign In button on the identity step', async () => {
    renderPage();
    await screen.findByText(/how would you like to check out/i);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  // ── Authenticated path ──────────────────────────────────────────────────

  it('shows the shipping step directly for authenticated users', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/shipping address/i)).toBeInTheDocument();
    });
    // Identity step should NOT be shown
    expect(screen.queryByText(/how would you like to check out/i)).not.toBeInTheDocument();
  });

  it('shows a "signed in as" banner for authenticated users', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/signed in as jane@example\.com/i)).toBeInTheDocument();
    });
  });

  // ── Shipping step ───────────────────────────────────────────────────────

  it('renders all shipping form fields', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    renderPage();
    await screen.findByRole('heading', { name: /shipping address/i });

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    // Address label text is "Address *" — check by id
    expect(screen.getByPlaceholderText('123 Main St')).toBeInTheDocument();
    expect(screen.getByLabelText(/city/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/state \/ region/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/postal code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/country/i)).toBeInTheDocument();
  });

  it('shows validation errors when shipping form is submitted empty', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => {
      expect(screen.getByText(/full name is required/i)).toBeInTheDocument();
    });
  });

  it('advances to the payment step when the shipping form is valid', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.type(screen.getByLabelText(/full name/i), 'Jane Smith');
    await user.type(screen.getByPlaceholderText('123 Main St'), '123 Main St');
    await user.type(screen.getByLabelText(/city/i), 'New York');
    await user.type(screen.getByLabelText(/state/i), 'NY');
    await user.type(screen.getByLabelText(/postal code/i), '10001');

    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^payment$/i })).toBeInTheDocument();
    });
  });

  it('shows a summary of the shipping address on the payment step', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.type(screen.getByLabelText(/full name/i), 'Jane Smith');
    await user.type(screen.getByPlaceholderText('123 Main St'), '123 Main St');
    await user.type(screen.getByLabelText(/city/i), 'New York');
    await user.type(screen.getByLabelText(/state/i), 'NY');
    await user.type(screen.getByLabelText(/postal code/i), '10001');
    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => {
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('123 Main St')).toBeInTheDocument();
    });
  });

  it('returns to shipping step when back is clicked on payment step', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.type(screen.getByLabelText(/full name/i), 'Jane Smith');
    await user.type(screen.getByPlaceholderText('123 Main St'), '123 Main St');
    await user.type(screen.getByLabelText(/city/i), 'New York');
    await user.type(screen.getByLabelText(/state/i), 'NY');
    await user.type(screen.getByLabelText(/postal code/i), '10001');
    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => screen.getByRole('heading', { name: /^payment$/i }));

    await user.click(screen.getByRole('button', { name: /← back/i }));

    await waitFor(() => {
      expect(screen.getByText(/shipping address/i)).toBeInTheDocument();
    });
  });

  it('renders the Stripe card element on the payment step', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.type(screen.getByLabelText(/full name/i), 'Jane Smith');
    await user.type(screen.getByPlaceholderText('123 Main St'), '123 Main St');
    await user.type(screen.getByLabelText(/city/i), 'New York');
    await user.type(screen.getByLabelText(/state/i), 'NY');
    await user.type(screen.getByLabelText(/postal code/i), '10001');
    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => {
      expect(screen.getByTestId('card-element')).toBeInTheDocument();
    });
  });

  // ── Confirmation ────────────────────────────────────────────────────────

  it('navigates to /order-confirmation after successful payment', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    mockCreatePaymentIntent.mockResolvedValue({
      client_secret: 'pi_secret_test',
      payment_intent_id: 'pi_test_123',
      amount: 8999,
      currency: 'gbp',
    });
    mockConfirmOrder.mockResolvedValue(MOCK_ORDER);

    const { useStripe, useElements } = await import('@stripe/react-stripe-js');
    vi.mocked(useStripe).mockReturnValue({
      confirmCardPayment: vi.fn().mockResolvedValue({
        paymentIntent: { status: 'succeeded' },
        error: null,
      }),
    } as unknown as ReturnType<typeof useStripe>);
    vi.mocked(useElements).mockReturnValue({
      getElement: vi.fn().mockReturnValue({ _element: true }),
    } as unknown as ReturnType<typeof useElements>);

    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.type(screen.getByLabelText(/full name/i), 'Jane Smith');
    await user.type(screen.getByPlaceholderText('123 Main St'), '123 Main St');
    await user.type(screen.getByLabelText(/city/i), 'New York');
    await user.type(screen.getByLabelText(/state/i), 'NY');
    await user.type(screen.getByLabelText(/postal code/i), '10001');
    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => screen.getByRole('heading', { name: /^payment$/i }));
    await user.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(screen.getByTestId('order-confirmation-page')).toBeInTheDocument();
    });
  });

  it('calls confirmOrder with the payment_intent_id from Stripe', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    mockCreatePaymentIntent.mockResolvedValue({
      client_secret: 'pi_secret_test',
      payment_intent_id: 'pi_test_123',
      amount: 8999,
      currency: 'gbp',
    });
    mockConfirmOrder.mockResolvedValue(MOCK_ORDER);

    const { useStripe, useElements } = await import('@stripe/react-stripe-js');
    vi.mocked(useStripe).mockReturnValue({
      confirmCardPayment: vi.fn().mockResolvedValue({
        paymentIntent: { status: 'succeeded' },
        error: null,
      }),
    } as unknown as ReturnType<typeof useStripe>);
    vi.mocked(useElements).mockReturnValue({
      getElement: vi.fn().mockReturnValue({ _element: true }),
    } as unknown as ReturnType<typeof useElements>);

    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.type(screen.getByLabelText(/full name/i), 'Jane Smith');
    await user.type(screen.getByPlaceholderText('123 Main St'), '123 Main St');
    await user.type(screen.getByLabelText(/city/i), 'New York');
    await user.type(screen.getByLabelText(/state/i), 'NY');
    await user.type(screen.getByLabelText(/postal code/i), '10001');
    await user.click(screen.getByRole('button', { name: /continue to payment/i }));
    await waitFor(() => screen.getByRole('heading', { name: /^payment$/i }));
    await user.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(mockConfirmOrder).toHaveBeenCalledWith({ payment_intent_id: 'pi_test_123' });
    });
  });

  // ── Step indicator ──────────────────────────────────────────────────────

  it('renders a step-indicator nav for guests', async () => {
    renderPage();
    await screen.findByText(/how would you like to check out/i);
    expect(
      screen.getByRole('navigation', { name: /checkout progress/i })
    ).toBeInTheDocument();
  });

  it('shows step indicator on the payment step', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.type(screen.getByLabelText(/full name/i), 'Jane Smith');
    await user.type(screen.getByPlaceholderText('123 Main St'), '123 Main St');
    await user.type(screen.getByLabelText(/city/i), 'New York');
    await user.type(screen.getByLabelText(/state/i), 'NY');
    await user.type(screen.getByLabelText(/postal code/i), '10001');
    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => screen.getByRole('heading', { name: /^payment$/i }));
    expect(
      screen.getByRole('navigation', { name: /checkout progress/i })
    ).toBeInTheDocument();
  });

  // ── Accessibility ───────────────────────────────────────────────────────

  it('marks email input as aria-required on the identity step', async () => {
    renderPage();
    await screen.findByLabelText(/email address/i);
    const emailInput = screen.getByLabelText(/email address/i);
    expect(emailInput).toHaveAttribute('aria-required', 'true');
  });

  it('uses a main h1 heading "Checkout"', async () => {
    renderPage();
    await screen.findByText(/how would you like to check out/i);
    expect(screen.getByRole('heading', { level: 1, name: /checkout/i })).toBeInTheDocument();
  });

  it('form sections are identified by headings', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /shipping address/i })
      ).toBeInTheDocument();
    });
  });

  it('sends guest_email in the payment-intent request for guest users', async () => {
    mockCreatePaymentIntent.mockResolvedValue({
      client_secret: 'pi_secret_test',
      payment_intent_id: 'pi_test_123',
      amount: 8999,
      currency: 'gbp',
    });
    mockConfirmOrder.mockResolvedValue(MOCK_ORDER);

    const { useStripe, useElements } = await import('@stripe/react-stripe-js');
    vi.mocked(useStripe).mockReturnValue({
      confirmCardPayment: vi.fn().mockResolvedValue({
        paymentIntent: { status: 'succeeded' },
        error: null,
      }),
    } as unknown as ReturnType<typeof useStripe>);
    vi.mocked(useElements).mockReturnValue({
      getElement: vi.fn().mockReturnValue({ _element: true }),
    } as unknown as ReturnType<typeof useElements>);

    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/how would you like to check out/i);

    // Step 1 — identity
    await user.type(screen.getByLabelText(/email address/i), 'guest@test.com');
    await user.click(screen.getByRole('button', { name: /continue as guest/i }));

    // Step 2 — shipping
    await screen.findByText(/shipping address/i);
    await user.type(screen.getByLabelText(/full name/i), 'Guest User');
    await user.type(screen.getByPlaceholderText('123 Main St'), '1 Test Rd');
    await user.type(screen.getByLabelText(/city/i), 'Boston');
    await user.type(screen.getByLabelText(/state/i), 'MA');
    await user.type(screen.getByLabelText(/postal code/i), '02101');
    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    // Step 3 — payment
    await waitFor(() => screen.getByRole('heading', { name: /^payment$/i }));
    await user.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(mockCreatePaymentIntent).toHaveBeenCalledWith(
        expect.objectContaining({ guest_email: 'guest@test.com' })
      );
    });
  });

  it('does NOT include guest_email in payment-intent for authenticated users', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    mockCreatePaymentIntent.mockResolvedValue({
      client_secret: 'pi_secret_test',
      payment_intent_id: 'pi_test_123',
      amount: 8999,
      currency: 'gbp',
    });
    mockConfirmOrder.mockResolvedValue(MOCK_ORDER);

    const { useStripe, useElements } = await import('@stripe/react-stripe-js');
    vi.mocked(useStripe).mockReturnValue({
      confirmCardPayment: vi.fn().mockResolvedValue({
        paymentIntent: { status: 'succeeded' },
        error: null,
      }),
    } as unknown as ReturnType<typeof useStripe>);
    vi.mocked(useElements).mockReturnValue({
      getElement: vi.fn().mockReturnValue({ _element: true }),
    } as unknown as ReturnType<typeof useElements>);

    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/shipping address/i);

    await user.type(screen.getByLabelText(/full name/i), 'Jane Smith');
    await user.type(screen.getByPlaceholderText('123 Main St'), '123 Main St');
    await user.type(screen.getByLabelText(/city/i), 'New York');
    await user.type(screen.getByLabelText(/state/i), 'NY');
    await user.type(screen.getByLabelText(/postal code/i), '10001');
    await user.click(screen.getByRole('button', { name: /continue to payment/i }));

    await waitFor(() => screen.getByRole('heading', { name: /^payment$/i }));
    await user.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(mockCreatePaymentIntent).toHaveBeenCalledWith(
        expect.not.objectContaining({ guest_email: expect.anything() })
      );
    });
  });
});
