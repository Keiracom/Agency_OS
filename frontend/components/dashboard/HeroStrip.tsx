/**
 * FILE: frontend/components/dashboard/HeroStrip.tsx
 * PURPOSE: BDR hero card + 4-card sum-row for Home v10
 * PHASE: PHASE-2.1-HOME-V10-PORT
 *
 * Dark theme, Tailwind only. All numbers from useDashboardStats — no fabricated data.
 */

"use client";

import { useDashboardStats } from "@/lib/hooks/useDashboardStats";
import { agencyPersona } from "@/lib/provider-labels";

interface SumCardProps {
  value: string;
  label: string;
  delta: string;
}

function SumCard({ value, label, delta }: SumCardProps) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
      <div className="font-serif text-3xl font-bold text-gray-100 leading-none">{value}</div>
      <div className="font-mono text-[10px] tracking-widest text-gray-500 uppercase mt-1.5">
        {label}
      </div>
      <div className="font-mono text-[11px] text-emerald-400 mt-1">{delta}</div>
    </div>
  );
}

function SumCardSkeleton() {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 animate-pulse">
      <div className="h-8 bg-gray-700 rounded w-16 mb-2" />
      <div className="h-2.5 bg-gray-700 rounded w-24 mb-1.5" />
      <div className="h-2.5 bg-gray-700 rounded w-16" />
    </div>
  );
}

export function HeroStrip({ personaName = "Maya" }: { personaName?: string }) {
  const stats = useDashboardStats();

  const headline = agencyPersona(
    `${personaName} found %%REPLIES%% replies and booked %%MEETINGS%% meetings this week.`,
    undefined
  );

  const [headPre, afterReplies] = headline.split("%%REPLIES%%");
  const [betweenMid, headPost] = afterReplies.split("%%MEETINGS%%");

  return (
    <section className="mb-6">
      {/* BDR Hero */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-4 grid grid-cols-[60px_1fr] gap-5 items-center">
        {/* Avatar */}
        <div className="w-[60px] h-[60px] rounded-full bg-gradient-to-br from-amber-400 to-amber-700 border-2 border-amber-500 flex items-center justify-center font-serif font-bold text-2xl text-gray-900">
          {personaName[0]}
        </div>

        {/* Copy */}
        <div>
          <div className="font-mono text-[10px] tracking-[0.16em] text-gray-500 uppercase mb-1.5">
            Your BDR report this week
          </div>
          {stats.isLoading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-4 bg-gray-700 rounded w-3/4" />
              <div className="h-4 bg-gray-700 rounded w-1/2" />
            </div>
          ) : (
            <p className="font-serif font-bold text-[22px] leading-tight tracking-[-0.01em] text-gray-100">
              {headPre}
              <em className="text-amber-400 not-italic">
                {stats.deltas.repliesThisWeek} replies
              </em>
              {betweenMid}
              <em className="text-amber-400 not-italic">
                {stats.deltas.meetingsThisWeek} meetings
              </em>
              {headPost}
            </p>
          )}
        </div>
      </div>

      {/* Sum row — 4 cards */}
      <div className="grid grid-cols-4 gap-3.5">
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
              value={`${stats.meetingsBooked}/${stats.meetingsTarget}`}
              label="Meetings Booked"
              delta={`+${stats.deltas.meetingsThisWeek} this week`}
            />
            <SumCard
              value={`${stats.winRatePercent}%`}
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
