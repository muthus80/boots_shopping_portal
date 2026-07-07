/**
 * useFocusTrap — T-033 / US-015
 *
 * Traps keyboard focus within a container element for the lifetime of the hook.
 * Required by WCAG 2.1 SC 2.1.2 (No Keyboard Trap) + the acceptance criteria
 * "when a modal window opens, keyboard focus is trapped within the modal until
 * it is closed."
 *
 * Usage:
 *   const containerRef = useFocusTrap(isOpen);
 *   <div ref={containerRef} role="dialog" ...>…</div>
 *
 * When `active` is true:
 *   - Focus is moved to the first focusable element inside the container on mount.
 *   - Tab / Shift+Tab cycle within the focusable elements inside the container.
 *   - Escape calls the optional `onEscape` callback (the parent should use this
 *     to close the modal and restore focus to the trigger).
 *
 * When `active` becomes false the event listener is removed automatically.
 */

import { useEffect, useRef, useCallback } from 'react';

const FOCUSABLE_SELECTORS = [
  'a[href]',
  'area[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
  'details > summary',
].join(', ');

interface UseFocusTrapOptions {
  /** Whether the trap is currently active. Default: true. */
  active?: boolean;
  /** Called when the user presses Escape inside the trapped container. */
  onEscape?: () => void;
}

export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(
  options: UseFocusTrapOptions = {}
): React.RefObject<T> {
  const { active = true, onEscape } = options;
  const containerRef = useRef<T>(null);

  /** Returns all focusable elements within the container, in DOM order. */
  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!containerRef.current) return [];
    return Array.from(
      containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)
    ).filter((el) => !el.closest('[inert]'));
  }, []);

  useEffect(() => {
    if (!active) return;

    const container = containerRef.current;
    if (!container) return;

    // Move focus to the first focusable element (or the container itself if none).
    const focusable = getFocusableElements();
    const firstFocusable = focusable[0] ?? container;
    // Defer slightly so the DOM has settled (e.g. after CSS transitions).
    const focusTimer = setTimeout(() => {
      firstFocusable.focus();
    }, 0);

    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') {
        onEscape?.();
        return;
      }

      if (e.key !== 'Tab') return;

      const elements = getFocusableElements();
      if (elements.length === 0) {
        e.preventDefault();
        return;
      }

      const first = elements[0];
      const last = elements[elements.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (e.shiftKey) {
        // Shift+Tab from first → wrap to last
        if (active === first || !container.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        // Tab from last → wrap to first
        if (active === last || !container.contains(active)) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimeout(focusTimer);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [active, getFocusableElements, onEscape]);

  return containerRef;
}
