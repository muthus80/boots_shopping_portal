import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getCategories } from '../../api/categories';
import type { Category } from '../../types/index';

// ── Category card ─────────────────────────────────────────────────────────────

interface CategoryCardProps {
  category: Category;
}

const CategoryCard: React.FC<CategoryCardProps> = ({ category }) => (
  <Link
    to={`/products?category=${category.id}`}
    aria-label={`Browse ${category.name}`}
    className="group flex flex-col items-center gap-3 rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-gray-900 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-gray-900"
  >
    {category.image_url ? (
      <img
        src={category.image_url}
        alt={category.name}
        className="h-16 w-16 rounded-full object-cover"
      />
    ) : (
      <span className="text-5xl" aria-hidden="true">
        👢
      </span>
    )}
    <div>
      <h3 className="text-base font-semibold text-gray-900 group-hover:text-gray-700">
        {category.name}
      </h3>
      {category.description && (
        <p className="mt-1 text-xs text-gray-500 line-clamp-2">{category.description}</p>
      )}
    </div>
  </Link>
);

// ── Skeleton card ─────────────────────────────────────────────────────────────

const CategoryCardSkeleton: React.FC = () => (
  <div className="flex flex-col items-center gap-3 rounded-xl border border-gray-200 bg-white p-6" aria-hidden="true">
    <div className="h-16 w-16 animate-pulse rounded-full bg-gray-200" />
    <div className="h-4 w-24 animate-pulse rounded bg-gray-200" />
    <div className="h-3 w-32 animate-pulse rounded bg-gray-100" />
  </div>
);

// ── CategoryGrid ──────────────────────────────────────────────────────────────

export interface CategoryGridProps {
  /** Called to retrieve the active category name for the heading. */
  activeCategoryId?: string;
}

export const CategoryGrid: React.FC<CategoryGridProps> = () => {
  const { data: categories, isLoading, isError } = useQuery<Category[], Error>({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: 1000 * 60 * 10,
  });

  if (isLoading) {
    return (
      <section aria-label="Product categories" aria-busy="true">
        <h2 className="mb-6 text-2xl font-bold text-gray-900">Shop by Category</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CategoryCardSkeleton key={i} />
          ))}
        </div>
      </section>
    );
  }

  if (isError || !categories || categories.length === 0) {
    return null;
  }

  return (
    <section aria-label="Product categories">
      <h2 className="mb-6 text-2xl font-bold text-gray-900">Shop by Category</h2>
      <div
        className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4"
        role="list"
      >
        {categories.map((cat) => (
          <div key={cat.id} role="listitem">
            <CategoryCard category={cat} />
          </div>
        ))}
      </div>
    </section>
  );
};

export default CategoryGrid;
