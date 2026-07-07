import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Elements,
  CardElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import { loadStripe, StripeCardElementOptions } from '@stripe/stripe-js';
import { createPaymentIntent, confirmOrder } from '../api/checkout';
import { getCart } from '../api/cart';
import { useAuth } from '../stores/authStore';
import { Cart, Order } from '../types/index';

const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || '');

const CARD_ELEMENT_OPTIONS: StripeCardElementOptions = {
  style: {
    base: {
      color: '#32325d',
      fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
      fontSmoothing: 'antialiased',
      fontSize: '16px',
      '::placeholder': {
        color: '#aab7c4',
      },
    },
    invalid: {
      color: '#fa755a',
      iconColor: '#fa755a',
    },
  },
};

interface ShippingAddress {
  full_name: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

interface CheckoutFormProps {
  cart: Cart;
  onOrderConfirmed: (order: Order) => void;
}

const CheckoutForm: React.FC<CheckoutFormProps> = ({ cart, onOrderConfirmed }) => {
  const stripe = useStripe();
  const elements = useElements();
  const { user } = useAuth();

  const [shippingAddress, setShippingAddress] = useState<ShippingAddress>({
    full_name: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    postal_code: '',
    country: 'US',
  });

  const [clientSecret, setClientSecret] = useState<string>('');
  const [paymentIntentId, setPaymentIntentId] = useState<string>('');
  const [isLoadingIntent, setIsLoadingIntent] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [intentError, setIntentError] = useState<string | null>(null);

  const totalAmount = cart.items.reduce((sum, item) => {
    return sum + item.quantity * parseFloat(String(item.product_variant?.price ?? 0));
  }, 0);

  useEffect(() => {
    const fetchPaymentIntent = async () => {
      setIsLoadingIntent(true);
      setIntentError(null);
      try {
        const data = await createPaymentIntent({ cart_id: cart.id });
        setClientSecret(data.client_secret);
        setPaymentIntentId(data.payment_intent_id);
      } catch (err: any) {
        setIntentError(err?.message || 'Failed to initialize payment. Please try again.');
      } finally {
        setIsLoadingIntent(false);
      }
    };

    if (cart && cart.items.length > 0) {
      fetchPaymentIntent();
    }
  }, [cart]);

  const handleAddressChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setShippingAddress((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    if (!clientSecret) {
      setError('Payment not initialized. Please refresh and try again.');
      return;
    }

    setIsProcessing(true);
    setError(null);

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      setError('Card element not found.');
      setIsProcessing(false);
      return;
    }

    const { error: stripeError, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
      payment_method: {
        card: cardElement,
        billing_details: {
          name: shippingAddress.full_name,
          email: user?.email,
        },
      },
    });

    if (stripeError) {
      setError(stripeError.message || 'Payment failed. Please try again.');
      setIsProcessing(false);
      return;
    }

    if (paymentIntent && paymentIntent.status === 'succeeded') {
      try {
        const order = await confirmOrder({
          payment_intent_id: paymentIntentId,
          cart_id: cart.id,
          shipping_address: shippingAddress,
        });
        onOrderConfirmed(order);
      } catch (err: any) {
        setError(err?.message || 'Order confirmation failed. Please contact support.');
      }
    } else {
      setError('Payment was not completed. Please try again.');
    }

    setIsProcessing(false);
  };

  const isFormValid =
    shippingAddress.full_name.trim() !== '' &&
    shippingAddress.address_line1.trim() !== '' &&
    shippingAddress.city.trim() !== '' &&
    shippingAddress.state.trim() !== '' &&
    shippingAddress.postal_code.trim() !== '' &&
    shippingAddress.country.trim() !== '';

