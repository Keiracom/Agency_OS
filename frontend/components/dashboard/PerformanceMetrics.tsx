/**
 * FILE: frontend/components/dashboard/PerformanceMetrics.tsx
 * PURPOSE: 4-column performance grid — Open Rate / Reply Rate /
 *          Meeting Rate / Avg Reply Time. PR2 dashboard rebuild.
 * REFERENCE: dashboard-master-agency-desk.html — `.sum-row` /
 *            `.sum-card` / `.sum-val` / `.sum-label` styling.
 */

"use client";

import { useDashboardV4 } from "@/hooks/use-dashboard-v4";

interface MetricCard {
  id: string;
  value: string;            // formatted display value
  unit?: string;             // amber suffix (em accent in prototype)
  label: string;             // mono uppercase
  delta?: string;            // small green/ink-3 line under the label
  todo?: boolean;            // when true, source is mocked — flag in UI
}

export function PerformanceMetrics() {
  const { data, isLoading } = useDashboardV4();

  // TODO(api): the V4 metrics endpoint exposes show_rate + meetings_*,
  // but does not yet return open_rate / reply_rate / avg_reply_time
  // directly. When `meetings_metrics_v4` is extended these constants
  // become real reads — until then we surface conservative placeholders
  // for the prototype layout, marked with `todo: true` so the UI
  // displays a small TODO badge.
  const cards: MetricCard[] = [
    {
      id: "open",
      value: "—",
      unit: "%",
      label: "Open Rate",
      delta: "endpoint pending",
      todo: true,
    },
    {
      id: "reply",
      value: "—",
      unit: "%",
      label: "Reply Rate",
      delta: "endpoint pending",
      todo: true,
    },
    {
      id: "meeting",
      value: data?.meetingsGoal?.target
        ? `${Math.round(((data?.meetingsGoal?.current ?? 0) / data.meetingsGoal.target) * 100)}`
        : "—",
      unit: "%",
      label: "Meeting Rate",
      delta:
        data?.meetingsGoal
          ? `${data.meetingsGoal.current}/${data.meetingsGoal.target} this cycle`
          : undefined,
    },
    {
      id: "avg-reply",
      value: "—",
      unit: "h",
      label: "Avg Reply Time",
      delta: "endpoint pending",
      todo: true,
    },
  ];

  return (
    <section>
      <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 font-semibold mb-3">
        Performance
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {cards.map(c => (
          <SumCard key={c.id} card={c} loading={isLoading} />
        ))}
      </div>
    </section>
  );
}

function SumCard({ card, loading }: { card: MetricCard; loading: boolean }) {
  return (
    <div className="rounded-[10px] border border-rule bg-panel px-[18px] py-4 relative">
      {card.todo && (
        <span className="absolute top-2 right-2 font-mono text-[8px] tracking-[0.12em] uppercase text-amber/80 bg-amber-soft border border-amber/30 rounded px-1.5 py-[1px]">
          TODO
        </span>
      )}

      {/* Value — Playfair 28px with amber em accent for the unit */}
      <div className="font-display font-bold text-[28px] leading-none text-ink">
        {loading ? "—" : card.value}
        {card.unit && (
          <em
            className="not-italic font-bold text-[18px] text-amber ml-0.5"
            style={{ fontStyle: "normal" }}
          >
            {card.unit}
          </em>
        )}
      </div>

      {/* Label — JetBrains Mono uppercase */}
      <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-ink-3 mt-1.5">
        {card.label}
      </div>

      {/* Delta — small mono line beneath the label */}
      {card.delta && (
        <div className="font-mono text-[11px] text-green mt-1">
          {card.delta}
        </div>
      )}
    </div>
  );
}
