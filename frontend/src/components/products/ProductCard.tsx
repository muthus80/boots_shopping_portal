import React from 'react';
import { Link } from 'react-router-dom';
import type { Product } from '../../types/index';

export interface ProductCardProps {
  product: Product;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const primaryImage =
    product.images && product.images.length > 0
      ? product.images[0]
      : product.image_url ?? null;

  const displayPrice =
    product.sale_price != null ? product.sale_price : product.base_price;
  const hasDiscount =
    product.sale_price != null && product.sale_price < product.base_price;

  const formattedPrice = (amount: number): string =>
    Number(amount).toLocaleString('en-GB', { style: 'currency', currency: 'GBP' });

  return (
    <Link
      to={`/products/${product.id}`}
      aria-label={`View ${product.name}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-gray-900"
    >
      {/* Product image */}
      <div
        className="relative w-full overflow-hidden bg-gray-50"
        style={{ paddingTop: '75%' }}
      >
        {primaryImage ? (
          <img
            src={primaryImage}
            alt={product.name}
            className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div
            className="absolute inset-0 flex items-center justify-center text-5xl"
            aria-hidden="true"
          >
            👢
          </div>
        )}
        {hasDiscount && (
          <span className="absolute left-2 top-2 rounded bg-red-600 px-2 py-0.5 text-xs font-bold text-white">
            SALE
          </span>
        )}
      </div>

      {/* Product info */}
      <div className="flex flex-1 flex-col p-4">
        {product.brand && (
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
            {product.brand}
          </p>
        )}

        <h3
          className="mb-3 flex-1 text-sm font-semibold leading-snug text-gray-900"
          style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {product.name}
        </h3>

        <div className="mt-auto flex items-center gap-2">
          <span className="text-base font-bold text-gray-900">
            {formattedPrice(displayPrice)}
          </span>
          {hasDiscount && (
            <span className="text-sm text-gray-400 line-through">
              {formattedPrice(product.base_price)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
};

export default ProductCard;
