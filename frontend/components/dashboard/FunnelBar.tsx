/**
 * FunnelBar — horizontal cycle funnel.
 *
 * Port of /demo's .funnel-bar block (dashboard-master-agency-desk.html
 * lines 207-218 + 1704-1710). Five segments — Discovered → Contacted →
 * Replied → Meeting → Won — with proportional widths and the /demo
 * colour scheme:
 *   discovered → ink-3
 *   contacted  → blue
 *   replied    → amber (with on-amber text — matches prototype)
 *   meeting    → green
 *   won        → copper
 *
 * Real data from useFunnelData; renders zeros without fabricating
 * numbers. Each segment's flex value is its raw count, with a small
 * floor (5% of the max) so a "Won = 3" sliver next to "Discovered =
 * 600" still shows its label.
 */

"use client";

import { useFunnelData, type FunnelStage } from "@/lib/hooks/useFunnelData";

const STAGE_BG: Record<FunnelStage["key"], string> = {
  discovered: "var(--ink-3)",
  contacted:  "var(--blue)",
  replied:    "var(--amber)",
  meeting:    "var(--green)",
  won:        "var(--copper)",
};

// `replied` uses on-amber text per the prototype; everything else is white.
const STAGE_FG: Partial<Record<FunnelStage["key"], string>> = {
  replied: "var(--on-amber)",
};

export function FunnelBar() {
  const { stages, total, contactedPercent, isLoading, error } = useFunnelData();

  if (isLoading) {
    return (
      <div className="mb-5">
        <div className="h-9 rounded-md bg-rule animate-pulse" />
        <div className="h-3 mt-1.5 w-72 rounded bg-rule animate-pulse" />
      </div>
    );
  }

  if (error || total === 0) {
    return (
      <div className="mb-5">
        <div className="flex h-9 rounded-md border border-rule overflow-hidden bg-surface">
          {stages.map((s) => (
            <div
              key={s.key}
              className="flex-1 flex flex-col justify-center px-3.5 font-mono border-r border-rule last:border-r-0 text-ink-3"
            >
              <div className="text-[11px] md:text-[13px] font-bold leading-none">0</div>
              <div className="text-[9px] tracking-[0.1em] opacity-80 mt-0.5 uppercase">
                {s.label}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-1.5 font-mono text-[11px] tracking-wide text-ink-3">
          No pipeline data yet — funnel activates when the first prospect
          enters the cycle.
        </div>
      </div>
    );
  }

  const max = Math.max(...stages.map((s) => s.count), 1);
  const minFloor = Math.ceil(max * 0.05);

  return (
    <div className="mb-5">
      <div className="flex h-9 rounded-md border border-rule overflow-hidden">
        {stages.map((s) => {
          const flex = Math.max(s.count, minFloor);
          return (
            <div
              key={s.key}
              style={{
                flex,
                backgroundColor: STAGE_BG[s.key],
                color: STAGE_FG[s.key] ?? "white",
              }}
              className="flex flex-col justify-center px-3.5 font-mono overflow-hidden min-w-0"
            >
              <div className="text-[11px] md:text-[13px] font-bold leading-none whitespace-nowrap">
                {s.count}
              </div>
              <div className="text-[9px] tracking-[0.1em] opacity-90 mt-0.5 uppercase whitespace-nowrap">
                {s.label}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-1.5 font-mono text-[11px] tracking-wide text-ink-3">
        {stages[0].count} prospects · {stages[1].count} contacted ({contactedPercent.toFixed(0)}%) · {stages[2].count} replied · {stages[3].count} meetings · {stages[4].count} won
      </div>
    </div>
  );
}

export default FunnelBar;
