import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EmptyState } from './EmptyState';

describe('EmptyState', () => {
  it('renders the required heading', () => {
    render(<EmptyState heading="No results found for your search" />);
    expect(screen.getByText('No results found for your search')).toBeInTheDocument();
  });

  it('renders the order history empty message from US-014', () => {
    render(<EmptyState heading="You have not placed any orders yet." />);
    expect(
      screen.getByText('You have not placed any orders yet.')
    ).toBeInTheDocument();
  });

  it('renders description text when provided', () => {
    render(
      <EmptyState
        heading="Nothing here"
        description="Try a different keyword or browse our full catalogue."
      />
    );
    expect(
      screen.getByText('Try a different keyword or browse our full catalogue.')
    ).toBeInTheDocument();
  });

  it('does NOT render a description element when omitted', () => {
    render(<EmptyState heading="Nothing here" />);
    expect(
      screen.queryByText('Try a different keyword or browse our full catalogue.')
    ).not.toBeInTheDocument();
  });

  it('renders an icon node when provided', () => {
    render(
      <EmptyState heading="Empty" icon={<span data-testid="boot-icon">👢</span>} />
    );
    expect(screen.getByTestId('boot-icon')).toBeInTheDocument();
  });

  it('does NOT render an icon wrapper when icon is omitted', () => {
    const { container } = render(<EmptyState heading="Empty" />);
    // The icon wrapper has aria-hidden="true"; it should not be present
    const iconWrapper = container.querySelector('[aria-hidden="true"]');
    expect(iconWrapper).not.toBeInTheDocument();
  });

  it('renders an action node when provided', () => {
    render(
      <EmptyState
        heading="Nothing here"
        action={<button type="button">Browse boots</button>}
      />
    );
    expect(
      screen.getByRole('button', { name: 'Browse boots' })
    ).toBeInTheDocument();
  });

  it('does NOT render an action container when action is omitted', () => {
    render(<EmptyState heading="Nothing here" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('has role="status" and aria-live="polite" for assistive technology', () => {
    render(<EmptyState heading="No orders yet." />);
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });
});
