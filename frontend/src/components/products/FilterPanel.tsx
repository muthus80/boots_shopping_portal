/**
 * FilterPanel — sidebar filter UI for the product listing page (T-015 / US-005)
 *
 * Renders collapsible sections for Size and Color filters.
 * All state is URL-driven (via `selectedSizes` / `selectedColors` props) so
 * the parent page owns the filter state and keeps the URL as the single source
 * of truth.
 */

import React, { useId } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface FilterPanelProps {
  /** Currently selected size values. */
  selectedSizes: string[];
  /** Currently selected color values. */
  selectedColors: string[];
  /** Called when the user toggles a size option. */
  onSizeChange: (size: string, checked: boolean) => void;
  /** Called when the user toggles a color option. */
  onColorChange: (color: string, checked: boolean) => void;
  /** Clears all active filters. */
  onClearAll: () => void;
}

// ── Static filter options ──────────────────────────────────────────────────────

/** Standard UK boot sizes */
export const BOOT_SIZES: string[] = [
  '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13',
];

/** Common boot color options */
export const BOOT_COLORS: string[] = [
  'Black', 'Brown', 'Tan', 'Grey', 'White', 'Navy',
];

// ── FilterSection helper ───────────────────────────────────────────────────────

interface FilterSectionProps {
  title: string;
  children: React.ReactNode;
}

const FilterSection: React.FC<FilterSectionProps> = ({ title, children }) => (
  <div className="border-b border-gray-200 pb-5 last:border-b-0 last:pb-0">
    <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-700">
      {title}
    </h3>
    {children}
  </div>
);

// ── FilterCheckbox helper ─────────────────────────────────────────────────────

interface FilterCheckboxProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

const FilterCheckbox: React.FC<FilterCheckboxProps> = ({
  id,
  label,
  checked,
  onChange,
}) => (
  <label
    htmlFor={id}
    className="flex cursor-pointer items-center gap-2 rounded py-0.5 text-sm text-gray-700 hover:text-gray-900"
  >
    <input
      id={id}
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      className="h-4 w-4 rounded border-gray-300 text-gray-900 accent-gray-900 focus:ring-2 focus:ring-gray-900 focus:ring-offset-1 cursor-pointer"
      aria-label={label}
    />
    <span>{label}</span>
  </label>
);

// ── FilterPanel ───────────────────────────────────────────────────────────────

export const FilterPanel: React.FC<FilterPanelProps> = ({
  selectedSizes,
  selectedColors,
  onSizeChange,
  onColorChange,
  onClearAll,
}) => {
  const uid = useId();
  const hasFilters = selectedSizes.length > 0 || selectedColors.length > 0;

  return (
    <aside
      aria-label="Product filters"
      className="w-full space-y-5 rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">Filters</h2>
        {hasFilters && (
          <button
            type="button"
            onClick={onClearAll}
            aria-label="Clear all filters"
            className="text-xs font-medium text-gray-500 underline hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 rounded"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Active filter chips */}
      {hasFilters && (
        <div
          aria-label="Active filters"
          className="flex flex-wrap gap-1.5"
        >
          {selectedSizes.map((size) => (
            <span
              key={`chip-size-${size}`}
              className="inline-flex items-center gap-1 rounded-full bg-gray-900 px-2.5 py-0.5 text-xs font-medium text-white"
            >
              Size {size}
              <button
                type="button"
                onClick={() => onSizeChange(size, false)}
                aria-label={`Remove size ${size} filter`}
                className="ml-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-white/20 hover:bg-white/40 focus:outline-none"
              >
                <span aria-hidden="true">&times;</span>
              </button>
            </span>
          ))}
          {selectedColors.map((color) => (
            <span
              key={`chip-color-${color}`}
              className="inline-flex items-center gap-1 rounded-full bg-gray-900 px-2.5 py-0.5 text-xs font-medium text-white"
            >
              {color}
              <button
                type="button"
                onClick={() => onColorChange(color, false)}
                aria-label={`Remove ${color} filter`}
                className="ml-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-white/20 hover:bg-white/40 focus:outline-none"
              >
                <span aria-hidden="true">&times;</span>
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Size filter */}
      <FilterSection title="Size (UK)">
        <div
          role="group"
          aria-label="Filter by size"
          className="flex flex-wrap gap-x-4 gap-y-2"
        >
          {BOOT_SIZES.map((size) => (
            <FilterCheckbox
              key={size}
              id={`${uid}-size-${size}`}
              label={size}
              checked={selectedSizes.includes(size)}
              onChange={(checked) => onSizeChange(size, checked)}
            />
          ))}
        </div>
      </FilterSection>

      {/* Color filter */}
      <FilterSection title="Color">
        <div
          role="group"
          aria-label="Filter by color"
          className="flex flex-col gap-1"
        >
          {BOOT_COLORS.map((color) => (
            <FilterCheckbox
              key={color}
              id={`${uid}-color-${color}`}
              label={color}
              checked={selectedColors.includes(color)}
              onChange={(checked) => onColorChange(color, checked)}
            />
          ))}
        </div>
      </FilterSection>
    </aside>
  );
};

export default FilterPanel;
