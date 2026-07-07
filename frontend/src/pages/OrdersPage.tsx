/**
 * OrdersPage — T-027 / US-003
 *
 * Displays a paginated list of past orders for the authenticated user.
 * Each order card shows the order number, date, total price, and status.
 * Status badges align right on desktop and bottom-left on mobile.
 *
 * Route: /orders (protected — requires authentication)
 * API:   GET /api/v1/account/orders
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getOrders } from '../api/orders';
import type { OrderSummary } from '../api/orders';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { EmptyState } from '../components/common/EmptyState';

// ── Helpers ───────────────────────────────────────────────────────────────────

const formatCurrency = (amount: number): string =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount);

const formatDate = (dateStr: string): string =>
  new Intl.DateTimeFormat('en-GB', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(dateStr));

// ── Status badge colours — maps status string to Tailwind class pair ───────────

type StatusVariant =
  | 'pending'
  | 'confirmed'
  | 'processing'
  | 'shipped'
  | 'delivered'
  | 'cancelled'
  | 'refunded';

const STATUS_CLASSES: Record<StatusVariant, string> = {
  pending:    'bg-amber-100  text-amber-800',
  confirmed:  'bg-blue-100   text-blue-800',
  processing: 'bg-violet-100 text-violet-800',
  shipped:    'bg-cyan-100   text-cyan-800',
  delivered:  'bg-emerald-100 text-emerald-800',
  cancelled:  'bg-red-100    text-red-800',
  refunded:   'bg-gray-100   text-gray-700',
};

const statusClasses = (status: string): string =>
  STATUS_CLASSES[status as StatusVariant] ?? 'bg-gray-100 text-gray-700';

// ── OrderCard ─────────────────────────────────────────────────────────────────

interface OrderCardProps {
  order: OrderSummary;
}

const OrderCard: React.FC<OrderCardProps> = ({ order }) => (
  <article
    aria-label={`Order ${order.order_number}`}
    className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
  >
    {/* Desktop: single row. Mobile: stacked. */}
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      {/* Left: order number + date */}
      <div className="min-w-0">
        <p className="truncate text-base font-semibold text-gray-900">
          Order {order.order_number}
        </p>
        <p className="mt-0.5 text-sm text-gray-500">
          <time dateTime={order.created_at}>{formatDate(order.created_at)}</time>
        </p>
      </div>

      {/* Right: total + status badge */}
      <div className="flex items-center justify-between gap-4 sm:flex-col sm:items-end sm:gap-1">
        <p
          className="text-base font-bold text-gray-900"
          data-testid={`order-total-${order.id}`}
        >
          {formatCurrency(order.total_amount)}
        </p>
        <span
          className={`inline-block rounded-full px-3 py-0.5 text-xs font-semibold capitalize ${statusClasses(order.status)}`}
          data-testid={`order-status-${order.id}`}
        >
          {order.status}
        </span>
      </div>
    </div>
  </article>
);

// ── Pagination controls ───────────────────────────────────────────────────────

interface PaginationProps {
  page: number;
  totalPages: number;
  onPrev: () => void;
  onNext: () => void;
}

const Pagination: React.FC<PaginationProps> = ({ page, totalPages, onPrev, onNext }) => {
  if (totalPages <= 1) return null;

  return (
    <nav
      aria-label="Order history pagination"
      className="mt-8 flex items-center justify-center gap-4"
    >
      <button
        type="button"
        onClick={onPrev}
        disabled={page <= 1}
        aria-label="Previous page"
        className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-gray-900"
      >
        ← Previous
      </button>

      <span className="text-sm text-gray-600" aria-live="polite">
        Page {page} of {totalPages}
      </span>

      <button
        type="button"
        onClick={onNext}
        disabled={page >= totalPages}
        aria-label="Next page"
        className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-gray-900"
      >
        Next →
      </button>
    </nav>
  );
};

// ── OrdersPage ────────────────────────────────────────────────────────────────

const PER_PAGE = 10;

export const OrdersPage: React.FC = () => {
  const [page, setPage] = useState<number>(1);

  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['orders', page],
    queryFn: () => getOrders({ page, per_page: PER_PAGE }),
  });

  const orders = data?.orders ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));

  // ── Loading ──────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="mb-8 text-3xl font-bold tracking-tight text-gray-900">Order History</h1>
        <LoadingSpinner size="lg" label="Loading your orders…" centered />
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────

  if (isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="mb-8 text-3xl font-bold tracking-tight text-gray-900">Order History</h1>
        <ErrorMessage
          heading="Something went wrong, please try again"
          detail="We couldn't load your orders. Please check your connection and try again."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  // ── Empty ─────────────────────────────────────────────────────────────────

  if (orders.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="mb-8 text-3xl font-bold tracking-tight text-gray-900">Order History</h1>
        <EmptyState
          icon={<span aria-hidden="true">📦</span>}
          heading="You have not placed any orders yet."
          description="Explore our catalogue to find something you love."
          action={
            <Link
              to="/products"
              className="inline-block rounded-lg bg-gray-900 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
            >
              Browse Boots
            </Link>
          }
        />
      </div>
    );
  }

  // ── Order list ────────────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="mb-2 text-3xl font-bold tracking-tight text-gray-900">Order History</h1>
      <p className="mb-8 text-sm text-gray-500">
        {total} {total === 1 ? 'order' : 'orders'} placed
      </p>

      <section aria-label="Orders list">
        <ul className="flex flex-col gap-4 list-none p-0 m-0" role="list">
          {orders.map((order: OrderSummary) => (
            <li key={order.id}>
              <OrderCard order={order} />
            </li>
          ))}
        </ul>
      </section>

      <Pagination
        page={page}
        totalPages={totalPages}
        onPrev={() => setPage((p) => Math.max(1, p - 1))}
        onNext={() => setPage((p) => Math.min(totalPages, p + 1))}
      />
    </div>
  );
};

export default OrdersPage;
