/**
 * FILE: frontend/components/dashboard/TodayStrip.tsx
 * PURPOSE: Today's meetings timeline + scheduled-touches channel tally — Home v10
 * PHASE: PHASE-2.1-HOME-V10-PORT
 *
 * Dark theme, Tailwind only. Meetings from useUpcomingMeetings (existing).
 * Scheduled-touches counts from inline Supabase query. No emoji — lucide-react icons.
 */

"use client";

import { useEffect, useState } from "react";
import { useUpcomingMeetings } from "@/hooks/use-meetings";
import { useDashboardStats } from "@/lib/hooks/useDashboardStats";
import { createBrowserClient } from "@/lib/supabase";
import { useClient } from "@/hooks/use-client";
import { providerLabel } from "@/lib/provider-labels";
import { Mail, Linkedin, Phone, MessageSquare, Video } from "lucide-react";
import type { Meeting } from "@/lib/api/meetings";

// ── Channel touch tally ─────────────────────────────────────────────────────

interface TouchCounts {
  email: number;
  linkedin: number;
  phone: number;
  sms: number;
}

function useTodayTouches(): { counts: TouchCounts; isLoading: boolean } {
  const { clientId } = useClient();
  const [counts, setCounts] = useState<TouchCounts>({ email: 0, linkedin: 0, phone: 0, sms: 0 });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!clientId) return;
    let active = true;

    async function load() {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const sb = createBrowserClient() as any;
      const todayAEST = new Date(
        new Date().toLocaleString("en-AU", { timeZone: "Australia/Sydney" })
      )
        .toISOString()
        .slice(0, 10);

      try {
        const { data } = await sb
          .from("scheduled_touches")
          .select("channel")
          .eq("client_id", clientId)
          .eq("status", "pending")
          .gte("scheduled_at", `${todayAEST}T00:00:00`)
          .lt("scheduled_at", `${todayAEST}T23:59:59`);

        if (!active) return;
        const acc: TouchCounts = { email: 0, linkedin: 0, phone: 0, sms: 0 };
        for (const row of (data ?? []) as { channel: string }[]) {
          const ch = (row.channel ?? "").toLowerCase();
          if (ch === "email" || ch === "salesforge" || ch === "resend") acc.email++;
          else if (ch === "linkedin" || ch === "unipile") acc.linkedin++;
          else if (ch === "phone" || ch === "voice" || ch === "vapi") acc.phone++;
          else if (ch === "sms" || ch === "telnyx") acc.sms++;
        }
        setCounts(acc);
      } catch (e) {
        console.error("[TodayStrip] scheduled_touches failed", e);
      } finally {
        if (active) setIsLoading(false);
      }
    }

    load();
    return () => { active = false; };
  }, [clientId]);

  return { counts, isLoading };
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function todayAEST(): string {
  return new Date(
    new Date().toLocaleString("en-AU", { timeZone: "Australia/Sydney" })
  )
    .toISOString()
    .slice(0, 10);
}

function formatTimeAEST(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-AU", {
    timeZone: "Australia/Sydney",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function isMeetingToday(m: Meeting): boolean {
  if (!m.scheduled_at) return false;
  return m.scheduled_at.slice(0, 10) === todayAEST();
}

// ── Sub-components ───────────────────────────────────────────────────────────

function MeetingCard({ meeting }: { meeting: Meeting }) {
  return (
    <div className="flex-none w-72 bg-gray-800 border border-gray-700 rounded-xl p-3.5 cursor-pointer hover:border-amber-500 hover:shadow-[0_2px_10px_rgba(212,149,106,0.12)] transition-all scroll-snap-align-start">
      <div className="font-mono text-[11px] text-amber-400 font-semibold tracking-wider mb-1">
        {formatTimeAEST(meeting.scheduled_at)}
      </div>
      <div className="font-serif font-bold text-base text-gray-100 leading-tight">
        {providerLabel(meeting.lead_name)}
      </div>
      {meeting.lead_company && (
        <div className="text-[12.5px] text-gray-400 mt-0.5">
          {providerLabel(meeting.lead_company)}
        </div>
      )}
      <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-dashed border-gray-700">
        <Video size={16} className="text-gray-500" />
        <a
          href={`/dashboard/meetings/${meeting.id}`}
          className="font-mono text-[10px] tracking-wider text-amber-400 uppercase hover:text-amber-300"
        >
          Prep
        </a>
      </div>
    </div>
  );
}

function TouchCountRow({ counts, isLoading }: { counts: TouchCounts; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="animate-pulse flex gap-4 mt-4 pt-4 border-t border-gray-800">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-4 bg-gray-700 rounded w-16" />
        ))}
      </div>
    );
  }

  const total = counts.email + counts.linkedin + counts.phone + counts.sms;
  if (total === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-gray-800 font-mono text-[12px] text-gray-400">
      <span className="text-gray-600 uppercase text-[10px] tracking-wider mr-1">
        Scheduled today:
      </span>
      {counts.email > 0 && (
        <span className="flex items-center gap-1.5">
          <Mail size={13} className="text-gray-500" />
          <span className="text-gray-300">{counts.email} emails</span>
        </span>
      )}
      {counts.linkedin > 0 && (
        <span className="flex items-center gap-1.5">
          <Linkedin size={13} className="text-gray-500" />
          <span className="text-gray-300">{counts.linkedin} LinkedIn</span>
        </span>
      )}
      {counts.phone > 0 && (
        <span className="flex items-center gap-1.5">
          <Phone size={13} className="text-gray-500" />
          <span className="text-gray-300">{counts.phone} calls</span>
        </span>
      )}
      {counts.sms > 0 && (
        <span className="flex items-center gap-1.5">
          <MessageSquare size={13} className="text-gray-500" />
          <span className="text-gray-300">{counts.sms} SMS</span>
        </span>
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export function TodayStrip() {
  const { data: meetingsData, isLoading: meetingsLoading } = useUpcomingMeetings(20);
  const { cycleDay, cycleLength } = useDashboardStats();
  const { counts: touchCounts, isLoading: touchLoading } = useTodayTouches();

  const todayMeetings = (meetingsData?.items ?? []).filter(isMeetingToday);

  return (
    <section className="mb-6">
      {/* Strip header */}
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-serif font-bold text-[18px] text-gray-100">
          Your meetings <em className="text-amber-400 not-italic">today</em>
        </h2>
        <span className="font-mono text-[11px] text-gray-500">
          {meetingsLoading
            ? "—"
            : `${todayMeetings.length} ${todayMeetings.length === 1 ? "meeting" : "meetings"}`}
          {cycleDay > 0 && ` · cycle day ${cycleDay}/${cycleLength}`}
        </span>
      </div>

      {/* Meeting cards */}
      {meetingsLoading ? (
        <div className="flex gap-3 overflow-x-auto pb-2 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-none w-72 h-28 bg-gray-800 border border-gray-700 rounded-xl"
            />
          ))}
        </div>
      ) : todayMeetings.length === 0 ? (
        <div className="bg-gray-900 border border-dashed border-gray-700 rounded-xl px-5 py-4 text-[13px] text-gray-400">
          <span className="text-gray-200 font-medium">No meetings today.</span> Your schedule is
          clear.
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-2 scroll-snap-type-x-mandatory">
          {todayMeetings.map((m) => (
            <MeetingCard key={m.id} meeting={m} />
          ))}
        </div>
      )}

      {/* Scheduled-touches tally */}
      <TouchCountRow counts={touchCounts} isLoading={touchLoading} />
    </section>
  );
}

export default TodayStrip;
