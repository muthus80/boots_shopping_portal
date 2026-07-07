/**
 * CartPage — T-024 / US-010
 *
 * Displays all cart items with their price, quantity controls, and per-item
 * subtotal.  Quantity changes and removals are committed immediately via React
 * Query mutations, and the order summary recalculates optimistically.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCart, updateCartItem, removeCartItem } from '../api/cart';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { EmptyState } from '../components/common/EmptyState';
import type { CartItem } from '../types/index';

// ── Helpers ───────────────────────────────────────────────────────────────────

const formatPrice = (amount: number): string =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount);

// ── CartItemRow ───────────────────────────────────────────────────────────────

interface CartItemRowProps {
  item: CartItem;
  isUpdating: boolean;
  onQuantityChange: (item: CartItem, newQty: number) => void;
  onRemove: (itemId: string) => void;
}

const CartItemRow: React.FC<CartItemRowProps> = ({
  item,
  isUpdating,
  onQuantityChange,
  onRemove,
}) => {
  const unitPrice = item.unit_price ?? 0;
  const lineTotal = unitPrice * item.quantity;
  const productName = item.product?.name ?? item.product_id;

  return (
    <li
      className={`flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white p-4 transition-opacity ${
        isUpdating ? 'opacity-50' : 'opacity-100'
      }`}
      aria-busy={isUpdating}
    >
      {/* Product image */}
      {item.product?.image_url ? (
        <img
          src={item.product.image_url}
          alt={productName}
          className="h-20 w-20 flex-shrink-0 rounded-lg object-cover"
        />
      ) : (
        <div
          className="flex h-20 w-20 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100"
          aria-hidden="true"
        >
          <span className="text-3xl">👢</span>
        </div>
      )}

      {/* Item details */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-gray-900">{productName}</p>
        {item.variant && (
          <p className="mt-0.5 text-xs text-gray-500">
            {item.variant.size && <span>Size: {item.variant.size}</span>}
            {item.variant.size && item.variant.color && <span className="mx-1">·</span>}
            {item.variant.color && <span>Colour: {item.variant.color}</span>}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-500">{formatPrice(unitPrice)} each</p>
      </div>

      {/* Quantity stepper */}
      <div className="flex items-center gap-2" role="group" aria-label={`Quantity for ${productName}`}>
        <button
          type="button"
          onClick={() => onQuantityChange(item, item.quantity - 1)}
          disabled={isUpdating || item.quantity <= 1}
          aria-label={`Decrease quantity of ${productName}`}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-gray-300 bg-gray-50 text-lg font-semibold text-gray-700 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-gray-900"
        >
          −
        </button>
        <span
          className="min-w-[2rem] text-center text-sm font-semibold text-gray-900"
          aria-live="polite"
          aria-label={`Quantity: ${item.quantity}`}
        >
          {item.quantity}
        </span>
        <button
          type="button"
          onClick={() => onQuantityChange(item, item.quantity + 1)}
          disabled={isUpdating}
          aria-label={`Increase quantity of ${productName}`}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-gray-300 bg-gray-50 text-lg font-semibold text-gray-700 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-gray-900"
        >
          +
        </button>
      </div>

      {/* Line total */}
      <p className="min-w-[4.5rem] text-right text-sm font-semibold text-gray-900">
        {formatPrice(lineTotal)}
      </p>

      {/* Remove button */}
      <button
        type="button"
        onClick={() => onRemove(item.id)}
        disabled={isUpdating}
        aria-label={`Remove ${productName} from cart`}
        className="rounded-md border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-red-400"
      >
        Remove
      </button>
    </li>
  );
};

// ── CartPage ──────────────────────────────────────────────────────────────────

export const CartPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ── Data fetching ─────────────────────────────────────────────────────────

  const {
    data: cart,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
  });

  // ── Mutations ─────────────────────────────────────────────────────────────

  const { mutate: changeQty, isPending: isChangingQty, variables: changingVars } = useMutation({
    mutationFn: ({ itemId, quantity }: { itemId: string; quantity: number }) =>
      updateCartItem(itemId, quantity),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });

  const { mutate: removeItem, isPending: isRemoving, variables: removingVars } = useMutation({
    mutationFn: (itemId: string) => removeCartItem(itemId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });

  // ── Event handlers ────────────────────────────────────────────────────────

  const handleQuantityChange = (item: CartItem, newQty: number): void => {
    if (newQty < 1) return;
    changeQty({ itemId: item.id, quantity: newQty });
  };

  const handleRemove = (itemId: string): void => {
    removeItem(itemId);
  };

  const isItemUpdating = (itemId: string): boolean =>
    (isChangingQty && changingVars?.itemId === itemId) ||
    (isRemoving && removingVars === itemId);

  // ── Derived values ────────────────────────────────────────────────────────

  const items = cart?.items ?? [];
  const subtotal = items.reduce(
    (sum, item) => sum + (item.unit_price ?? 0) * item.quantity,
    0
  );
  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);

  // ── Render states ─────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="mb-8 text-3xl font-bold tracking-tight text-gray-900">Your Cart</h1>
        <LoadingSpinner size="lg" label="Loading your cart…" centered />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="mb-8 text-3xl font-bold tracking-tight text-gray-900">Your Cart</h1>
        <ErrorMessage
          heading="Something went wrong, please try again"
          detail="We couldn't load your cart. Please check your connection and try again."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <h1 className="mb-8 text-3xl font-bold tracking-tight text-gray-900">Your Cart</h1>
        <EmptyState
          icon={<span aria-hidden="true">🛒</span>}
          heading="Your cart is empty"
          description="Looks like you haven't added any boots yet."
          action={
            <Link
              to="/products"
              className="inline-block rounded-lg bg-gray-900 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
            >
              Continue Shopping
            </Link>
          }
        />
      </div>
    );
  }

  // ── Full cart view ────────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="mb-8 text-3xl font-bold tracking-tight text-gray-900">Your Cart</h1>

      <div className="flex flex-col gap-8 lg:flex-row lg:items-start">
        {/* Items list */}
        <section aria-label="Cart items" className="flex-1">
          <ul className="flex flex-col gap-4 list-none p-0 m-0">
            {items.map((item) => (
              <CartItemRow
                key={item.id}
                item={item}
                isUpdating={isItemUpdating(item.id)}
                onQuantityChange={handleQuantityChange}
                onRemove={handleRemove}
              />
            ))}
          </ul>

          <div className="mt-6">
            <Link
              to="/products"
              className="text-sm font-medium text-gray-600 underline-offset-2 hover:text-gray-900 hover:underline focus:outline-none focus:ring-2 focus:ring-gray-900 rounded"
            >
              ← Continue Shopping
            </Link>
          </div>
        </section>

        {/* Order summary */}
        <aside
          aria-label="Order summary"
          className="w-full rounded-xl border border-gray-200 bg-gray-50 p-6 lg:w-80 lg:flex-shrink-0"
        >
          <h2 className="mb-4 text-xl font-bold text-gray-900">Order Summary</h2>

          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-600">
                Subtotal ({totalItems} {totalItems === 1 ? 'item' : 'items'})
              </dt>
              <dd className="font-semibold text-gray-900" data-testid="cart-subtotal">
                {formatPrice(subtotal)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">Shipping</dt>
              <dd className="text-gray-500">Calculated at checkout</dd>
            </div>
            <div className="flex justify-between border-t border-gray-200 pt-3">
              <dt className="text-base font-bold text-gray-900">Total</dt>
              <dd className="text-base font-bold text-gray-900">{formatPrice(subtotal)}</dd>
            </div>
          </dl>

          <Link
            to="/checkout"
            className="mt-6 flex w-full items-center justify-center rounded-lg bg-gray-900 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
            aria-label="Proceed to checkout"
          >
            Proceed to Checkout
          </Link>
        </aside>
      </div>
    </div>
  );
};

export default CartPage;
