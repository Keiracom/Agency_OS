/**
 * FILE: frontend/components/dashboard/TodayStrip.tsx
 * PURPOSE: Today's meetings horizontal scroll strip + scheduled-touches tally
 * PHASE: B2.4 — cream/amber rebrand matching /demo renderHome lines 1685-1686
 *
 * Tailwind cream tokens. Meetings from useUpcomingMeetings, scheduled-touches
 * from inline Supabase query. lucide-react icons only.
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

interface TouchCounts {
  email: number;
  linkedin: number;
  phone: number;
  sms: number;
}

function useTodayTouches(): { counts: TouchCounts; isLoading: boolean } {
  const { clientId } = useClient();
  const [counts, setCounts] = useState<TouchCounts>({
    email: 0, linkedin: 0, phone: 0, sms: 0,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!clientId) return;
    let active = true;

    async function load() {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const sb = createBrowserClient() as any;
      const todayAEST = new Date(
        new Date().toLocaleString("en-AU", { timeZone: "Australia/Sydney" }),
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
    return () => {
      active = false;
    };
  }, [clientId]);

  return { counts, isLoading };
}

function todayAEST(): string {
  return new Date(
    new Date().toLocaleString("en-AU", { timeZone: "Australia/Sydney" }),
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

function MeetingCard({ meeting }: { meeting: Meeting }) {
  return (
    <div className="flex-none w-full sm:w-72 rounded-[10px] border border-rule bg-panel p-3.5 cursor-pointer hover:border-amber hover:shadow-[0_2px_10px_rgba(212,149,106,0.18)] transition-all scroll-snap-align-start">
      <div className="font-mono text-[11px] text-amber font-semibold tracking-wider mb-1">
        {formatTimeAEST(meeting.scheduled_at)}
      </div>
      <div className="font-display font-bold text-base text-ink leading-tight">
        {providerLabel(meeting.lead_name)}
      </div>
      {meeting.lead_company && (
        <div className="text-[12.5px] text-ink-2 mt-0.5">
          {providerLabel(meeting.lead_company)}
        </div>
      )}
      <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-dashed border-rule">
        <Video size={16} className="text-ink-3" />
        <a
          href={`/dashboard/meetings/${meeting.id}`}
          className="font-mono text-[10px] tracking-wider text-amber uppercase hover:opacity-80"
        >
          Prep
        </a>
      </div>
    </div>
  );
}

function TouchCountRow({
  counts, isLoading,
}: { counts: TouchCounts; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="animate-pulse flex gap-4 mt-4 pt-4 border-t border-rule">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-4 bg-surface rounded w-16" />
        ))}
      </div>
    );
  }

  const total = counts.email + counts.linkedin + counts.phone + counts.sms;
  if (total === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-rule font-mono text-[12px] text-ink-2">
      <span className="text-ink-3 uppercase text-[10px] tracking-wider mr-1">
        Scheduled today:
      </span>
      {counts.email > 0 && (
        <span className="flex items-center gap-1.5">
          <Mail size={13} className="text-ink-3" />
          <span className="text-ink">{counts.email} emails</span>
        </span>
      )}
      {counts.linkedin > 0 && (
        <span className="flex items-center gap-1.5">
          <Linkedin size={13} className="text-ink-3" />
          <span className="text-ink">{counts.linkedin} LinkedIn</span>
        </span>
      )}
      {counts.phone > 0 && (
        <span className="flex items-center gap-1.5">
          <Phone size={13} className="text-ink-3" />
          <span className="text-ink">{counts.phone} calls</span>
        </span>
      )}
      {counts.sms > 0 && (
        <span className="flex items-center gap-1.5">
          <MessageSquare size={13} className="text-ink-3" />
          <span className="text-ink">{counts.sms} SMS</span>
        </span>
      )}
    </div>
  );
}

export function TodayStrip() {
  const { data: meetingsData, isLoading: meetingsLoading } = useUpcomingMeetings(20);
  const { cycleDay, cycleLength } = useDashboardStats();
  const { counts: touchCounts, isLoading: touchLoading } = useTodayTouches();

  const todayMeetings = (meetingsData?.items ?? []).filter(isMeetingToday);

  return (
    <section>
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-display font-bold text-[18px] text-ink">
          Your meetings{" "}
          <em className="text-amber not-italic" style={{ fontStyle: "italic" }}>
            today
          </em>
        </h2>
        <span className="font-mono text-[11px] text-ink-3">
          {meetingsLoading
            ? "—"
            : `${todayMeetings.length} ${
                todayMeetings.length === 1 ? "meeting" : "meetings"
              }`}
          {cycleDay > 0 && ` · cycle day ${cycleDay}/${cycleLength}`}
        </span>
      </div>

      {meetingsLoading ? (
        <div className="flex gap-3 overflow-x-auto pb-2 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-none w-72 h-28 rounded-[10px] border border-rule bg-panel"
            />
          ))}
        </div>
      ) : todayMeetings.length === 0 ? (
        <div className="rounded-[10px] border border-dashed border-rule bg-panel px-5 py-4 text-[13px] text-ink-2">
          <span className="text-ink font-medium">No meetings today.</span> Your
          schedule is clear.
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-2 scroll-snap-type-x-mandatory">
          {todayMeetings.map((m) => (
            <MeetingCard key={m.id} meeting={m} />
          ))}
        </div>
      )}

      <TouchCountRow counts={touchCounts} isLoading={touchLoading} />
    </section>
  );
}

export default TodayStrip;
