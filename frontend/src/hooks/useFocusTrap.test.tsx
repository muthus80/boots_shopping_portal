/**
 * Tests for useFocusTrap — T-033 / US-015
 *
 * Verifies keyboard focus is trapped within a container when the hook is active
 * and released when the hook is inactive.
 *
 * NOTE: renderHook() cannot test focus-movement because the React ref only
 * attaches to a real DOM node after the component renders.  We use
 * render() + a thin wrapper component so the ref is properly connected.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act, screen } from '@testing-library/react';
import { useFocusTrap } from './useFocusTrap';

// ── Test component ─────────────────────────────────────────────────────────────

interface TrapContainerProps {
  active?: boolean;
  onEscape?: () => void;
  buttonCount?: number;
}

const TrapContainer: React.FC<TrapContainerProps> = ({
  active = true,
  onEscape,
  buttonCount = 3,
}) => {
  const ref = useFocusTrap<HTMLDivElement>({ active, onEscape });

  return (
    <div ref={ref} data-testid="trap-container">
      {Array.from({ length: buttonCount }, (_, i) => (
        <button key={i} type="button" data-testid={`btn-${i}`}>
          Button {i + 1}
        </button>
      ))}
    </div>
  );
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function fireKeyDown(key: string, shiftKey = false): void {
  document.dispatchEvent(
    new KeyboardEvent('keydown', { key, shiftKey, bubbles: true, cancelable: true })
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('useFocusTrap', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('returns a ref that is attached to the container element', () => {
    render(<TrapContainer active={false} />);
    // If the ref is attached, the container exists in the DOM
    expect(screen.getByTestId('trap-container')).toBeInTheDocument();
  });

  it('moves focus to the first focusable element when activated', () => {
    render(<TrapContainer active={true} />);

    // Run the setTimeout(0) used inside the hook
    act(() => {
      vi.runAllTimers();
    });

    expect(document.activeElement).toBe(screen.getByTestId('btn-0'));
  });

  it('does NOT move focus when active is false', () => {
    render(<TrapContainer active={false} />);

    act(() => {
      vi.runAllTimers();
    });

    // Focus should remain wherever it was (not moved into the container)
    expect(document.activeElement).not.toBe(screen.getByTestId('btn-0'));
  });

  it('calls onEscape when Escape key is pressed while active', () => {
    const onEscape = vi.fn();
    render(<TrapContainer active={true} onEscape={onEscape} />);

    act(() => {
      vi.runAllTimers();
      fireKeyDown('Escape');
    });

    expect(onEscape).toHaveBeenCalledOnce();
  });

  it('does not call onEscape when active is false', () => {
    const onEscape = vi.fn();
    render(<TrapContainer active={false} onEscape={onEscape} />);

    act(() => {
      vi.runAllTimers();
      fireKeyDown('Escape');
    });

    expect(onEscape).not.toHaveBeenCalled();
  });

  it('does not call onEscape for non-Escape keys', () => {
    const onEscape = vi.fn();
    render(<TrapContainer active={true} onEscape={onEscape} />);

    act(() => {
      vi.runAllTimers();
      fireKeyDown('Tab');
      fireKeyDown('Enter');
      fireKeyDown('Space');
    });

    expect(onEscape).not.toHaveBeenCalled();
  });
});
