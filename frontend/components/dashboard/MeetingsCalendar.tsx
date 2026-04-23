/**
 * FILE: frontend/components/dashboard/MeetingsCalendar.tsx
 * PURPOSE: Week calendar view of booked meetings with today highlight
 * PHASE: PHASE-2.1-PIPELINE-MEETINGS
 *
 * Dark theme, Tailwind only. Groups meetings by day; click opens briefing.
 */

"use client";

import { useMemo } from "react";
import { Mail, Linkedin, Phone, MessageSquare } from "lucide-react";
import { MeetingRow } from "@/lib/hooks/useMeetingsData";
import { canonicalChannel } from "@/lib/provider-labels";

interface Props {
  meetings: MeetingRow[];
  onOpen: (id: string) => void;
  isLoading?: boolean;
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function startOfWeekMon(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  const day = x.getDay();            // 0=Sun
  const diff = day === 0 ? 6 : day - 1;
  x.setDate(x.getDate() - diff);
  return x;
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate();
}

function channelIcon(channel: string | null) {
  const label = canonicalChannel(channel ?? "");
  const Icon =
    label === "Email"    ? Mail :
    label === "LinkedIn" ? Linkedin :
    label === "SMS"      ? MessageSquare :
    label === "Voice AI" ? Phone :
    Mail;
  return <Icon className="w-3 h-3" strokeWidth={1.75} />;
}

export function MeetingsCalendar({ meetings, onOpen, isLoading }: Props) {
  const today = new Date();
  const weekStart = useMemo(() => startOfWeekMon(today), [today]);

  const days = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(weekStart);
      d.setDate(weekStart.getDate() + i);
      return d;
    });
  }, [weekStart]);

  const byDay = useMemo(() => {
    const m = new Map<string, MeetingRow[]>();
    for (const row of meetings) {
      if (!row.scheduledAt) continue;
      const key = new Date(row.scheduledAt).toDateString();
      const list = m.get(key) ?? [];
      list.push(row);
      m.set(key, list);
    }
    for (const list of m.values()) {
      list.sort((a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime());
    }
    return m;
  }, [meetings]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
      {days.map((d, i) => {
        const list = byDay.get(d.toDateString()) ?? [];
        const isToday = sameDay(d, today);
        return (
          <div
            key={d.toISOString()}
            className={`bg-gray-900 border rounded-xl p-3 min-h-[220px] ${
              isToday ? "border-amber-500/60 bg-amber-500/5" : "border-gray-800"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-[10px] tracking-widest uppercase text-gray-400">
                {DAY_LABELS[i]}
              </span>
              <span className={`font-mono text-[11px] ${isToday ? "text-amber-300" : "text-gray-500"}`}>
                {d.toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              </span>
            </div>
            <div className="space-y-2">
              {list.length === 0 ? (
                <div className="text-[11px] text-gray-600 italic py-4 text-center">
                  {isLoading ? "Loading…" : "No meetings"}
                </div>
              ) : list.map((m) => (
                <button
                  key={m.id}
                  onClick={() => onOpen(m.id)}
                  className="w-full text-left bg-gray-800 border border-gray-700 hover:border-amber-500/50 rounded-lg p-2.5 transition"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-serif text-sm text-gray-100 truncate">{m.dmName}</div>
                    {m.vrGrade && (
                      <span className="shrink-0 text-[10px] font-mono font-bold px-1 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                        {m.vrGrade}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-gray-400 truncate">{m.company}</div>
                  <div className="flex items-center justify-between mt-1.5 text-[10px] text-gray-500 font-mono">
                    <span className="inline-flex items-center gap-1">
                      {channelIcon(m.channel)}
                      {new Date(m.scheduledAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
