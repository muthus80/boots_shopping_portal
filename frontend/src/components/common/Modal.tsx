/**
 * Modal — T-033 / US-015
 *
 * Accessible dialog component satisfying WCAG 2.1 AA:
 *   - role="dialog" with aria-modal="true"
 *   - aria-labelledby wired to the modal title
 *   - Focus is trapped inside the dialog (useFocusTrap)
 *   - Escape key dismisses the dialog
 *   - Focus is restored to the trigger element on close
 *   - Background scroll is locked while the dialog is open
 *
 * Usage:
 *   const [open, setOpen] = useState(false);
 *   const triggerRef = useRef<HTMLButtonElement>(null);
 *
 *   <button ref={triggerRef} onClick={() => setOpen(true)}>Open</button>
 *   <Modal
 *     isOpen={open}
 *     onClose={() => setOpen(false)}
 *     title="Confirm action"
 *     triggerRef={triggerRef}
 *   >
 *     <p>Are you sure?</p>
 *   </Modal>
 */

import React, { useEffect, useId } from 'react';
import { createPortal } from 'react-dom';
import { useFocusTrap } from '../../hooks/useFocusTrap';

export interface ModalProps {
  /** Controls whether the dialog is rendered and visible. */
  isOpen: boolean;
  /** Called when the user closes the dialog (Escape, backdrop click, close button). */
  onClose: () => void;
  /** The modal title — shown as a heading and used for aria-labelledby. */
  title: string;
  /** Optional additional description for aria-describedby. */
  description?: string;
  /** Modal body content. */
  children: React.ReactNode;
  /**
   * Ref to the element that triggered the dialog. Focus is restored here on close.
   * If not provided, focus returns to document.body.
   */
  triggerRef?: React.RefObject<HTMLElement | null>;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  triggerRef,
}) => {
  const titleId = useId();
  const descId = useId();

  // Trap focus inside the dialog while open
  const dialogRef = useFocusTrap<HTMLDivElement>({
    active: isOpen,
    onEscape: onClose,
  });

  // Restore focus to the trigger element when dialog closes
  useEffect(() => {
    if (!isOpen) {
      const trigger = triggerRef?.current ?? null;
      // Defer so the browser has finished removing the dialog from the DOM
      setTimeout(() => {
        (trigger as HTMLElement | null)?.focus();
      }, 0);
    }
  }, [isOpen, triggerRef]);

  // Lock body scroll while dialog is open
  useEffect(() => {
    if (isOpen) {
      const previous = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = previous;
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    // Only close if the click was directly on the backdrop (not a child element)
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      aria-hidden={false}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        aria-hidden="true"
        onClick={handleBackdropClick}
      />

      {/* Dialog panel */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        className="relative z-10 w-full max-w-md rounded-2xl bg-white p-6 shadow-xl focus:outline-none"
      >
        {/* Header */}
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2
            id={titleId}
            className="text-xl font-bold text-gray-900"
          >
            {title}
          </h2>
          <button
            type="button"
            aria-label="Close dialog"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>

        {/* Optional description */}
        {description && (
          <p id={descId} className="mb-4 text-sm text-gray-500">
            {description}
          </p>
        )}

        {/* Body */}
        {children}
      </div>
    </div>,
    document.body
  );
};

export default Modal;
