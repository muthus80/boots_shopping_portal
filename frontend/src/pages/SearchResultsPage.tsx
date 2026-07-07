import React, { useState, useCallback, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { searchProducts, PaginatedProducts } from '../api/products';
import { ProductCard } from '../components/products/ProductCard';
import type { Product } from '../types/index';

// ── Skeleton card ─────────────────────────────────────────────────────────────

const ProductCardSkeleton: React.FC = () => (
  <div
    className="flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white"
    aria-hidden="true"
  >
    <div className="w-full animate-pulse bg-gray-200" style={{ paddingTop: '75%' }} />
    <div className="flex flex-col gap-2 p-4">
      <div className="h-3 w-1/3 animate-pulse rounded bg-gray-200" />
      <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
      <div className="mt-2 h-5 w-1/4 animate-pulse rounded bg-gray-200" />
    </div>
  </div>
);

// ── SearchResultsPage ─────────────────────────────────────────────────────────

export const SearchResultsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const query = searchParams.get('q') ?? '';
  const page = parseInt(searchParams.get('page') ?? '1', 10);

  // Local input state — keeps the search field in sync with the URL query
  const [inputValue, setInputValue] = useState<string>(query);

  // Sync input when URL query changes (e.g. navigating via header search bar)
  useEffect(() => {
    setInputValue(query);
  }, [query]);

  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery<PaginatedProducts, Error>({
    queryKey: ['search', query, page],
    queryFn: () => searchProducts({ q: query, page, page_size: 12 }),
    enabled: query.trim().length > 0,
    placeholderData: keepPreviousData,
  });

  const products: Product[] = data?.items ?? [];
  const totalCount: number = data?.total ?? 0;
  const totalPages: number = data?.total_pages ?? 1;

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleSearchSubmit = useCallback(
    (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const trimmed = inputValue.trim();
      if (trimmed) {
        setSearchParams({ q: trimmed, page: '1' });
      }
    },
    [inputValue, setSearchParams]
  );

  const handleClear = useCallback(() => {
    setInputValue('');
    navigate('/products');
  }, [navigate]);

  const handlePageChange = useCallback(
    (newPage: number) => {
      const next = new URLSearchParams(searchParams);
      next.set('page', String(newPage));
      setSearchParams(next);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [searchParams, setSearchParams]
  );

  // ── No query state ───────────────────────────────────────────────────────────

  if (!query.trim()) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 text-center">
        <span className="text-5xl" aria-hidden="true">🔍</span>
        <p className="mt-4 text-lg font-semibold text-gray-700">
          Enter a keyword to start searching
        </p>
        <p className="mt-1 text-sm text-gray-500">
          Try searching for &lsquo;hiking&rsquo;, &lsquo;work boots&rsquo;, or &lsquo;leather&rsquo;.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">

      {/* Page heading */}
      <h1 className="mb-6 text-3xl font-extrabold text-gray-900">
        {`Search results for "${query}"`}
      </h1>

      {/* Search form — refine or start a new search */}
      <div className="mb-8 flex flex-wrap items-end gap-4">
        <form
          role="search"
          onSubmit={handleSearchSubmit}
          className="flex gap-2"
          aria-label="Search products"
        >
          <label htmlFor="search-results-input" className="sr-only">
            Search products
          </label>
          <input
            id="search-results-input"
            type="search"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Search boots…"
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
          <button
            type="button"
            aria-label="Clear search"
            onClick={handleClear}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors"
          >
            Clear
          </button>
        </form>
      </div>

      {/* Result count */}
      {!isLoading && !isError && (
        <p className="mb-4 text-sm text-gray-500" aria-live="polite" aria-atomic="true">
          {totalCount > 0
            ? `${totalCount} result${totalCount !== 1 ? 's' : ''} for "${query}"`
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
      {!isLoading && !isError && products.length === 0 && (
        <div className="py-16 text-center">
          <span className="text-5xl" aria-hidden="true">👢</span>
          <p className="mt-4 text-lg font-semibold text-gray-700">
            No results found for your search
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Try a different keyword or browse our{' '}
            <a
              href="/products"
              className="font-medium text-gray-900 underline hover:text-gray-700"
            >
              full catalogue
            </a>
            .
          </p>
        </div>
      )}

      {/* Product grid */}
      {!isLoading && !isError && products.length > 0 && (
        <div
          className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4"
          aria-label="Search results grid"
        >
          {products.map((product: Product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && !isError && totalPages > 1 && (
        <nav
          aria-label="Search results pagination"
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

export default SearchResultsPage;
