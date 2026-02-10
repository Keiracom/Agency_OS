/**
 * DateSelector.tsx - Button Group for Time Period Selection
 * Sprint 4 - Reports Page
 *
 * Button group component for selecting date ranges.
 */

"use client";

import type { DateRange } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface DateOption {
  value: DateRange;
  label: string;
}

interface DateSelectorProps {
  options: DateOption[];
  selected: DateRange;
  onSelect: (value: DateRange) => void;
}

// ============================================
// Component
// ============================================

export function DateSelector({ options, selected, onSelect }: DateSelectorProps) {
  return (
    <div className="flex gap-1 bg-bg-base p-1 rounded-lg border border-border-subtle">
      {options.map((option) => {
        const isActive = option.value === selected;

        return (
          <button
            key={option.value}
            onClick={() => onSelect(option.value)}
            className={`
              px-4 py-2 text-sm font-medium rounded-md transition-all
              ${
                isActive
                  ? "bg-accent-primary text-white"
                  : "text-text-muted hover:text-text-secondary hover:bg-bg-surface-hover"
              }
            `}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export default DateSelector;
