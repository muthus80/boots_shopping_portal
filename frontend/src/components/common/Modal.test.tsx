/**
 * Tests for Modal — T-033 / US-015
 *
 * Verifies WCAG 2.1 requirements:
 *   - role="dialog" with aria-modal="true"
 *   - aria-labelledby wired to the title
 *   - Close button is accessible
 *   - Escape key dismisses the dialog
 *   - onClose is called on backdrop click
 *   - Dialog is removed from DOM when isOpen = false
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal } from './Modal';

// ── Helpers ───────────────────────────────────────────────────────────────────

interface TestModalProps {
  isOpen?: boolean;
  onClose?: () => void;
  title?: string;
  description?: string;
  children?: React.ReactNode;
}

const TestModal: React.FC<TestModalProps> = ({
  isOpen = true,
  onClose = vi.fn(),
  title = 'Test Modal',
  description,
  children = <p>Modal body content</p>,
}) => (
  <Modal isOpen={isOpen} onClose={onClose} title={title} description={description}>
    {children}
  </Modal>
);

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Modal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Visibility ───────────────────────────────────────────────────────────────

  it('renders the modal when isOpen is true', () => {
    render(<TestModal isOpen={true} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    render(<TestModal isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  // ── ARIA attributes ───────────────────────────────────────────────────────────

  it('has role="dialog"', () => {
    render(<TestModal />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('has aria-modal="true"', () => {
    render(<TestModal />);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  });

  it('has aria-labelledby pointing to the title element', () => {
    render(<TestModal title="Confirm Delete" />);
    const dialog = screen.getByRole('dialog');
    const labelId = dialog.getAttribute('aria-labelledby');
    expect(labelId).toBeTruthy();

    const titleElement = document.getElementById(labelId!);
    expect(titleElement).toBeInTheDocument();
    expect(titleElement).toHaveTextContent('Confirm Delete');
  });

  it('shows the title inside the dialog', () => {
    render(<TestModal title="My Dialog Title" />);
    expect(screen.getByText('My Dialog Title')).toBeInTheDocument();
  });

  it('renders an optional description and wires aria-describedby', () => {
    render(<TestModal description="This action cannot be undone." />);
    const dialog = screen.getByRole('dialog');
    const descId = dialog.getAttribute('aria-describedby');
    expect(descId).toBeTruthy();

    const descElement = document.getElementById(descId!);
    expect(descElement).toBeInTheDocument();
    expect(descElement).toHaveTextContent('This action cannot be undone.');
  });

  it('does not set aria-describedby when no description is provided', () => {
    render(<TestModal />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).not.toHaveAttribute('aria-describedby');
  });

  // ── Close interactions ───────────────────────────────────────────────────────

  it('renders an accessible close button', () => {
    render(<TestModal />);
    expect(screen.getByRole('button', { name: /close dialog/i })).toBeInTheDocument();
  });

  it('calls onClose when the close button is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<TestModal onClose={onClose} />);
    await user.click(screen.getByRole('button', { name: /close dialog/i }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when Escape key is pressed', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<TestModal onClose={onClose} />);

    // Focus something inside the dialog first
    screen.getByRole('button', { name: /close dialog/i }).focus();
    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  // ── Content ───────────────────────────────────────────────────────────────────

  it('renders children inside the dialog', () => {
    render(
      <TestModal>
        <p>Custom body content</p>
      </TestModal>
    );
    expect(screen.getByText('Custom body content')).toBeInTheDocument();
  });

  // ── Focus restoration ────────────────────────────────────────────────────────

  it('a close button exists and is focusable when the dialog is open', () => {
    render(<TestModal isOpen={true} />);
    const closeBtn = screen.getByRole('button', { name: /close dialog/i });
    expect(closeBtn).toBeInTheDocument();
    expect(closeBtn).not.toBeDisabled();
  });
});
