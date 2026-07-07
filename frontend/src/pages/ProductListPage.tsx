import React, { useState, useCallback } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { getProducts, PaginatedProducts } from '../api/products';
import type { Product } from '../types/index';

export const ProductListPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [searchInput, setSearchInput] = useState<string>(
    searchParams.get('search') || ''
  );

  const categoryId = searchParams.get('category') || undefined;
  const search = searchParams.get('search') || undefined;
  const page = parseInt(searchParams.get('page') || '1', 10);

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

  return (
    <div className="product-list-page" style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24 }}>Our Products</h1>

      {/* Filters */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 32,
          alignItems: 'flex-end',
        }}
      >
        {/* Search */}
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            placeholder="Search products..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            style={{
              padding: '8px 12px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              fontSize: 14,
              minWidth: 220,
            }}
          />
          <button
            type="submit"
            style={{
              padding: '8px 16px',
              backgroundColor: '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Search
          </button>
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearchInput('');
                const next = new URLSearchParams(searchParams);
                next.delete('search');
                next.set('page', '1');
                setSearchParams(next);
              }}
              style={{
                padding: '8px 12px',
                backgroundColor: '#f3f4f6',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                fontSize: 14,
                cursor: 'pointer',
              }}
            >
              Clear
            </button>
          )}
        </form>
      </div>

      {/* Active filters summary */}
      {(search || categoryId) && (
        <div style={{ marginBottom: 16, fontSize: 14, color: '#6b7280' }}>
          {totalCount > 0 ? `${totalCount} result${totalCount !== 1 ? 's' : ''}` : 'No results'}
          {search && (
            <span>
              {' '}for <strong>&ldquo;{search}&rdquo;</strong>
            </span>
          )}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
            gap: 24,
          }}
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              style={{
                backgroundColor: '#f3f4f6',
                borderRadius: 8,
                height: 320,
              }}
            />
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div
          style={{
            padding: 24,
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 8,
            color: '#dc2626',
            textAlign: 'center',
          }}
        >
          <p style={{ fontWeight: 600, marginBottom: 8 }}>Failed to load products</p>
          <p style={{ fontSize: 14 }}>
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && products.length === 0 && (
        <div
          style={{
            padding: 48,
            textAlign: 'center',
            color: '#6b7280',
          }}
        >
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No products found</p>
          <p style={{ fontSize: 14 }}>Try adjusting your search or filter criteria.</p>
        </div>
      )}

      {/* Product grid */}
      {!isLoading && !isError && products.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
            gap: 24,
          }}
        >
          {products.map((product: Product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && !isError && totalPages > 1 && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: 8,
            marginTop: 40,
          }}
        >
          <button
            onClick={() => handlePageChange(page - 1)}
            disabled={page <= 1}
            style={{
              padding: '8px 16px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              backgroundColor: page <= 1 ? '#f9fafb' : '#fff',
              color: page <= 1 ? '#9ca3af' : '#374151',
              cursor: page <= 1 ? 'not-allowed' : 'pointer',
              fontSize: 14,
            }}
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
                <span key={`ellipsis-${idx}`} style={{ padding: '0 4px', color: '#9ca3af' }}>
                  &hellip;
                </span>
              ) : (
                <button
                  key={item}
                  onClick={() => handlePageChange(item as number)}
                  style={{
                    padding: '8px 14px',
                    border: '1px solid',
                    borderColor: item === page ? '#2563eb' : '#d1d5db',
                    borderRadius: 6,
                    backgroundColor: item === page ? '#2563eb' : '#fff',
                    color: item === page ? '#fff' : '#374151',
                    cursor: 'pointer',
                    fontSize: 14,
                    fontWeight: item === page ? 600 : 400,
                  }}
                >
                  {item}
                </button>
              )
            )}

          <button
            onClick={() => handlePageChange(page + 1)}
            disabled={page >= totalPages}
            style={{
              padding: '8px 16px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              backgroundColor: page >= totalPages ? '#f9fafb' : '#fff',
              color: page >= totalPages ? '#9ca3af' : '#374151',
              cursor: page >= totalPages ? 'not-allowed' : 'pointer',
              fontSize: 14,
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

interface ProductCardProps {
  product: Product;
}

const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const primaryImage =
    product.images && product.images.length > 0 ? product.images[0] : null;

  const displayPrice = product.sale_price != null ? product.sale_price : product.base_price;
  const hasDiscount = product.sale_price != null && product.sale_price < product.base_price;

  return (
    <Link
      to={`/products/${product.id}`}
      style={{ textDecoration: 'none', color: 'inherit' }}
    >
      <div
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: 8,
          overflow: 'hidden',
          backgroundColor: '#fff',
          transition: 'box-shadow 0.2s ease, transform 0.2s ease',
          cursor: 'pointer',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow =
            '0 4px 12px rgba(0,0,0,0.12)';
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
        }}
      >
        {/* Image */}
        <div
          style={{
            width: '100%',
            paddingTop: '75%',
            position: 'relative',
            backgroundColor: '#f9fafb',
            overflow: 'hidden',
          }}
        >
          {primaryImage ? (
            <img
              src={primaryImage}
              alt={product.name}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          ) : (
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#9ca3af',
                fontSize: 13,
              }}
            >
              No image
            </div>
          )}
          {hasDiscount && (
            <span
              style={{
                position: 'absolute',
                top: 8,
                left: 8,
                backgroundColor: '#dc2626',
                color: '#fff',
                fontSize: 11,
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 4,
              }}
            >
              SALE
            </span>
          )}
        </div>

        {/* Info */}
        <div style={{ padding: '12px 16px 16px', flex: 1, display: 'flex', flexDirection: 'column' }}>
          <h3
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: '#111827',
              marginBottom: 8,
              lineHeight: 1.4,
              flex: 1,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {product.name}
          </h3>

          {product.description && (
            <p
              style={{
                fontSize: 13,
                color: '#6b7280',
                marginBottom: 12,
                lineHeight: 1.5,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {product.description}
            </p>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 'auto' }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: '#111827' }}>
              {Number(displayPrice).toLocaleString('en-GB', { style: 'currency', currency: 'GBP' })}
            </span>
            {hasDiscount && (
              <span style={{ fontSize: 13, color: '#9ca3af', textDecoration: 'line-through' }}>
                {Number(product.base_price).toLocaleString('en-GB', { style: 'currency', currency: 'GBP' })}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
};

export default ProductListPage;
