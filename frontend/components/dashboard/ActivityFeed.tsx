/**
 * FILE: frontend/components/dashboard/ActivityFeed.tsx
 * PURPOSE: Day-grouped activity feed with channel filter chips and
 *          expandable event cards. Matches /demo renderFeed (lines
 *          1973-2017).
 * PHASE: B2.4 — single canonical activity surface.
 *
 * Data source: cis_outreach_outcomes joined with business_universe (same
 * shape as the prior ActivityFeedFull component, kept for parity). Click
 * any event row to expand; click the prospect name (or expanded "Open
 * briefing" CTA) to open the ProspectDrawer.
 */

"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Mail,
  Linkedin,
  Phone,
  MessageSquare,
  ChevronRight,
} from "lucide-react";
import { useClient } from "@/hooks/use-client";
import { useLiveActivityFeed } from "@/lib/useLiveActivityFeed";
import { createBrowserClient } from "@/lib/supabase";
import { canonicalChannel } from "@/lib/provider-labels";
import { ProspectDrawer } from "./ProspectDrawer";

type ChannelKey = "all" | "email" | "linkedin" | "voice" | "sms";

interface FeedEvent {
  id: string;
  leadId: string;
  channel: string;        // raw provider channel
  canonicalChannel: ChannelKey;
  action: string;         // sent / replied
  sentAt: string;
  leadName: string;
  company: string;
  status: string | null;
}

const FILTERS: { k: ChannelKey; l: string }[] = [
  { k: "all",      l: "All"      },
  { k: "email",    l: "Email"    },
  { k: "linkedin", l: "LinkedIn" },
  { k: "voice",    l: "Voice"    },
  { k: "sms",      l: "SMS"      },
];

function toChannelKey(channel: string): ChannelKey {
  const label = canonicalChannel(channel ?? "");
  if (label === "Email")    return "email";
  if (label === "LinkedIn") return "linkedin";
  if (label === "Voice AI") return "voice";
  if (label === "SMS")      return "sms";
  return "email";
}

function channelIcon(key: ChannelKey) {
  const Icon =
    key === "email"    ? Mail :
    key === "linkedin" ? Linkedin :
    key === "voice"    ? Phone :
    key === "sms"      ? MessageSquare :
    Mail;
  return <Icon className="w-4 h-4" strokeWidth={1.75} />;
}

function dayHeader(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d
    .toLocaleDateString("en-AU", {
      weekday: "long",
      day: "numeric",
      month: "long",
    })
    .toUpperCase();
}

function hourMinute(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

async function fetchEvents(
  clientId: string, limit: number,
): Promise<FeedEvent[]> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;

  const { data: outcomes } = await client
    .from("cis_outreach_outcomes")
    .select("id, lead_id, channel, sent_at, final_outcome, replied_at")
    .eq("client_id", clientId)
    .order("sent_at", { ascending: false })
    .limit(limit);

  const rows = (outcomes ?? []) as Array<Record<string, unknown>>;
  const leadIds = Array.from(
    new Set(rows.map((r) => String(r.lead_id)).filter(Boolean)),
  );

  const nameByLead = new Map<string, { name: string; company: string }>();
  if (leadIds.length) {
    const { data: bu } = await client
      .from("business_universe")
      .select("id, display_name, dm_name")
      .in("id", leadIds);
    for (const b of (bu ?? []) as Array<Record<string, unknown>>) {
      nameByLead.set(String(b.id), {
        name: (b.dm_name as string | null) ?? "Unknown",
        company: (b.display_name as string | null) ?? "—",
      });
    }
  }

  return rows.map((r) => {
    const id = String(r.id);
    const leadId = String(r.lead_id);
    const n = nameByLead.get(leadId) ?? { name: "Unknown", company: "—" };
    const ch = String(r.channel ?? "");
    return {
      id,
      leadId,
      channel: ch,
      canonicalChannel: toChannelKey(ch),
      action: r.replied_at ? "replied" : "sent",
      sentAt: String(r.sent_at ?? ""),
      leadName: n.name,
      company: n.company,
      status: (r.final_outcome as string | null) ?? null,
    };
  });
}

interface Props {
  limit?: number;
}

