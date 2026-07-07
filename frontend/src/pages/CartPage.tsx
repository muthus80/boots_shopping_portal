import React, { useEffect, useState, useCallback } from 'react';
import { getCart, updateCartItem, removeCartItem } from '../api/cart';
import { Cart, CartItem } from '../types/index';

export const CartPage: React.FC = () => {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingItems, setUpdatingItems] = useState<Set<string>>(new Set());

  const fetchCart = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getCart();
      setCart(data);
    } catch (err: unknown) {
      setError('Failed to load cart. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  const handleQuantityChange = async (item: CartItem, newQuantity: number) => {
    if (newQuantity < 1) return;
    setUpdatingItems((prev) => new Set(prev).add(item.id));
    try {
      const updatedCart = await updateCartItem(item.id, newQuantity);
      setCart(updatedCart);
    } catch (err: unknown) {
      setError('Failed to update item quantity. Please try again.');
    } finally {
      setUpdatingItems((prev) => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    }
  };

  const handleRemoveItem = async (itemId: string) => {
    setUpdatingItems((prev) => new Set(prev).add(itemId));
    try {
      const updatedCart = await removeCartItem(itemId);
      setCart(updatedCart);
    } catch (err: unknown) {
      setError('Failed to remove item. Please try again.');
    } finally {
      setUpdatingItems((prev) => {
        const next = new Set(prev);
        next.delete(itemId);
        return next;
      });
    }
  };

  const handleProceedToCheckout = () => {
    window.location.href = '/checkout';
  };

  const calculateTotal = (items: CartItem[]): number => {
    return items.reduce((sum, item) => {
      const price = item.variant?.price ?? 0;
      return sum + price * item.quantity;
    }, 0);
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <h1 style={styles.title}>Your Cart</h1>
        <p style={styles.message}>Loading your cart...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <h1 style={styles.title}>Your Cart</h1>
        <p style={styles.errorMessage}>{error}</p>
        <button style={styles.retryButton} onClick={fetchCart}>
          Retry
        </button>
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div style={styles.container}>
        <h1 style={styles.title}>Your Cart</h1>
        <p style={styles.message}>Your cart is empty.</p>
        <button style={styles.continueShoppingButton} onClick={() => (window.location.href = '/products')}>
          Continue Shopping
        </button>
      </div>
    );
  }

  const total = calculateTotal(cart.items);

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Your Cart</h1>
      {error && <p style={styles.errorMessage}>{error}</p>}
      <div style={styles.cartContent}>
        <div style={styles.itemsList}>
          {cart.items.map((item: CartItem) => {
            const isUpdating = updatingItems.has(item.id);
            const price = item.variant?.price ?? 0;
            const itemTotal = price * item.quantity;

            return (
              <div key={item.id} style={{ ...styles.cartItem, opacity: isUpdating ? 0.6 : 1 }}>
                <div style={styles.itemInfo}>
                  <div style={styles.itemName}>
                    {item.variant?.product_id ?? 'Product'}
                  </div>
                  {item.variant && (
                    <div style={styles.itemVariant}>
                      {item.variant.size && <span>Size: {item.variant.size}</span>}
                      {item.variant.color && <span style={{ marginLeft: '8px' }}>Color: {item.variant.color}</span>}
                    </div>
                  )}
                  <div style={styles.itemPrice}>£{price.toFixed(2)} each</div>
                </div>
                <div style={styles.quantityControls}>
                  <button
                    style={styles.quantityButton}
                    onClick={() => handleQuantityChange(item, item.quantity - 1)}
                    disabled={isUpdating || item.quantity <= 1}
                    aria-label="Decrease quantity"
                  >
                    −
                  </button>
                  <span style={styles.quantityDisplay}>{item.quantity}</span>
                  <button
                    style={styles.quantityButton}
                    onClick={() => handleQuantityChange(item, item.quantity + 1)}
                    disabled={isUpdating}
                    aria-label="Increase quantity"
                  >
                    +
                  </button>
                </div>
                <div style={styles.itemTotal}>£{itemTotal.toFixed(2)}</div>
                <button
                  style={styles.removeButton}
                  onClick={() => handleRemoveItem(item.id)}
                  disabled={isUpdating}
                  aria-label="Remove item"
                >
                  Remove
                </button>
              </div>
            );
          })}
        </div>
        <div style={styles.orderSummary}>
          <h2 style={styles.summaryTitle}>Order Summary</h2>
          <div style={styles.summaryRow}>
            <span>Subtotal ({cart.items.length} {cart.items.length === 1 ? 'item' : 'items'})</span>
            <span>£{total.toFixed(2)}</span>
          </div>
          <div style={styles.summaryRow}>
            <span>Shipping</span>
            <span>Calculated at checkout</span>
          </div>
          <div style={{ ...styles.summaryRow, ...styles.totalRow }}>
            <span>Total</span>
            <span>£{total.toFixed(2)}</span>
          </div>
          <button
            style={styles.checkoutButton}
            onClick={handleProceedToCheckout}
            disabled={cart.items.length === 0}
          >
            Proceed to Checkout
          </button>
          <button
            style={styles.continueShoppingButton}
            onClick={() => (window.location.href = '/products')}
          >
            Continue Shopping
          </button>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '32px 16px',
    fontFamily: 'Arial, sans-serif',
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    marginBottom: '24px',
    color: '#1a1a1a',
  },
  message: {
    fontSize: '16px',
    color: '#555',
    marginBottom: '16px',
  },
  errorMessage: {
    fontSize: '15px',
    color: '#c0392b',
    marginBottom: '16px',
    padding: '12px',
    backgroundColor: '#fdecea',
    borderRadius: '6px',
  },
  retryButton: {
    padding: '10px 20px',
    backgroundColor: '#333',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  cartContent: {
    display: 'flex',
    gap: '32px',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
  },
  itemsList: {
    flex: '1 1 500px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  cartItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
    backgroundColor: '#fff',
    flexWrap: 'wrap',
    transition: 'opacity 0.2s',
  },
  itemInfo: {
    flex: '1 1 200px',
  },
  itemName: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#1a1a1a',
    marginBottom: '4px',
  },
  itemVariant: {
    fontSize: '13px',
    color: '#666',
    marginBottom: '4px',
  },
  itemPrice: {
    fontSize: '14px',
    color: '#444',
  },
  quantityControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  quantityButton: {
    width: '32px',
    height: '32px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    backgroundColor: '#f5f5f5',
    cursor: 'pointer',
    fontSize: '18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    lineHeight: 1,
  },
  quantityDisplay: {
    minWidth: '32px',
    textAlign: 'center',
    fontSize: '16px',
    fontWeight: 600,
  },
  itemTotal: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#1a1a1a',
    minWidth: '70px',
    textAlign: 'right',
  },
  removeButton: {
    padding: '6px 12px',
    backgroundColor: 'transparent',
    color: '#c0392b',
    border: '1px solid #c0392b',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '13px',
    transition: 'background-color 0.2s',
  },
  orderSummary: {
    flex: '0 1 320px',
    padding: '24px',
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
    backgroundColor: '#fafafa',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  summaryTitle: {
    fontSize: '20px',
    fontWeight: 700,
    marginBottom: '8px',
    color: '#1a1a1a',
  },
  summaryRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '15px',
    color: '#444',
  },
  totalRow: {
    fontWeight: 700,
    fontSize: '17px',
    color: '#1a1a1a',
    borderTop: '1px solid #e0e0e0',
    paddingTop: '12px',
    marginTop: '4px',
  },
  checkoutButton: {
    padding: '14px',
    backgroundColor: '#1a1a1a',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: 600,
    marginTop: '8px',
    transition: 'background-color 0.2s',
  },
  continueShoppingButton: {
    padding: '12px',
    backgroundColor: 'transparent',
    color: '#1a1a1a',
    border: '1px solid #1a1a1a',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '15px',
    transition: 'background-color 0.2s',
  },
};

export default CartPage;