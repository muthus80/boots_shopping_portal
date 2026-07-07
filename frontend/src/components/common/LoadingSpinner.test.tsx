import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from './LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders with default accessible label', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status', { name: 'Loading…' })).toBeInTheDocument();
  });

  it('renders a custom label', () => {
    render(<LoadingSpinner label="Loading products…" />);
    expect(screen.getByRole('status', { name: 'Loading products…' })).toBeInTheDocument();
  });

  it('exposes the label text for screen readers via sr-only span', () => {
    render(<LoadingSpinner label="Fetching results" />);
    const srText = screen.getByText('Fetching results');
    expect(srText).toHaveClass('sr-only');
  });

  it('has aria-live="polite" to announce non-urgent status updates', () => {
    render(<LoadingSpinner />);
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
  });

  it('wraps in a centered container when centered=true', () => {
    const { container } = render(<LoadingSpinner centered />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('flex', 'justify-center', 'items-center');
    expect(wrapper).toHaveAttribute('aria-busy', 'true');
  });

  it('does NOT add centering wrapper when centered is false (default)', () => {
    const { container } = render(<LoadingSpinner />);
    const wrapper = container.firstChild as HTMLElement;
    // The outermost element should be the inline <span role="status">, not a div
    expect(wrapper.tagName).toBe('SPAN');
  });

  it('applies sm size classes to the inner spinner element', () => {
    const { container } = render(<LoadingSpinner size="sm" />);
    const spinnerEl = container.querySelector('[aria-hidden="true"]') as HTMLElement;
    expect(spinnerEl).toHaveClass('h-5', 'w-5');
  });

  it('applies lg size classes to the inner spinner element', () => {
    const { container } = render(<LoadingSpinner size="lg" />);
    const spinnerEl = container.querySelector('[aria-hidden="true"]') as HTMLElement;
    expect(spinnerEl).toHaveClass('h-12', 'w-12');
  });

  it('applies animate-spin to the inner spinner element', () => {
    const { container } = render(<LoadingSpinner />);
    const spinnerEl = container.querySelector('[aria-hidden="true"]') as HTMLElement;
    expect(spinnerEl).toHaveClass('animate-spin');
  });
});
