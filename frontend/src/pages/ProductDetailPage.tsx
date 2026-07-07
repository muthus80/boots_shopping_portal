import React, { useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProduct } from '../api/products';
import { addCartItem } from '../api/cart';
import { apiClient } from '../api/client';
import { useAuth } from '../stores/authStore';
import type { Product, ProductVariant, Review } from '../types/index';

// ── Extended types for extra fields returned by detail endpoint ───────────────

interface ProductVariantFull extends ProductVariant {
  /** Variant-level price override (returned by the detail endpoint). */
  price?: number;
}

interface ProductDetail extends Omit<Product, 'variants' | 'reviews'> {
  variants?: ProductVariantFull[];
  reviews?: Review[];
  category?: { id: string; name: string };
  materials?: string | null;
  features?: string[] | null;
}

// ── API helper for reviews (uses product-scoped route) ────────────────────────

interface CreateReviewPayload {
  rating: number;
  comment?: string;
}

async function createProductReview(
  productId: string,
  payload: CreateReviewPayload
): Promise<Review> {
  const response = await apiClient.post<Review>(
    `/api/v1/products/${productId}/reviews`,
    payload
  );
  return response.data;
}

// ── ImageGallery ──────────────────────────────────────────────────────────────

interface ImageGalleryProps {
  images: string[];
  productName: string;
}

