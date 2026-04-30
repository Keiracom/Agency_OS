/**
 * TierBadge.tsx - Lead Tier Badge Component
 * Phase: Operation Modular Cockpit
 * 
 * Per LEADS.md spec:
 * - Clients see friendly labels, NOT internal tier names
 * - Hot → "High Priority", Warm → "Engaged", Cool → "Nurturing",
 *   Cold → "Low Activity", Dead → "Inactive"
 */

"use client";

import type { ALSTier } from "@/lib/api/types";

// ============================================
// Types
// ============================================

interface TierBadgeProps {
  tier: ALSTier;
  /** Show internal tier label instead of client-friendly label */
  showInternalLabel?: boolean;
  /** Size variant */
  size?: "sm" | "md";
  /** Custom class name */
  className?: string;
}

// ============================================
// Configuration
// ============================================

// Glass-themed tier configuration
const tierConfig: Record<ALSTier, { style: string; clientLabel: string }> = {
  hot: { style: "bg-orange-500/20 text-orange-400 border border-orange-500/30", clientLabel: "High Priority" },
  warm: { style: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30", clientLabel: "Engaged" },
  cool: { style: "bg-panel/20 text-ink-2 border border-default/30", clientLabel: "Nurturing" },
  cold: { style: "bg-slate-500/20 text-ink-2 border border-slate-500/30", clientLabel: "Low Activity" },
  dead: { style: "bg-panel/20 text-ink-3 border border-slate-600/30", clientLabel: "Inactive" },
};

// ============================================
// Component
// ============================================

export function TierBadge({
  tier,
  showInternalLabel = false,
  size = "sm",
  className = "",
}: TierBadgeProps) {
  const config = tierConfig[tier] ?? tierConfig.cool;
  
  const label = showInternalLabel
    ? tier.charAt(0).toUpperCase() + tier.slice(1)
    : config.clientLabel;

  const sizeClasses = size === "sm" 
    ? "px-2 py-0.5 text-xs"
    : "px-3 py-1 text-sm";

  return (
    <span
      className={`rounded font-medium ${config.style} ${sizeClasses} ${className}`}
    >
      {label}
    </span>
  );
}

export default TierBadge;
