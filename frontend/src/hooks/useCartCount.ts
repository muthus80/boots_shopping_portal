import { useQuery } from '@tanstack/react-query';
import { getCart } from '../api/cart';
import type { Cart } from '../types/index';

/**
 * Returns the total number of items (sum of quantities) in the current cart.
 * Returns 0 when the cart is empty, loading, or the request fails.
 *
 * The query key matches the one used by ProductDetailPage's addToCart mutation
 * (`queryClient.invalidateQueries({ queryKey: ['cart'] })`), so the badge
 * automatically refreshes after every successful add-to-cart action.
 */
export function useCartCount(): number {
  const { data } = useQuery<Cart>({
    queryKey: ['cart'],
    queryFn: getCart,
    staleTime: 1000 * 60, // 1 minute — cart is invalidated by mutations anyway
  });

  if (!data?.items) return 0;
  return data.items.reduce((sum, item) => sum + item.quantity, 0);
}
