import { apiClient } from './client';
import { Cart, CartItem } from '../types/index';

export const getCart = async (): Promise<Cart> => {
  const response = await apiClient.get<Cart>('/api/v1/cart');
  return response.data;
};

export const addCartItem = async (
  productVariantId: string,
  quantity: number
): Promise<CartItem> => {
  const response = await apiClient.post<CartItem>('/api/v1/cart/items', {
    product_variant_id: productVariantId,
    quantity,
  });
  return response.data;
};

export const updateCartItem = async (
  cartItemId: string,
  quantity: number
): Promise<CartItem> => {
  const response = await apiClient.put<CartItem>(`/api/v1/cart/items/${cartItemId}`, {
    quantity,
  });
  return response.data;
};

export const removeCartItem = async (cartItemId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/cart/items/${cartItemId}`);
};