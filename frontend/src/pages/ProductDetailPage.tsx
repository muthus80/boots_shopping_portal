import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProduct } from '../api/products';
import { addCartItem } from '../api/cart';
import { useAuth } from '../stores/authStore';
import { Product, ProductVariant, Review } from '../types/index';
import { apiClient } from '../api/client';

// Extended types for fields the API returns but are not yet in the base types
interface ProductVariantExtended extends ProductVariant {
  price?: number;
}

interface ProductExtended extends Omit<Product, 'variants'> {
  variants?: ProductVariantExtended[];
  reviews?: Review[];
  category?: { id: string; name: string };
}

interface CreateReviewPayload {
  rating: number;
  comment?: string;
}

const createReviewForProduct = async (
  productId: string,
  payload: CreateReviewPayload
): Promise<Review> => {
  const response = await apiClient.post<Review>(
    `/api/v1/products/${productId}/reviews`,
    payload
  );
  return response.data;
};

const ProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [product, setProduct] = useState<ProductExtended | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedVariant, setSelectedVariant] = useState<ProductVariantExtended | null>(null);
  const [quantity, setQuantity] = useState<number>(1);
  const [addingToCart, setAddingToCart] = useState<boolean>(false);
  const [cartMessage, setCartMessage] = useState<string | null>(null);

  const [reviewRating, setReviewRating] = useState<number>(5);
  const [reviewComment, setReviewComment] = useState<string>('');
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewSuccess, setReviewSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const fetchProduct = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getProduct(id) as ProductExtended;
        setProduct(data);
        if (data.variants && data.variants.length > 0) {
          setSelectedVariant(data.variants[0]);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load product.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    };
    fetchProduct();
  }, [id]);

  const handleVariantSelect = (variant: ProductVariantExtended) => {
    setSelectedVariant(variant);
    setQuantity(1);
    setCartMessage(null);
  };

  const handleAddToCart = async () => {
    if (!selectedVariant) {
      setCartMessage('Please select a variant.');
      return;
    }
    if (!user) {
      navigate('/login');
      return;
    }
    setAddingToCart(true);
    setCartMessage(null);
    try {
      await addCartItem(selectedVariant.id, quantity);
      setCartMessage('Item added to cart!');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add item to cart.';
      setCartMessage(msg);
    } finally {
      setAddingToCart(false);
    }
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) {
      navigate('/login');
      return;
    }
    if (!id) return;
    setSubmittingReview(true);
    setReviewError(null);
    setReviewSuccess(null);
    try {
      await createReviewForProduct(id, { rating: reviewRating, comment: reviewComment });
      setReviewSuccess('Review submitted successfully!');
      setReviewRating(5);
      setReviewComment('');
      const updated = await getProduct(id) as ProductExtended;
      setProduct(updated);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit review.';
      setReviewError(msg);
    } finally {
      setSubmittingReview(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <p style={styles.loadingText}>Loading product...</p>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div style={styles.container}>
        <p style={styles.errorText}>{error || 'Product not found.'}</p>
        <button style={styles.backButton} onClick={() => navigate(-1)}>
          Go Back
        </button>
      </div>
    );
  }

  const reviews = product.reviews ?? [];
  const averageRating =
    reviews.length > 0
      ? (
          reviews.reduce((sum: number, r: Review) => sum + r.rating, 0) /
          reviews.length
        ).toFixed(1)
      : null;

  const displayPrice = selectedVariant?.price != null
    ? Number(selectedVariant.price)
    : Number(product.base_price);

  return (
    <div style={styles.container}>
      <button style={styles.backButton} onClick={() => navigate(-1)}>
        ← Back
      </button>

      <div style={styles.productSection}>
        <div style={styles.imageContainer}>
          {product.image_url ? (
            <img src={product.image_url} alt={product.name} style={styles.productImage} />
          ) : (
            <div style={styles.imagePlaceholder}>No Image</div>
          )}
        </div>

        <div style={styles.detailsContainer}>
          <h1 style={styles.productName}>{product.name}</h1>
          {product.category && (
            <p style={styles.category}>{product.category.name}</p>
          )}
          <p style={styles.description}>{product.description}</p>

          {averageRating && (
            <p style={styles.rating}>
              ⭐ {averageRating} ({reviews.length} review
              {reviews.length !== 1 ? 's' : ''})
            </p>
          )}

          <div style={styles.priceRow}>
            <span style={styles.price}>
              ${displayPrice.toFixed(2)}
            </span>
            {selectedVariant && selectedVariant.stock_quantity <= 0 && (
              <span style={styles.outOfStock}>Out of Stock</span>
            )}
            {selectedVariant && selectedVariant.stock_quantity > 0 && (
              <span style={styles.inStock}>In Stock ({selectedVariant.stock_quantity} left)</span>
            )}
          </div>

          {product.variants && product.variants.length > 0 && (
            <div style={styles.variantSection}>
              <h3 style={styles.variantTitle}>Select Variant</h3>
              <div style={styles.variantGrid}>
                {product.variants.map((variant: ProductVariantExtended) => (
                  <button
                    key={variant.id}
                    style={{
                      ...styles.variantButton,
                      ...(selectedVariant?.id === variant.id ? styles.variantButtonSelected : {}),
                      ...(variant.stock_quantity <= 0 ? styles.variantButtonDisabled : {}),
                    }}
                    onClick={() => handleVariantSelect(variant)}
                    disabled={variant.stock_quantity <= 0}
                  >
                    <span style={styles.variantSize}>{variant.size}</span>
                    {variant.color && (
                      <span style={styles.variantColor}>{variant.color}</span>
                    )}
                    {variant.price != null && (
                      <span style={styles.variantPrice}>${Number(variant.price).toFixed(2)}</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={styles.quantityRow}>
            <label style={styles.quantityLabel}>Quantity:</label>
            <button
              style={styles.qtyBtn}
              onClick={() => setQuantity((q) => Math.max(1, q - 1))}
              disabled={quantity <= 1}
            >
              −
            </button>
            <span style={styles.quantityValue}>{quantity}</span>
            <button
              style={styles.qtyBtn}
              onClick={() =>
                setQuantity((q) =>
                  selectedVariant ? Math.min(selectedVariant.stock_quantity, q + 1) : q + 1
                )
              }
              disabled={
                selectedVariant ? quantity >= selectedVariant.stock_quantity : false
              }
            >
              +
            </button>
          </div>

          <button
            style={{
              ...styles.addToCartButton,
              ...(addingToCart || (selectedVariant && selectedVariant.stock_quantity <= 0)
                ? styles.addToCartButtonDisabled
                : {}),
            }}
            onClick={handleAddToCart}
            disabled={addingToCart || (selectedVariant ? selectedVariant.stock_quantity <= 0 : false)}
          >
            {addingToCart ? 'Adding...' : 'Add to Cart'}
          </button>

          {cartMessage && (
            <p
              style={
                cartMessage.includes('added')
                  ? styles.successMessage
                  : styles.errorMessage
              }
            >
              {cartMessage}
            </p>
          )}
        </div>
      </div>

      <div style={styles.reviewsSection}>
        <h2 style={styles.reviewsTitle}>Customer Reviews</h2>

        {reviews.length > 0 ? (
          <div style={styles.reviewsList}>
            {reviews.map((review: Review) => (
              <div key={review.id} style={styles.reviewCard}>
                <div style={styles.reviewHeader}>
                  <span style={styles.reviewRating}>
                    {'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}
                  </span>
                  <span style={styles.reviewDate}>
                    {new Date(review.created_at).toLocaleDateString()}
                  </span>
                </div>
                {review.body && (
                  <p style={styles.reviewComment}>{review.body}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p style={styles.noReviews}>No reviews yet. Be the first to review!</p>
        )}

        <div style={styles.reviewFormContainer}>
          <h3 style={styles.reviewFormTitle}>Write a Review</h3>
          {!user && (
            <p style={styles.loginPrompt}>
              <button style={styles.loginLink} onClick={() => navigate('/login')}>
                Log in
              </button>{' '}
              to submit a review.
            </p>
          )}
          {user && (
            <form onSubmit={handleReviewSubmit} style={styles.reviewForm}>
              <div style={styles.formGroup}>
                <label style={styles.formLabel}>Rating</label>
                <div style={styles.starSelector}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      style={{
                        ...styles.starButton,
                        color: star <= reviewRating ? '#f59e0b' : '#d1d5db',
                      }}
                      onClick={() => setReviewRating(star)}
                    >
                      ★
                    </button>
                  ))}
                </div>
              </div>
              <div style={styles.formGroup}>
                <label style={styles.formLabel}>Comment (optional)</label>
                <textarea
                  style={styles.textarea}
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  rows={4}
                  placeholder="Share your thoughts about this product..."
                />
              </div>
              {reviewError && <p style={styles.errorMessage}>{reviewError}</p>}
              {reviewSuccess && <p style={styles.successMessage}>{reviewSuccess}</p>}
              <button
                type="submit"
                style={{
                  ...styles.submitReviewButton,
                  ...(submittingReview ? styles.submitReviewButtonDisabled : {}),
                }}
                disabled={submittingReview}
              >
                {submittingReview ? 'Submitting...' : 'Submit Review'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '24px 16px',
    fontFamily: 'sans-serif',
    color: '#111827',
  },
  loadingText: {
    textAlign: 'center',
    fontSize: '18px',
    color: '#6b7280',
    marginTop: '60px',
  },
  errorText: {
    textAlign: 'center',
    fontSize: '18px',
    color: '#ef4444',
    marginTop: '60px',
  },
  backButton: {
    background: 'none',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: '14px',
    color: '#374151',
    marginBottom: '24px',
  },
  productSection: {
    display: 'flex',
    gap: '40px',
    flexWrap: 'wrap',
    marginBottom: '48px',
  },
  imageContainer: {
    flex: '0 0 400px',
    maxWidth: '100%',
  },
  productImage: {
    width: '100%',
    borderRadius: '12px',
    objectFit: 'cover',
    maxHeight: '450px',
  },
  imagePlaceholder: {
    width: '100%',
    height: '350px',
    background: '#f3f4f6',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#9ca3af',
    fontSize: '16px',
  },
  detailsContainer: {
    flex: '1 1 300px',
  },
  productName: {
    fontSize: '28px',
    fontWeight: 700,
    marginBottom: '8px',
  },
  category: {
    fontSize: '14px',
    color: '#6b7280',
    marginBottom: '12px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  description: {
    fontSize: '16px',
    lineHeight: '1.6',
    color: '#374151',
    marginBottom: '16px',
  },
  rating: {
    fontSize: '16px',
    color: '#f59e0b',
    marginBottom: '12px',
  },
  priceRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '20px',
  },
  price: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#111827',
  },
  outOfStock: {
    fontSize: '14px',
    color: '#ef4444',
    fontWeight: 600,
  },
  inStock: {
    fontSize: '14px',
    color: '#10b981',
    fontWeight: 600,
  },
  variantSection: {
    marginBottom: '20px',
  },
  variantTitle: {
    fontSize: '16px',
    fontWeight: 600,
    marginBottom: '10px',
  },
  variantGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '10px',
  },
  variantButton: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '10px 14px',
    border: '2px solid #d1d5db',
    borderRadius: '8px',
    background: '#fff',
    cursor: 'pointer',
    fontSize: '13px',
    color: '#374151',
    minWidth: '80px',
    transition: 'border-color 0.15s',
  },
  variantButtonSelected: {
    borderColor: '#6366f1',
    background: '#eef2ff',
    color: '#4338ca',
  },
  variantButtonDisabled: {
    opacity: 0.4,
    cursor: 'not-allowed',
  },
  variantSize: {
    fontWeight: 700,
    fontSize: '14px',
  },
  variantColor: {
    fontSize: '12px',
    color: '#6b7280',
  },
  variantPrice: {
    fontSize: '13px',
    fontWeight: 600,
    marginTop: '4px',
  },
  quantityRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '20px',
  },
  quantityLabel: {
    fontSize: '15px',
    fontWeight: 600,
  },
  qtyBtn: {
    width: '32px',
    height: '32px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    background: '#f9fafb',
    cursor: 'pointer',
    fontSize: '18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    lineHeight: 1,
  },
  quantityValue: {
    fontSize: '16px',
    fontWeight: 600,
    minWidth: '24px',
    textAlign: 'center',
  },
  addToCartButton: {
    width: '100%',
    padding: '14px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 700,
    cursor: 'pointer',
    marginBottom: '12px',
    transition: 'background 0.15s',
  },
  addToCartButtonDisabled: {
    background: '#a5b4fc',
    cursor: 'not-allowed',
  },
  successMessage: {
    color: '#10b981',
    fontSize: '14px',
    fontWeight: 600,
  },
  errorMessage: {
    color: '#ef4444',
    fontSize: '14px',
    fontWeight: 600,
  },
  reviewsSection: {
    borderTop: '1px solid #e5e7eb',
    paddingTop: '40px',
  },
  reviewsTitle: {
    fontSize: '22px',
    fontWeight: 700,
    marginBottom: '24px',
  },
  reviewsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    marginBottom: '40px',
  },
  reviewCard: {
    background: '#f9fafb',
    borderRadius: '10px',
    padding: '16px 20px',
    border: '1px solid #e5e7eb',
  },
  reviewHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  reviewRating: {
    color: '#f59e0b',
    fontSize: '18px',
    letterSpacing: '2px',
  },
  reviewDate: {
    fontSize: '13px',
    color: '#9ca3af',
  },
  reviewComment: {
    fontSize: '15px',
    color: '#374151',
    lineHeight: '1.5',
    margin: 0,
  },
  noReviews: {
    color: '#6b7280',
    fontSize: '15px',
    marginBottom: '32px',
  },
  reviewFormContainer: {
    background: '#f9fafb',
    borderRadius: '12px',
    padding: '28px',
    border: '1px solid #e5e7eb',
    maxWidth: '600px',
  },
  reviewFormTitle: {
    fontSize: '18px',
    fontWeight: 700,
    marginBottom: '20px',
  },
  loginPrompt: {
    fontSize: '15px',
    color: '#374151',
  },
  loginLink: {
    background: 'none',
    border: 'none',
    color: '#6366f1',
    cursor: 'pointer',
    fontSize: '15px',
    fontWeight: 600,
    padding: 0,
    textDecoration: 'underline',
  },
  reviewForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  formLabel: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#374151',
  },
  starSelector: {
    display: 'flex',
    gap: '4px',
  },
  starButton: {
    background: 'none',
    border: 'none',
    fontSize: '28px',
    cursor: 'pointer',
    padding: '0 2px',
    lineHeight: 1,
    transition: 'color 0.1s',
  },
  textarea: {
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    resize: 'vertical',
    fontFamily: 'sans-serif',
    color: '#111827',
    background: '#fff',
  },
  submitReviewButton: {
    padding: '12px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '15px',
    fontWeight: 700,
    cursor: 'pointer',
    alignSelf: 'flex-start',
    minWidth: '160px',
  },
  submitReviewButtonDisabled: {
    background: '#a5b4fc',
    cursor: 'not-allowed',
  },
};

export { ProductDetailPage };
export default ProductDetailPage;
