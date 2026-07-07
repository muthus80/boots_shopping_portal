import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useAuth } from '../stores/authStore';
import axios from 'axios';

interface RegisterFormValues {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/;

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register: authRegister } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    mode: 'onBlur',
    defaultValues: {
      fullName: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  });

  const passwordValue = watch('password');

  const onSubmit = async (data: RegisterFormValues): Promise<void> => {
    setServerError(null);

    try {
      await authRegister({
        email: data.email,
        password: data.password,
        full_name: data.fullName || undefined,
      });
      setIsSuccess(true);
      // Navigate to home if the auth context set a user, otherwise to login
      navigate('/');
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        const detail = err.response?.data?.detail;

        if (status === 409) {
          setServerError('An account with this email already exists. Please sign in.');
        } else if (status === 422) {
          if (Array.isArray(detail)) {
            setServerError(detail.map((d: { msg: string }) => d.msg).join(' '));
          } else if (typeof detail === 'string') {
            setServerError(detail);
          } else {
            setServerError('Your password does not meet the complexity requirements.');
          }
        } else if (status === 429) {
          setServerError('Too many attempts. Please wait a moment before trying again.');
        } else if (typeof detail === 'string') {
          setServerError(detail);
        } else {
          setServerError('Registration failed. Please try again.');
        }
      } else if (err instanceof Error) {
        setServerError(err.message);
      } else {
        setServerError('An unexpected error occurred. Please try again.');
      }
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
        <div className="w-full max-w-md bg-white rounded-xl shadow-md p-10 text-center">
          <div
            className="mx-auto mb-4 flex items-center justify-center w-14 h-14 rounded-full bg-green-100"
            aria-hidden="true"
          >
            <svg
              className="w-7 h-7 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Account Created!</h1>
          <p className="text-gray-600 mb-6">
            A confirmation email has been sent to your inbox. You can now start shopping.
          </p>
          <Link
            to="/"
            className="inline-block w-full py-3 bg-gray-900 text-white font-semibold rounded-lg text-center hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 transition-colors"
          >
            Go to Homepage
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md bg-white rounded-xl shadow-md p-8 sm:p-10">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Create Account</h1>
          <p className="mt-2 text-sm text-gray-500">
            Join us and start shopping for boots!
          </p>
        </header>

        {serverError && (
          <div
            role="alert"
            aria-live="polite"
            className="mb-6 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            <svg
              className="mt-0.5 h-4 w-4 shrink-0"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
            <span>{serverError}</span>
          </div>
        )}

        <form
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          aria-label="Registration form"
        >
          <div className="space-y-5">
            {/* Full Name */}
            <div>
              <label
                htmlFor="fullName"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Full Name{' '}
                <span className="font-normal text-gray-400 text-xs">(optional)</span>
              </label>
              <input
                id="fullName"
                type="text"
                autoComplete="name"
                aria-label="Full name (optional)"
                aria-describedby={errors.fullName ? 'fullName-error' : undefined}
                aria-invalid={errors.fullName ? 'true' : 'false'}
                className={`w-full rounded-lg border px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors ${
                  errors.fullName
                    ? 'border-red-400 focus:ring-red-500'
                    : 'border-gray-300 focus:border-gray-900'
                }`}
                placeholder="Jane Doe"
                {...register('fullName', {
                  maxLength: {
                    value: 100,
                    message: 'Full name must be at most 100 characters.',
                  },
                })}
              />
              {errors.fullName && (
                <p id="fullName-error" role="alert" className="mt-1 text-xs text-red-600">
                  {errors.fullName.message}
                </p>
              )}
            </div>

            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Email Address <span className="text-red-500" aria-hidden="true">*</span>
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                aria-label="Email address"
                aria-required="true"
                aria-describedby={errors.email ? 'email-error' : undefined}
                aria-invalid={errors.email ? 'true' : 'false'}
                className={`w-full rounded-lg border px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors ${
                  errors.email
                    ? 'border-red-400 focus:ring-red-500'
                    : 'border-gray-300 focus:border-gray-900'
                }`}
                placeholder="you@example.com"
                {...register('email', {
                  required: 'Email address is required.',
                  pattern: {
                    value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    message: 'Please enter a valid email address.',
                  },
                })}
              />
              {errors.email && (
                <p id="email-error" role="alert" className="mt-1 text-xs text-red-600">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Password <span className="text-red-500" aria-hidden="true">*</span>
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                aria-label="Password"
                aria-required="true"
                aria-describedby="password-hint"
                aria-invalid={errors.password ? 'true' : 'false'}
                className={`w-full rounded-lg border px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors ${
                  errors.password
                    ? 'border-red-400 focus:ring-red-500'
                    : 'border-gray-300 focus:border-gray-900'
                }`}
                placeholder="At least 8 characters"
                {...register('password', {
                  required: 'Password is required.',
                  minLength: {
                    value: PASSWORD_MIN_LENGTH,
                    message: `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`,
                  },
                  validate: (value) =>
                    PASSWORD_REGEX.test(value) ||
                    'Password must contain at least one uppercase letter, one lowercase letter, and one number.',
                })}
              />
              <p id="password-hint" className="mt-1 text-xs text-gray-500">
                Minimum 8 characters with uppercase, lowercase, and a number.
              </p>
              {errors.password && (
                <p role="alert" className="mt-1 text-xs text-red-600">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-semibold text-gray-700 mb-1"
              >
                Confirm Password <span className="text-red-500" aria-hidden="true">*</span>
              </label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                aria-label="Confirm password"
                aria-required="true"
                aria-describedby={errors.confirmPassword ? 'confirmPassword-error' : undefined}
                aria-invalid={errors.confirmPassword ? 'true' : 'false'}
                className={`w-full rounded-lg border px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 transition-colors ${
                  errors.confirmPassword
                    ? 'border-red-400 focus:ring-red-500'
                    : 'border-gray-300 focus:border-gray-900'
                }`}
                placeholder="Repeat your password"
                {...register('confirmPassword', {
                  required: 'Please confirm your password.',
                  validate: (value) =>
                    value === passwordValue || 'Passwords do not match.',
                })}
              />
              {errors.confirmPassword && (
                <p id="confirmPassword-error" role="alert" className="mt-1 text-xs text-red-600">
                  {errors.confirmPassword.message}
                </p>
              )}
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            aria-busy={isSubmitting}
            className="mt-7 w-full rounded-lg bg-gray-900 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="h-4 w-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Creating Account…
              </span>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Already have an account?{' '}
          <Link
            to="/login"
            className="font-semibold text-gray-900 underline underline-offset-2 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export { RegisterPage };
export default RegisterPage;
