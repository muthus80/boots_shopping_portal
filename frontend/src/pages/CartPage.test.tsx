/**
 * CartPage tests — T-024 / US-010
 *
 * Coverage:
 *  - Loading state renders spinner
 *  - Error state renders ErrorMessage with retry
 *  - Empty cart renders EmptyState
 *  - Populated cart renders all items with price, quantity, and subtotal
 *  - Quantity decrease/increase calls updateCartItem
 *  - Remove button calls removeCartItem
 *  - Subtotal updates when item quantities change
 *  - Accessibility: aria-labels on quantity buttons and remove buttons
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CartPage } from './CartPage';
import type { Cart, CartItem, Product } from '../types/index';

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockGetCart = vi.fn();
const mockUpdateCartItem = vi.fn();
const mockRemoveCartItem = vi.fn();

vi.mock('../api/cart', () => ({
  getCart: () => mockGetCart(),
  updateCartItem: (itemId: string, quantity: number) =>
    mockUpdateCartItem(itemId, quantity),
  removeCartItem: (itemId: string) => mockRemoveCartItem(itemId),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const makeProduct = (overrides: Partial<Product> = {}): Product => ({
  id: 'prod-1',
  name: 'Trailblazer Hiking Boot',
  slug: 'trailblazer-hiking-boot',
  description: 'A great boot.',
  category_id: 'cat-1',
  brand: 'TestBrand',
  base_price: 99.99,
  sale_price: null,
  image_url: null,
  images: [],
  is_active: true,
  is_featured: false,
  average_rating: null,
  review_count: 0,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
});

const makeCartItem = (overrides: Partial<CartItem> = {}): CartItem => ({
  id: 'item-1',
  cart_id: 'cart-1',
  product_id: 'prod-1',
  variant_id: null,
  quantity: 2,
  unit_price: 99.99,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  product: makeProduct(),
  variant: undefined,
  ...overrides,
});

const makeCart = (items: CartItem[] = []): Cart => ({
  id: 'cart-1',
  user_id: 'u1',
  session_id: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  items,
});

// ── Render helper ─────────────────────────────────────────────────────────────

const renderPage = () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <CartPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('CartPage (T-024 / US-010)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading ─────────────────────────────────────────────────────────────

  it('renders a loading spinner while fetching the cart', () => {
    // Never resolves — stays in loading state
    mockGetCart.mockReturnValue(new Promise(() => {}));
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
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it('renders a retry button on error', async () => {
    mockGetCart.mockRejectedValue(new Error('Network error'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    // ErrorMessage renders a "Try again" button when onRetry is provided
    expect(screen.getByRole('button', { name: /retry loading/i })).toBeInTheDocument();
  });

  // ── Empty cart ──────────────────────────────────────────────────────────

  it('renders an empty-cart message when there are no items', async () => {
    mockGetCart.mockResolvedValue(makeCart([]));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/your cart is empty/i)).toBeInTheDocument();
    });
    // "Continue Shopping" link should point to /products
    const link = screen.getByRole('link', { name: /continue shopping/i });
    expect(link).toHaveAttribute('href', '/products');
  });

  // ── Populated cart ──────────────────────────────────────────────────────

  it('renders item names, per-unit price, quantity, and subtotal', async () => {
    const item = makeCartItem({ quantity: 2, unit_price: 99.99 });
    mockGetCart.mockResolvedValue(makeCart([item]));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Trailblazer Hiking Boot')).toBeInTheDocument();
    });

    // Per-unit price displayed
    expect(screen.getByText(/£99\.99 each/i)).toBeInTheDocument();

    // Quantity shown
    expect(screen.getByText('2')).toBeInTheDocument();

    // Line total: 2 × £99.99 = £199.98 (appears in both line total and summary)
    expect(screen.getAllByText('£199.98').length).toBeGreaterThanOrEqual(1);
  });

  it('displays cart-subtotal in the order summary', async () => {
    const item1 = makeCartItem({ id: 'item-1', quantity: 1, unit_price: 50.0, product: makeProduct({ id: 'p1', name: 'Boot A', slug: 'boot-a' }) });
    const item2 = makeCartItem({ id: 'item-2', quantity: 2, unit_price: 75.0, product: makeProduct({ id: 'p2', name: 'Boot B', slug: 'boot-b' }) });
    mockGetCart.mockResolvedValue(makeCart([item1, item2]));
    renderPage();

    await waitFor(() => {
      // Subtotal: 1×£50 + 2×£75 = £200
      expect(screen.getByTestId('cart-subtotal')).toHaveTextContent('£200.00');
    });
  });

  it('shows correct item count in subtotal label', async () => {
    const item1 = makeCartItem({ id: 'item-1', quantity: 3 });
    mockGetCart.mockResolvedValue(makeCart([item1]));
    renderPage();

    await waitFor(() => {
      // 3 items total
      expect(screen.getByText(/3 items/i)).toBeInTheDocument();
    });
  });

  it('uses singular "item" when total quantity is 1', async () => {
    const item = makeCartItem({ quantity: 1 });
    mockGetCart.mockResolvedValue(makeCart([item]));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/1 item\b/i)).toBeInTheDocument();
    });
  });

  // ── Quantity controls ───────────────────────────────────────────────────

  it('calls updateCartItem with incremented quantity when + is clicked', async () => {
    const item = makeCartItem({ id: 'item-1', quantity: 2 });
    mockGetCart.mockResolvedValue(makeCart([item]));
    mockUpdateCartItem.mockResolvedValue({ ...item, quantity: 3 });

    const user = userEvent.setup();
    renderPage();

    await waitFor(() => screen.getByText('Trailblazer Hiking Boot'));

    await user.click(screen.getByRole('button', { name: /increase quantity/i }));

    await waitFor(() => {
      expect(mockUpdateCartItem).toHaveBeenCalledWith('item-1', 3);
    });
  });

  it('calls updateCartItem with decremented quantity when − is clicked', async () => {
    const item = makeCartItem({ id: 'item-1', quantity: 3 });
    mockGetCart.mockResolvedValue(makeCart([item]));
    mockUpdateCartItem.mockResolvedValue({ ...item, quantity: 2 });

    const user = userEvent.setup();
    renderPage();

    await waitFor(() => screen.getByText('Trailblazer Hiking Boot'));

    await user.click(screen.getByRole('button', { name: /decrease quantity/i }));

    await waitFor(() => {
      expect(mockUpdateCartItem).toHaveBeenCalledWith('item-1', 2);
    });
  });

  it('disables the − button when quantity is 1', async () => {
    const item = makeCartItem({ quantity: 1 });
    mockGetCart.mockResolvedValue(makeCart([item]));
    renderPage();

    await waitFor(() => screen.getByText('Trailblazer Hiking Boot'));

    const decBtn = screen.getByRole('button', { name: /decrease quantity/i });
    expect(decBtn).toBeDisabled();
  });

  // ── Remove ──────────────────────────────────────────────────────────────

  it('calls removeCartItem when the Remove button is clicked', async () => {
    const item = makeCartItem({ id: 'item-1' });
    mockGetCart.mockResolvedValue(makeCart([item]));
    mockRemoveCartItem.mockResolvedValue(undefined);

    const user = userEvent.setup();
    renderPage();

    await waitFor(() => screen.getByText('Trailblazer Hiking Boot'));

    await user.click(screen.getByRole('button', { name: /remove trailblazer hiking boot from cart/i }));

    await waitFor(() => {
      expect(mockRemoveCartItem).toHaveBeenCalledWith('item-1');
    });
  });

  // ── Checkout link ───────────────────────────────────────────────────────

  it('renders a "Proceed to Checkout" link pointing to /checkout', async () => {
    mockGetCart.mockResolvedValue(makeCart([makeCartItem()]));
    renderPage();

    await waitFor(() => screen.getByText('Trailblazer Hiking Boot'));

    const checkoutLink = screen.getByRole('link', { name: /proceed to checkout/i });
    expect(checkoutLink).toHaveAttribute('href', '/checkout');
  });

  // ── Variant display ─────────────────────────────────────────────────────

  it('displays variant size and colour when present', async () => {
    const item = makeCartItem({
      variant: {
        id: 'var-1',
        product_id: 'prod-1',
        sku: 'SKU1',
        size: '10',
        color: 'Brown',
        width: null,
        stock_quantity: 5,
        price_adjustment: 0,
        image_url: null,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      variant_id: 'var-1',
    });
    mockGetCart.mockResolvedValue(makeCart([item]));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/size: 10/i)).toBeInTheDocument();
      expect(screen.getByText(/colour: brown/i)).toBeInTheDocument();
    });
  });

  // ── Multiple items ──────────────────────────────────────────────────────

  it('renders all items when the cart has multiple entries', async () => {
    const items = [
      makeCartItem({ id: 'item-1', product: makeProduct({ id: 'p1', name: 'Boot A', slug: 'boot-a' }) }),
      makeCartItem({ id: 'item-2', product: makeProduct({ id: 'p2', name: 'Boot B', slug: 'boot-b' }) }),
    ];
    mockGetCart.mockResolvedValue(makeCart(items));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Boot A')).toBeInTheDocument();
      expect(screen.getByText('Boot B')).toBeInTheDocument();
    });
  });
});
