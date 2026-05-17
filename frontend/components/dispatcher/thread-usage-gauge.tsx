/**
 * FILE: frontend/components/dispatcher/thread-usage-gauge.tsx
 * PURPOSE: Customer-facing thread-usage gauge for the Dispatcher dashboard.
 *          Shows current concurrent thread count vs the tenant's tier
 *          ceiling. Sub-KEI claimer wires the Valkey-backed live count
 *          (acceptance: updates within 5s of consumption).
 * KEI: 161 (Part 17.4 sub-KEI of KEI-114 dashboard MVP).
 *
 * Stub: typed component shell + props interface. Renders the shadcn
 * Progress primitive at `(active / ceiling) * 100`. Data layer is the
 * companion useThreadUsage hook stub. No realtime — sub-KEI implements.
 */

import * as React from "react";
import { Progress } from "../ui/progress";

export type DispatcherTier = "free" | "starter" | "growth" | "scale" | "enterprise";

export interface ThreadUsage {
  /** Live count of concurrent threads currently consumed by this tenant. */
  active: number;
  /** Hard ceiling for the tenant's current tier. */
  ceiling: number;
  /** Tier the tenant is on (display only — does NOT affect the bar math). */
  tier: DispatcherTier;
}

export interface ThreadUsageGaugeProps {
  usage: ThreadUsage | null;
  loading?: boolean;
  loadingLabel?: string;
}

const TIER_LABEL: Record<DispatcherTier, string> = {
  free: "Free",
  starter: "Starter",
  growth: "Growth",
  scale: "Scale",
  enterprise: "Enterprise",
};

function _pct(usage: ThreadUsage): number {
  if (usage.ceiling <= 0) return 0;
  const raw = (usage.active / usage.ceiling) * 100;
  // Cap at 100 so we don't visually overflow on burst-then-drain races.
  return Math.min(100, Math.max(0, raw));
}

export function ThreadUsageGauge({
  usage,
  loading = false,
  loadingLabel = "Loading thread usage…",
}: Readonly<ThreadUsageGaugeProps>) {
  if (loading) {
    return (
      <div
        data-testid="thread-usage-loading"
        className="py-4 text-sm text-muted-foreground"
      >
        {loadingLabel}
      </div>
    );
  }
  if (usage === null) {
    return (
      <div data-testid="thread-usage-empty" className="py-4 text-sm text-muted-foreground">
        No usage data yet.
      </div>
    );
  }
  const pct = _pct(usage);
  const isAtCeiling = usage.active >= usage.ceiling;
  return (
    <div
      data-testid="thread-usage-gauge"
      data-tier={usage.tier}
      data-at-ceiling={isAtCeiling}
      className="space-y-2 py-2"
    >
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">
          {usage.active} / {usage.ceiling} threads
        </span>
        <span className="text-muted-foreground">{TIER_LABEL[usage.tier]}</span>
      </div>
      <Progress value={pct} data-testid="thread-usage-bar" />
      {isAtCeiling ? (
        <p data-testid="thread-usage-at-ceiling" className="text-xs text-destructive">
          At tier ceiling — new threads queue or fail until a slot frees.
        </p>
      ) : null}
    </div>
  );
}
