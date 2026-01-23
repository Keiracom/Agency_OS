/**
 * FILE: frontend/components/campaigns/PrioritySlider.tsx
 * PURPOSE: Campaign priority slider for allocation UI
 * PHASE: Phase I Dashboard Redesign (Item 52)
 *
 * Features:
 * - Draggable slider showing percentage (10-80%)
 * - Real-time percentage display
 * - Touch-friendly (larger hit area)
 * - Keyboard accessible (arrow keys)
 * - ARIA labels for screen readers
 */

"use client";

import * as React from "react";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";

interface PrioritySliderProps {
  /** Current priority percentage (10-80) */
  value: number;
  /** Callback when value changes */
  onChange: (value: number) => void;
  /** Campaign name for accessibility */
  campaignName: string;
  /** Whether the slider is disabled */
  disabled?: boolean;
  /** Additional class names */
  className?: string;
  /** Show percentage label */
  showLabel?: boolean;
}

/**
 * Priority slider for campaign allocation.
 *
 * Allows users to set campaign priority between 10-80%.
 * Shows real-time percentage while dragging.
 */
export function PrioritySlider({
  value,
  onChange,
  campaignName,
  disabled = false,
  className,
  showLabel = true,
}: PrioritySliderProps) {
  const [isDragging, setIsDragging] = React.useState(false);
  const [localValue, setLocalValue] = React.useState(value);

  // Sync local value with prop changes
  React.useEffect(() => {
    if (!isDragging) {
      setLocalValue(value);
    }
  }, [value, isDragging]);

  const handleValueChange = (newValue: number[]) => {
    const clampedValue = Math.max(10, Math.min(80, newValue[0]));
    setLocalValue(clampedValue);
  };

  const handleValueCommit = (newValue: number[]) => {
    const clampedValue = Math.max(10, Math.min(80, newValue[0]));
    setIsDragging(false);
    onChange(clampedValue);
  };

  const handlePointerDown = () => {
    setIsDragging(true);
  };

  return (
    <div className={cn("w-full", className)}>
      {/* Label row */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-muted-foreground">Priority</span>
        {showLabel && (
          <span
            className={cn(
              "text-sm font-medium tabular-nums transition-colors",
              isDragging ? "text-primary" : "text-foreground"
            )}
          >
            {localValue}%
          </span>
        )}
      </div>

      {/* Slider track labels */}
      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
        <span>Low</span>
        <span>High</span>
      </div>

      {/* Slider */}
      <Slider
        value={[localValue]}
        min={10}
        max={80}
        step={5}
        disabled={disabled}
        onValueChange={handleValueChange}
        onValueCommit={handleValueCommit}
        onPointerDown={handlePointerDown}
        aria-label={`Campaign priority for ${campaignName}, currently ${localValue}%`}
        className={cn(
          "touch-action-none",
          // Larger touch target for mobile
          "[&_[data-radix-slider-thumb]]:h-6 [&_[data-radix-slider-thumb]]:w-6",
          "[&_[data-radix-slider-track]]:h-2",
          // Visual feedback while dragging
          isDragging && "[&_[data-radix-slider-thumb]]:ring-2 [&_[data-radix-slider-thumb]]:ring-primary/50"
        )}
      />

      {/* Min/Max hints */}
      <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
        <span>10%</span>
        <span>80%</span>
      </div>
    </div>
  );
}

/**
 * Props for managing multiple campaign allocations.
 * Used by CampaignAllocationManager to auto-balance sliders.
 */
export interface CampaignAllocation {
  campaignId: string;
  campaignName: string;
  priorityPct: number;
}

/**
 * Hook for managing auto-balanced campaign allocations.
 *
 * When one slider changes, others adjust proportionally
 * to maintain 100% total allocation.
 */
export function useCampaignAllocations(
  initialAllocations: CampaignAllocation[]
) {
  const [allocations, setAllocations] = React.useState(initialAllocations);

  const updateAllocation = React.useCallback(
    (campaignId: string, newValue: number) => {
      setAllocations((current) => {
        const otherCampaigns = current.filter((c) => c.campaignId !== campaignId);
        const currentTotal = otherCampaigns.reduce((sum, c) => sum + c.priorityPct, 0);
        const targetOtherTotal = 100 - newValue;

        // Calculate proportional adjustments for other campaigns
        const adjustedOthers = otherCampaigns.map((campaign) => {
          if (currentTotal === 0) {
            // Edge case: evenly distribute
            return {
              ...campaign,
              priorityPct: Math.floor(targetOtherTotal / otherCampaigns.length),
            };
          }

          // Proportional adjustment
          const ratio = campaign.priorityPct / currentTotal;
          let adjusted = Math.round(targetOtherTotal * ratio);

          // Enforce min/max constraints
          adjusted = Math.max(10, Math.min(80, adjusted));

          return { ...campaign, priorityPct: adjusted };
        });

        // Find and update the changed campaign
        const changedCampaign = current.find((c) => c.campaignId === campaignId);
        if (!changedCampaign) return current;

        const result = [
          ...adjustedOthers,
          { ...changedCampaign, priorityPct: newValue },
        ];

        // Sort to maintain consistent order
        return result.sort((a, b) =>
          current.findIndex((c) => c.campaignId === a.campaignId) -
          current.findIndex((c) => c.campaignId === b.campaignId)
        );
      });
    },
    []
  );

  // Check if allocations sum to 100%
  const isValid = React.useMemo(() => {
    const total = allocations.reduce((sum, c) => sum + c.priorityPct, 0);
    return total === 100;
  }, [allocations]);

  return {
    allocations,
    setAllocations,
    updateAllocation,
    isValid,
  };
}

export default PrioritySlider;
