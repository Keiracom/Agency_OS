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

const tierConfig: Record<ALSTier, { style: string; clientLabel: string }> = {
  hot: { style: "bg-orange-100 text-orange-700", clientLabel: "High Priority" },
  warm: { style: "bg-yellow-100 text-yellow-700", clientLabel: "Engaged" },
  cool: { style: "bg-blue-100 text-blue-700", clientLabel: "Nurturing" },
  cold: { style: "bg-slate-100 text-slate-600", clientLabel: "Low Activity" },
  dead: { style: "bg-slate-100 text-slate-500", clientLabel: "Inactive" },
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
