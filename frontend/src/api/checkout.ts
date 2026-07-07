/**
 * Checkout API client — T-030 / US-011
 *
 * Implements the two-phase checkout flow:
 *   1. POST /api/v1/checkout/payment-intent — creates a Stripe PaymentIntent
 *      server-side; returns the client_secret for Stripe Elements.
 *   2. POST /api/v1/checkout/confirm — verifies payment, creates the order
 *      record, clears the cart, and triggers the confirmation email.
 *
 * PCI compliance (ADR-003): card data never touches application servers.
 * The frontend confirms the payment directly with Stripe using the
 * client_secret; only the resulting payment_intent_id goes to our backend.
 */

import { apiClient } from './client';

// ── Shipping address ──────────────────────────────────────────────────────────

export interface ShippingAddress {
  line1: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

// ── Payment-intent ────────────────────────────────────────────────────────────

export interface CreatePaymentIntentRequest {
  shipping_name: string;
  shipping_address: ShippingAddress;
  /** Required when the customer is not authenticated. */
  guest_email?: string;
}

export interface CreatePaymentIntentResponse {
  client_secret: string;
  payment_intent_id: string;
  amount: number;
  currency: string;
}

export async function createPaymentIntent(
  data: CreatePaymentIntentRequest
): Promise<CreatePaymentIntentResponse> {
  const response = await apiClient.post<CreatePaymentIntentResponse>(
    '/api/v1/checkout/payment-intent',
    data
  );
  return response.data;
}

// ── Confirm order ─────────────────────────────────────────────────────────────

export interface ConfirmOrderRequest {
  payment_intent_id: string;
}

export interface ConfirmOrderResponseItem {
  product_name: string;
  color: string;
  size: string;
  quantity: number;
  unit_price: number;
}

export interface ConfirmOrderResponse {
  order_id: string;
  order_number: string;
  total_amount: number;
  shipping_address: {
    line1: string;
    city: string;
    state: string;
    postal_code: string;
  };
  items: ConfirmOrderResponseItem[];
}

export async function confirmOrder(
  data: ConfirmOrderRequest
): Promise<ConfirmOrderResponse> {
  const response = await apiClient.post<ConfirmOrderResponse>(
    '/api/v1/checkout/confirm',
    data
  );
  return response.data;
}
