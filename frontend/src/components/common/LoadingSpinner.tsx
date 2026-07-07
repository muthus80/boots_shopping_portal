import React from 'react';

export interface LoadingSpinnerProps {
  /** Size of the spinner — maps to Tailwind h-/w- classes. Default: 'md'. */
  size?: 'sm' | 'md' | 'lg';
  /** Accessible label read by screen readers. Default: 'Loading…' */
  label?: string;
  /** If true, the spinner is centered inside a full-width container. Default: false. */
  centered?: boolean;
}

const SIZE_CLASSES: Record<NonNullable<LoadingSpinnerProps['size']>, string> = {
  sm: 'h-5 w-5 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-4',
};

/**
 * LoadingSpinner — accessible spinner used whenever async data is in-flight.
 *
 * Usage:
 *   <LoadingSpinner />
 *   <LoadingSpinner size="lg" label="Loading products…" centered />
 */
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  label = 'Loading…',
  centered = false,
}) => {
  const spinner = (
    <span
      role="status"
      aria-label={label}
      aria-live="polite"
      className="inline-flex items-center justify-center"
    >
      <span
        className={`${SIZE_CLASSES[size]} animate-spin rounded-full border-gray-200 border-t-gray-900`}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </span>
  );

  if (centered) {
    return (
      <div
        className="flex w-full items-center justify-center py-16"
        aria-busy="true"
      >
        {spinner}
      </div>
    );
  }

  return spinner;
};

export default LoadingSpinner;
