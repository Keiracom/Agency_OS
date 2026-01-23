"use client";

/**
 * ALS Tier type
 */
export type ALSTier = "hot" | "warm" | "cool" | "cold" | "dead";

/**
 * ALSTierBadge props
 */
export interface ALSTierBadgeProps {
  /** ALS tier */
  tier: ALSTier;
  /** Show client-friendly label instead of tier name */
  showLabel?: boolean;
  /** Badge size */
  size?: "sm" | "md" | "lg";
}

/**
 * Tier configuration mapping
 */
const tierConfig: Record<
  ALSTier,
  { bg: string; text: string; label: string; internalLabel: string }
> = {
  hot: {
    bg: "bg-[#EF4444]",
    text: "text-white",
    label: "High Priority",
    internalLabel: "Hot",
  },
  warm: {
    bg: "bg-[#F97316]",
    text: "text-white",
    label: "Engaged",
    internalLabel: "Warm",
  },
  cool: {
    bg: "bg-[#3B82F6]",
    text: "text-white",
    label: "Nurturing",
    internalLabel: "Cool",
  },
  cold: {
    bg: "bg-[#6B7280]",
    text: "text-white",
    label: "Low Activity",
    internalLabel: "Cold",
  },
  dead: {
    bg: "bg-[#D1D5DB]",
    text: "text-[#374151]",
    label: "Inactive",
    internalLabel: "Dead",
  },
};

/**
 * Size configuration
 */
const sizeConfig: Record<"sm" | "md" | "lg", string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-xs",
  lg: "px-3 py-1.5 text-sm",
};

/**
 * ALSTierBadge - Color-coded ALS tier badge
 *
 * Features:
 * - Color-coded background based on tier
 * - Client-friendly labels (High Priority, Engaged, etc.)
 * - Multiple size options
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Hot: #EF4444 (tier-hot)
 * - Warm: #F97316 (tier-warm)
 * - Cool: #3B82F6 (tier-cool)
 * - Cold: #6B7280 (tier-cold)
 * - Dead: #D1D5DB (tier-dead)
 *
 * Usage:
 * ```tsx
 * <ALSTierBadge tier="hot" showLabel />
 * <ALSTierBadge tier="warm" size="lg" />
 * ```
 */
export function ALSTierBadge({
  tier,
  showLabel = false,
  size = "md",
}: ALSTierBadgeProps) {
  const config = tierConfig[tier];
  const sizeClass = sizeConfig[size];
  const displayText = showLabel ? config.label : config.internalLabel;

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full font-medium ${config.bg} ${config.text} ${sizeClass}`}
    >
      {displayText}
    </span>
  );
}

export default ALSTierBadge;
