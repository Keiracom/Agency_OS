/**
 * FILE: frontend/components/dashboard/OutreachTimeline.tsx
 * PURPOSE: Vertical timeline — past (emerald) + NOW divider + future (amber) + state (blue)
 * PHASE: PHASE-2.1-TIMELINE-VR-POPOVERS
 *
 * Used inside ProspectDrawer. Consumes TimelineEvent[] from useOutreachTimeline.
 * Per-future-touch controls (Pause / Skip / Accelerate) POST to
 * /api/v1/outreach/approval.
 */

"use client";

import { useState } from "react";
import {
  Mail, Linkedin, Phone, MessageSquare, MessageCircle,
  PauseCircle, SkipForward, FastForward, Flag,
} from "lucide-react";
import type { TimelineEvent } from "@/lib/hooks/useOutreachTimeline";
import { canonicalChannel, providerLabel } from "@/lib/provider-labels";

interface Props {
  events: TimelineEvent[];
  isLoading?: boolean;
}

function channelIcon(channel: string | null) {
  const label = canonicalChannel(channel ?? "");
  const Icon =
    label === "Email"    ? Mail :
    label === "LinkedIn" ? Linkedin :
    label === "SMS"      ? MessageSquare :
    label === "Voice AI" ? Phone :
    MessageCircle;
  return <Icon className="w-3.5 h-3.5" strokeWidth={1.75} />;
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function OutreachTimeline({ events, isLoading }: Props) {
  // Split at "now" to insert the NOW divider
  const pastOrNow: TimelineEvent[] = [];
  const future: TimelineEvent[] = [];
  for (const e of events) {
    if (e.isFuture) future.push(e);
    else pastOrNow.push(e);
  }

  if (!events.length) {
    return (
      <div className="text-xs text-gray-500 italic">
        {isLoading ? "Loading timeline…" : "No outreach activity yet."}
      </div>
    );
  }

  return (
    <ol className="relative pl-5 border-l border-gray-800 space-y-3">
      {pastOrNow.map((e) => <TimelineRow key={e.id} event={e} />)}
      <NowDivider />
      {future.map((e) => <TimelineRow key={e.id} event={e} />)}
    </ol>
  );
}

function NowDivider() {
  return (
    <li className="relative -ml-[9px] flex items-center gap-2 py-1">
      <span className="w-[18px] h-[18px] rounded-full bg-gray-950 border-2 border-amber-400 flex items-center justify-center">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
      </span>
      <span className="font-mono text-[10px] uppercase tracking-widest text-amber-300">
        Now
      </span>
      <span className="flex-1 h-px bg-amber-400/20" />
    </li>
  );
}

function TimelineRow({ event }: { event: TimelineEvent }) {
  const [pending, setPending] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const color = colorFor(event);
  const timeColor =
    event.type === "state" ? "text-sky-300" :
    event.isFuture         ? "text-amber-300" :
                             "text-emerald-300";

  const runAction = async (action: "pause" | "skip" | "accelerate") => {
    if (!event.touchId) return;
    setPending(action);
    try {
      const res = await fetch("/api/v1/outreach/approval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          touch_id: event.touchId,
          action: action === "accelerate" ? "approve" :
                  action === "skip"       ? "reject"  :
                                            "defer",
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDone(action);
    } catch (e) {
      console.error("[OutreachTimeline] action failed", e);
    } finally {
      setPending(null);
    }
  };

  return (
    <li className="relative">
      {/* Dot on the rail */}
      <span
        className={`absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full border-2 bg-gray-950 ${color.dot}`}
        aria-hidden
      />
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className={`flex items-center gap-2 text-xs font-mono uppercase tracking-wider ${timeColor}`}>
            {event.type === "state" ? <Flag className="w-3 h-3" /> : channelIcon(event.channel)}
            <span>
              {event.type === "state"
                ? event.title
                : canonicalChannel(event.channel ?? "")}
            </span>
            {event.sequenceStep && event.type !== "state" && (
              <span className="text-gray-500"> · step {event.sequenceStep}</span>
            )}
          </div>
          <div className="text-[11px] text-gray-500 font-mono mt-0.5">
            {fmt(event.timestamp)}
            {event.status ? <span> · {providerLabel(event.status)}</span> : null}
          </div>
          {event.content && (
            <div className="text-xs text-gray-400 mt-1 line-clamp-2">
              &ldquo;{providerLabel(event.content)}&rdquo;
            </div>
          )}
        </div>
      </div>

      {/* Per-future-touch controls */}
      {event.type === "scheduled" && event.isFuture && event.touchId && (
        <div className="flex gap-1.5 mt-1.5">
          <CtlBtn
            icon={<PauseCircle className="w-3 h-3" />}
            label="Pause 24h"
            onClick={() => runAction("pause")}
            pending={pending === "pause"} done={done === "pause"}
          />
          <CtlBtn
            icon={<SkipForward className="w-3 h-3" />}
            label="Skip"
            onClick={() => runAction("skip")}
            pending={pending === "skip"} done={done === "skip"}
          />
          <CtlBtn
            icon={<FastForward className="w-3 h-3" />}
            label="Accelerate"
            onClick={() => runAction("accelerate")}
            pending={pending === "accelerate"} done={done === "accelerate"}
          />
        </div>
      )}
    </li>
  );
}

function CtlBtn({
  icon, label, onClick, pending, done,
}: { icon: React.ReactNode; label: string; onClick: () => void; pending: boolean; done: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={pending}
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-gray-800 bg-gray-900 text-[10px] text-gray-400 hover:border-amber-500/40 hover:text-amber-300 disabled:opacity-40"
    >
      {icon}
      <span>{pending ? "…" : done ? "✓" : label}</span>
    </button>
  );
}

function colorFor(e: TimelineEvent): { dot: string } {
  if (e.type === "state")       return { dot: "border-sky-400" };
  if (e.isFuture)               return { dot: "border-amber-400" };
  if (e.type === "reply")       return { dot: "border-emerald-400" };
  return { dot: "border-emerald-500" };
}
