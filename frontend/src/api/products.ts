import { apiClient } from './client';
import { Product, Review } from '../types/index';

export interface GetProductsParams {
  category_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateReviewPayload {
  product_id: string;
  rating: number;
  title?: string;
  body?: string;
}

export async function getProducts(params?: GetProductsParams): Promise<PaginatedProducts> {
  const response = await apiClient.get<PaginatedProducts>('/api/v1/products', { params });
  return response.data;
}

export async function getProduct(productId: string): Promise<Product> {
  const response = await apiClient.get<Product>(`/api/v1/products/${productId}`);
  return response.data;
}

export async function createReview(payload: CreateReviewPayload): Promise<Review> {
  const response = await apiClient.post<Review>('/api/v1/products/reviews', payload);
  return response.data;
}