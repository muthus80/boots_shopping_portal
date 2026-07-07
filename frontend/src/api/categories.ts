import { apiClient } from './client';
import type { Category } from '../types/index';

export async function getCategories(): Promise<Category[]> {
  const response = await apiClient.get<Category[]>('/api/v1/categories');
  return response.data;
}
