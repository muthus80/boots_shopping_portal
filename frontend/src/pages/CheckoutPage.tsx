/**
 * CheckoutPage — T-030 / US-011
 *
 * 5-step-or-fewer guest checkout flow (ADR-003 / NFR-usability):
 *   Step 1 — Identity     (guest email OR "you're signed in" banner)
 *   Step 2 — Shipping     (react-hook-form validated address form)
 *   Step 3 — Payment      (Stripe Elements — card data never on our servers)
 *   Done   — Confirmation (order summary)
 *
 * Authenticated users skip Step 1 automatically.
 *
 * PCI compliance: the Stripe CardElement handles raw card data inside an
 * iframe; only the resulting payment_intent_id ever reaches our backend.
 *
 * Route: /checkout  (NOT protected — allows guest access per US-011)
 */

import React, { useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import {
  Elements,
  CardElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import type { StripeCardElementOptions } from '@stripe/stripe-js';
import { useQuery } from '@tanstack/react-query';
import { getCart } from '../api/cart';
import {
  createPaymentIntent,
  confirmOrder,
} from '../api/checkout';
import type { ConfirmOrderResponse, ShippingAddress } from '../api/checkout';
import { useAuth } from '../stores/authStore';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

// ── Stripe init ───────────────────────────────────────────────────────────────

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '');

const CARD_ELEMENT_OPTIONS: StripeCardElementOptions = {
  style: {
    base: {
      color: '#111827',
      fontFamily: '"Inter", ui-sans-serif, system-ui, sans-serif',
      fontSmoothing: 'antialiased',
      fontSize: '16px',
      '::placeholder': { color: '#9ca3af' },
    },
    invalid: { color: '#dc2626', iconColor: '#dc2626' },
  },
};

// ── Step tracker ──────────────────────────────────────────────────────────────

type CheckoutStep = 'identity' | 'shipping' | 'payment' | 'confirmation';

// ── Form types ────────────────────────────────────────────────────────────────

interface IdentityFormValues {
  guest_email: string;
}

interface ShippingFormValues {
  shipping_name: string;
  line1: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

// ── StepIndicator ─────────────────────────────────────────────────────────────

interface StepIndicatorProps {
  current: CheckoutStep;
  isGuest: boolean;
}

const STEP_LABELS: { key: CheckoutStep; label: string }[] = [
  { key: 'identity', label: 'Identity' },
  { key: 'shipping', label: 'Shipping' },
  { key: 'payment', label: 'Payment' },
  { key: 'confirmation', label: 'Confirmation' },
];

const STEP_ORDER: CheckoutStep[] = ['identity', 'shipping', 'payment', 'confirmation'];

const StepIndicator: React.FC<StepIndicatorProps> = ({ current, isGuest }) => {
  const visibleSteps = isGuest
    ? STEP_LABELS
    : STEP_LABELS.filter((s) => s.key !== 'identity');

  const currentIdx = STEP_ORDER.indexOf(current);

  return (
    <nav aria-label="Checkout progress" className="mb-8">
      <ol className="flex items-center justify-center gap-0">
        {visibleSteps.map((step, i) => {
          const stepIdx = STEP_ORDER.indexOf(step.key);
          const isActive = step.key === current;
          const isCompleted = stepIdx < currentIdx;

          return (
            <li key={step.key} className="flex items-center">
              {i > 0 && (
                <div
                  className={`h-0.5 w-8 sm:w-16 ${isCompleted ? 'bg-gray-900' : 'bg-gray-200'}`}
                  aria-hidden="true"
                />
              )}
              <div className="flex flex-col items-center gap-1">
                <span
                  aria-current={isActive ? 'step' : undefined}
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-colors ${
                    isActive
                      ? 'bg-gray-900 text-white'
                      : isCompleted
                      ? 'bg-gray-900 text-white'
                      : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {isCompleted ? '✓' : i + 1}
                </span>
                <span
                  className={`hidden sm:block text-xs font-medium ${
                    isActive ? 'text-gray-900' : 'text-gray-400'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

// ── IdentityStep ──────────────────────────────────────────────────────────────

interface IdentityStepProps {
  onSubmit: (email: string) => void;
  onSignIn: () => void;
}

const IdentityStep: React.FC<IdentityStepProps> = ({ onSubmit, onSignIn }) => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<IdentityFormValues>({ mode: 'onBlur' });

  const handleFormSubmit = (data: IdentityFormValues) => {
    onSubmit(data.guest_email.trim());
  };

  return (
    <section aria-labelledby="identity-heading">
      <h2
        id="identity-heading"
        className="mb-2 text-xl font-bold text-gray-900"
      >
        How would you like to check out?
      </h2>
      <p className="mb-6 text-sm text-gray-500">
        Sign in for a faster experience, or continue as a guest.
      </p>

      {/* Sign-in option */}
      <div className="mb-4 rounded-xl border border-gray-200 bg-gray-50 p-5">
        <p className="mb-3 text-sm font-semibold text-gray-900">
          Already have an account?
        </p>
        <button
          type="button"
          onClick={onSignIn}
          className="rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
        >
          Sign In
        </button>
      </div>

      {/* Guest option */}
      <div className="rounded-xl border border-gray-200 p-5">
        <p className="mb-3 text-sm font-semibold text-gray-900">
          Continue as guest
        </p>
        <form
          onSubmit={handleSubmit(handleFormSubmit)}
          noValidate
          aria-label="Guest checkout identity form"
        >
          <div className="mb-4">
            <label
              htmlFor="guest_email"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              Email address <span aria-hidden="true">*</span>
            </label>
            <input
              id="guest_email"
              type="email"
              autoComplete="email"
              aria-required="true"
              aria-describedby={errors.guest_email ? 'guest-email-error' : undefined}
              className={`w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 ${
                errors.guest_email
                  ? 'border-red-400 focus:border-red-400'
                  : 'border-gray-300 focus:border-gray-900'
              }`}
              placeholder="you@example.com"
              {...register('guest_email', {
                required: 'Email address is required.',
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: 'Please enter a valid email address.',
                },
              })}
            />
            {errors.guest_email && (
              <p
                id="guest-email-error"
                role="alert"
                className="mt-1 text-xs text-red-600"
              >
                {errors.guest_email.message}
              </p>
            )}
          </div>

          <p className="mb-4 text-xs text-gray-500">
            Your order confirmation will be sent to this address.
          </p>

          <button
            type="submit"
            className="w-full rounded-lg bg-gray-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
          >
            Continue as Guest
          </button>
        </form>
      </div>
    </section>
  );
};

// ── ShippingStep ──────────────────────────────────────────────────────────────

interface ShippingStepProps {
  onSubmit: (values: ShippingFormValues) => void;
  onBack?: () => void;
  defaultValues?: Partial<ShippingFormValues>;
}

const ShippingStep: React.FC<ShippingStepProps> = ({
  onSubmit,
  onBack,
  defaultValues,
}) => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ShippingFormValues>({
    mode: 'onBlur',
    defaultValues: { country: 'US', ...defaultValues },
  });

  return (
    <section aria-labelledby="shipping-heading">
      <h2
        id="shipping-heading"
        className="mb-6 text-xl font-bold text-gray-900"
      >
        Shipping address
      </h2>

      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        aria-label="Shipping address form"
      >
        {/* Full name */}
        <div className="mb-4">
          <label
            htmlFor="shipping_name"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Full name <span aria-hidden="true">*</span>
          </label>
          <input
            id="shipping_name"
            type="text"
            autoComplete="name"
            aria-required="true"
            aria-describedby={errors.shipping_name ? 'shipping-name-error' : undefined}
            placeholder="Jane Smith"
            className={`w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 ${
              errors.shipping_name
                ? 'border-red-400 focus:border-red-400'
                : 'border-gray-300 focus:border-gray-900'
            }`}
            {...register('shipping_name', {
              required: 'Full name is required.',
              minLength: { value: 2, message: 'Name must be at least 2 characters.' },
            })}
          />
          {errors.shipping_name && (
            <p id="shipping-name-error" role="alert" className="mt-1 text-xs text-red-600">
              {errors.shipping_name.message}
            </p>
          )}
        </div>

        {/* Address line 1 */}
        <div className="mb-4">
          <label
            htmlFor="line1"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Address <span aria-hidden="true">*</span>
          </label>
          <input
            id="line1"
            type="text"
            autoComplete="street-address"
            aria-required="true"
            aria-describedby={errors.line1 ? 'line1-error' : undefined}
            placeholder="123 Main St"
            className={`w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 ${
              errors.line1
                ? 'border-red-400 focus:border-red-400'
                : 'border-gray-300 focus:border-gray-900'
            }`}
            {...register('line1', { required: 'Street address is required.' })}
          />
          {errors.line1 && (
            <p id="line1-error" role="alert" className="mt-1 text-xs text-red-600">
              {errors.line1.message}
            </p>
          )}
        </div>

        {/* City + State row */}
        <div className="mb-4 grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="city"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              City <span aria-hidden="true">*</span>
            </label>
            <input
              id="city"
              type="text"
              autoComplete="address-level2"
              aria-required="true"
              aria-describedby={errors.city ? 'city-error' : undefined}
              placeholder="New York"
              className={`w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 ${
                errors.city
                  ? 'border-red-400 focus:border-red-400'
                  : 'border-gray-300 focus:border-gray-900'
              }`}
              {...register('city', { required: 'City is required.' })}
            />
            {errors.city && (
              <p id="city-error" role="alert" className="mt-1 text-xs text-red-600">
                {errors.city.message}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="state"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              State / Region <span aria-hidden="true">*</span>
            </label>
            <input
              id="state"
              type="text"
              autoComplete="address-level1"
              aria-required="true"
              aria-describedby={errors.state ? 'state-error' : undefined}
              placeholder="NY"
              className={`w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 ${
                errors.state
                  ? 'border-red-400 focus:border-red-400'
                  : 'border-gray-300 focus:border-gray-900'
              }`}
              {...register('state', { required: 'State or region is required.' })}
            />
            {errors.state && (
              <p id="state-error" role="alert" className="mt-1 text-xs text-red-600">
                {errors.state.message}
              </p>
            )}
          </div>
        </div>

        {/* Postal code + Country row */}
        <div className="mb-6 grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="postal_code"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              Postal code <span aria-hidden="true">*</span>
            </label>
            <input
              id="postal_code"
              type="text"
              autoComplete="postal-code"
              aria-required="true"
              aria-describedby={errors.postal_code ? 'postal-code-error' : undefined}
              placeholder="10001"
              className={`w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 ${
                errors.postal_code
                  ? 'border-red-400 focus:border-red-400'
                  : 'border-gray-300 focus:border-gray-900'
              }`}
              {...register('postal_code', { required: 'Postal code is required.' })}
            />
            {errors.postal_code && (
              <p id="postal-code-error" role="alert" className="mt-1 text-xs text-red-600">
                {errors.postal_code.message}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="country"
              className="mb-1.5 block text-sm font-medium text-gray-700"
            >
              Country <span aria-hidden="true">*</span>
            </label>
            <select
              id="country"
              autoComplete="country"
              aria-required="true"
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 focus:border-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900"
              {...register('country', { required: 'Country is required.' })}
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

        {/* Actions */}
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-900"
            >
              ← Back
            </button>
          )}
          <button
            type="submit"
            className="flex-1 rounded-lg bg-gray-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 sm:flex-none sm:min-w-[10rem]"
          >
            Continue to Payment →
          </button>
        </div>
      </form>
    </section>
  );
};

// ── PaymentStep (inner — needs Stripe context) ────────────────────────────────

interface PaymentStepInnerProps {
  guestEmail: string | null;
  shipping: ShippingFormValues;
  onBack: () => void;
  onConfirmed: (order: ConfirmOrderResponse) => void;
}

const PaymentStepInner: React.FC<PaymentStepInnerProps> = ({
  guestEmail,
  shipping,
  onBack,
  onConfirmed,
}) => {
  const stripe = useStripe();
  const elements = useElements();

  const [isCreatingIntent, setIsCreatingIntent] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [intentError, setIntentError] = useState<string | null>(null);

  const handlePay = useCallback(async () => {
    if (!stripe || !elements) return;

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      setPaymentError('Card input not found. Please refresh and try again.');
      return;
    }

    setIsCreatingIntent(true);
    setPaymentError(null);
    setIntentError(null);

    let clientSecret: string;
    let paymentIntentId: string;

    // Step A — create payment intent server-side
    try {
      const shippingAddress: ShippingAddress = {
        line1: shipping.line1,
        city: shipping.city,
        state: shipping.state,
        postal_code: shipping.postal_code,
        country: shipping.country,
      };

      const intentPayload = {
        shipping_name: shipping.shipping_name,
        shipping_address: shippingAddress,
        ...(guestEmail ? { guest_email: guestEmail } : {}),
      };

      const intentData = await createPaymentIntent(intentPayload);
      clientSecret = intentData.client_secret;
      paymentIntentId = intentData.payment_intent_id;
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to initialise payment. Please try again.';
      setIntentError(msg);
      setIsCreatingIntent(false);
      return;
    }

    setIsCreatingIntent(false);
    setIsProcessing(true);

    // Step B — confirm card payment directly with Stripe
    const { error: stripeError, paymentIntent } = await stripe.confirmCardPayment(
      clientSecret,
      {
        payment_method: {
          card: cardElement,
          billing_details: { name: shipping.shipping_name },
        },
      }
    );

    if (stripeError) {
      setPaymentError(stripeError.message ?? 'Payment failed. Please try again.');
      setIsProcessing(false);
      return;
    }

    if (paymentIntent?.status !== 'succeeded') {
      setPaymentError('Payment was not completed. Please try again.');
      setIsProcessing(false);
      return;
    }

    // Step C — confirm order server-side using only the payment_intent_id
    try {
      const order = await confirmOrder({ payment_intent_id: paymentIntentId });
      onConfirmed(order);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Order confirmation failed. Please contact support.';
      setPaymentError(msg);
    } finally {
      setIsProcessing(false);
    }
  }, [stripe, elements, guestEmail, shipping, onConfirmed]);

  const isBusy = isCreatingIntent || isProcessing;

  return (
    <section aria-labelledby="payment-heading">
      <h2
        id="payment-heading"
        className="mb-2 text-xl font-bold text-gray-900"
      >
        Payment
      </h2>
      <p className="mb-6 text-sm text-gray-500">
        Your card details are handled securely by Stripe. We never see your full card number.
      </p>

      {/* Shipping summary */}
      <div className="mb-6 rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
        <p className="font-semibold text-gray-900">{shipping.shipping_name}</p>
        <p>{shipping.line1}</p>
        <p>
          {shipping.city}, {shipping.state} {shipping.postal_code}
        </p>
        <p>{shipping.country}</p>
        {guestEmail && <p className="mt-1 text-gray-500">{guestEmail}</p>}
      </div>

      {/* Card element */}
      <div className="mb-6">
        <label className="mb-1.5 block text-sm font-medium text-gray-700">
          Card details
        </label>
        <div
          className="rounded-lg border border-gray-300 bg-white p-3 focus-within:border-gray-900 focus-within:ring-2 focus-within:ring-gray-900"
          aria-label="Card details input"
        >
          <CardElement options={CARD_ELEMENT_OPTIONS} />
        </div>
      </div>

      {/* Errors */}
      {intentError && (
        <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {intentError}
        </div>
      )}
      {paymentError && (
        <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {paymentError}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={isBusy}
          className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-gray-900"
        >
          ← Back
        </button>
        <button
          type="button"
          onClick={handlePay}
          disabled={!stripe || isBusy}
          aria-busy={isBusy}
          className="flex-1 rounded-lg bg-gray-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 sm:flex-none sm:min-w-[10rem]"
        >
          {isBusy ? (
            <span className="flex items-center justify-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" aria-hidden="true" />
              {isCreatingIntent ? 'Preparing…' : 'Processing…'}
            </span>
          ) : (
            'Pay Now'
          )}
        </button>
      </div>
    </section>
  );
};

// ── CheckoutPage ──────────────────────────────────────────────────────────────
// Note: order confirmation is rendered by the standalone OrderConfirmationPage
// at /order-confirmation (T-032). On successful payment, CheckoutPage navigates
// there via React Router state, passing the ConfirmOrderResponse as state.order.

export const CheckoutPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();

  // Determine initial step — authenticated users skip identity
  const initialStep: CheckoutStep = isAuthenticated ? 'shipping' : 'identity';

  const [step, setStep] = useState<CheckoutStep>(initialStep);
  const [guestEmail, setGuestEmail] = useState<string | null>(null);
  const [shippingValues, setShippingValues] = useState<ShippingFormValues | null>(null);

  // Fetch cart to validate it is non-empty
  const { data: cart, isLoading: cartLoading, isError: cartError, refetch } = useQuery({
    queryKey: ['cart'],
    queryFn: getCart,
  });

  // ── Event handlers ────────────────────────────────────────────────────────

  const handleIdentitySubmit = useCallback((email: string) => {
    setGuestEmail(email);
    setStep('shipping');
  }, []);

  const handleSignIn = useCallback(() => {
    navigate('/login', { state: { returnTo: '/checkout' } });
  }, [navigate]);

  const handleShippingSubmit = useCallback((values: ShippingFormValues) => {
    setShippingValues(values);
    setStep('payment');
  }, []);

  const handleShippingBack = useCallback(() => {
    setStep(isAuthenticated ? 'identity' : 'identity');
  }, [isAuthenticated]);

  const handleAuthenticatedShippingBack = useCallback(() => {
    // Authenticated users have no identity step — go back to cart
    navigate('/cart');
  }, [navigate]);

  const handlePaymentBack = useCallback(() => {
    setStep('shipping');
  }, []);

  const handleOrderConfirmed = useCallback((order: ConfirmOrderResponse) => {
    navigate('/order-confirmation', { state: { order } });
  }, [navigate]);

  // ── Derived values ────────────────────────────────────────────────────────

  const isGuest = !isAuthenticated;
  // Pass guest_email only for unauthenticated users — authenticated requests
  // are identified by the JWT bearer token, so no guest_email is needed.
  const effectiveEmail = isAuthenticated ? null : guestEmail;

  // Confirmation step is now handled by the standalone OrderConfirmationPage —
  // the step state never reaches 'confirmation' inside CheckoutPage.

  // ── Loading / error / empty states ───────────────────────────────────────

  if (cartLoading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6 lg:px-8">
        <LoadingSpinner size="lg" label="Loading your cart…" centered />
      </div>
    );
  }

  if (cartError) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6 lg:px-8">
        <ErrorMessage
          heading="Could not load your cart"
          detail="Please check your connection and try again."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center sm:px-6 lg:px-8">
        <span className="mb-4 inline-block text-5xl" aria-hidden="true">🛒</span>
        <h1 className="mb-2 text-2xl font-bold text-gray-900">Your cart is empty</h1>
        <p className="mb-8 text-sm text-gray-500">
          Add some boots to your cart before checking out.
        </p>
        <Link
          to="/products"
          className="inline-block rounded-lg bg-gray-900 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
        >
          Browse Boots
        </Link>
      </div>
    );
  }

  // ── Main checkout layout ──────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="mb-6 text-3xl font-bold tracking-tight text-gray-900">Checkout</h1>

      <StepIndicator current={step} isGuest={isGuest} />

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        {/* ── Identity step ──────────────────────────────────────────────── */}
        {step === 'identity' && (
          <IdentityStep
            onSubmit={handleIdentitySubmit}
            onSignIn={handleSignIn}
          />
        )}

        {/* ── Auth banner (instead of identity step for signed-in users) ─── */}
        {step === 'shipping' && isAuthenticated && (
          <div className="mb-6 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
            <strong>Signed in as {user?.email}.</strong>{' '}
            Your order history will be saved to your account.
          </div>
        )}

        {/* ── Shipping step ──────────────────────────────────────────────── */}
        {step === 'shipping' && (
          <ShippingStep
            onSubmit={handleShippingSubmit}
            onBack={isAuthenticated ? handleAuthenticatedShippingBack : handleShippingBack}
            defaultValues={shippingValues ?? undefined}
          />
        )}

        {/* ── Payment step ───────────────────────────────────────────────── */}
        {step === 'payment' && shippingValues && (
          <Elements stripe={stripePromise}>
            <PaymentStepInner
              guestEmail={effectiveEmail}
              shipping={shippingValues}
              onBack={handlePaymentBack}
              onConfirmed={handleOrderConfirmed}
            />
          </Elements>
        )}
      </div>
    </div>
  );
};

export default CheckoutPage;
