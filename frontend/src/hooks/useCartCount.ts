import { useQuery } from '@tanstack/react-query';
import { getCart } from '../api/cart';
import { useAuth } from '../stores/authStore';
import type { Cart } from '../types/index';

/**
 * Returns the total number of items (sum of quantities) in the current cart.
 * Returns 0 when the cart is empty, loading, or the request fails.
 *
 * The query is disabled for unauthenticated users. Without this guard,
 * the GET /api/v1/cart request on a public page (e.g. /register) returns a
 * 401, and the Axios interceptor — finding no refresh token — calls
 * authFailureHandler() which redirects the user to /login before they can
 * interact with the page.
 *
 * The query key matches the one used by ProductDetailPage's addToCart mutation
 * (`queryClient.invalidateQueries({ queryKey: ['cart'] })`), so the badge
 * automatically refreshes after every successful add-to-cart action.
 */
export function useCartCount(): number {
  const { isAuthenticated } = useAuth();
  const { data } = useQuery<Cart>({
    queryKey: ['cart'],
    queryFn: getCart,
    staleTime: 1000 * 60, // 1 minute — cart is invalidated by mutations anyway
    enabled: isAuthenticated,
  });

  if (!data?.items) return 0;
  return data.items.reduce((sum, item) => sum + item.quantity, 0);
}
