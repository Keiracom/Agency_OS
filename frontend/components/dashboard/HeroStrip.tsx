/**
 * FILE: frontend/components/dashboard/HeroStrip.tsx
 * PURPOSE: BDR hero card + 4-card sum-row for /dashboard home
 * PHASE: B2.4 — cream/amber rebrand matching /demo renderHome lines 1670-1683
 *
 * Tailwind cream tokens (bg-panel/border-rule/text-ink). All numbers from
 * useDashboardStats — no fabricated data.
 */

"use client";

import { useDashboardStats } from "@/lib/hooks/useDashboardStats";
import { agencyPersona } from "@/lib/provider-labels";

interface SumCardProps {
  value: string;
  emSuffix?: string;
  label: string;
  delta: string;
}

function SumCard({ value, emSuffix, label, delta }: SumCardProps) {
  return (
    <div className="rounded-[10px] border border-rule bg-panel px-[18px] py-4">
      <div className="font-display font-bold text-[28px] leading-none text-ink">
        {value}
        {emSuffix && (
          <em
            className="not-italic font-bold text-[18px] text-amber ml-0.5"
            style={{ fontStyle: "normal" }}
          >
            {emSuffix}
          </em>
        )}
      </div>
      <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-ink-3 mt-1.5">
        {label}
      </div>
      <div className="font-mono text-[11px] text-ink-3 mt-1">{delta}</div>
    </div>
  );
}

function SumCardSkeleton() {
  return (
    <div className="rounded-[10px] border border-rule bg-panel px-[18px] py-4 animate-pulse">
      <div className="h-7 bg-surface rounded w-16 mb-2" />
      <div className="h-2.5 bg-surface rounded w-24 mb-1.5" />
      <div className="h-2.5 bg-surface rounded w-16" />
    </div>
  );
}

export function HeroStrip({ personaName = "Maya" }: { personaName?: string }) {
  const stats = useDashboardStats();

  const headline = agencyPersona(
    `${personaName} found %%REPLIES%% replies and booked %%MEETINGS%% meetings this week.`,
    undefined,
  );

  const [headPre, afterReplies] = headline.split("%%REPLIES%%");
  const [betweenMid, headPost] = afterReplies.split("%%MEETINGS%%");

  return (
    <section>
      {/* BDR hero card */}
      <div className="rounded-[12px] border border-rule bg-panel p-5 sm:p-6 mb-4 grid grid-cols-[60px_1fr] gap-5 items-center">
        <div className="w-[60px] h-[60px] rounded-full bg-gradient-to-br from-amber to-copper border-2 border-amber flex items-center justify-center font-display font-bold text-2xl text-white">
          {personaName[0]}
        </div>
        <div>
          <div className="font-mono text-[10px] tracking-[0.16em] text-ink-3 uppercase mb-1.5">
            Your BDR report this week
          </div>
          {stats.isLoading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-4 bg-surface rounded w-3/4" />
              <div className="h-4 bg-surface rounded w-1/2" />
            </div>
          ) : (
            <p className="font-display font-bold text-[20px] sm:text-[22px] leading-tight tracking-[-0.01em] text-ink">
              {headPre}
              <em
                className="text-amber not-italic"
                style={{ fontStyle: "italic" }}
              >
                {stats.deltas.repliesThisWeek} replies
              </em>
              {betweenMid}
              <em
                className="text-amber not-italic"
                style={{ fontStyle: "italic" }}
              >
                {stats.deltas.meetingsThisWeek} meetings
              </em>
              {headPost}
            </p>
          )}
        </div>
      </div>

      {/* Sum row — 4 cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-3.5">
        {stats.isLoading ? (
          <>
            <SumCardSkeleton />
            <SumCardSkeleton />
            <SumCardSkeleton />
            <SumCardSkeleton />
          </>
        ) : (
          <>
            <SumCard
              value={String(stats.prospectsContacted)}
              label="Prospects Contacted"
              delta={`+${stats.deltas.contactedThisWeek} this week`}
            />
            <SumCard
              value={String(stats.repliesReceived)}
              label="Replies Received"
              delta={`+${stats.deltas.repliesThisWeek} this week`}
            />
            <SumCard
              value={String(stats.meetingsBooked)}
              emSuffix={`/${stats.meetingsTarget}`}
              label="Meetings Booked"
              delta={`+${stats.deltas.meetingsThisWeek} this week`}
            />
            <SumCard
              value={String(stats.winRatePercent)}
              emSuffix="%"
              label="Win Rate"
              delta={`cycle day ${stats.cycleDay}/${stats.cycleLength}`}
            />
          </>
        )}
      </div>
    </section>
  );
}

export default HeroStrip;
