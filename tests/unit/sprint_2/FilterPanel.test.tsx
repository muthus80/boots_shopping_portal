/**
 * FilterPanel — unit tests (T-015 / US-005)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FilterPanel } from './FilterPanel';

// ── Helpers ───────────────────────────────────────────────────────────────────

const defaultProps = {
  selectedSizes: [] as string[],
  selectedColors: [] as string[],
  onSizeChange: vi.fn(),
  onColorChange: vi.fn(),
  onClearAll: vi.fn(),
};

const renderPanel = (overrides: Partial<typeof defaultProps> = {}) =>
  render(<FilterPanel {...defaultProps} {...overrides} />);

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('FilterPanel', () => {
  beforeEach(() => vi.clearAllMocks());

  // ── Rendering ─────────────────────────────────────────────────────────────────

  it('renders the aside with accessible label', () => {
    renderPanel();
    expect(screen.getByRole('complementary', { name: /product filters/i })).toBeInTheDocument();
  });

  it('renders the Filters heading', () => {
    renderPanel();
    expect(screen.getByRole('heading', { level: 2, name: /filters/i })).toBeInTheDocument();
  });

  it('renders Size (UK) section heading', () => {
    renderPanel();
    expect(screen.getByText(/size \(uk\)/i)).toBeInTheDocument();
  });

  it('renders Color section heading', () => {
    renderPanel();
    expect(screen.getByText(/^color$/i)).toBeInTheDocument();
  });

  it('renders all standard boot sizes', () => {
    renderPanel();
    // Spot-check a few sizes
    expect(screen.getByRole('checkbox', { name: '8' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: '10' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: '5' })).toBeInTheDocument();
  });

  it('renders all standard boot colors', () => {
    renderPanel();
    expect(screen.getByRole('checkbox', { name: 'Black' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Brown' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Tan' })).toBeInTheDocument();
  });

  // ── No active filters ─────────────────────────────────────────────────────────

  it('does not render "Clear all" button when no filters are selected', () => {
    renderPanel();
    expect(screen.queryByRole('button', { name: /clear all filters/i })).not.toBeInTheDocument();
  });

  it('does not render active filter chips when no filters are selected', () => {
    renderPanel();
    expect(screen.queryByLabelText(/active filters/i)).not.toBeInTheDocument();
  });

  // ── Size selection ────────────────────────────────────────────────────────────

  it('marks selected sizes as checked', () => {
    renderPanel({ selectedSizes: ['8', '10'] });
    expect(screen.getByRole('checkbox', { name: '8' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: '10' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: '9' })).not.toBeChecked();
  });

  it('calls onSizeChange(size, true) when an unchecked size is clicked', async () => {
    const onSizeChange = vi.fn();
    renderPanel({ onSizeChange });
    await userEvent.click(screen.getByRole('checkbox', { name: '9' }));
    expect(onSizeChange).toHaveBeenCalledOnce();
    expect(onSizeChange).toHaveBeenCalledWith('9', true);
  });

  it('calls onSizeChange(size, false) when a checked size is clicked', async () => {
    const onSizeChange = vi.fn();
    renderPanel({ selectedSizes: ['8'], onSizeChange });
    await userEvent.click(screen.getByRole('checkbox', { name: '8' }));
    expect(onSizeChange).toHaveBeenCalledOnce();
    expect(onSizeChange).toHaveBeenCalledWith('8', false);
  });

  // ── Color selection ───────────────────────────────────────────────────────────

  it('marks selected colors as checked', () => {
    renderPanel({ selectedColors: ['Black', 'Brown'] });
    expect(screen.getByRole('checkbox', { name: 'Black' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Brown' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Tan' })).not.toBeChecked();
  });

  it('calls onColorChange(color, true) when an unchecked color is clicked', async () => {
    const onColorChange = vi.fn();
    renderPanel({ onColorChange });
    await userEvent.click(screen.getByRole('checkbox', { name: 'Black' }));
    expect(onColorChange).toHaveBeenCalledOnce();
    expect(onColorChange).toHaveBeenCalledWith('Black', true);
  });

  it('calls onColorChange(color, false) when a checked color is clicked', async () => {
    const onColorChange = vi.fn();
    renderPanel({ selectedColors: ['Brown'], onColorChange });
    await userEvent.click(screen.getByRole('checkbox', { name: 'Brown' }));
    expect(onColorChange).toHaveBeenCalledOnce();
    expect(onColorChange).toHaveBeenCalledWith('Brown', false);
  });

  // ── Active filter chips ────────────────────────────────────────────────────────

  it('renders a chip for each active size filter', () => {
    renderPanel({ selectedSizes: ['8', '9'] });
    // Size chips have unique text "Size 8" / "Size 9"
    expect(screen.getByText('Size 8')).toBeInTheDocument();
    expect(screen.getByText('Size 9')).toBeInTheDocument();
  });

  it('renders a chip for each active color filter via remove button', () => {
    // Verify chips exist by checking their remove buttons (unique aria-labels)
    renderPanel({ selectedColors: ['Black', 'Tan'] });
    expect(screen.getByRole('button', { name: /remove black filter/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /remove tan filter/i })).toBeInTheDocument();
  });

  it('calls onSizeChange(size, false) when size chip remove button is clicked', async () => {
    const onSizeChange = vi.fn();
    renderPanel({ selectedSizes: ['8'], onSizeChange });
    await userEvent.click(screen.getByRole('button', { name: /remove size 8 filter/i }));
    expect(onSizeChange).toHaveBeenCalledWith('8', false);
  });

  it('calls onColorChange(color, false) when color chip remove button is clicked', async () => {
    const onColorChange = vi.fn();
    renderPanel({ selectedColors: ['Black'], onColorChange });
    await userEvent.click(screen.getByRole('button', { name: /remove black filter/i }));
    expect(onColorChange).toHaveBeenCalledWith('Black', false);
  });

  // ── Clear all ─────────────────────────────────────────────────────────────────

  it('renders "Clear all" button when sizes are selected', () => {
    renderPanel({ selectedSizes: ['8'] });
    expect(screen.getByRole('button', { name: /clear all filters/i })).toBeInTheDocument();
  });

  it('renders "Clear all" button when colors are selected', () => {
    renderPanel({ selectedColors: ['Black'] });
    expect(screen.getByRole('button', { name: /clear all filters/i })).toBeInTheDocument();
  });

  it('calls onClearAll when "Clear all" is clicked', async () => {
    const onClearAll = vi.fn();
    renderPanel({ selectedSizes: ['8'], onClearAll });
    await userEvent.click(screen.getByRole('button', { name: /clear all filters/i }));
    expect(onClearAll).toHaveBeenCalledOnce();
  });

  // ── Accessibility ─────────────────────────────────────────────────────────────

  it('size checkboxes are grouped with accessible group label', () => {
    renderPanel();
    expect(screen.getByRole('group', { name: /filter by size/i })).toBeInTheDocument();
  });

  it('color checkboxes are grouped with accessible group label', () => {
    renderPanel();
    expect(screen.getByRole('group', { name: /filter by color/i })).toBeInTheDocument();
  });
});
