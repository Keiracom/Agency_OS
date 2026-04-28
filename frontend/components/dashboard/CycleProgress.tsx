/**
 * FILE: frontend/components/dashboard/CycleProgress.tsx
 * PURPOSE: "Day X of 30" cycle progress card — progress bar +
 *          contacted / replies / meetings counts. PR2 dashboard rebuild.
 * REFERENCE: dashboard-master-agency-desk.html — `.bdr-hero` +
 *            `MAYA · DAY 14/30` cycle indicator combined into one card.
 */

"use client";

import { useDashboardV4 } from "@/hooks/use-dashboard-v4";

const CYCLE_LENGTH_DAYS = 30;

interface CycleProgressData {
  currentDay: number;            // 1..30
  contacted: number;
  replies: number;
  meetings: number;
}

/**
 * Pull cycle data from useDashboardV4. The V4 hook does not yet return a
 * cycle_day field — use the calendar day-of-month (1..30) modulo 30 as a
 * stand-in until the backend exposes a real cycle origin.
 *
 * TODO(api): wire to a real cycle_day from `meetings_metrics_v4` once the
 * backend tracks cycle start. Until then this is approximate.
 */
function useCycleProgress(): { data: CycleProgressData; loading: boolean } {
  const { data, isLoading } = useDashboardV4();

  // TODO(api): replace with metrics.cycle_day once backend exposes it.
  const today = new Date();
  const dayOfMonth = today.getDate();
  const currentDay = Math.min(CYCLE_LENGTH_DAYS, Math.max(1, dayOfMonth));

  const contacted = pickQuickStat(data?.quickStats ?? [], ["contacted", "prospects"]);
  const replies   = pickQuickStat(data?.quickStats ?? [], ["replies", "reply"]);
  const meetings  = data?.meetingsGoal?.current ?? 0;

  return {
    data: { currentDay, contacted, replies, meetings },
    loading: isLoading,
  };
}

function pickQuickStat(
  stats: Array<{ label: string; value: string | number }>,
  needles: string[],
): number {
  for (const s of stats) {
    const lbl = (s.label || "").toLowerCase();
    if (needles.some(n => lbl.includes(n))) {
      const num = typeof s.value === "number" ? s.value : parseInt(String(s.value).replace(/[^\d]/g, ""), 10);
      if (!Number.isNaN(num)) return num;
    }
  }
  return 0;
}

export function CycleProgress() {
  const { data: c, loading } = useCycleProgress();
  const pct = Math.round((c.currentDay / CYCLE_LENGTH_DAYS) * 100);

  return (
    <section className="rounded-[10px] border border-rule bg-panel p-5 sm:p-6">
      {/* Eyebrow + day label */}
      <div className="flex items-baseline justify-between gap-4">
        <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 font-semibold">
          Cycle Progress
        </div>
        <div className="font-mono text-[11px] text-ink-3 tracking-[0.06em]">
          {loading ? "—" : `${CYCLE_LENGTH_DAYS - c.currentDay} days remaining`}
        </div>
      </div>

      {/* Headline — Playfair with amber italic accent */}
      <h2 className="font-display font-bold text-[28px] text-ink leading-[1.15] tracking-[-0.02em] mt-2">
        Day <em className="text-amber not-italic" style={{ fontStyle: "italic" }}>{c.currentDay}</em>
        <span className="text-ink-3"> of {CYCLE_LENGTH_DAYS}</span>
      </h2>

      {/* Progress bar */}
      <div
        className="mt-4 h-2 w-full rounded-full overflow-hidden"
        style={{ backgroundColor: "rgba(12,10,8,0.06)" }}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={CYCLE_LENGTH_DAYS}
        aria-valuenow={c.currentDay}
      >
        <div
          className="h-full transition-[width] duration-500 ease-out"
          style={{
            width: `${pct}%`,
            background: "linear-gradient(90deg, var(--amber) 0%, var(--copper) 100%)",
          }}
        />
      </div>

      {/* Counts row — 3 cells */}
      <div className="grid grid-cols-3 gap-4 mt-5 pt-5 border-t border-rule">
        <CycleCell label="Contacted" value={c.contacted} loading={loading} />
        <CycleCell label="Replies"    value={c.replies}    loading={loading} />
        <CycleCell label="Meetings"   value={c.meetings}   loading={loading} />
      </div>
    </section>
  );
}

function CycleCell({
  label, value, loading,
}: { label: string; value: number; loading: boolean }) {
  return (
    <div>
      <div className="font-display font-bold text-[24px] text-ink leading-none">
        {loading ? "—" : value.toLocaleString()}
      </div>
      <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-ink-3 mt-1.5">
        {label}
      </div>
    </div>
  );
}
