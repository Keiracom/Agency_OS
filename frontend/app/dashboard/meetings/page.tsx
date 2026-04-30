"use client";

/**
 * FILE: frontend/app/dashboard/meetings/page.tsx
 * PURPOSE: Meetings route — week calendar of booked meetings + per-meeting briefing
 * PHASE: PHASE-2.1-PIPELINE-MEETINGS
 */

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { MeetingsCalendar } from "@/components/dashboard/MeetingsCalendar";
import { MeetingBriefing } from "@/components/dashboard/MeetingBriefing";
import { ProspectDrawer } from "@/components/dashboard/ProspectDrawer";
import { useMeetingsData, MeetingRow } from "@/lib/hooks/useMeetingsData";

type Surface = "briefing" | "drawer";

export default function MeetingsPage() {
  const { meetings, isLoading } = useMeetingsData();
  const [activeMeetingId, setActiveMeetingId] = useState<string | null>(null);
  const [activeLeadId, setActiveLeadId] = useState<string | null>(null);
  const [surface, setSurface] = useState<Surface>("drawer");

  const active = useMemo<MeetingRow | null>(
    () => meetings.find((m) => m.id === activeMeetingId) ?? null,
    [meetings, activeMeetingId],
  );

  const openMeeting = (id: string) => {
    const m = meetings.find((x) => x.id === id);
    if (!m) return;
    if (surface === "briefing") setActiveMeetingId(id);
    else setActiveLeadId(m.leadId);
  };

  const upcomingThisWeek = useMemo(() => {
    const now = Date.now();
    const end = now + 7 * 24 * 60 * 60 * 1000;
    return meetings.filter((m) => {
      const t = m.scheduledAt ? new Date(m.scheduledAt).getTime() : NaN;
      return Number.isFinite(t) && t >= now && t <= end;
    });
  }, [meetings]);

  return (
    <AppShell pageTitle="Meetings">
      <div>
        <header className="mb-6">
          <h1 className="font-display font-bold text-[28px] md:text-[36px] text-ink leading-[1.06] tracking-[-0.02em]">
            Your week,
            <br />
            <em className="text-amber" style={{ fontStyle: "italic" }}>
              {upcomingThisWeek.length}{" "}
              {upcomingThisWeek.length === 1 ? "meeting" : "meetings"}.
            </em>
          </h1>
          <div className="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-2 mt-3">
            <p className="text-[13px] text-ink-3">
              Click any calendar slot or row to open the briefing.
            </p>
            <div className="inline-flex flex-wrap gap-1 rounded-md bg-surface p-[2px]">
              {(["drawer", "briefing"] as Surface[]).map((v) => {
                const isActive = surface === v;
                return (
                  <button
                    key={v}
                    onClick={() => setSurface(v)}
                    className={`px-3.5 py-1.5 font-mono text-[11px] tracking-[0.06em] rounded-[4px] uppercase transition-colors ${
                      isActive
                        ? "bg-ink text-white font-semibold"
                        : "text-ink-3 hover:text-ink"
                    }`}
                  >
                    {v}
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        <MeetingsCalendar
          meetings={meetings}
          onOpen={openMeeting}
          isLoading={isLoading}
        />

        {/* Upcoming list */}
        <section className="mt-8">
          <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 font-semibold mb-3">
            Upcoming this week
          </div>
          {upcomingThisWeek.length === 0 ? (
            <div className="rounded-[10px] border border-dashed border-rule bg-surface px-5 py-5 text-[13px] text-ink-2">
              <b className="text-ink">No meetings booked yet</b> — Maya is working on{" "}
              {meetings.length > 0 ? `${meetings.length} prospect${meetings.length === 1 ? "" : "s"}` : "your prospects"}.
            </div>
          ) : (
            <ul className="bg-panel border border-rule rounded-[10px] overflow-hidden divide-y divide-rule">
              {upcomingThisWeek.map((m) => {
                const dt = new Date(m.scheduledAt);
                return (
                  <li
                    key={m.id}
                    onClick={() => openMeeting(m.id)}
                    className="px-4 py-3.5 flex items-center gap-3 cursor-pointer hover:bg-amber-soft transition-colors"
                  >
                    {m.vrGrade && (
                      <span
                        className="shrink-0 grid place-items-center w-7 h-7 rounded-[5px] font-display font-bold text-[14px]"
                        style={{
                          backgroundColor:
                            m.vrGrade === "A" || m.vrGrade === "B" ? "var(--green)" :
                            m.vrGrade === "C" ? "var(--amber)" :
                            m.vrGrade === "D" ? "var(--copper)" :
                            "var(--red)",
                          color: m.vrGrade === "C" ? "var(--on-amber)" : "white",
                        }}
                      >
                        {m.vrGrade}
                      </span>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-[14px] text-ink truncate">
                        <span className="font-display font-bold">{m.dmName}</span>
                        <span className="text-ink-3"> · {m.company}</span>
                      </div>
                      {m.dmTitle && (
                        <div className="text-[12px] text-ink-3 truncate">{m.dmTitle}</div>
                      )}
                    </div>
                    <div className="text-[11.5px] text-ink-3 font-mono shrink-0 text-right">
                      {dt.toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                      {" · "}
                      {dt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <nav className="mt-6 text-[11px] font-mono text-ink-3 flex gap-3 pt-4 border-t border-rule">
          <Link href="/dashboard" className="hover:text-copper transition-colors">
            ← Home
          </Link>
          <Link href="/dashboard/pipeline" className="hover:text-copper transition-colors">
            Pipeline →
          </Link>
        </nav>
      </div>

      {active && <MeetingBriefing meeting={active} onClose={() => setActiveMeetingId(null)} />}
      <ProspectDrawer leadId={activeLeadId} onClose={() => setActiveLeadId(null)} />
    </AppShell>
  );
}
