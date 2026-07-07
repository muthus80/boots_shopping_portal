import React from 'react';

export interface ErrorMessageProps {
  /**
   * Primary error heading. Defaults to the US-014 acceptance-criteria wording:
   * "Something went wrong, please try again".
   */
  heading?: string;
  /**
   * Optional technical detail (e.g. the Error.message). Rendered beneath the
   * heading in a smaller, muted style. Do not expose raw stack traces here.
   */
  detail?: string;
  /** Optional retry callback. When provided, a "Try again" button is rendered. */
  onRetry?: () => void;
}

/**
 * ErrorMessage — user-friendly error block rendered when an API call fails or
 * an unexpected runtime error prevents a section from loading.
 *
 * Marked with `role="alert"` so screen readers announce it immediately.
 *
 * Usage:
 *   <ErrorMessage />
 *   <ErrorMessage detail={error.message} onRetry={() => refetch()} />
 */
export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  heading = 'Something went wrong, please try again',
  detail,
  onRetry,
}) => (
  <div
    role="alert"
    aria-live="assertive"
    className="rounded-xl border border-red-200 bg-red-50 p-8 text-center"
  >
    {/* Warning icon */}
    <span className="mb-2 inline-block text-3xl" aria-hidden="true">
      ⚠️
    </span>

    <p className="text-base font-semibold text-red-700">{heading}</p>

    {detail && (
      <p className="mt-1 text-sm text-red-500">{detail}</p>
    )}

    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        aria-label="Retry loading"
        className="mt-6 rounded-lg border border-red-300 bg-white px-5 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-400"
      >
        Try again
      </button>
    )}
  </div>
);

export default ErrorMessage;
