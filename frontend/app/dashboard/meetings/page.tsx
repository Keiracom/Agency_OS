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
      <div className="min-h-screen bg-gray-950 text-gray-100 p-4 md:p-6">
        <header className="mb-4">
          <h1 className="font-serif text-2xl md:text-3xl text-gray-100">
            Your week,{" "}
            <em className="font-normal italic text-amber-300">
              {upcomingThisWeek.length}{" "}
              {upcomingThisWeek.length === 1 ? "meeting" : "meetings"}.
            </em>
          </h1>
          <div className="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-2">
            <p className="text-sm text-gray-400">
              Click any slot to open the prospect drawer.
            </p>
            <div className="inline-flex flex-wrap gap-1 rounded-lg border border-gray-800 bg-gray-900 p-0.5">
              {(["drawer", "briefing"] as Surface[]).map((v) => (
                <button
                  key={v}
                  onClick={() => setSurface(v)}
                  className={`px-3 py-1 text-[10px] font-mono uppercase tracking-widest rounded-md ${
                    surface === v
                      ? "bg-amber-500/10 text-amber-300 border border-amber-500/40"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>
        </header>

        <MeetingsCalendar
          meetings={meetings}
          onOpen={openMeeting}
          isLoading={isLoading}
        />

        {/* Upcoming list */}
        <section className="mt-6">
          <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500 mb-2">
            Upcoming this week
          </div>
          {upcomingThisWeek.length === 0 ? (
            <div className="text-sm text-gray-500 italic py-4">
              No meetings booked yet.
            </div>
          ) : (
            <ul className="divide-y divide-gray-800 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              {upcomingThisWeek.map((m) => (
                <li
                  key={m.id}
                  onClick={() => openMeeting(m.id)}
                  className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-gray-800/60"
                >
                  {m.vrGrade && (
                    <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                      {m.vrGrade}
                    </span>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-gray-100 truncate">
                      {m.dmName} · <span className="text-gray-400">{m.company}</span>
                    </div>
                    <div className="text-xs text-gray-500 truncate">
                      {m.dmTitle ?? ""}
                    </div>
                  </div>
                  <div className="text-xs text-gray-400 font-mono shrink-0">
                    {new Date(m.scheduledAt).toLocaleDateString(undefined, {
                      month: "short", day: "numeric",
                    })}
                    {" · "}
                    {new Date(m.scheduledAt).toLocaleTimeString([], {
                      hour: "numeric", minute: "2-digit",
                    })}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <nav className="mt-6 text-xs text-gray-500 font-mono flex gap-3">
          <Link href="/dashboard" className="hover:text-gray-300">← Home</Link>
          <Link href="/dashboard/pipeline" className="hover:text-gray-300">
            Pipeline →
          </Link>
        </nav>
      </div>

      {active && <MeetingBriefing meeting={active} onClose={() => setActiveMeetingId(null)} />}
      <ProspectDrawer leadId={activeLeadId} onClose={() => setActiveLeadId(null)} />
    </AppShell>
  );
}
