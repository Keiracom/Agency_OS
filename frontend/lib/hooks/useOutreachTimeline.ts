/**
 * FILE: frontend/lib/hooks/useOutreachTimeline.ts
 * PURPOSE: Merge touches + scheduled + replies + state events into one sorted timeline
 * PHASE: PHASE-2.1-TIMELINE-VR-POPOVERS
 *
 * Input: ProspectDetail from useProspectDetail (no extra network calls here —
 * this hook is a pure transform).
 *
 * Output: TimelineEvent[] sorted chronologically ascending.
 *
 * Type key:
 *   sent       — a completed outreach touch (past)
 *   reply      — inbound reply from prospect (past)
 *   scheduled  — pending/paused touch (future)
 *   state      — cadence lifecycle event (past or future, e.g. "Sequence started",
 *                "Paused due to OOO", "Suppressed")
 */

"use client";

import { useMemo } from "react";
import type { ProspectDetail } from "@/lib/hooks/useProspectDetail";

export type TimelineEventType = "sent" | "reply" | "scheduled" | "state";

export interface TimelineEvent {
  id: string;
  type: TimelineEventType;
  timestamp: string;
  channel: string | null;
  status: string | null;
  content: string | null;
  touchId: string | null;
  sequenceStep: number | null;
  isFuture: boolean;
  title: string;
}

export function useOutreachTimeline(detail: ProspectDetail | null): TimelineEvent[] {
  return useMemo(() => {
    if (!detail) return [];
    const now = Date.now();
    const events: TimelineEvent[] = [];

    // Past touches
    for (const t of detail.touches) {
      events.push({
        id: `touch-${t.id}`,
        type: "sent",
        timestamp: t.sentAt,
        channel: t.channel,
        status: t.replied ? "replied" : (t.status ?? "sent"),
        content: t.preview,
        touchId: t.id,
        sequenceStep: t.sequenceStep,
        isFuture: false,
        title: `Sent step ${t.sequenceStep ?? "?"}`,
      });
    }

    // Replies
    for (const r of detail.replies) {
      events.push({
        id: `reply-${r.id}`,
        type: "reply",
        timestamp: r.receivedAt,
        channel: r.channel,
        status: r.intent ?? "replied",
        content: r.preview,
        touchId: null,
        sequenceStep: null,
        isFuture: false,
        title: r.intent ? `Reply — ${r.intent}` : "Reply received",
      });
    }

    // Scheduled (future — unless scheduled_at is already past, in which case treat as due)
    for (const s of detail.scheduled) {
      const ts = s.scheduledAt ? new Date(s.scheduledAt).getTime() : NaN;
      const isFuture = Number.isFinite(ts) ? ts > now : true;
      events.push({
        id: `sched-${s.id}`,
        type: "scheduled",
        timestamp: s.scheduledAt,
        channel: s.channel,
        status: s.status,
        content: null,
        touchId: s.id,
        sequenceStep: s.sequenceStep,
        isFuture,
        title: `Scheduled step ${s.sequenceStep ?? "?"}`,
      });
    }

    // Derived state markers
    if (detail.touches.length > 0) {
      const first = detail.touches[0];
      events.push({
        id: "state-start",
        type: "state",
        timestamp: first.sentAt,
        channel: null,
        status: "started",
        content: null,
        touchId: null,
        sequenceStep: null,
        isFuture: false,
        title: "Sequence started",
      });
    }
    const pausedScheduled = detail.scheduled.find((s) => s.status === "paused");
    if (pausedScheduled) {
      events.push({
        id: "state-paused",
        type: "state",
        timestamp: pausedScheduled.scheduledAt,
        channel: null,
        status: "paused",
        content: null,
        touchId: null,
        sequenceStep: null,
        isFuture: true,
        title: "Cadence paused",
      });
    }

    events.sort((a, b) => {
      const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
      const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
      return ta - tb;
    });

    return events;
  }, [detail]);
}
