import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErrorMessage } from './ErrorMessage';

describe('ErrorMessage', () => {
  it('renders the default heading from US-014 acceptance criteria', () => {
    render(<ErrorMessage />);
    expect(
      screen.getByText('Something went wrong, please try again')
    ).toBeInTheDocument();
  });

  it('renders a custom heading when provided', () => {
    render(<ErrorMessage heading="Failed to load products" />);
    expect(screen.getByText('Failed to load products')).toBeInTheDocument();
  });

  it('renders a technical detail when provided', () => {
    render(<ErrorMessage detail="Network Error: timeout after 15 s" />);
    expect(
      screen.getByText('Network Error: timeout after 15 s')
    ).toBeInTheDocument();
  });

  it('does NOT render a detail paragraph when omitted', () => {
    render(<ErrorMessage />);
    // Only the heading should be present; no secondary text
    expect(
      screen.queryByText('Network Error')
    ).not.toBeInTheDocument();
  });

  it('renders a "Try again" button when onRetry is provided', () => {
    const handleRetry = vi.fn();
    render(<ErrorMessage onRetry={handleRetry} />);
    expect(
      screen.getByRole('button', { name: 'Retry loading' })
    ).toBeInTheDocument();
  });

  it('calls onRetry when the retry button is clicked', async () => {
    const handleRetry = vi.fn();
    const user = userEvent.setup();
    render(<ErrorMessage onRetry={handleRetry} />);
    await user.click(screen.getByRole('button', { name: 'Retry loading' }));
    expect(handleRetry).toHaveBeenCalledOnce();
  });

  it('does NOT render a retry button when onRetry is omitted', () => {
    render(<ErrorMessage />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('has role="alert" so screen readers announce it immediately', () => {
    render(<ErrorMessage />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('has aria-live="assertive" for immediate announcement', () => {
    render(<ErrorMessage />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveAttribute('aria-live', 'assertive');
  });

  it('displays the warning icon element', () => {
    const { container } = render(<ErrorMessage />);
    const icon = container.querySelector('[aria-hidden="true"]');
    expect(icon).toBeInTheDocument();
    expect(icon?.textContent).toContain('⚠');
  });
});
