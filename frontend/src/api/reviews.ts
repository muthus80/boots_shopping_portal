/**
 * Reviews API client
 *
 * Handles GET and POST for product reviews.
 * Uses the product-scoped route: /api/v1/products/{product_id}/reviews
 */

import { apiClient } from './client';

/** A single review item as returned by GET /api/v1/products/{id}/reviews */
export interface ReviewApiItem {
  id: string;
  rating: number;
  review_text: string;
  created_at: string;
}

/** Response envelope for GET /api/v1/products/{id}/reviews */
export interface ReviewsResponse {
  reviews: ReviewApiItem[];
  average_rating: number;
  total_reviews: number;
}

/** Payload for POST /api/v1/products/{id}/reviews */
export interface CreateReviewPayload {
  rating: number;
  review_text: string;
}

export const REVIEWS_PER_PAGE = 10;

/**
 * Fetch paginated reviews for a product.
 *
 * @param productId - UUID of the product
 * @param page      - 1-based page number (default: 1)
 * @param perPage   - Reviews per page (default: REVIEWS_PER_PAGE)
 */
export async function getProductReviews(
  productId: string,
  page = 1,
  perPage = REVIEWS_PER_PAGE
): Promise<ReviewsResponse> {
  const response = await apiClient.get<ReviewsResponse>(
    `/api/v1/products/${productId}/reviews`,
    { params: { page, per_page: perPage } }
  );
  return response.data;
}

/**
 * Submit a purchase-verified review.
 * Requires auth (member role). Returns 403 if no matching purchase found.
 *
 * @param productId - UUID of the product
 * @param payload   - { rating: 1-5, review_text }
 */
export async function createProductReview(
  productId: string,
  payload: CreateReviewPayload
): Promise<ReviewApiItem> {
  const response = await apiClient.post<ReviewApiItem>(
    `/api/v1/products/${productId}/reviews`,
    payload
  );
  return response.data;
}