const ImageGallery: React.FC<ImageGalleryProps> = ({ images, productName }) => {
  const [activeIdx, setActiveIdx] = useState<number>(0);

  const handleThumbnailKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>, idx: number) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setActiveIdx(idx);
      }
    },
    []
  );

  if (images.length === 0) {
    return (
      <div className="flex h-80 w-full items-center justify-center rounded-2xl bg-gray-100 text-6xl sm:h-96 lg:h-[480px]">
        <span role="img" aria-label="No image available">👢</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Main image */}
      <div className="relative overflow-hidden rounded-2xl bg-gray-50">
        <img
          src={images[activeIdx]}
          alt={`${productName} — image ${activeIdx + 1} of ${images.length}`}
          className="h-80 w-full object-cover sm:h-96 lg:h-[480px]"
        />
        {images.length > 1 && (
          <span className="absolute bottom-3 right-3 rounded-full bg-black/50 px-2.5 py-1 text-xs font-medium text-white">
            {activeIdx + 1} / {images.length}
          </span>
        )}
      </div>

      {/* Thumbnail strip */}
      {images.length > 1 && (
        <div
          className="flex gap-2 overflow-x-auto pb-1"
          role="tablist"
          aria-label="Product image thumbnails"
        >
          {images.map((src, idx) => (
            <button
              key={`${src}-${idx}`}
              type="button"
              role="tab"
              aria-selected={idx === activeIdx}
              aria-label={`View image ${idx + 1}`}
              onClick={() => setActiveIdx(idx)}
              onKeyDown={(e) => handleThumbnailKeyDown(e, idx)}
              className={`h-16 w-16 shrink-0 overflow-hidden rounded-lg border-2 transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 ${
                idx === activeIdx
                  ? 'border-gray-900 opacity-100'
                  : 'border-transparent opacity-60 hover:opacity-90'
              }`}
            >
              <img
                src={src}
                alt=""
                aria-hidden="true"
                className="h-full w-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// ── StarRating ────────────────────────────────────────────────────────────────

interface StarRatingProps {
  rating: number;
  max?: number;
  interactive?: false;
}

interface InteractiveStarRatingProps {
  rating: number;
  max?: number;
  interactive: true;
  onChange: (value: number) => void;
}

const StarRating: React.FC<StarRatingProps | InteractiveStarRatingProps> = (props) => {
  const { rating, max = 5 } = props;

  return (
    <span className="inline-flex gap-0.5">
      {Array.from({ length: max }, (_, i) => {
        const filled = i < Math.round(rating);
        if (props.interactive) {
          return (
            <button
              key={i}
              type="button"
              aria-label={`Rate ${i + 1} out of ${max}`}
              onClick={() => props.onChange(i + 1)}
              className={`text-2xl leading-none transition-colors focus:outline-none ${
                filled ? 'text-amber-400' : 'text-gray-300 hover:text-amber-300'
              }`}
            >
              ★
            </button>
          );
        }
        return (
          <span
            key={i}
            aria-hidden="true"
            className={`text-base leading-none ${filled ? 'text-amber-400' : 'text-gray-300'}`}
          >
            ★
          </span>
        );
      })}
    </span>
  );
};

// ── SizePicker ────────────────────────────────────────────────────────────────

interface SizePickerProps {
  sizes: string[];
  selectedSize: string | null;
  availableSizes: Set<string>;
  onSelect: (size: string) => void;
}

const SizePicker: React.FC<SizePickerProps> = ({
  sizes,
  selectedSize,
  availableSizes,
  onSelect,
}) => (
  <div>
    <p className="mb-2 text-sm font-semibold text-gray-700">
      Size{selectedSize ? <span className="ml-2 font-normal text-gray-500">— {selectedSize}</span> : null}
    </p>
    <div className="flex flex-wrap gap-2" role="group" aria-label="Select a size">
      {sizes.map((size) => {
        const available = availableSizes.has(size);
        const selected = selectedSize === size;
        return (
          <button
            key={size}
            type="button"
            disabled={!available}
            aria-pressed={selected}
            aria-label={`Size ${size}${!available ? ' — out of stock' : ''}`}
            onClick={() => available && onSelect(size)}
            className={`relative min-w-[3rem] rounded-md border px-3.5 py-2 text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 ${
              selected
                ? 'border-gray-900 bg-gray-900 text-white'
                : available
                ? 'border-gray-300 bg-white text-gray-800 hover:border-gray-900'
                : 'cursor-not-allowed border-gray-200 bg-gray-50 text-gray-300 line-through'
            }`}
          >
            {size}
          </button>
        );
      })}
    </div>
  </div>
);

// ── ColorPicker ───────────────────────────────────────────────────────────────

const COLOR_SWATCHES: Record<string, string> = {
  black: '#1a1a1a',
  white: '#ffffff',
  brown: '#7B4F2B',
  tan: '#C5A57A',
  navy: '#1e3a5f',
  grey: '#9ca3af',
  gray: '#9ca3af',
  red: '#dc2626',
  green: '#16a34a',
  blue: '#2563eb',
  beige: '#e8d5b7',
  chestnut: '#954535',
  cognac: '#9A4722',
  wheat: '#F5DEB3',
};

interface ColorPickerProps {
  colors: string[];
  selectedColor: string | null;
  availableColors: Set<string>;
  onSelect: (color: string) => void;
}

const ColorPicker: React.FC<ColorPickerProps> = ({
  colors,
  selectedColor,
  availableColors,
  onSelect,
}) => (
  <div>
    <p className="mb-2 text-sm font-semibold text-gray-700">
      Color
      {selectedColor ? (
        <span className="ml-2 font-normal capitalize text-gray-500">— {selectedColor}</span>
      ) : null}
    </p>
    <div className="flex flex-wrap gap-2" role="group" aria-label="Select a color">
      {colors.map((color) => {
        const available = availableColors.has(color);
        const selected = selectedColor === color;
        const swatch = COLOR_SWATCHES[color.toLowerCase()];
        return (
          <button
            key={color}
            type="button"
            disabled={!available}
            aria-pressed={selected}
            aria-label={`Color: ${color}${!available ? ' — out of stock' : ''}`}
            onClick={() => available && onSelect(color)}
            className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium capitalize transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 ${
              selected
                ? 'border-gray-900 bg-gray-900 text-white'
                : available
                ? 'border-gray-300 bg-white text-gray-800 hover:border-gray-900'
                : 'cursor-not-allowed border-gray-200 bg-gray-50 text-gray-300'
            }`}
          >
            {swatch && (
              <span
                aria-hidden="true"
                className="inline-block h-3.5 w-3.5 rounded-full border border-gray-300"
                style={{ backgroundColor: swatch }}
              />
            )}
            {color}
          </button>
        );
      })}
    </div>
  </div>
);

// ── ProductDetailSkeleton ─────────────────────────────────────────────────────

const ProductDetailSkeleton: React.FC = () => (
  <div
    className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
    aria-busy="true"
    aria-label="Loading product details"
  >
    <div className="mb-6 h-5 w-24 animate-pulse rounded bg-gray-200" />
    <div className="flex flex-col gap-10 lg:flex-row">
      {/* Image skeleton */}
      <div className="w-full lg:w-1/2">
        <div className="h-80 w-full animate-pulse rounded-2xl bg-gray-200 sm:h-96 lg:h-[480px]" />
        <div className="mt-3 flex gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 w-16 animate-pulse rounded-lg bg-gray-200" />
          ))}
        </div>
      </div>
      {/* Info skeleton */}
      <div className="flex flex-1 flex-col gap-4">
        <div className="h-4 w-20 animate-pulse rounded bg-gray-200" />
        <div className="h-8 w-3/4 animate-pulse rounded bg-gray-200" />
        <div className="h-8 w-24 animate-pulse rounded bg-gray-200" />
        <div className="mt-2 space-y-2">
          <div className="h-4 w-full animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-5/6 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-4/6 animate-pulse rounded bg-gray-200" />
        </div>
        <div className="mt-4 h-10 w-full animate-pulse rounded-lg bg-gray-200" />
        <div className="h-12 w-full animate-pulse rounded-lg bg-gray-200" />
      </div>
    </div>
  </div>
);

// ── ReviewCard ────────────────────────────────────────────────────────────────

interface ReviewCardProps {
  review: Review;
}

const ReviewCard: React.FC<ReviewCardProps> = ({ review }) => (
  <article className="rounded-xl border border-gray-200 bg-white p-5">
    <div className="mb-2 flex items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        <StarRating rating={review.rating} />
        {review.user?.full_name && (
          <span className="text-sm font-medium text-gray-700">{review.user.full_name}</span>
        )}
      </div>
      <time
        className="shrink-0 text-xs text-gray-400"
        dateTime={review.created_at}
      >
        {new Date(review.created_at).toLocaleDateString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        })}
      </time>
    </div>
    {review.title && (
      <p className="mb-1 text-sm font-semibold text-gray-900">{review.title}</p>
    )}
    {review.body && (
      <p className="text-sm leading-relaxed text-gray-600">{review.body}</p>
    )}
  </article>
);

// ── ProductDetailPage ─────────────────────────────────────────────────────────

const ProductDetailPage: React.FC = () => {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // ── Fetch product detail ─────────────────────────────────────────────────────

  const {
    data: product,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<ProductDetail, Error>({
    queryKey: ['product', productId],
    queryFn: () => getProduct(productId!) as Promise<ProductDetail>,
    enabled: !!productId,
  });

  // ── Variant selection state ──────────────────────────────────────────────────

  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [selectedColor, setSelectedColor] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<number>(1);
  const [cartSuccess, setCartSuccess] = useState<string | null>(null);
  const [cartError, setCartError] = useState<string | null>(null);

  // ── Review form state ────────────────────────────────────────────────────────

  const [reviewRating, setReviewRating] = useState<number>(5);
  const [reviewComment, setReviewComment] = useState<string>('');
  const [reviewSubmitting, setReviewSubmitting] = useState<boolean>(false);
  const [reviewSuccess, setReviewSuccess] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  // ── Derived variant data ─────────────────────────────────────────────────────

  const variants: ProductVariantFull[] = product?.variants ?? [];

  const allSizes = useMemo<string[]>(
    () =>
      [...new Set(variants.map((v) => v.size).filter((s): s is string => !!s))].sort((a, b) => {
        const na = parseFloat(a);
        const nb = parseFloat(b);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        return a.localeCompare(b);
      }),
    [variants]
  );

  const allColors = useMemo<string[]>(
    () =>
      [...new Set(variants.map((v) => v.color).filter((c): c is string => !!c))].sort((a, b) =>
        a.localeCompare(b)
      ),
    [variants]
  );

  // Sizes available given selected color (or all if no color)
  const availableSizes = useMemo<Set<string>>(
    () =>
      new Set(
        variants
          .filter((v) => v.stock_quantity > 0 && (!selectedColor || v.color === selectedColor))
          .map((v) => v.size)
          .filter((s): s is string => !!s)
      ),
    [variants, selectedColor]
  );

  // Colors available given selected size (or all if no size)
  const availableColors = useMemo<Set<string>>(
    () =>
      new Set(
        variants
          .filter((v) => v.stock_quantity > 0 && (!selectedSize || v.size === selectedSize))
          .map((v) => v.color)
          .filter((c): c is string => !!c)
      ),
    [variants, selectedSize]
  );

  // Exact selected variant
  const selectedVariant = useMemo<ProductVariantFull | null>(() => {
    if (variants.length === 0) return null;
    if (allSizes.length === 0 && allColors.length === 0) return variants[0] ?? null;
    return (
      variants.find((v) => {
        const sizeMatch = !selectedSize || v.size === selectedSize;
        const colorMatch = !selectedColor || v.color === selectedColor;
        return sizeMatch && colorMatch;
      }) ?? null
    );
  }, [variants, selectedSize, selectedColor, allSizes, allColors]);

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const handleSizeSelect = useCallback((size: string) => {
    setSelectedSize((prev) => (prev === size ? null : size));
    setCartSuccess(null);
    setCartError(null);
    setQuantity(1);
  }, []);

  const handleColorSelect = useCallback((color: string) => {
    setSelectedColor((prev) => (prev === color ? null : color));
    setCartSuccess(null);
    setCartError(null);
    setQuantity(1);
  }, []);

  // ── Add to cart mutation ─────────────────────────────────────────────────────

  const addToCartMutation = useMutation({
    mutationFn: ({ variantId, qty }: { variantId: string; qty: number }) =>
      addCartItem(variantId, qty),
    onSuccess: () => {
      setCartSuccess('Item added to cart!');
      setCartError(null);
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
    onError: (err: Error) => {
      setCartError(err.message || 'Failed to add item to cart. Please try again.');
      setCartSuccess(null);
    },
  });

  const handleAddToCart = useCallback(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    if (!selectedVariant) {
      setCartError(
        [
          allSizes.length > 0 && !selectedSize && 'Please select a size',
          allColors.length > 0 && !selectedColor && 'Please select a color',
        ]
          .filter(Boolean)
          .join(' and ') || 'Please select a variant.'
      );
      return;
    }
    if (selectedVariant.stock_quantity <= 0) {
      setCartError('This variant is out of stock.');
      return;
    }
    addToCartMutation.mutate({ variantId: selectedVariant.id, qty: quantity });
  }, [
    user,
    navigate,
    selectedVariant,
    quantity,
    allSizes,
    allColors,
    selectedSize,
    selectedColor,
    addToCartMutation,
  ]);

  // ── Review submission ────────────────────────────────────────────────────────

  const handleReviewSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (!user) {
        navigate('/login');
        return;
      }
      if (!productId) return;

      setReviewSubmitting(true);
      setReviewError(null);
      setReviewSuccess(null);

      try {
        await createProductReview(productId, { rating: reviewRating, comment: reviewComment });
        setReviewSuccess('Thank you! Your review has been submitted.');
        setReviewRating(5);
        setReviewComment('');
        queryClient.invalidateQueries({ queryKey: ['product', productId] });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to submit review.';
        setReviewError(msg);
      } finally {
        setReviewSubmitting(false);
      }
    },
    [user, navigate, productId, reviewRating, reviewComment, queryClient]
  );

  // ── Render: loading ───────────────────────────────────────────────────────────

  if (isLoading) {
    return <ProductDetailSkeleton />;
  }

  // ── Render: error ─────────────────────────────────────────────────────────────

  if (isError || !product) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div
          role="alert"
          className="mx-auto max-w-md rounded-xl border border-red-200 bg-red-50 p-8 text-center"
        >
          <span className="mb-2 inline-block text-3xl" aria-hidden="true">⚠️</span>
          <p className="mb-1 text-base font-semibold text-red-700">
            Something went wrong, please try again
          </p>
          {error && (
            <p className="mb-4 text-sm text-red-500">{error.message}</p>
          )}
          <div className="flex justify-center gap-3">
            <button
              type="button"
              onClick={() => refetch()}
              className="rounded-lg border border-red-300 bg-white px-5 py-2 text-sm font-medium text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-400 transition-colors"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="rounded-lg border border-gray-300 bg-white px-5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors"
            >
              Go back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Derived display values ────────────────────────────────────────────────────

  const images: string[] = (() => {
    const imgs: string[] = [];
    if (product.images && product.images.length > 0) {
      imgs.push(...product.images);
    } else if (product.image_url) {
      imgs.push(product.image_url);
    }
    return imgs;
  })();

  const displayPrice: number = (() => {
    if (selectedVariant?.price != null) return Number(selectedVariant.price);
    if (product.sale_price != null) return Number(product.sale_price);
    return Number(product.base_price);
  })();

  const hasDiscount =
    product.sale_price != null && product.sale_price < product.base_price;

  const formattedPrice = (amount: number): string =>
    Number(amount).toLocaleString('en-GB', { style: 'currency', currency: 'GBP' });

  const stockStatus: 'in_stock' | 'out_of_stock' | 'unknown' = selectedVariant
    ? selectedVariant.stock_quantity > 0
      ? 'in_stock'
      : 'out_of_stock'
    : 'unknown';

  const reviews: Review[] = product.reviews ?? [];
  const avgRating: number | null =
    reviews.length > 0
      ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
      : product.average_rating ?? null;

  const needsSizeSelection = allSizes.length > 0 && selectedSize === null;
  const needsColorSelection = allColors.length > 0 && selectedColor === null;
  const canAddToCart =
    !addToCartMutation.isPending &&
    stockStatus !== 'out_of_stock' &&
    !needsSizeSelection &&
    !needsColorSelection;

  // ── Render: product detail ────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">

      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="mb-6">
        <ol className="flex items-center gap-2 text-sm text-gray-500">
          <li>
            <Link to="/" className="hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors">
              Home
            </Link>
          </li>
          <li aria-hidden="true">›</li>
          <li>
            <Link to="/products" className="hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors">
              Boots
            </Link>
          </li>
          {product.category && (
            <>
              <li aria-hidden="true">›</li>
              <li>
                <Link
                  to={`/products?category=${product.category.id}`}
                  className="hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded transition-colors"
                >
                  {product.category.name}
                </Link>
              </li>
            </>
          )}
          <li aria-hidden="true">›</li>
          <li aria-current="page" className="font-medium text-gray-900 truncate max-w-[200px]">
            {product.name}
          </li>
        </ol>
      </nav>

      {/* Main layout: images + info */}
      <div className="flex flex-col gap-10 lg:flex-row">

        {/* Image gallery — left column */}
        <div className="w-full lg:sticky lg:top-24 lg:w-1/2 lg:self-start">
          <ImageGallery images={images} productName={product.name} />
        </div>

        {/* Product info — right column */}
        <div className="flex-1">

          {/* Brand */}
          {product.brand && (
            <p className="mb-1 text-sm font-semibold uppercase tracking-wider text-gray-500">
              {product.brand}
            </p>
          )}

          {/* Product name */}
          <h1 className="mb-3 text-3xl font-extrabold leading-tight text-gray-900">
            {product.name}
          </h1>

          {/* Rating summary */}
          {avgRating !== null && (
            <div className="mb-4 flex items-center gap-2">
              <StarRating rating={avgRating} />
              <span className="text-sm text-gray-500">
                {avgRating.toFixed(1)}{' '}
                ({product.review_count > 0 ? product.review_count : reviews.length}{' '}
                {(product.review_count === 1 || reviews.length === 1) ? 'review' : 'reviews'})
              </span>
            </div>
          )}

          {/* Price */}
          <div className="mb-6 flex items-baseline gap-3">
            <span className="text-3xl font-bold text-gray-900">
              {formattedPrice(displayPrice)}
            </span>
            {hasDiscount && (
              <span className="text-lg text-gray-400 line-through">
                {formattedPrice(product.base_price)}
              </span>
            )}
            {hasDiscount && (
              <span className="rounded bg-red-100 px-2 py-0.5 text-sm font-semibold text-red-700">
                SALE
              </span>
            )}
          </div>

          {/* Stock status */}
          {stockStatus === 'in_stock' && (
            <p className="mb-4 flex items-center gap-1.5 text-sm font-medium text-green-700">
              <span className="h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
              In stock
              {selectedVariant && selectedVariant.stock_quantity <= 5 && (
                <span className="font-normal text-amber-600">
                  — only {selectedVariant.stock_quantity} left
                </span>
              )}
            </p>
          )}
          {stockStatus === 'out_of_stock' && (
            <p className="mb-4 flex items-center gap-1.5 text-sm font-medium text-red-600">
              <span className="h-2 w-2 rounded-full bg-red-500" aria-hidden="true" />
              Out of stock
            </p>
          )}

          {/* Description */}
          {product.description && (
            <div className="mb-6">
              <p className="leading-relaxed text-gray-700">{product.description}</p>
            </div>
          )}

          {/* Feature badges */}
          {product.features && product.features.length > 0 && (
            <div className="mb-6 flex flex-wrap gap-2">
              {product.features.map((feature: string) => (
                <span
                  key={feature}
                  className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700"
                >
                  {feature}
                </span>
              ))}
            </div>
          )}

          {/* Divider */}
          <hr className="mb-6 border-gray-200" />

          {/* Size picker */}
          {allSizes.length > 0 && (
            <div className="mb-5">
              <SizePicker
                sizes={allSizes}
                selectedSize={selectedSize}
                availableSizes={availableSizes}
                onSelect={handleSizeSelect}
              />
            </div>
          )}

          {/* Color picker */}
          {allColors.length > 0 && (
            <div className="mb-5">
              <ColorPicker
                colors={allColors}
                selectedColor={selectedColor}
                availableColors={availableColors}
                onSelect={handleColorSelect}
              />
            </div>
          )}

          {/* Quantity selector */}
          {stockStatus !== 'out_of_stock' && (
            <div className="mb-6 flex items-center gap-3">
              <label htmlFor="pdp-quantity" className="text-sm font-semibold text-gray-700">
                Qty
              </label>
              <div className="flex items-center rounded-lg border border-gray-300">
                <button
                  type="button"
                  aria-label="Decrease quantity"
                  onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                  disabled={quantity <= 1}
                  className="flex h-10 w-10 items-center justify-center rounded-l-lg text-lg text-gray-700 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-gray-900"
                >
                  −
                </button>
                <span
                  id="pdp-quantity"
                  role="spinbutton"
                  aria-valuenow={quantity}
                  aria-valuemin={1}
                  aria-valuemax={selectedVariant?.stock_quantity ?? 99}
                  className="w-10 text-center text-sm font-semibold text-gray-900"
                >
                  {quantity}
                </span>
                <button
                  type="button"
                  aria-label="Increase quantity"
                  onClick={() =>
                    setQuantity((q) =>
                      selectedVariant
                        ? Math.min(selectedVariant.stock_quantity, q + 1)
                        : q + 1
                    )
                  }
                  disabled={
                    selectedVariant ? quantity >= selectedVariant.stock_quantity : false
                  }
                  className="flex h-10 w-10 items-center justify-center rounded-r-lg text-lg text-gray-700 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-gray-900"
                >
                  +
                </button>
              </div>
            </div>
          )}

          {/* Add to cart button */}
          <button
            type="button"
            onClick={handleAddToCart}
            disabled={!canAddToCart && stockStatus !== 'unknown'}
            aria-label="Add to cart"
            className={`w-full rounded-xl py-4 text-base font-bold transition-all focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 ${
              stockStatus === 'out_of_stock'
                ? 'cursor-not-allowed bg-gray-200 text-gray-400'
                : addToCartMutation.isPending
                ? 'cursor-wait bg-gray-700 text-white opacity-75'
                : 'bg-gray-900 text-white hover:bg-gray-700 active:scale-[0.98]'
            }`}
          >
            {stockStatus === 'out_of_stock'
              ? 'Out of Stock'
              : addToCartMutation.isPending
              ? 'Adding to cart…'
              : 'Add to Cart'}
          </button>

          {/* Selection hint */}
          {(needsSizeSelection || needsColorSelection) && !cartError && (
            <p className="mt-2 text-center text-sm text-amber-600" role="status">
              {[
                needsSizeSelection && 'Please select a size',
                needsColorSelection && 'Please select a color',
              ]
                .filter(Boolean)
                .join(' and ')}
            </p>
          )}

          {/* Cart feedback */}
          {cartSuccess && (
            <p className="mt-3 text-center text-sm font-medium text-green-700" role="status">
              ✓ {cartSuccess}
            </p>
          )}
          {cartError && (
            <p className="mt-3 text-center text-sm font-medium text-red-600" role="alert">
              {cartError}
            </p>
          )}

          {/* Product details accordion */}
          <div className="mt-8 space-y-px divide-y divide-gray-200 rounded-xl border border-gray-200">
            {product.materials && (
              <details className="group p-4">
                <summary className="flex cursor-pointer items-center justify-between text-sm font-semibold text-gray-900 focus:outline-none">
                  Materials
                  <span className="text-gray-400 group-open:rotate-180 transition-transform" aria-hidden="true">▾</span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-gray-600">{product.materials}</p>
              </details>
            )}
            <details className="group p-4">
              <summary className="flex cursor-pointer items-center justify-between text-sm font-semibold text-gray-900 focus:outline-none">
                Sizing &amp; Fit
                <span className="text-gray-400 group-open:rotate-180 transition-transform" aria-hidden="true">▾</span>
              </summary>
              <div className="mt-3 space-y-2 text-sm text-gray-600">
                {allSizes.length > 0 ? (
                  <>
                    <p>Available sizes: {allSizes.join(', ')}</p>
                    <p className="text-gray-500">
                      We recommend sizing up half a size for wider feet. All sizes are UK sizing.
                    </p>
                  </>
                ) : (
                  <p>Please contact us for sizing information.</p>
                )}
              </div>
            </details>
            <details className="group p-4">
              <summary className="flex cursor-pointer items-center justify-between text-sm font-semibold text-gray-900 focus:outline-none">
                Delivery &amp; Returns
                <span className="text-gray-400 group-open:rotate-180 transition-transform" aria-hidden="true">▾</span>
              </summary>
              <div className="mt-3 space-y-1 text-sm text-gray-600">
                <p>Free standard delivery on orders over £50.</p>
                <p>Express delivery available at checkout.</p>
                <p>Free returns within 30 days of purchase.</p>
              </div>
            </details>
          </div>

        </div>
      </div>

      {/* Reviews section */}
      <section
        aria-labelledby="reviews-heading"
        className="mt-16 border-t border-gray-200 pt-12"
      >
        <h2
          id="reviews-heading"
          className="mb-8 text-2xl font-extrabold text-gray-900"
        >
          Customer Reviews
          {reviews.length > 0 && (
            <span className="ml-2 text-lg font-normal text-gray-400">
              ({reviews.length})
            </span>
          )}
        </h2>

        {reviews.length > 0 ? (
          <div className="mb-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {reviews.map((review) => (
              <ReviewCard key={review.id} review={review} />
            ))}
          </div>
        ) : (
          <p className="mb-10 text-gray-500">
            No reviews yet — be the first to share your thoughts!
          </p>
        )}

        {/* Write-a-review form */}
        <div className="max-w-lg rounded-xl border border-gray-200 bg-gray-50 p-6">
          <h3 className="mb-5 text-lg font-bold text-gray-900">Write a Review</h3>

          {!user ? (
            <p className="text-sm text-gray-600">
              <Link
                to="/login"
                className="font-semibold text-gray-900 underline hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded"
              >
                Sign in
              </Link>{' '}
              to leave a review.
            </p>
          ) : (
            <form onSubmit={handleReviewSubmit} noValidate>
              <div className="mb-4">
                <label className="mb-2 block text-sm font-semibold text-gray-700">
                  Your Rating
                </label>
                <StarRating
                  rating={reviewRating}
                  interactive
                  onChange={setReviewRating}
                />
              </div>

              <div className="mb-4">
                <label
                  htmlFor="review-comment"
                  className="mb-2 block text-sm font-semibold text-gray-700"
                >
                  Comment <span className="font-normal text-gray-400">(optional)</span>
                </label>
                <textarea
                  id="review-comment"
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  rows={4}
                  placeholder="What did you think of these boots?"
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 resize-y"
                />
              </div>

              {reviewSuccess && (
                <p className="mb-3 text-sm font-medium text-green-700" role="status">
                  ✓ {reviewSuccess}
                </p>
              )}
              {reviewError && (
                <p className="mb-3 text-sm font-medium text-red-600" role="alert">
                  {reviewError}
                </p>
              )}

              <button
                type="submit"
                disabled={reviewSubmitting}
                className="rounded-lg bg-gray-900 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-700 disabled:cursor-wait disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-gray-900"
              >
                {reviewSubmitting ? 'Submitting…' : 'Submit Review'}
              </button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
};

export { ProductDetailPage };
export default ProductDetailPage;
