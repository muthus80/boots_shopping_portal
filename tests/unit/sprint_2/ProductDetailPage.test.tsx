import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProductDetailPage } from './ProductDetailPage';
import type { Product, ProductVariant, Review } from '../types/index';

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockGetProduct = vi.fn();
const mockAddCartItem = vi.fn();
const mockUseAuth = vi.fn();

vi.mock('../api/products', () => ({
  getProduct: (...args: unknown[]) => mockGetProduct(...args),
}));

vi.mock('../api/cart', () => ({
  addCartItem: (...args: unknown[]) => mockAddCartItem(...args),
}));

vi.mock('../stores/authStore', () => ({
  useAuth: () => mockUseAuth(),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_VARIANT_1: ProductVariant = {
  id: 'var-1',
  product_id: 'prod-1',
  sku: 'BOOT-1-8-BLK',
  size: '8',
  color: 'black',
  width: null,
  stock_quantity: 5,
  price_adjustment: 0,
  image_url: null,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const MOCK_VARIANT_2: ProductVariant = {
  id: 'var-2',
  product_id: 'prod-1',
  sku: 'BOOT-1-9-BLK',
  size: '9',
  color: 'black',
  width: null,
  stock_quantity: 0,
  price_adjustment: 0,
  image_url: null,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const MOCK_VARIANT_3: ProductVariant = {
  id: 'var-3',
  product_id: 'prod-1',
  sku: 'BOOT-1-8-BRN',
  size: '8',
  color: 'brown',
  width: null,
  stock_quantity: 3,
  price_adjustment: 0,
  image_url: null,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const MOCK_REVIEW: Review = {
  id: 'rev-1',
  product_id: 'prod-1',
  user_id: 'user-1',
  rating: 4,
  title: 'Great boots!',
  body: 'Very comfortable and well-made.',
  is_verified_purchase: true,
  is_approved: true,
  created_at: '2024-03-01T00:00:00Z',
  updated_at: '2024-03-01T00:00:00Z',
  user: { id: 'user-1', full_name: 'Jane Doe' },
};

const MOCK_PRODUCT: Product & {
  variants?: ProductVariant[];
  reviews?: Review[];
  category?: { id: string; name: string };
} = {
  id: 'prod-1',
  name: 'Trek Leather Boot',
  slug: 'trek-leather-boot',
  description: 'Durable waterproof hiking boot for all terrains.',
  category_id: 'cat-1',
  brand: 'OutdoorPro',
  base_price: 120,
  sale_price: null,
  image_url: 'https://example.com/boot-main.jpg',
  images: [
    'https://example.com/boot-1.jpg',
    'https://example.com/boot-2.jpg',
    'https://example.com/boot-3.jpg',
  ],
  is_active: true,
  is_featured: false,
  average_rating: 4.0,
  review_count: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  variants: [MOCK_VARIANT_1, MOCK_VARIANT_2, MOCK_VARIANT_3],
  reviews: [MOCK_REVIEW],
  category: { id: 'cat-1', name: 'Hiking Boots' },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const createQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderPage = (productId = 'prod-1') => {
  const qc = createQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/products/${productId}`]}>
        <Routes>
          <Route path="/products/:productId" element={<ProductDetailPage />} />
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/cart" element={<div>Cart Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ProductDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: 'user-1', email: 'test@test.com' } });
    mockGetProduct.mockResolvedValue(MOCK_PRODUCT);
    mockAddCartItem.mockResolvedValue({ id: 'cart-item-1' });
  });

  // ── Loading state ─────────────────────────────────────────────────────────────

  it('shows a loading indicator while the product is being fetched', () => {
    mockGetProduct.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByLabelText(/loading product details/i)).toBeInTheDocument();
  });

  // ── Error state ───────────────────────────────────────────────────────────────

  it('shows an error message when the product fails to load', async () => {
    mockGetProduct.mockRejectedValueOnce(new Error('Network failure'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(
        screen.getByText(/something went wrong, please try again/i)
      ).toBeInTheDocument();
    });
  });

  it('shows a try again button on error', async () => {
    mockGetProduct.mockRejectedValueOnce(new Error('Network failure'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });
  });

  // ── Product info ──────────────────────────────────────────────────────────────

  it('renders the product name as an h1 heading', async () => {
    renderPage();
    expect(
      await screen.findByRole('heading', { level: 1, name: /trek leather boot/i })
    ).toBeInTheDocument();
  });

  it('renders the brand', async () => {
    renderPage();
    expect(await screen.findByText('OutdoorPro')).toBeInTheDocument();
  });

  it('renders the product description', async () => {
    renderPage();
    expect(
      await screen.findByText(/durable waterproof hiking boot/i)
    ).toBeInTheDocument();
  });

  it('renders the base price', async () => {
    renderPage();
    expect(await screen.findByText(/£120\.00/)).toBeInTheDocument();
  });

  it('renders the category breadcrumb', async () => {
    renderPage();
    expect(await screen.findByText('Hiking Boots')).toBeInTheDocument();
  });

  // ── Image gallery ─────────────────────────────────────────────────────────────

  it('renders the primary product image', async () => {
    renderPage();
    const img = await screen.findByAltText(/trek leather boot — image 1/i);
    expect(img).toHaveAttribute('src', 'https://example.com/boot-1.jpg');
  });

  it('renders image thumbnails when multiple images exist', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 }); // wait for load
    const tablist = screen.getByRole('tablist', { name: /product image thumbnails/i });
    expect(tablist).toBeInTheDocument();
  });

  it('shows 3 thumbnail buttons for 3 images', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 }); // wait for load
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
  });

  it('switches main image when a thumbnail is clicked', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    const tabs = screen.getAllByRole('tab');
    fireEvent.click(tabs[1]); // click second thumbnail

    await waitFor(() => {
      const mainImg = screen.getByAltText(/trek leather boot — image 2/i);
      expect(mainImg).toHaveAttribute('src', 'https://example.com/boot-2.jpg');
    });
  });

  // ── Size picker ───────────────────────────────────────────────────────────────

  it('renders a size picker with available sizes', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    const sizeGroup = screen.getByRole('group', { name: /select a size/i });
    expect(sizeGroup).toBeInTheDocument();
  });

  it('renders size 8 and size 9 as options', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    expect(screen.getByRole('button', { name: /size 8/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /size 9/i })).toBeInTheDocument();
  });

  it('marks out-of-stock size variants as disabled', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    // Size 9 is only available in black with 0 stock
    // It should be disabled because variant-2 has stock_quantity 0
    // and no other size-9 variants exist
    const size9Btn = screen.getByRole('button', { name: /size 9/i });
    expect(size9Btn).toBeDisabled();
  });

  it('marks selected size as aria-pressed true', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    const size8Btn = screen.getByRole('button', { name: /^size 8$/i });
    fireEvent.click(size8Btn);

    await waitFor(() => {
      expect(size8Btn).toHaveAttribute('aria-pressed', 'true');
    });
  });

  // ── Color picker ──────────────────────────────────────────────────────────────

  it('renders a color picker with available colors', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    const colorGroup = screen.getByRole('group', { name: /select a color/i });
    expect(colorGroup).toBeInTheDocument();
  });

  it('renders black and brown as color options', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    expect(screen.getByRole('button', { name: /color: black/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /color: brown/i })).toBeInTheDocument();
  });

  it('marks selected color as aria-pressed true', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    const brownBtn = screen.getByRole('button', { name: /color: brown/i });
    fireEvent.click(brownBtn);

    await waitFor(() => {
      expect(brownBtn).toHaveAttribute('aria-pressed', 'true');
    });
  });

  // ── Quantity selector ─────────────────────────────────────────────────────────

  it('renders quantity increase and decrease buttons', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    expect(screen.getByRole('button', { name: /increase quantity/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /decrease quantity/i })).toBeInTheDocument();
  });

  it('decrements quantity but not below 1', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    const decrementBtn = screen.getByRole('button', { name: /decrease quantity/i });
    expect(decrementBtn).toBeDisabled(); // already at 1
  });

  it('increments quantity when plus button is clicked', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    const incrementBtn = screen.getByRole('button', { name: /increase quantity/i });
    fireEvent.click(incrementBtn);

    await waitFor(() => {
      const spinbutton = screen.getByRole('spinbutton');
      expect(spinbutton).toHaveTextContent('2');
    });
  });

  // ── Add to cart ───────────────────────────────────────────────────────────────

  it('renders the Add to Cart button', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    expect(screen.getByRole('button', { name: /add to cart/i })).toBeInTheDocument();
  });

  it('calls addCartItem when a variant is selected and Add to Cart is clicked', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    // Select size 8 and color black
    fireEvent.click(screen.getByRole('button', { name: /^size 8$/i }));
    fireEvent.click(screen.getByRole('button', { name: /color: black/i }));

    fireEvent.click(screen.getByRole('button', { name: /add to cart/i }));

    await waitFor(() => {
      expect(mockAddCartItem).toHaveBeenCalledWith('var-1', 1);
    });
  });

  it('shows a success confirmation after adding to cart', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    fireEvent.click(screen.getByRole('button', { name: /^size 8$/i }));
    fireEvent.click(screen.getByRole('button', { name: /color: black/i }));
    fireEvent.click(screen.getByRole('button', { name: /add to cart/i }));

    await waitFor(() => {
      expect(screen.getByText(/item added to cart/i)).toBeInTheDocument();
    });
  });

  it('shows an error if add to cart API fails', async () => {
    mockAddCartItem.mockRejectedValueOnce(new Error('Out of stock'));
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    fireEvent.click(screen.getByRole('button', { name: /^size 8$/i }));
    fireEvent.click(screen.getByRole('button', { name: /color: black/i }));
    fireEvent.click(screen.getByRole('button', { name: /add to cart/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('does not call addCartItem when unauthenticated user clicks Add to Cart', async () => {
    mockUseAuth.mockReturnValue({ user: null });
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    fireEvent.click(screen.getByRole('button', { name: /add to cart/i }));

    // Unauthenticated path calls navigate('/login') — addCartItem should NOT be called
    await waitFor(() => {
      expect(mockAddCartItem).not.toHaveBeenCalled();
    });
  });

  // ── Reviews section ───────────────────────────────────────────────────────────

  it('renders the customer reviews section', async () => {
    renderPage();
    expect(
      await screen.findByRole('heading', { name: /customer reviews/i })
    ).toBeInTheDocument();
  });

  it('displays existing reviews', async () => {
    renderPage();
    expect(await screen.findByText('Very comfortable and well-made.')).toBeInTheDocument();
  });

  it('shows reviewer name', async () => {
    renderPage();
    expect(await screen.findByText('Jane Doe')).toBeInTheDocument();
  });

  it('renders the write a review form for authenticated users', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });
    expect(await screen.findByRole('heading', { name: /write a review/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit review/i })).toBeInTheDocument();
  });

  it('shows a sign-in prompt for unauthenticated users in the review section', async () => {
    mockUseAuth.mockReturnValue({ user: null });
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    expect(await screen.findByText(/sign in/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /submit review/i })).not.toBeInTheDocument();
  });

  // ── Ratings summary ───────────────────────────────────────────────────────────

  it('renders the rating summary stars when reviews exist', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 1 });

    // avgRating should show (we use product.average_rating or computed avg)
    await waitFor(() => {
      expect(screen.getByText(/4\.0/)).toBeInTheDocument();
    });
  });

  // ── Sale price ────────────────────────────────────────────────────────────────

  it('shows sale price and SALE badge when product is on sale', async () => {
    const saleProduct = { ...MOCK_PRODUCT, base_price: 120, sale_price: 90 };
    mockGetProduct.mockResolvedValueOnce(saleProduct);

    renderPage();
    await screen.findByRole('heading', { level: 1 });

    expect(screen.getByText(/£90\.00/)).toBeInTheDocument();
    expect(screen.getByText(/£120\.00/)).toBeInTheDocument(); // strikethrough
    expect(screen.getByText('SALE')).toBeInTheDocument();
  });

  // ── No variants ───────────────────────────────────────────────────────────────

  it('renders without size/color pickers when product has no variants', async () => {
    const noVariantProduct = { ...MOCK_PRODUCT, variants: [] };
    mockGetProduct.mockResolvedValueOnce(noVariantProduct);

    renderPage();
    await screen.findByRole('heading', { level: 1 });

    expect(screen.queryByRole('group', { name: /select a size/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('group', { name: /select a color/i })).not.toBeInTheDocument();
  });

  // ── Product with no images ────────────────────────────────────────────────────

  it('renders a fallback when there are no images', async () => {
    const noImgProduct = { ...MOCK_PRODUCT, images: [], image_url: null };
    mockGetProduct.mockResolvedValueOnce(noImgProduct);

    renderPage();
    await screen.findByRole('heading', { level: 1 });

    expect(screen.getByRole('img', { name: /no image available/i })).toBeInTheDocument();
  });
});
