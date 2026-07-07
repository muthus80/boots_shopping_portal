import React from 'react';

export interface EmptyStateProps {
  /** Large icon or illustration displayed above the heading. */
  icon?: React.ReactNode;
  /** Primary message — what is empty. Required. */
  heading: string;
  /** Optional supporting text or hint to help the user take action. */
  description?: string;
  /** Optional CTA button or link rendered below the description. */
  action?: React.ReactNode;
}

/**
 * EmptyState — shown whenever a list, search, or section has no content.
 *
 * Usage:
 *   <EmptyState heading="No results found for your search" />
 *   <EmptyState
 *     icon={<span aria-hidden="true">📦</span>}
 *     heading="You have not placed any orders yet."
 *     description="Explore our catalogue to find something you love."
 *     action={<Link to="/products">Browse boots</Link>}
 *   />
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  heading,
  description,
  action,
}) => (
  <div
    role="status"
    aria-live="polite"
    className="flex w-full flex-col items-center justify-center py-16 text-center"
  >
    {icon && (
      <div className="mb-4 text-5xl leading-none" aria-hidden="true">
        {icon}
      </div>
    )}

    <p className="text-lg font-semibold text-gray-700">{heading}</p>

    {description && (
      <p className="mt-1 max-w-xs text-sm text-gray-500">{description}</p>
    )}

    {action && <div className="mt-6">{action}</div>}
  </div>
);

export default EmptyState;
