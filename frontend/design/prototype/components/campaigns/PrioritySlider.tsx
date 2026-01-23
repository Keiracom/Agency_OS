"use client";

/**
 * PrioritySlider - Standalone priority allocation slider
 *
 * Features:
 * - Draggable slider with visual track
 * - Percentage display
 * - Low/High labels
 * - Min/Max constraints (default 10-80%)
 * - Disabled state support
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Track background: #E2E8F0
 * - Track fill: #3B82F6 (accent-blue)
 * - Thumb: #3B82F6 with white border
 * - Text: #64748B (labels), #1E293B (percentage)
 */

export interface PrioritySliderProps {
  /** Current priority value (0-100) */
  value: number;
  /** Callback when value changes */
  onChange: (value: number) => void;
  /** Minimum allowed value (default 10) */
  min?: number;
  /** Maximum allowed value (default 80) */
  max?: number;
  /** Whether the slider is disabled */
  disabled?: boolean;
}

export function PrioritySlider({
  value,
  onChange,
  min = 10,
  max = 80,
  disabled = false,
}: PrioritySliderProps) {
  // Calculate percentage for track fill
  const fillPercentage = ((value - min) / (max - min)) * 100;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseInt(e.target.value, 10);
    // Clamp value to min/max
    const clampedValue = Math.max(min, Math.min(max, newValue));
    onChange(clampedValue);
  };

  return (
    <div className="w-full">
      {/* Labels */}
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs font-medium text-[#94A3B8]">Low</span>
        <span className="text-sm font-semibold text-[#1E293B]">{value}%</span>
        <span className="text-xs font-medium text-[#94A3B8]">High</span>
      </div>

      {/* Slider Track */}
      <div className="relative h-2">
        {/* Background Track */}
        <div className="absolute inset-0 bg-[#E2E8F0] rounded-full" />

        {/* Fill Track */}
        <div
          className="absolute left-0 top-0 h-full bg-[#3B82F6] rounded-full transition-all duration-150"
          style={{ width: `${fillPercentage}%` }}
        />

        {/* Native Range Input (invisible but functional) */}
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={`
            absolute inset-0 w-full h-full opacity-0 cursor-pointer
            ${disabled ? "cursor-not-allowed" : "cursor-pointer"}
          `}
        />

        {/* Custom Thumb */}
        <div
          className={`
            absolute top-1/2 -translate-y-1/2 -translate-x-1/2
            w-4 h-4 bg-white border-2 border-[#3B82F6] rounded-full shadow-md
            transition-all duration-150
            ${disabled ? "opacity-50" : "hover:scale-110"}
          `}
          style={{ left: `${fillPercentage}%` }}
        />
      </div>
    </div>
  );
}

export default PrioritySlider;
