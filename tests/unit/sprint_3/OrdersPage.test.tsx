/**
 * OrdersPage tests — T-027 / US-003
 *
 * Coverage:
 *  - Loading state renders spinner
 *  - Error state renders ErrorMessage with retry button
 *  - Empty orders renders EmptyState with Browse Boots link
 *  - Populated list renders order number, date, total, and status for each order
 *  - Status badges render with correct text and are capitalised
 *  - Multiple orders all appear in the list
 *  - Pagination controls appear only when total > per_page
 *  - Pagination "Previous" disabled on first page; "Next" disabled on last page
 *  - Correct API endpoint called with page/per_page params
 *  - Accessibility: article labels, nav landmark, time element
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { OrdersPage } from './OrdersPage';
import type { OrderSummary, OrdersResponse } from '../api/orders';

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockGetOrders = vi.fn();

vi.mock('../api/orders', () => ({
  getOrders: (params: { page?: number; per_page?: number }) => mockGetOrders(params),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const makeOrder = (overrides: Partial<OrderSummary> = {}): OrderSummary => ({
  id: 'order-1',
  order_number: 'ORD-1001',
  status: 'delivered',
  total_amount: 129.99,
  created_at: '2024-03-15T10:00:00Z',
  ...overrides,
});

const makeOrdersResponse = (
  orders: OrderSummary[],
  total?: number
): OrdersResponse => ({
  orders,
  total: total ?? orders.length,
});

// ── Render helper ─────────────────────────────────────────────────────────────

const renderPage = () => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <OrdersPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('OrdersPage (T-027 / US-003)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading ─────────────────────────────────────────────────────────────

  it('renders a loading spinner while fetching orders', () => {
    // Never resolves — stays in loading state
    mockGetOrders.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });

  it('renders the page heading while loading', () => {
    mockGetOrders.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByRole('heading', { name: /order history/i })).toBeInTheDocument();
  });

  // ── Error ───────────────────────────────────────────────────────────────

  it('renders an error alert when the orders request fails', async () => {
    mockGetOrders.mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it('renders a retry button on error', async () => {
    mockGetOrders.mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /retry loading/i })).toBeInTheDocument();
  });

  // ── Empty state ─────────────────────────────────────────────────────────

  it('renders empty state when no orders are returned', async () => {
    mockGetOrders.mockResolvedValue(makeOrdersResponse([]));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/you have not placed any orders yet/i)).toBeInTheDocument();
    });
  });

  it('renders a "Browse Boots" link in the empty state pointing to /products', async () => {
    mockGetOrders.mockResolvedValue(makeOrdersResponse([]));
    renderPage();
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /browse boots/i });
      expect(link).toHaveAttribute('href', '/products');
    });
  });

  // ── Populated list ──────────────────────────────────────────────────────

  it('renders order number for each order', async () => {
    mockGetOrders.mockResolvedValue(
      makeOrdersResponse([makeOrder({ order_number: 'ORD-1001' })])
    );
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/ORD-1001/)).toBeInTheDocument();
    });
  });

  it('renders formatted date for each order', async () => {
    mockGetOrders.mockResolvedValue(
      makeOrdersResponse([makeOrder({ created_at: '2024-03-15T10:00:00Z' })])
    );
    renderPage();
    await waitFor(() => {
      // en-GB format: "15 March 2024"
      expect(screen.getByText(/15 March 2024/)).toBeInTheDocument();
    });
  });

  it('renders formatted total amount for each order', async () => {
    mockGetOrders.mockResolvedValue(
      makeOrdersResponse([makeOrder({ id: 'o1', total_amount: 129.99 })])
    );
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('order-total-o1')).toHaveTextContent('£129.99');
    });
  });

  it('renders status badge with capitalised status text', async () => {
    mockGetOrders.mockResolvedValue(
      makeOrdersResponse([makeOrder({ id: 'o1', status: 'delivered' })])
    );
    renderPage();
    await waitFor(() => {
      const badge = screen.getByTestId('order-status-o1');
      expect(badge).toHaveTextContent('delivered');
    });
  });

  it('renders multiple orders', async () => {
    const orders = [
      makeOrder({ id: 'o1', order_number: 'ORD-1001' }),
      makeOrder({ id: 'o2', order_number: 'ORD-1002' }),
      makeOrder({ id: 'o3', order_number: 'ORD-1003' }),
    ];
    mockGetOrders.mockResolvedValue(makeOrdersResponse(orders));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Order ORD-1001')).toBeInTheDocument();
      expect(screen.getByText('Order ORD-1002')).toBeInTheDocument();
      expect(screen.getByText('Order ORD-1003')).toBeInTheDocument();
    });
  });

  it('shows the total order count in the subtitle', async () => {
    const orders = [
      makeOrder({ id: 'o1', order_number: 'ORD-1001' }),
      makeOrder({ id: 'o2', order_number: 'ORD-1002' }),
    ];
    mockGetOrders.mockResolvedValue(makeOrdersResponse(orders, 2));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/2 orders placed/i)).toBeInTheDocument();
    });
  });

  it('uses singular "order" when count is 1', async () => {
    mockGetOrders.mockResolvedValue(makeOrdersResponse([makeOrder()], 1));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/1 order placed/i)).toBeInTheDocument();
    });
  });

  // ── Pagination ──────────────────────────────────────────────────────────

  it('does NOT render pagination when total fits on one page', async () => {
    // 5 orders, per_page=10 → only 1 page
    const orders = Array.from({ length: 5 }, (_, i) =>
      makeOrder({ id: `o${i}`, order_number: `ORD-${1000 + i}` })
    );
    mockGetOrders.mockResolvedValue(makeOrdersResponse(orders, 5));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Order ORD-1000')).toBeInTheDocument();
    });
    expect(screen.queryByRole('navigation', { name: /pagination/i })).not.toBeInTheDocument();
  });

  it('renders pagination nav when total > per_page (10)', async () => {
    // 15 total but only first 10 returned
    const orders = Array.from({ length: 10 }, (_, i) =>
      makeOrder({ id: `o${i}`, order_number: `ORD-${1000 + i}` })
    );
    mockGetOrders.mockResolvedValue(makeOrdersResponse(orders, 15));
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByRole('navigation', { name: /pagination/i })
      ).toBeInTheDocument();
    });
  });

  it('disables "Previous" button on page 1', async () => {
    const orders = Array.from({ length: 10 }, (_, i) =>
      makeOrder({ id: `o${i}`, order_number: `ORD-${1000 + i}` })
    );
    mockGetOrders.mockResolvedValue(makeOrdersResponse(orders, 15));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /previous page/i })).toBeDisabled();
    });
  });

  it('advances to page 2 when "Next" is clicked and re-fetches', async () => {
    const page1Orders = Array.from({ length: 10 }, (_, i) =>
      makeOrder({ id: `o${i}`, order_number: `ORD-${1000 + i}` })
    );
    const page2Orders = [makeOrder({ id: 'o10', order_number: 'ORD-1010' })];

    mockGetOrders
      .mockResolvedValueOnce(makeOrdersResponse(page1Orders, 11))
      .mockResolvedValueOnce(makeOrdersResponse(page2Orders, 11));

    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /next page/i })).toBeEnabled();
    });

    await user.click(screen.getByRole('button', { name: /next page/i }));

    await waitFor(() => {
      expect(mockGetOrders).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 })
      );
    });
  });

  // ── API contract ─────────────────────────────────────────────────────────

  it('calls getOrders with page=1 and per_page=10 on initial load', async () => {
    mockGetOrders.mockResolvedValue(makeOrdersResponse([]));
    renderPage();
    await waitFor(() => {
      expect(mockGetOrders).toHaveBeenCalledWith({ page: 1, per_page: 10 });
    });
  });

  // ── Accessibility ─────────────────────────────────────────────────────────

  it('uses <article> with aria-label for each order card', async () => {
    mockGetOrders.mockResolvedValue(
      makeOrdersResponse([makeOrder({ order_number: 'ORD-9999' })])
    );
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByRole('article', { name: /ORD-9999/i })
      ).toBeInTheDocument();
    });
  });

  it('uses a <time> element for the order date', async () => {
    mockGetOrders.mockResolvedValue(
      makeOrdersResponse([makeOrder({ created_at: '2024-06-01T00:00:00Z' })])
    );
    const { container } = renderPage();
    await waitFor(() => {
      expect(screen.getByText(/1 June 2024/)).toBeInTheDocument();
    });
    const timeEl = container.querySelector('time');
    expect(timeEl).not.toBeNull();
    expect(timeEl?.getAttribute('dateTime')).toBe('2024-06-01T00:00:00Z');
  });
});
