/**
 * FILE: frontend/components/dashboard/PerformanceMetrics.tsx
 * PURPOSE: Performance grid — Meeting Rate (live, wired to
 *          useDashboardV4.meetingsGoal). Open Rate / Reply Rate /
 *          Avg Reply Time render an "awaiting first cycle" empty
 *          state until the metrics endpoint exposes them. A3
 *          dispatch (2026-04-30): no fabricated numbers, no
 *          internal TODO badges visible to users.
 * REFERENCE: dashboard-master-agency-desk.html — `.sum-row` /
 *            `.sum-card` / `.sum-val` / `.sum-label` styling.
 */

"use client";

import { useDashboardV4 } from "@/hooks/use-dashboard-v4";

interface MetricCard {
  id: string;
  /** Formatted live value, or undefined when not yet wired. */
  value?: string;
  /** Amber unit suffix (em accent). */
  unit?: string;
  /** Mono uppercase label. */
  label: string;
  /** Small green/ink-3 line under the label — only shown for live cards. */
  delta?: string;
}

export function PerformanceMetrics() {
  const { data, isLoading } = useDashboardV4();

  const meetingsGoal = data?.meetingsGoal;
  const meetingRate = meetingsGoal?.target
    ? `${Math.round(((meetingsGoal.current ?? 0) / meetingsGoal.target) * 100)}`
    : undefined;

  const cards: MetricCard[] = [
    {
      id: "open",
      label: "Open Rate",
      // value left undefined → renders "—" + "Awaiting first cycle"
    },
    {
      id: "reply",
      label: "Reply Rate",
    },
    {
      id: "meeting",
      value: meetingRate,
      unit: meetingRate ? "%" : undefined,
      label: "Meeting Rate",
      delta: meetingsGoal
        ? `${meetingsGoal.current}/${meetingsGoal.target} this cycle`
        : undefined,
    },
    {
      id: "avg-reply",
      label: "Avg Reply Time",
    },
  ];

  return (
    <section>
      <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 font-semibold mb-3">
        Performance
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-3.5">
        {cards.map(c => (
          <SumCard key={c.id} card={c} loading={isLoading} />
        ))}
      </div>
    </section>
  );
}

function SumCard({ card, loading }: { card: MetricCard; loading: boolean }) {
  const hasValue = card.value !== undefined;
  return (
    <div className="rounded-[10px] border border-rule bg-panel px-[18px] py-4">
      <div className="font-display font-bold text-[28px] leading-none text-ink">
        {loading ? "—" : (hasValue ? card.value : "—")}
        {hasValue && card.unit && (
          <em
            className="not-italic font-bold text-[18px] text-amber ml-0.5"
            style={{ fontStyle: "normal" }}
          >
            {card.unit}
          </em>
        )}
      </div>

      <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-ink-3 mt-1.5">
        {card.label}
      </div>

      {hasValue ? (
        card.delta && (
          <div className="font-mono text-[11px] text-green mt-1">
            {card.delta}
          </div>
        )
      ) : (
        <div className="font-mono text-[11px] text-ink-3 mt-1">
          Awaiting first cycle
        </div>
      )}
    </div>
  );
}
