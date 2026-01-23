"use client";

import { useState } from "react";
import { Calendar, ChevronDown } from "lucide-react";

/**
 * Date range preset option
 */
interface PresetOption {
  label: string;
  value: string;
}

/**
 * DateRangePicker props
 */
export interface DateRangePickerProps {
  /** Start date of the range */
  startDate?: Date;
  /** End date of the range */
  endDate?: Date;
  /** Callback when date range changes */
  onChange?: (startDate: Date, endDate: Date) => void;
}

/**
 * Preset date range options
 */
const presetOptions: PresetOption[] = [
  { label: "Last 7 days", value: "7d" },
  { label: "Last 30 days", value: "30d" },
  { label: "This month", value: "this_month" },
  { label: "Last month", value: "last_month" },
  { label: "Custom range", value: "custom" },
];

/**
 * DateRangePicker - Date range selector component
 *
 * Features:
 * - Preset options: Last 7 days, Last 30 days, This month, Last month
 * - Custom range option (placeholder)
 * - Dropdown for selection
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Background: #FFFFFF (card-bg)
 * - Border: #E2E8F0 (card-border)
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 * - Accent: #3B82F6
 */
export function DateRangePicker({
  startDate,
  endDate,
  onChange,
}: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string>("30d");

  const handlePresetSelect = (value: string) => {
    setSelectedPreset(value);
    setIsOpen(false);

    // Calculate dates based on preset (prototype - static dates)
    const end = new Date();
    let start = new Date();

    switch (value) {
      case "7d":
        start.setDate(end.getDate() - 7);
        break;
      case "30d":
        start.setDate(end.getDate() - 30);
        break;
      case "this_month":
        start = new Date(end.getFullYear(), end.getMonth(), 1);
        break;
      case "last_month":
        start = new Date(end.getFullYear(), end.getMonth() - 1, 1);
        end.setDate(0); // Last day of previous month
        break;
      case "custom":
        // Would open a date picker in production
        break;
    }

    if (onChange && value !== "custom") {
      onChange(start, end);
    }
  };

  const getSelectedLabel = () => {
    return presetOptions.find((opt) => opt.value === selectedPreset)?.label || "Select range";
  };

  const formatDateRange = () => {
    if (startDate && endDate) {
      const formatDate = (d: Date) =>
        d.toLocaleDateString("en-AU", { month: "short", day: "numeric" });
      return `${formatDate(startDate)} - ${formatDate(endDate)}`;
    }
    return null;
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-4 py-2.5 bg-white border border-[#E2E8F0] rounded-lg hover:bg-[#F8FAFC] transition-colors"
      >
        <Calendar className="h-4 w-4 text-[#64748B]" />
        <div className="flex flex-col items-start">
          <span className="text-sm font-medium text-[#1E293B]">
            {getSelectedLabel()}
          </span>
          {formatDateRange() && (
            <span className="text-xs text-[#94A3B8]">{formatDateRange()}</span>
          )}
        </div>
        <ChevronDown
          className={`h-4 w-4 text-[#94A3B8] transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-48 bg-white rounded-lg border border-[#E2E8F0] shadow-lg z-10">
          <div className="p-1">
            {presetOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => handlePresetSelect(option.value)}
                className={`w-full px-3 py-2 text-left text-sm rounded-md transition-colors ${
                  selectedPreset === option.value
                    ? "bg-[#EFF6FF] text-[#3B82F6] font-medium"
                    : "text-[#1E293B] hover:bg-[#F8FAFC]"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default DateRangePicker;