export function ActivityFeed({ limit = 150 }: Props) {
  const { clientId } = useClient();
  const live = useLiveActivityFeed({ limit });
  const [filter, setFilter] = useState<ChannelKey>("all");
  const [activeLead, setActiveLead] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data, isLoading } = useQuery({
    queryKey: ["activity-feed", clientId, limit, live.status],
    queryFn: () => fetchEvents(clientId!, limit),
    enabled: !!clientId,
    staleTime: 15_000,
  });

  const events = useMemo(() => data ?? [], [data]);

  const counts = useMemo(() => {
    const c: Record<ChannelKey, number> = {
      all: events.length,
      email: 0, linkedin: 0, voice: 0, sms: 0,
    };
    for (const e of events) c[e.canonicalChannel]++;
    return c;
  }, [events]);

  const filtered = useMemo(
    () => (filter === "all" ? events : events.filter((e) => e.canonicalChannel === filter)),
    [events, filter],
  );

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <>
      {/* Filter chips */}
      <div className="flex flex-wrap gap-2 mb-5">
        {FILTERS.map((f) => {
          const active = filter === f.k;
          return (
            <button
              key={f.k}
              type="button"
              onClick={() => setFilter(f.k)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] border text-[12px] font-mono uppercase tracking-wider transition-colors ${
                active
                  ? "bg-amber-soft border-amber text-copper"
                  : "bg-panel border-rule text-ink-2 hover:border-amber/40"
              }`}
            >
              {f.l}
              <span
                className={`text-[11px] tabular-nums ${
                  active ? "text-copper" : "text-ink-3"
                }`}
              >
                {counts[f.k]}
              </span>
            </button>
          );
        })}
        <span className="ml-auto inline-flex items-center gap-1.5 self-center text-[10px] font-mono uppercase tracking-widest text-ink-3">
          {live.isLive ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-amber animate-pulse" />
              Live
            </>
          ) : live.status === "polling" ? (
            "Polling"
          ) : (
            "Connecting"
          )}
        </span>
      </div>

      {/* Event list */}
      {isLoading ? (
        <div className="rounded-[10px] border border-rule bg-panel px-5 py-10 text-center text-sm text-ink-2 italic">
          Loading activity…
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-[10px] border border-rule bg-panel px-5 py-10 text-center text-sm text-ink-2 italic">
          {filter === "all"
            ? "No activity yet."
            : `No ${filter} activity in this window.`}
        </div>
      ) : (
        <DayGroupedList
          events={filtered}
          expanded={expanded}
          onToggle={toggle}
          onOpenLead={setActiveLead}
        />
      )}

      <ProspectDrawer leadId={activeLead} onClose={() => setActiveLead(null)} />
    </>
  );
}

function DayGroupedList({
  events,
  expanded,
  onToggle,
  onOpenLead,
}: {
  events: FeedEvent[];
  expanded: Set<string>;
  onToggle: (id: string) => void;
  onOpenLead: (leadId: string) => void;
}) {
  const out: React.ReactNode[] = [];
  let lastDay: string | null = null;
  events.forEach((e) => {
    const day = dayHeader(e.sentAt);
    if (day !== lastDay) {
      out.push(
        <div
          key={`day-${day}-${e.id}`}
          className="font-mono text-[10px] tracking-[0.16em] uppercase text-ink-3 mt-6 mb-2"
        >
          {day}
        </div>,
      );
      lastDay = day;
    }
    const isOpen = expanded.has(e.id);
    out.push(
      <EventCard
        key={e.id}
        event={e}
        isOpen={isOpen}
        onToggle={() => onToggle(e.id)}
        onOpenLead={() => onOpenLead(e.leadId)}
      />,
    );
  });
  return <div className="space-y-2">{out}</div>;
}

function EventCard({
  event,
  isOpen,
  onToggle,
  onOpenLead,
}: {
  event: FeedEvent;
  isOpen: boolean;
  onToggle: () => void;
  onOpenLead: () => void;
}) {
  const isReply = event.action === "replied";
  return (
    <div
      onClick={onToggle}
      className={`rounded-[10px] border bg-panel transition-colors cursor-pointer ${
        isOpen ? "border-amber" : "border-rule hover:border-amber/40"
      }`}
    >
      <div className="grid grid-cols-[60px_36px_1fr_auto] gap-3 items-center px-4 py-3">
        <div className="font-mono text-[11px] text-ink-3 tabular-nums">
          {hourMinute(event.sentAt)}
        </div>
        <div
          className={`w-9 h-9 rounded-md flex items-center justify-center ${
            isReply ? "bg-amber-soft text-copper" : "bg-surface text-ink-3"
          }`}
        >
          {channelIcon(event.canonicalChannel)}
        </div>
        <div className="min-w-0">
          <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">
            {isReply ? "Reply received" : "Outreach sent"} · {event.canonicalChannel}
          </div>
          <div className="text-[14px] text-ink truncate">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenLead();
              }}
              className="font-medium hover:text-copper underline-offset-2 hover:underline"
            >
              {event.leadName}
            </button>
            <span className="text-ink-2"> · {event.company}</span>
          </div>
          {event.status && (
            <div className="font-mono text-[11px] text-ink-3 mt-0.5">
              {event.status}
            </div>
          )}
        </div>
        <ChevronRight
          className={`w-4 h-4 text-ink-3 transition-transform ${
            isOpen ? "rotate-90" : ""
          }`}
          strokeWidth={2}
        />
      </div>

      {isOpen && (
        <div className="border-t border-rule px-4 py-4 space-y-3">
          <div>
            <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-ink-3 mb-1">
              {isReply ? "What Maya is doing next" : "Touch detail"}
            </div>
            <p className="text-[13px] text-ink-2">
              {isReply
                ? "Drafting follow-up reply for critic loop. Open the briefing for full thread context."
                : `Sent via ${event.channel || event.canonicalChannel}. Awaiting recipient response.`}
            </p>
          </div>
          <div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenLead();
              }}
              className="px-3 py-1.5 rounded-[6px] bg-ink text-white font-mono text-[11px] tracking-[0.08em] uppercase hover:opacity-90 transition-opacity"
            >
              Open briefing
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ActivityFeed;
