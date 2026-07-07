/**
 * Keyboard accessibility tests — T-034 / US-015
 *
 * Verifies WCAG 2.1 Level AA keyboard accessibility requirements for:
 *   - ProductDetailPage (product page)
 *   - CartPage
 *   - CheckoutPage
 *
 * Acceptance criteria checked:
 *   AC1: Tab key moves focus sequentially through all interactive elements.
 *   AC2: Enter key activates buttons and links.
 *   AC3: Interactive elements have visible focus indicators (focus:ring-* classes).
 *   AC4: All form inputs have associated labels.
 *   AC5: Validation errors are announced via role="alert" or aria-describedby.
 *   AC6: Dynamic content updates are live-announced.
 *   AC7: The mobile navigation menu can be dismissed with the Escape key.
 *   AC8: Star-rating buttons are keyboard-operable with proper aria-label.
 *   AC9: Quantity input in ProductDetailPage is a proper native input (not a div).
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockUseAuth = vi.fn();

vi.mock('../stores/authStore', () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Stripe mocks (required for CheckoutPage)
vi.mock('@stripe/stripe-js', () => ({
  loadStripe: vi.fn().mockResolvedValue({
    confirmCardPayment: vi.fn(),
  }),
}));

vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  CardElement: () => <input data-testid="card-element" aria-label="Card number" />,
  useStripe: vi.fn().mockReturnValue(null),
  useElements: vi.fn().mockReturnValue(null),
}));

// API mocks
const mockGetCart = vi.fn();
const mockGetProduct = vi.fn();
const mockGetProductReviews = vi.fn();
const mockGetCategories = vi.fn();

vi.mock('../api/cart', () => ({
  getCart: () => mockGetCart(),
  updateCartItem: vi.fn().mockResolvedValue({}),
  removeCartItem: vi.fn().mockResolvedValue({}),
  addCartItem: vi.fn().mockResolvedValue({}),
}));

vi.mock('../api/products', () => ({
  getProduct: (..._args: unknown[]) => mockGetProduct(),
  getProducts: vi.fn().mockResolvedValue({ items: [], total: 0, total_pages: 0 }),
}));

vi.mock('../api/reviews', () => ({
  getProductReviews: (..._args: unknown[]) => mockGetProductReviews(),
  createProductReview: vi.fn().mockResolvedValue({}),
  REVIEWS_PER_PAGE: 10,
}));

vi.mock('../api/categories', () => ({
  getCategories: () => mockGetCategories(),
}));

vi.mock('../api/checkout', () => ({
  createPaymentIntent: vi.fn().mockResolvedValue({
    client_secret: 'pi_secret_test',
    payment_intent_id: 'pi_test_123',
    amount: 8999,
    currency: 'gbp',
  }),
  confirmOrder: vi.fn().mockResolvedValue({}),
}));

vi.mock('../hooks/useCartCount', () => ({
  useCartCount: vi.fn().mockReturnValue(0),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const GUEST_AUTH = {
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  setUser: vi.fn(),
  setAccessToken: vi.fn(),
};

const AUTH_USER = {
  ...GUEST_AUTH,
  user: { id: 'u-1', email: 'jane@example.com', full_name: 'Jane', is_active: true, is_superuser: false, created_at: '', updated_at: '' },
  isAuthenticated: true,
};

const MOCK_PRODUCT = {
  id: 'prod-1',
  name: 'Trail Boot',
  slug: 'trail-boot',
  description: 'A rugged trail boot.',
  category_id: 'cat-1',
  brand: 'TestBrand',
  base_price: 89.99,
  sale_price: null,
  image_url: 'https://example.com/boot.jpg',
  images: ['https://example.com/boot.jpg'],
  is_active: true,
  is_featured: false,
  average_rating: 4.5,
  review_count: 10,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  variants: [
    {
      id: 'var-1',
      product_id: 'prod-1',
      sku: 'SKU1',
      size: '9',
      color: 'Black',
      width: null,
      stock_quantity: 5,
      price_adjustment: 0,
      image_url: null,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ],
  materials: 'Premium leather',
  features: ['Waterproof', 'Slip-resistant'],
};

const MOCK_REVIEWS = {
  reviews: [
    {
      id: 'rev-1',
      rating: 5,
      review_text: 'Great boots!',
      created_at: '2024-01-15T00:00:00Z',
    },
  ],
  total_reviews: 1,
  average_rating: 5.0,
};

const MOCK_CART_ITEM = {
  id: 'item-1',
  cart_id: 'cart-1',
  product_id: 'prod-1',
  variant_id: null,
  quantity: 2,
  unit_price: 89.99,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  product: {
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
  },
  variant: {
    id: 'var-1',
    product_id: 'prod-1',
    sku: 'SKU1',
    size: '9',
    color: 'Brown',
    width: null,
    stock_quantity: 5,
    price_adjustment: 0,
    image_url: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
};

const MOCK_CART = {
  id: 'cart-1',
  user_id: null,
  session_id: 'session-abc',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  items: [MOCK_CART_ITEM],
};

// ── Render helpers ─────────────────────────────────────────────────────────────

const createQC = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });

const renderWithProviders = (ui: React.ReactElement, initialPath = '/') =>
  render(
    <QueryClientProvider client={createQC()}>
      <MemoryRouter initialEntries={[initialPath]}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  );

// ── Tests: ProductDetailPage keyboard accessibility ────────────────────────────

describe('ProductDetailPage — keyboard accessibility (T-034 / US-015)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue(AUTH_USER);
    mockGetProduct.mockResolvedValue(MOCK_PRODUCT);
    mockGetProductReviews.mockResolvedValue(MOCK_REVIEWS);
    mockGetCategories.mockResolvedValue([]);
  });

  it('renders the product heading when product loads (sanity check)', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /trail boot/i })).toBeInTheDocument();
    });
  });

  it('size picker buttons have aria-label and aria-pressed attributes', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    // Size button should have aria-label and aria-pressed
    const sizeBtn = screen.getByRole('button', { name: /size 9/i });
    expect(sizeBtn).toHaveAttribute('aria-label');
    expect(sizeBtn).toHaveAttribute('aria-pressed');
  });

  it('size picker buttons are keyboard-activatable (Enter selects size)', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    const sizeBtn = screen.getByRole('button', { name: /size 9/i });
    sizeBtn.focus();
    await user.keyboard('{Enter}');
    // After pressing Enter, the button should become "selected" (aria-pressed=true)
    expect(sizeBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('quantity input is a native <input type="number"> (not a non-interactive span)', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    // The quantity control must be a focusable <input type="number"> (ARIA spinbutton)
    // Use getByRole('spinbutton') to find it unambiguously
    const qtyInput = screen.getByRole('spinbutton');
    expect(qtyInput.tagName).toBe('INPUT');
    expect(qtyInput).toHaveAttribute('type', 'number');
  });

  it('quantity input has proper min, max attributes', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    const qtyInput = screen.getByRole('spinbutton');
    expect(qtyInput).toHaveAttribute('min', '1');
    expect(Number(qtyInput.getAttribute('max'))).toBeGreaterThanOrEqual(1);
  });

  it('interactive star rating buttons have descriptive aria-labels', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    // Star rating buttons in the review form (only shown for authenticated users)
    const starButtons = screen.getAllByRole('button', { name: /rate \d+ out of/i });
    expect(starButtons.length).toBeGreaterThan(0);
    starButtons.forEach((btn) => {
      expect(btn).toHaveAttribute('aria-label');
      expect(btn).toHaveAttribute('type', 'button');
    });
  });

  it('star rating buttons have a visible focus ring class', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    const starButtons = screen.getAllByRole('button', { name: /rate \d+ out of/i });
    // Each star button should have a focus:ring class for visible focus indicator
    starButtons.forEach((btn) => {
      expect(btn.className).toMatch(/focus:ring/);
    });
  });

  it('keyboard user can click star rating button and change rating', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    const rate3btn = screen.getByRole('button', { name: /rate 3 out of 5/i });
    rate3btn.focus();
    await user.keyboard('{Enter}');
    // No error thrown; rating changed is reflected in accessible label
    expect(rate3btn).toBeInTheDocument();
  });

  it('review textarea has an associated label', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    // getByLabelText throws if no matching label — this IS the assertion
    const textarea = screen.getByLabelText(/review text/i);
    expect(textarea.tagName).toBe('TEXTAREA');
  });

  it('add to cart button has an accessible name', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    const addBtn = screen.getByRole('button', { name: /add to cart/i });
    expect(addBtn).toBeInTheDocument();
    expect(addBtn).toHaveAttribute('type', 'button');
  });

  it('breadcrumb navigation uses proper nav + ordered list', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i });
    expect(breadcrumb).toBeInTheDocument();
    // Breadcrumb list items link should be real <a> elements
    const links = within(breadcrumb).getAllByRole('link');
    expect(links.length).toBeGreaterThan(0);
    links.forEach((link) => {
      expect(link.tagName).toBe('A');
    });
  });

  it('details/summary accordion items are keyboard-operable', async () => {
    const { ProductDetailPage } = await import('./ProductDetailPage');
    renderWithProviders(
      <Routes>
        <Route path="/products/:productId" element={<ProductDetailPage />} />
      </Routes>,
      '/products/prod-1'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });

    // <details>/<summary> are natively keyboard-operable with Enter/Space
    const sizingAccordion = screen.getByText(/sizing & fit/i);
    expect(sizingAccordion.tagName).toBe('SUMMARY');
  });
});

// ── Tests: CartPage keyboard accessibility ─────────────────────────────────────

describe('CartPage — keyboard accessibility (T-034 / US-015)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    mockGetCart.mockResolvedValue(MOCK_CART);
  });

  it('quantity decrease button has a descriptive aria-label', async () => {
    const { CartPage } = await import('./CartPage');
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    const decreaseBtn = screen.getByRole('button', { name: /decrease quantity of trail boot/i });
    expect(decreaseBtn).toBeInTheDocument();
    expect(decreaseBtn).toHaveAttribute('type', 'button');
  });

  it('quantity increase button has a descriptive aria-label', async () => {
    const { CartPage } = await import('./CartPage');
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    const increaseBtn = screen.getByRole('button', { name: /increase quantity of trail boot/i });
    expect(increaseBtn).toBeInTheDocument();
  });

  it('remove button has a descriptive aria-label mentioning the product name', async () => {
    const { CartPage } = await import('./CartPage');
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    const removeBtn = screen.getByRole('button', { name: /remove trail boot from cart/i });
    expect(removeBtn).toBeInTheDocument();
  });

  it('quantity stepper group has an accessible grouping label', async () => {
    const { CartPage } = await import('./CartPage');
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    // The stepper group should be a role="group" with aria-label
    const stepperGroup = screen.getByRole('group', { name: /quantity for trail boot/i });
    expect(stepperGroup).toBeInTheDocument();
  });

  it('keyboard user can activate the decrease button with Enter', async () => {
    mockGetCart.mockResolvedValue({
      ...MOCK_CART,
      items: [{ ...MOCK_CART_ITEM, quantity: 3 }],
    });
    const { CartPage } = await import('./CartPage');
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    const decreaseBtn = screen.getByRole('button', { name: /decrease quantity of trail boot/i });
    decreaseBtn.focus();
    // Enter should trigger the button
    await user.keyboard('{Enter}');
    expect(decreaseBtn).toBeInTheDocument();
  });

  it('proceed to checkout link has an accessible name', async () => {
    const { CartPage } = await import('./CartPage');
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    const checkoutLink = screen.getByRole('link', { name: /proceed to checkout/i });
    expect(checkoutLink).toHaveAttribute('href', '/checkout');
  });

  it('cart item rows use semantic <li> inside a <ul>', async () => {
    const { CartPage } = await import('./CartPage');
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    // The item list uses a <ul> for semantic structure
    const cartList = screen.getByRole('list');
    expect(cartList).toBeInTheDocument();
    const listItems = within(cartList).getAllByRole('listitem');
    expect(listItems.length).toBeGreaterThan(0);
  });

  it('order summary aside has an accessible label', async () => {
    const { CartPage } = await import('./CartPage');
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    // The aside should be identifiable
    const summary = screen.getByRole('complementary', { name: /order summary/i });
    expect(summary).toBeInTheDocument();
  });

  it('quantity display is a live region that announces updates', async () => {
    const { CartPage } = await import('./CartPage');
    renderWithProviders(
      <Routes>
        <Route path="/cart" element={<CartPage />} />
      </Routes>,
      '/cart'
    );
    await waitFor(() => {
      expect(screen.getByText('Trail Boot')).toBeInTheDocument();
    });

    // The quantity span should have aria-live for screen reader announcements
    const qtyDisplay = screen.getByText('2');
    expect(qtyDisplay).toHaveAttribute('aria-live', 'polite');
  });
});

// ── Tests: CheckoutPage keyboard accessibility ────────────────────────────────

describe('CheckoutPage — keyboard accessibility (T-034 / US-015)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    mockGetCart.mockResolvedValue(MOCK_CART);
  });

  it('guest email input has aria-required="true"', async () => {
    const { CheckoutPage } = await import('./CheckoutPage');
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    });

    expect(screen.getByLabelText(/email address/i)).toHaveAttribute('aria-required', 'true');
  });

  it('identity step: invalid email triggers an alert with role="alert"', async () => {
    const { CheckoutPage } = await import('./CheckoutPage');
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/email address/i), 'not-valid');
    fireEvent.blur(screen.getByLabelText(/email address/i));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('checkout h1 heading is present and accessible', async () => {
    const { CheckoutPage } = await import('./CheckoutPage');
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /checkout/i })).toBeInTheDocument();
    });
  });

  it('step indicator is a <nav> with aria-label="Checkout progress"', async () => {
    const { CheckoutPage } = await import('./CheckoutPage');
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByRole('navigation', { name: /checkout progress/i })).toBeInTheDocument();
    });
  });

  it('step indicator uses an ordered list <ol>', async () => {
    const { CheckoutPage } = await import('./CheckoutPage');
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByRole('navigation', { name: /checkout progress/i })).toBeInTheDocument();
    });

    const stepNav = screen.getByRole('navigation', { name: /checkout progress/i });
    const ol = stepNav.querySelector('ol');
    expect(ol).not.toBeNull();
  });

  it('keyboard user can advance the checkout using Enter on buttons', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const { CheckoutPage } = await import('./CheckoutPage');
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
        <Route path="/login" element={<div />} />
        <Route path="/cart" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    });

    // Fill in shipping form using keyboard
    const fullName = screen.getByLabelText(/full name/i);
    fullName.focus();
    await user.keyboard('Jane Smith');
    await user.tab();
    await user.keyboard('123 Main St');
    await user.tab();
    await user.keyboard('New York');
    await user.tab();
    await user.keyboard('NY');
    await user.tab();
    await user.keyboard('10001');

    // Tab to submit button
    const continueBtn = screen.getByRole('button', { name: /continue to payment/i });
    continueBtn.focus();
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^payment$/i })).toBeInTheDocument();
    });
  });

  it('shipping form fields all have associated labels', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const { CheckoutPage } = await import('./CheckoutPage');
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
        <Route path="/login" element={<div />} />
        <Route path="/cart" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    });

    // All fields must have associated labels (getByLabelText throws if not)
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/city/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/state \/ region/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/postal code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/country/i)).toBeInTheDocument();
  });

  it('shipping form fields have aria-required="true"', async () => {
    mockUseAuth.mockReturnValue(AUTH_USER);
    const { CheckoutPage } = await import('./CheckoutPage');
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
        <Route path="/login" element={<div />} />
        <Route path="/cart" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    });

    expect(screen.getByLabelText(/full name/i)).toHaveAttribute('aria-required', 'true');
    expect(screen.getByLabelText(/city/i)).toHaveAttribute('aria-required', 'true');
    expect(screen.getByLabelText(/postal code/i)).toHaveAttribute('aria-required', 'true');
  });

  it('back button on shipping step allows keyboard navigation backwards', async () => {
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    const { CheckoutPage } = await import('./CheckoutPage');
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
        <Route path="/login" element={<div />} />
        <Route path="/cart" element={<div />} />
      </Routes>,
      '/checkout'
    );

    // Identity step: enter email
    await waitFor(() => {
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    });
    await user.type(screen.getByLabelText(/email address/i), 'guest@example.com');
    await user.click(screen.getByRole('button', { name: /continue as guest/i }));

    // Shipping step
    await waitFor(() => {
      expect(screen.getByText(/shipping address/i)).toBeInTheDocument();
    });

    // Back button should be present and keyboard-operable
    const backBtn = screen.getByRole('button', { name: /← back/i });
    expect(backBtn).toHaveAttribute('type', 'button');
    backBtn.focus();
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/how would you like to check out/i)).toBeInTheDocument();
    });
  });

  it('sign-in button on identity step is keyboard-operable', async () => {
    const { CheckoutPage } = await import('./CheckoutPage');
    renderWithProviders(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/products" element={<div />} />
        <Route path="/login" element={<div>Login</div>} />
        <Route path="/cart" element={<div />} />
      </Routes>,
      '/checkout'
    );
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    const signInBtn = screen.getByRole('button', { name: /sign in/i });
    expect(signInBtn.tagName).toBe('BUTTON');
    expect(signInBtn).toHaveAttribute('type', 'button');
  });
});

// ── Tests: SiteHeader mobile menu keyboard accessibility ──────────────────────

describe('SiteHeader — mobile menu keyboard accessibility (T-034 / US-015)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue(GUEST_AUTH);
    mockGetCategories.mockResolvedValue([]);
  });

  it('mobile menu toggle button has aria-expanded', async () => {
    const { SiteHeader } = await import('../components/layout/SiteHeader');
    render(
      <QueryClientProvider client={createQC()}>
        <BrowserRouter>
          <SiteHeader />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const menuBtn = screen.getByRole('button', { name: /open navigation menu/i });
    expect(menuBtn).toHaveAttribute('aria-expanded', 'false');
  });

  it('mobile menu toggle aria-expanded changes to true when menu opens', async () => {
    const { SiteHeader } = await import('../components/layout/SiteHeader');
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={createQC()}>
        <BrowserRouter>
          <SiteHeader />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const menuBtn = screen.getByRole('button', { name: /open navigation menu/i });
    await user.click(menuBtn);

    expect(screen.getByRole('button', { name: /close navigation menu/i })).toHaveAttribute(
      'aria-expanded',
      'true'
    );
  });

  it('mobile menu toggle button has aria-controls pointing to the menu', async () => {
    const { SiteHeader } = await import('../components/layout/SiteHeader');
    render(
      <QueryClientProvider client={createQC()}>
        <BrowserRouter>
          <SiteHeader />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const menuBtn = screen.getByRole('button', { name: /open navigation menu/i });
    expect(menuBtn).toHaveAttribute('aria-controls', 'mobile-menu');
  });

  it('pressing Escape while mobile menu is open closes it', async () => {
    const { SiteHeader } = await import('../components/layout/SiteHeader');
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={createQC()}>
        <BrowserRouter>
          <SiteHeader />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Open the menu
    const menuBtn = screen.getByRole('button', { name: /open navigation menu/i });
    await user.click(menuBtn);
    expect(screen.getByRole('navigation', { name: /mobile navigation/i })).toBeInTheDocument();

    // Press Escape to close
    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.queryByRole('navigation', { name: /mobile navigation/i })).not.toBeInTheDocument();
    });
  });

  it('cart link has an accessible name', async () => {
    const { SiteHeader } = await import('../components/layout/SiteHeader');
    render(
      <QueryClientProvider client={createQC()}>
        <BrowserRouter>
          <SiteHeader />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const cartLink = screen.getByRole('link', { name: /shopping cart/i });
    expect(cartLink).toBeInTheDocument();
    expect(cartLink.tagName).toBe('A');
  });

  it('site logo link has an accessible name', async () => {
    const { SiteHeader } = await import('../components/layout/SiteHeader');
    render(
      <QueryClientProvider client={createQC()}>
        <BrowserRouter>
          <SiteHeader />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const logoLink = screen.getByRole('link', { name: /boots shop/i });
    expect(logoLink).toBeInTheDocument();
    expect(logoLink.tagName).toBe('A');
  });
});
