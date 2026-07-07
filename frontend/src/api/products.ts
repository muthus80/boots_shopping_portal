import { apiClient } from './client';
import { Product, Review } from '../types/index';

export interface GetProductsParams {
  category_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  /** Filter by one or more sizes (e.g. ['8', '9']). Serialised as repeated `size` params. */
  sizes?: string[];
  /** Filter by one or more colors (e.g. ['black', 'brown']). Serialised as repeated `color` params. */
  colors?: string[];
}

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SearchProductsParams {
  q: string;
  page?: number;
  page_size?: number;
}

export interface CreateReviewPayload {
  product_id: string;
  rating: number;
  title?: string;
  body?: string;
}

export async function getProducts(params?: GetProductsParams): Promise<PaginatedProducts> {
  // Axios serialises arrays as `key[0]=v0&key[1]=v1` by default, but the
  // backend expects repeated params: `size=8&size=9`.  We build URLSearchParams
  // manually for the array fields and pass the rest normally.
  const { sizes, colors, ...rest } = params ?? {};

  const urlParams = new URLSearchParams();

  // Append scalar params
  Object.entries(rest).forEach(([k, v]) => {
    if (v !== undefined && v !== null) {
      urlParams.append(k, String(v));
    }
  });

  // Append repeated params
  sizes?.forEach((s) => urlParams.append('size', s));
  colors?.forEach((c) => urlParams.append('color', c));

  const response = await apiClient.get<PaginatedProducts>(
    `/api/v1/products?${urlParams.toString()}`
  );
  return response.data;
}

export async function getProduct(productId: string): Promise<Product> {
  const response = await apiClient.get<Product>(`/api/v1/products/${productId}`);
  return response.data;
}

export async function searchProducts(params: SearchProductsParams): Promise<PaginatedProducts> {
  const response = await apiClient.get<PaginatedProducts>('/api/v1/products/search', { params });
  return response.data;
}

export async function createReview(payload: CreateReviewPayload): Promise<Review> {
  const response = await apiClient.post<Review>('/api/v1/products/reviews', payload);
  return response.data;
}