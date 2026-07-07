import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SearchResultsPage } from './SearchResultsPage';
import type { Product } from '../types/index';

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockSearchProducts = vi.fn();

vi.mock('../api/products', () => ({
  searchProducts: (...args: unknown[]) => mockSearchProducts(...args),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_PRODUCT: Product = {
  id: 'prod-1',
  name: 'Hiking Leather Boot',
  slug: 'hiking-leather-boot',
  description: 'A robust hiking boot',
  category_id: 'cat-1',
  brand: 'TrailMaster',
  base_price: 150,
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

const MOCK_PAGINATED_ONE = {
  items: [MOCK_PRODUCT],
  total: 1,
  page: 1,
  page_size: 12,
  total_pages: 1,
};

const MOCK_PAGINATED_EMPTY = {
  items: [],
  total: 0,
  page: 1,
  page_size: 12,
  total_pages: 1,
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

interface RenderOptions {
  initialUrl?: string;
}

const renderPage = (opts: RenderOptions = {}) => {
  const qc = createQueryClient();
  const url = opts.initialUrl ?? '/search?q=hiking';
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <SearchResultsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('SearchResultsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchProducts.mockResolvedValue(MOCK_PAGINATED_ONE);
  });

  // ── Heading ──────────────────────────────────────────────────────────────────

  it('renders the search results heading with the query term', async () => {
    renderPage();
    expect(
      await screen.findByRole('heading', { level: 1, name: /search results for "hiking"/i })
    ).toBeInTheDocument();
  });

  it('calls searchProducts with the query from the URL', async () => {
    renderPage({ initialUrl: '/search?q=chelsea' });
    await waitFor(() => {
      expect(mockSearchProducts).toHaveBeenCalledWith(
        expect.objectContaining({ q: 'chelsea' })
      );
    });
  });

  // ── Empty query state ─────────────────────────────────────────────────────

  it('shows a prompt to enter a keyword when no query is provided', () => {
    renderPage({ initialUrl: '/search' });
    expect(screen.getByText(/enter a keyword to start searching/i)).toBeInTheDocument();
  });

  it('does not call searchProducts when query is empty', () => {
    renderPage({ initialUrl: '/search' });
    expect(mockSearchProducts).not.toHaveBeenCalled();
  });

  // ── Loading state ─────────────────────────────────────────────────────────

  it('shows a loading skeleton while results are fetching', () => {
    mockSearchProducts.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByLabelText(/loading products/i)).toBeInTheDocument();
  });

  // ── Error state ───────────────────────────────────────────────────────────

  it('shows an error alert when the search request fails', async () => {
    mockSearchProducts.mockRejectedValueOnce(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(
        screen.getByText(/something went wrong, please try again/i)
      ).toBeInTheDocument();
    });
  });

  // ── Empty results ─────────────────────────────────────────────────────────

  it('shows "No results found" when the search returns no products', async () => {
    mockSearchProducts.mockResolvedValueOnce(MOCK_PAGINATED_EMPTY);
    renderPage({ initialUrl: '/search?q=xyzxyz' });
    await waitFor(() => {
      const matches = screen.getAllByText(/no results found for your search/i);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  // ── Product grid ──────────────────────────────────────────────────────────

  it('renders product cards after data loads', async () => {
    renderPage();
    expect(await screen.findByText('Hiking Leather Boot')).toBeInTheDocument();
  });

  it('each product card displays the brand', async () => {
    renderPage();
    expect(await screen.findByText('TrailMaster')).toBeInTheDocument();
  });

  it('each product card displays the price', async () => {
    renderPage();
    expect(await screen.findByText(/£150\.00/)).toBeInTheDocument();
  });

  it('product card links to the product detail page', async () => {
    renderPage();
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /view hiking leather boot/i });
      expect(link).toHaveAttribute('href', '/products/prod-1');
    });
  });

  // ── Result count ──────────────────────────────────────────────────────────

  it('shows the result count when results are present', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/1 result for "hiking"/i)).toBeInTheDocument();
    });
  });

  // ── Search form ───────────────────────────────────────────────────────────

  it('renders a search form with an accessible role', () => {
    renderPage();
    expect(screen.getByRole('search', { name: /search products/i })).toBeInTheDocument();
  });

  it('prefills the search input with the current query', () => {
    renderPage({ initialUrl: '/search?q=chelsea' });
    const input = screen.getByRole('searchbox') as HTMLInputElement;
    expect(input.value).toBe('chelsea');
  });

  it('renders a clear button', () => {
    renderPage();
    expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument();
  });

  // ── Pagination ────────────────────────────────────────────────────────────

  it('does not render pagination when there is only one page', async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.queryByRole('navigation', { name: /search results pagination/i })
      ).not.toBeInTheDocument();
    });
  });

  it('renders pagination when there are multiple pages', async () => {
    mockSearchProducts.mockResolvedValueOnce({
      items: [MOCK_PRODUCT],
      total: 30,
      page: 1,
      page_size: 12,
      total_pages: 3,
    });
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByRole('navigation', { name: /search results pagination/i })
      ).toBeInTheDocument();
    });
  });

  it('previous page button is disabled on page 1', async () => {
    mockSearchProducts.mockResolvedValueOnce({
      items: [MOCK_PRODUCT],
      total: 30,
      page: 1,
      page_size: 12,
      total_pages: 3,
    });
    renderPage();
    await waitFor(() => {
      const prevBtn = screen.getByRole('button', { name: /previous page/i });
      expect(prevBtn).toBeDisabled();
    });
  });

  it('next page button is disabled on the last page', async () => {
    mockSearchProducts.mockResolvedValueOnce({
      items: [MOCK_PRODUCT],
      total: 30,
      page: 3,
      page_size: 12,
      total_pages: 3,
    });
    renderPage({ initialUrl: '/search?q=hiking&page=3' });
    await waitFor(() => {
      const nextBtn = screen.getByRole('button', { name: /next page/i });
      expect(nextBtn).toBeDisabled();
    });
  });

  // ── Search form submission ────────────────────────────────────────────────

  it('re-executes search when the form is submitted with a new term', async () => {
    renderPage();
    // Wait for initial load
    await screen.findByText('Hiking Leather Boot');

    mockSearchProducts.mockResolvedValueOnce({
      ...MOCK_PAGINATED_ONE,
      items: [{ ...MOCK_PRODUCT, name: 'Work Steel-Toe Boot' }],
    });

    const input = screen.getByRole('searchbox') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'work boots' } });

    const form = screen.getByRole('search', { name: /search products/i });
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockSearchProducts).toHaveBeenCalledWith(
        expect.objectContaining({ q: 'work boots' })
      );
    });
  });
});
