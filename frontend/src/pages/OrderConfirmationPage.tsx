/**
 * OrderConfirmationPage — T-032 / US-011
 *
 * Standalone order confirmation page rendered after a successful checkout.
 * The previous page (CheckoutPage) navigates here via React Router `state`,
 * passing the ConfirmOrderResponse as `location.state.order`.
 *
 * If the page is accessed without state (e.g. direct URL navigation), the user
 * is redirected to the home page to avoid a blank/broken confirmation view.
 *
 * Route: /order-confirmation (accessible to guests and authenticated users)
 *
 * Displays:
 *   - Success icon and "Order Confirmed!" heading
 *   - Order number
 *   - Line items with pricing breakdown
 *   - Shipping address
 *   - Order total
 *   - CTA links: Continue Shopping / View Order History (auth only)
 */

import React from 'react';
import { Link, useLocation, Navigate } from 'react-router-dom';
import type { ConfirmOrderResponse } from '../api/checkout';
import { useAuth } from '../stores/authStore';

// ── Helpers ───────────────────────────────────────────────────────────────────

const formatCurrency = (amount: number): string =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount);

// ── LocationState type ────────────────────────────────────────────────────────

interface OrderConfirmationLocationState {
  order: ConfirmOrderResponse;
}

function isOrderLocationState(state: unknown): state is OrderConfirmationLocationState {
  return (
    state !== null &&
    typeof state === 'object' &&
    'order' in (state as Record<string, unknown>) &&
    typeof (state as Record<string, unknown>).order === 'object'
  );
}

// ── OrderConfirmationPage ─────────────────────────────────────────────────────

export const OrderConfirmationPage: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  // Guard: redirect if page was accessed without order state
  if (!isOrderLocationState(location.state)) {
    return <Navigate to="/" replace />;
  }

  const order = location.state.order;

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6 lg:px-8">
      {/* ── Success icon ─────────────────────────────────────────────────── */}
      <div
        className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-green-100"
        aria-hidden="true"
      >
        <svg
          className="h-10 w-10 text-green-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>

      {/* ── Heading ──────────────────────────────────────────────────────── */}
      <div className="mb-8 text-center">
        <h1
          className="mb-2 text-3xl font-bold tracking-tight text-gray-900"
          aria-live="polite"
        >
          Order Confirmed!
        </h1>
        <p className="mb-1 text-sm text-gray-600">
          Thank you for your purchase. A confirmation email is on its way to you.
        </p>
        <p className="text-sm font-semibold text-gray-700">
          Order{' '}
          <span data-testid="order-number">#{order.order_number}</span>
        </p>
      </div>

      {/* ── Items ordered ────────────────────────────────────────────────── */}
      {order.items.length > 0 && (
        <section
          aria-labelledby="items-heading"
          className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
        >
          <h2
            id="items-heading"
            className="mb-4 text-base font-bold text-gray-900"
          >
            Items ordered
          </h2>

          <ul className="space-y-3" role="list">
            {order.items.map((item, index) => (
              <li
                key={index}
                className="flex items-start justify-between gap-4 text-sm"
              >
                <span className="text-gray-700">
                  <span className="font-medium text-gray-900">{item.product_name}</span>
                  {item.size && (
                    <span className="ml-1.5 text-gray-500">
                      / {item.size}
                    </span>
                  )}
                  {item.color && (
                    <span className="ml-1.5 text-gray-500">
                      / {item.color}
                    </span>
                  )}
                  <span className="ml-2 text-gray-400">
                    ×{item.quantity}
                  </span>
                </span>
                <span className="shrink-0 font-medium text-gray-900">
                  {formatCurrency(item.unit_price * item.quantity)}
                </span>
              </li>
            ))}
          </ul>

          {/* Total row */}
          <div className="mt-4 flex items-center justify-between border-t border-gray-200 pt-4">
            <span className="text-sm font-bold text-gray-900">Order total</span>
            <span
              className="text-base font-bold text-gray-900"
              data-testid="order-total"
            >
              {formatCurrency(order.total_amount)}
            </span>
          </div>
        </section>
      )}

      {/* ── Shipping address ──────────────────────────────────────────────── */}
      <section
        aria-labelledby="shipping-heading"
        className="mb-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
      >
        <h2
          id="shipping-heading"
          className="mb-3 text-base font-bold text-gray-900"
        >
          Shipping to
        </h2>
        <address className="not-italic text-sm text-gray-700 leading-relaxed">
          <p>{order.shipping_address.line1}</p>
          <p>
            {order.shipping_address.city},{' '}
            {order.shipping_address.state}{' '}
            {order.shipping_address.postal_code}
          </p>
        </address>
      </section>

      {/* ── CTA buttons ──────────────────────────────────────────────────── */}
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
        <Link
          to="/products"
          className="w-full rounded-lg bg-gray-900 px-8 py-3 text-center text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 sm:w-auto"
        >
          Continue Shopping
        </Link>

        {isAuthenticated && (
          <Link
            to="/orders"
            className="w-full rounded-lg border border-gray-300 bg-white px-8 py-3 text-center text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 sm:w-auto"
          >
            View Order History
          </Link>
        )}
      </div>
    </div>
  );
};

export default OrderConfirmationPage;
