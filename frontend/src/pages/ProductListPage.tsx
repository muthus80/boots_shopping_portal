import React, { useState, useCallback } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getProducts, PaginatedProducts } from '../api/products';
import { getCategories } from '../api/categories';
import { ProductCard } from '../components/products/ProductCard';
import { CategoryGrid } from '../components/products/CategoryGrid';
import type { Category, Product } from '../types/index';

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Product skeleton card */
const ProductCardSkeleton: React.FC = () => (
  <div className="flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white" aria-hidden="true">
    <div className="w-full animate-pulse bg-gray-200" style={{ paddingTop: '75%' }} />
    <div className="flex flex-col gap-2 p-4">
      <div className="h-3 w-1/3 animate-pulse rounded bg-gray-200" />
      <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
      <div className="mt-2 h-5 w-1/4 animate-pulse rounded bg-gray-200" />
    </div>
  </div>
);

// ── ProductListPage ───────────────────────────────────────────────────────────

export const ProductListPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [searchInput, setSearchInput] = useState<string>(
    searchParams.get('search') || ''
  );

  // URL-driven state
  const categoryId = searchParams.get('category') || undefined;
  const search = searchParams.get('search') || undefined;
  const page = parseInt(searchParams.get('page') || '1', 10);

  // Fetch categories for heading resolution
  const { data: categories } = useQuery<Category[], Error>({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: 1000 * 60 * 10,
  });

  // Derive active category name for heading
  const activeCategoryName: string | undefined =
    categoryId && categories
      ? categories.find((c) => c.id === categoryId || c.slug === categoryId)?.name
      : undefined;

  // Fetch products
  const { data, isLoading, isError, error } = useQuery<PaginatedProducts, Error>({
    queryKey: ['products', { categoryId, search, page }],
    queryFn: () =>
      getProducts({ category_id: categoryId, search, page, page_size: 12 }),
    placeholderData: keepPreviousData,
  });

  const handleSearchSubmit = useCallback(
    (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const next = new URLSearchParams(searchParams);
      if (searchInput.trim()) {
        next.set('search', searchInput.trim());
      } else {
        next.delete('search');
      }
      next.set('page', '1');
      setSearchParams(next);
    },
    [searchInput, searchParams, setSearchParams]
  );

  const handlePageChange = useCallback(
    (newPage: number) => {
      const next = new URLSearchParams(searchParams);
      next.set('page', String(newPage));
      setSearchParams(next);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [searchParams, setSearchParams]
  );

  const products: Product[] = data?.items ?? [];
  const totalPages: number = data?.total_pages ?? 1;
  const totalCount: number = data?.total ?? 0;

  // Decide whether to show the category grid (no active filter)
  const showCategoryGrid = !categoryId && !search;

  // Build the page heading
  const pageHeading: string = activeCategoryName
    ? activeCategoryName
    : search
    ? `Search results for "${search}"`
    : 'All Boots';

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">

      {/* Page heading */}
      <h1 className="mb-6 text-3xl font-extrabold text-gray-900">
        {pageHeading}
      </h1>

      {/* Search + filter bar */}
      <div className="mb-8 flex flex-wrap items-end gap-4">
        <form
          role="search"
          onSubmit={handleSearchSubmit}
          className="flex gap-2"
          aria-label="Search products"
        >
          <label htmlFor="product-search" className="sr-only">
            Search products
          </label>
          <input
            id="product-search"
            type="search"
            placeholder="Search boots…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            aria-label="Search products"
            className="min-w-[220px] rounded-lg border border-gray-300 bg-gray-50 py-2 pl-3 pr-4 text-sm text-gray-900 placeholder-gray-400 focus:border-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors"
          />
          <button
            type="submit"
            aria-label="Submit search"
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors"
          >
            Search
          </button>
          {search && (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => {
                setSearchInput('');
                const next = new URLSearchParams(searchParams);
                next.delete('search');
                next.set('page', '1');
                setSearchParams(next);
              }}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors"
            >
              Clear
            </button>
          )}
        </form>
      </div>

      {/* Category grid (shown only when no filter is active) */}
      {showCategoryGrid && (
        <div className="mb-10">
          <CategoryGrid />
        </div>
      )}

      {/* Results count */}
      {(search || categoryId) && !isLoading && (
        <p className="mb-4 text-sm text-gray-500">
          {totalCount > 0
            ? `${totalCount} result${totalCount !== 1 ? 's' : ''}`
            : 'No results found for your search'}
        </p>
      )}

      {/* Loading state — skeleton grid */}
      {isLoading && (
        <div
          className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4"
          aria-busy="true"
          aria-label="Loading products"
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <ProductCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-8 text-center"
        >
          <p className="mb-1 text-base font-semibold text-red-700">
            Something went wrong, please try again
          </p>
          <p className="text-sm text-red-500">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && products.length === 0 && (search || categoryId) && (
        <div className="py-16 text-center">
          <span className="text-5xl" aria-hidden="true">👢</span>
          <p className="mt-4 text-lg font-semibold text-gray-700">
            {search ? 'No results found for your search' : 'No products found'}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Try adjusting your search or browse a different category.
          </p>
        </div>
      )}

      {/* Product grid */}
      {!isLoading && !isError && products.length > 0 && (
        <div
          className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4"
          aria-label="Product grid"
        >
          {products.map((product: Product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && !isError && totalPages > 1 && (
        <nav
          aria-label="Product pagination"
          className="mt-12 flex items-center justify-center gap-2"
        >
          <button
            onClick={() => handlePageChange(page - 1)}
            disabled={page <= 1}
            aria-label="Previous page"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-gray-900"
          >
            Previous
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter(
              (p) =>
                p === 1 ||
                p === totalPages ||
                (p >= page - 2 && p <= page + 2)
            )
            .reduce<(number | 'ellipsis')[]>((acc, p, idx, arr) => {
              if (idx > 0 && p - (arr[idx - 1] as number) > 1) {
                acc.push('ellipsis');
              }
              acc.push(p);
              return acc;
            }, [])
            .map((item, idx) =>
              item === 'ellipsis' ? (
                <span
                  key={`ellipsis-${idx}`}
                  className="px-1 text-sm text-gray-400"
                  aria-hidden="true"
                >
                  &hellip;
                </span>
              ) : (
                <button
                  key={item}
                  onClick={() => handlePageChange(item as number)}
                  aria-label={`Page ${item}`}
                  aria-current={item === page ? 'page' : undefined}
                  className={`rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-gray-900 ${
                    item === page
                      ? 'border-gray-900 bg-gray-900 text-white'
                      : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {item}
                </button>
              )
            )}

          <button
            onClick={() => handlePageChange(page + 1)}
            disabled={page >= totalPages}
            aria-label="Next page"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-gray-900"
          >
            Next
          </button>
        </nav>
      )}
    </div>
  );
};

export default ProductListPage;
