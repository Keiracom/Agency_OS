/**
 * FILE: frontend/components/dashboard/MeetingsCalendar.tsx
 * PURPOSE: Week calendar view of booked meetings with today highlight.
 * REFERENCE: dashboard-master-agency-desk.html — `.cal-grid` /
 *            `.cal-day-head.today` / `.cal-event` (lines 380-410).
 * UPDATED:   2026-04-30 — B2.2 visual parity. Cream/amber palette with
 *            today's column subtly amber-tinted, today's day-head
 *            getting the prototype's `--amber-soft` background +
 *            `var(--copper)` weekday label + corner "TODAY" mono pill.
 *            Meeting cards adopt `.cal-event` styling (amber-soft fill,
 *            amber left border, copper time, ink-bold name, VR chip in
 *            top-right). Past meetings render in green per /demo's
 *            `.cal-event.green` rule.
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
    for (const list of Array.from(m.values())) {
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
            className={`relative rounded-[10px] border p-3 min-h-[220px] transition-colors ${
              isToday
                ? "border-amber bg-amber-soft"
                : "border-rule bg-panel"
            }`}
          >
            {/* Day head — TODAY pill matches /demo's `.cal-day-head.today::after` */}
            <div className="flex items-center justify-between mb-2">
              <span
                className={`font-mono text-[10px] tracking-[0.16em] uppercase font-semibold ${
                  isToday ? "text-copper" : "text-ink-3"
                }`}
              >
                {DAY_LABELS[i]}
              </span>
              <span
                className={`font-display font-bold text-[18px] leading-none ${
                  isToday ? "text-copper" : "text-ink"
                }`}
              >
                {d.getDate()}
              </span>
            </div>
            {isToday && (
              <span
                aria-hidden
                className="absolute top-2 right-2 font-mono text-[8px] tracking-[0.16em] uppercase font-bold text-copper"
              >
                TODAY
              </span>
            )}
            {/* Sub-row: short month for non-today columns (today shows just
                the big day number for emphasis) */}
            {!isToday && (
              <div className="font-mono text-[10px] text-ink-3 -mt-1 mb-2">
                {d.toLocaleDateString(undefined, { month: "short" })}
              </div>
            )}

            <div className="space-y-2">
              {list.length === 0 ? (
                <div className="text-[11px] text-ink-3 italic py-4 text-center">
                  {isLoading ? "Loading…" : (isToday ? "No meetings today" : "No meetings")}
                </div>
              ) : list.map((m) => {
                const ts = m.scheduledAt ? new Date(m.scheduledAt).getTime() : NaN;
                const isPast = Number.isFinite(ts) && ts < today.getTime();
                return (
                  <button
                    key={m.id}
                    onClick={() => onOpen(m.id)}
                    className={`w-full text-left rounded-[5px] p-2.5 transition-shadow hover:shadow-[0_2px_10px_rgba(212,149,106,0.25)] hover:-translate-y-px ${
                      isPast
                        ? "bg-[rgba(107,142,90,0.14)] border border-green border-l-[3px]"
                        : "bg-amber-soft border border-amber border-l-[3px]"
                    }`}
                    style={{ borderLeftColor: isPast ? "var(--green)" : "var(--amber)" }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div
                        className={`font-mono text-[9.5px] font-semibold leading-tight tracking-[0.04em] ${
                          isPast ? "text-green" : "text-copper"
                        }`}
                      >
                        {new Date(m.scheduledAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                      </div>
                      {m.vrGrade && (
                        <span
                          className="shrink-0 grid place-items-center w-[18px] h-[18px] rounded-[4px] font-display font-bold text-[11px]"
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
                    </div>
                    <div className="font-display font-bold text-[12px] text-ink mt-0.5 leading-tight truncate">
                      {m.dmName}
                    </div>
                    <div className="text-[11px] text-ink-2 truncate flex items-center gap-1 mt-0.5">
                      <span className="text-ink-3">{channelIcon(m.channel)}</span>
                      <span className="truncate">{m.company}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
