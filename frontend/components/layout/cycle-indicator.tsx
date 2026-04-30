/**
 * FILE: frontend/components/layout/cycle-indicator.tsx
 * PURPOSE: "MAYA · DAY N/30" topbar indicator with pulsing amber dot.
 * REFERENCE: dashboard-master-agency-desk.html line 782 —
 *            <span class="tb-cycle"><span class="tb-dot"></span>
 *              MAYA · DAY 14/30
 *            </span>
 * USAGE:    Desktop header right-cluster + mobile topbar.
 *
 * Day count is derived from the calendar day-of-month modulo 30 — a
 * stand-in for a real `cycle_day` field on the metrics endpoint. When
 * the backend exposes a real cycle origin, swap the calendar fallback
 * for the live value (TODO(api) flagged below).
 */

"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const CYCLE_LENGTH_DAYS = 30;

function calendarCycleDay(): number {
  // TODO(api): replace with metrics.cycle_day once the dashboard
  // endpoint exposes it. Today = day-of-month, capped at 30.
  const today = new Date();
  const dayOfMonth = today.getDate();
  return Math.min(CYCLE_LENGTH_DAYS, Math.max(1, dayOfMonth));
}

interface Props {
  /** Optional override for tests / Storybook. */
  day?: number;
  /** Total cycle length. Defaults to 30. */
  total?: number;
  /** Compact mode (mobile topbar) — hides the "MAYA · " prefix. */
  compact?: boolean;
  className?: string;
}

export function CycleIndicator({
  day, total = CYCLE_LENGTH_DAYS, compact = false, className,
}: Props) {
  // Hydration-safe: SSR renders a placeholder, client computes the
  // real day after mount so React doesn't error on a Date mismatch.
  const [resolvedDay, setResolvedDay] = useState<number | null>(day ?? null);
  useEffect(() => {
    if (day === undefined) setResolvedDay(calendarCycleDay());
  }, [day]);

  const labelDay = resolvedDay ?? "—";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-mono text-[11px] tracking-[0.06em] text-ink-3",
        className,
      )}
      aria-label={`Maya cycle day ${labelDay} of ${total}`}
      title={`Maya cycle · day ${labelDay} of ${total}`}
    >
      {/* Pulsing amber dot — matches /demo's .tb-dot */}
      <span className="relative inline-flex w-[7px] h-[7px]">
        <span
          aria-hidden
          className="absolute inset-0 rounded-full opacity-60 animate-ping"
          style={{ backgroundColor: "var(--amber)" }}
        />
        <span
          aria-hidden
          className="relative inline-flex w-[7px] h-[7px] rounded-full"
          style={{
            backgroundColor: "var(--amber)",
            boxShadow: "0 0 0 3px rgba(212,149,106,0.18)",
          }}
        />
      </span>
      <span className="whitespace-nowrap">
        {compact ? "" : <span className="font-semibold">MAYA · </span>}
        DAY {labelDay}/{total}
      </span>
    </span>
  );
}
