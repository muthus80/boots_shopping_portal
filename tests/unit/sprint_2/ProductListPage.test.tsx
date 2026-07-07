import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProductListPage } from './ProductListPage';
import type { Product, Category } from '../types/index';

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockGetProducts = vi.fn();
const mockGetCategories = vi.fn();

vi.mock('../api/products', () => ({
  getProducts: (...args: unknown[]) => mockGetProducts(...args),
}));

vi.mock('../api/categories', () => ({
  getCategories: () => mockGetCategories(),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_PRODUCT: Product = {
  id: 'prod-1',
  name: 'Trek Leather Boot',
  slug: 'trek-leather-boot',
  description: 'Durable hiking boot',
  category_id: 'cat-1',
  brand: 'OutdoorPro',
  base_price: 120,
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

const MOCK_CATEGORY: Category = {
  id: 'cat-1',
  name: 'Work Boots',
  slug: 'work-boots',
  description: 'Durable work boots',
  parent_id: null,
  image_url: null,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const MOCK_PAGINATED = {
  items: [MOCK_PRODUCT],
  total: 1,
  page: 1,
  page_size: 12,
  total_pages: 1,
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const createQueryClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false } } });

interface RenderOptions {
  initialUrl?: string;
}

const renderPage = (opts: RenderOptions = {}) => {
  const qc = createQueryClient();
  const url = opts.initialUrl ?? '/products';
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <ProductListPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ProductListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCategories.mockResolvedValue([MOCK_CATEGORY]);
    mockGetProducts.mockResolvedValue(MOCK_PAGINATED);
  });

  // ── Heading ──────────────────────────────────────────────────────────────────

  it('renders a default heading when no filter is active', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { level: 1, name: /all boots/i })).toBeInTheDocument();
  });

  it('renders a search results heading when search param is present', async () => {
    renderPage({ initialUrl: '/products?search=hiking' });
    expect(
      await screen.findByRole('heading', { level: 1, name: /search results for "hiking"/i })
    ).toBeInTheDocument();
  });

  // ── Category grid ─────────────────────────────────────────────────────────────

  it('shows the category grid when no filter is active', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /shop by category/i })).toBeInTheDocument();
    });
  });

  it('hides the category grid when a category filter is active', async () => {
    renderPage({ initialUrl: '/products?category=cat-1' });
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /shop by category/i })).not.toBeInTheDocument();
    });
  });

  it('hides the category grid when a search filter is active', async () => {
    renderPage({ initialUrl: '/products?search=leather' });
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /shop by category/i })).not.toBeInTheDocument();
    });
  });

  // ── Category links ────────────────────────────────────────────────────────────

  it('renders category cards with accessible labels', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /browse work boots/i })).toBeInTheDocument();
    });
  });

  // ── Product grid ──────────────────────────────────────────────────────────────

  it('renders product cards after data loads', async () => {
    renderPage({ initialUrl: '/products?category=cat-1' });
    await waitFor(() => {
      expect(screen.getByText('Trek Leather Boot')).toBeInTheDocument();
    });
  });

  it('each product card displays brand', async () => {
    renderPage({ initialUrl: '/products?category=cat-1' });
    await waitFor(() => {
      expect(screen.getByText('OutdoorPro')).toBeInTheDocument();
    });
  });

  it('each product card displays price', async () => {
    renderPage({ initialUrl: '/products?category=cat-1' });
    await waitFor(() => {
      expect(screen.getByText(/£120\.00/)).toBeInTheDocument();
    });
  });

  it('product card links to the product detail page', async () => {
    renderPage({ initialUrl: '/products?category=cat-1' });
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /view trek leather boot/i });
      expect(link).toHaveAttribute('href', '/products/prod-1');
    });
  });

  // ── Loading state ─────────────────────────────────────────────────────────────

  it('shows a loading indicator while products are fetching', () => {
    mockGetProducts.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage({ initialUrl: '/products?category=cat-1' });
    expect(screen.getByLabelText(/loading products/i)).toBeInTheDocument();
  });

  // ── Error state ───────────────────────────────────────────────────────────────

  it('shows an error message when products fail to load', async () => {
    mockGetProducts.mockRejectedValueOnce(new Error('Network error'));
    renderPage({ initialUrl: '/products?category=cat-1' });
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(
        screen.getByText(/something went wrong, please try again/i)
      ).toBeInTheDocument();
    });
  });

  // ── Empty state ───────────────────────────────────────────────────────────────

  it('shows "No results found" message when search returns nothing', async () => {
    mockGetProducts.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 12, total_pages: 1 });
    renderPage({ initialUrl: '/products?search=xyzxyz' });
    await waitFor(() => {
      const matches = screen.getAllByText(/no results found for your search/i);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  // ── Search form ───────────────────────────────────────────────────────────────

  it('renders a search form with accessible role', () => {
    renderPage();
    expect(screen.getByRole('search', { name: /search products/i })).toBeInTheDocument();
  });
});