  return (
    <form onSubmit={handleSubmit} className="checkout-form">
      <div className="checkout-section">
        <h2>Shipping Address</h2>
        <div className="form-group">
          <label htmlFor="full_name">Full Name *</label>
          <input
            id="full_name"
            name="full_name"
            type="text"
            value={shippingAddress.full_name}
            onChange={handleAddressChange}
            required
            placeholder="John Doe"
          />
        </div>
        <div className="form-group">
          <label htmlFor="address_line1">Address Line 1 *</label>
          <input
            id="address_line1"
            name="address_line1"
            type="text"
            value={shippingAddress.address_line1}
            onChange={handleAddressChange}
            required
            placeholder="123 Main St"
          />
        </div>
        <div className="form-group">
          <label htmlFor="address_line2">Address Line 2</label>
          <input
            id="address_line2"
            name="address_line2"
            type="text"
            value={shippingAddress.address_line2}
            onChange={handleAddressChange}
            placeholder="Apt 4B"
          />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="city">City *</label>
            <input
              id="city"
              name="city"
              type="text"
              value={shippingAddress.city}
              onChange={handleAddressChange}
              required
              placeholder="New York"
            />
          </div>
          <div className="form-group">
            <label htmlFor="state">State *</label>
            <input
              id="state"
              name="state"
              type="text"
              value={shippingAddress.state}
              onChange={handleAddressChange}
              required
              placeholder="NY"
            />
          </div>
          <div className="form-group">
            <label htmlFor="postal_code">Postal Code *</label>
            <input
              id="postal_code"
              name="postal_code"
              type="text"
              value={shippingAddress.postal_code}
              onChange={handleAddressChange}
              required
              placeholder="10001"
            />
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="country">Country *</label>
          <select
            id="country"
            name="country"
            value={shippingAddress.country}
            onChange={handleAddressChange}
            required
          >
            <option value="US">United States</option>
            <option value="CA">Canada</option>
            <option value="GB">United Kingdom</option>
            <option value="AU">Australia</option>
            <option value="DE">Germany</option>
            <option value="FR">France</option>
          </select>
        </div>
      </div>

      <div className="checkout-section">
        <h2>Order Summary</h2>
        <div className="order-items">
          {cart.items.map((item) => (
            <div key={item.id} className="order-item">
              <span className="item-name">
                {item.product_variant?.product_id ?? 'Product'} — {item.product_variant?.size ?? ''}{' '}
                {item.product_variant?.color ?? ''}
              </span>
              <span className="item-qty">x{item.quantity}</span>
              <span className="item-price">
                ${(item.quantity * parseFloat(String(item.product_variant?.price ?? 0))).toFixed(2)}
              </span>
            </div>
          ))}
        </div>
        <div className="order-total">
          <strong>Total: ${totalAmount.toFixed(2)}</strong>
        </div>
      </div>

      <div className="checkout-section">
        <h2>Payment Details</h2>
        {intentError && (
          <div className="error-message" role="alert">
            {intentError}
          </div>
        )}
        {isLoadingIntent ? (
          <div className="loading-message">Initializing payment...</div>
        ) : (
          <div className="card-element-wrapper">
            <CardElement options={CARD_ELEMENT_OPTIONS} />
          </div>
        )}
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={!stripe || isProcessing || isLoadingIntent || !clientSecret || !isFormValid}
        className="submit-button"
      >
        {isProcessing ? 'Processing...' : `Pay $${totalAmount.toFixed(2)}`}
      </button>
    </form>
  );
};

interface OrderConfirmationProps {
  order: Order;
  onContinueShopping: () => void;
}

const OrderConfirmation: React.FC<OrderConfirmationProps> = ({ order, onContinueShopping }) => {
  return (
    <div className="order-confirmation">
      <div className="confirmation-icon">✓</div>
      <h2>Order Confirmed!</h2>
      <p>Thank you for your purchase. Your order has been placed successfully.</p>
      <div className="order-details">
        <p>
          <strong>Order ID:</strong> {order.id}
        </p>
        <p>
          <strong>Status:</strong> {order.status}
        </p>
        <p>
          <strong>Total:</strong> ${parseFloat(String(order.total_amount)).toFixed(2)}
        </p>
      </div>
      <div className="order-items-summary">
        <h3>Items Ordered</h3>
        {order.items.map((item) => (
          <div key={item.id} className="confirmation-item">
            <span>Variant ID: {item.product_variant_id}</span>
            <span>Qty: {item.quantity}</span>
            <span>${parseFloat(String(item.unit_price)).toFixed(2)} each</span>
          </div>
        ))}
      </div>
      <button onClick={onContinueShopping} className="continue-button">
        Continue Shopping
      </button>
    </div>
  );
};

export const CheckoutPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoadingCart, setIsLoadingCart] = useState<boolean>(true);
  const [cartError, setCartError] = useState<string | null>(null);
  const [confirmedOrder, setConfirmedOrder] = useState<Order | null>(null);

  useEffect(() => {
    if (!user) {
      navigate('/login', { replace: true });
      return;
    }

    const fetchCart = async () => {
      setIsLoadingCart(true);
      setCartError(null);
      try {
        const cartData = await getCart();
        setCart(cartData);
      } catch (err: any) {
        setCartError(err?.message || 'Failed to load cart. Please try again.');
      } finally {
        setIsLoadingCart(false);
      }
    };

    fetchCart();
  }, [user, navigate]);

  const handleOrderConfirmed = (order: Order) => {
    setConfirmedOrder(order);
  };

  const handleContinueShopping = () => {
    navigate('/products');
  };

  if (!user) {
    return null;
  }

  if (isLoadingCart) {
    return (
      <div className="checkout-page">
        <div className="loading-container">
          <p>Loading your cart...</p>
        </div>
      </div>
    );
  }

  if (cartError) {
    return (
      <div className="checkout-page">
        <div className="error-container">
          <p>{cartError}</p>
          <button onClick={() => navigate('/cart')} className="back-button">
            Back to Cart
          </button>
        </div>
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="checkout-page">
        <div className="empty-cart-container">
          <h2>Your cart is empty</h2>
          <p>Add some items to your cart before checking out.</p>
          <button onClick={() => navigate('/products')} className="shop-button">
            Shop Now
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="checkout-page">
      <div className="checkout-container">
        <h1>Checkout</h1>
        {confirmedOrder ? (
          <OrderConfirmation order={confirmedOrder} onContinueShopping={handleContinueShopping} />
        ) : (
          <Elements stripe={stripePromise}>
            <CheckoutForm cart={cart} onOrderConfirmed={handleOrderConfirmed} />
          </Elements>
        )}
      </div>
    </div>
  );
};

export default CheckoutPage;