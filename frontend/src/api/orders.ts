/**
 * Orders API — T-027 / US-003
 *
 * Wraps GET /api/v1/account/orders with typed request/response shapes.
 * Requires an authenticated user (JWT access token set via setAuthToken).
 */
import { apiClient } from './client';

// ── Response types ─────────────────────────────────────────────────────────────

/** A single order summary row returned by the list endpoint. */
export interface OrderSummary {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  created_at: string;
}

/** Paginated response shape from GET /api/v1/account/orders */
export interface OrdersResponse {
  orders: OrderSummary[];
  total: number;
  /** Optional message present when orders array is empty. */
  message?: string;
}

// ── API function ───────────────────────────────────────────────────────────────

export interface GetOrdersParams {
  page?: number;
  per_page?: number;
}

export async function getOrders(params: GetOrdersParams = {}): Promise<OrdersResponse> {
  const response = await apiClient.get<OrdersResponse>('/api/v1/account/orders', {
    params: {
      page: params.page ?? 1,
      per_page: params.per_page ?? 10,
    },
  });
  return response.data;
}
