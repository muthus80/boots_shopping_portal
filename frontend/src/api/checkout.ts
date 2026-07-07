import { apiClient } from './client';
import { Order } from '../types/index';

export interface CreatePaymentIntentRequest {
  cart_id: string;
}

export interface CreatePaymentIntentResponse {
  client_secret: string;
  payment_intent_id: string;
  amount: number;
  currency: string;
}

export interface ConfirmOrderRequest {
  payment_intent_id: string;
  cart_id: string;
  shipping_address: {
    full_name: string;
    address_line1: string;
    address_line2?: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
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

export async function confirmOrder(data: ConfirmOrderRequest): Promise<Order> {
  const response = await apiClient.post<Order>(
    '/api/v1/checkout/confirm',
    data
  );
  return response.data;
}