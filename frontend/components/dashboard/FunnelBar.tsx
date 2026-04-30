/**
 * FunnelBar — horizontal cycle funnel.
 *
 * Port of Master v10 .funnel-bar (dashboard-master-agency-desk.html:207-218, 1704-1710).
 * 5 segments (Discovered > Contacted > Replied > Meeting > Won) with proportional widths.
 * Real data from useFunnelData hook; shows 0 on empty tables, never fabricates numbers.
 */

"use client";

import { useFunnelData, type FunnelStage } from "@/lib/hooks/useFunnelData";

const STAGE_STYLES: Record<FunnelStage["key"], string> = {
  discovered: "bg-gray-700",
  contacted: "bg-amber-700",
  replied: "bg-amber-600",
  meeting: "bg-emerald-700",
  won: "bg-emerald-500",
};

export function FunnelBar() {
  const { stages, total, contactedPercent, isLoading, error } = useFunnelData();

  if (isLoading) {
    return (
      <div className="mb-5">
        <div className="h-9 rounded-md bg-gray-800 animate-pulse" />
        <div className="h-3 mt-1.5 w-72 rounded bg-gray-800 animate-pulse" />
      </div>
    );
  }

  if (error || total === 0) {
    return (
      <div className="mb-5">
        <div className="flex h-9 rounded-md border border-gray-800 overflow-hidden">
          {stages.map((s) => (
            <div
              key={s.key}
              className="flex-1 flex flex-col justify-center px-3.5 text-white font-mono border-r border-white/20 last:border-r-0 bg-gray-800"
            >
              <div className="text-[11px] md:text-[13px] font-bold leading-none">0</div>
              <div className="text-[9px] tracking-[0.1em] opacity-80 mt-0.5 uppercase">
                {s.label}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-1.5 text-[11px] font-mono tracking-wide text-gray-400">
          No pipeline data yet — funnel activates when first prospect enters cycle.
        </div>
      </div>
    );
  }

  const max = Math.max(...stages.map((s) => s.count), 1);

  return (
    <div className="mb-5">
      <div className="flex h-9 rounded-md border border-gray-800 overflow-hidden">
        {stages.map((s) => {
          const flex = Math.max(s.count, Math.ceil(max * 0.05));
          return (
            <div
              key={s.key}
              style={{ flex }}
              className={`flex flex-col justify-center px-3.5 text-white font-mono border-r border-white/20 last:border-r-0 overflow-hidden min-w-0 ${STAGE_STYLES[s.key]}`}
            >
              <div className="text-[11px] md:text-[13px] font-bold leading-none whitespace-nowrap">
                {s.count}
              </div>
              <div className="text-[9px] tracking-[0.1em] opacity-85 mt-0.5 uppercase whitespace-nowrap">
                {s.label}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-1.5 text-[11px] font-mono tracking-wide text-gray-400">
        {stages[0].count} prospects · {stages[1].count} contacted ({contactedPercent.toFixed(0)}%) · {stages[2].count} replied · {stages[3].count} meetings · {stages[4].count} won
      </div>
    </div>
  );
}

export default FunnelBar;
