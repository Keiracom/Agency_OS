/**
 * FILE: frontend/components/dashboard/ActivityFeedFull.tsx
 * PURPOSE: Full-page activity timeline. Click any row opens ProspectDrawer.
 * PHASE: PHASE-2.1-PROSPECT-DRAWER-FEED
 *
 * NOTE: dispatch called this component `ActivityFeed.tsx` (NEW), but that
 * name is already taken by a home widget re-exported from
 * components/dashboard/index.ts. Renamed to ActivityFeedFull to avoid a
 * breaking rename — the route wire-up imports this new file directly.
 *
 * Uses useLiveActivityFeed for realtime-ness but runs its own direct
 * Supabase query alongside to resolve lead_id per event so click → drawer
 * works. The realtime subscription invalidates queries that share a key
 * prefix, which triggers the raw query refetch too.
 */

"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Mail, Linkedin, Phone, MessageSquare,
  CheckCircle, XCircle, Circle, MessageCircle,
} from "lucide-react";
import { useClient } from "@/hooks/use-client";
import { useLiveActivityFeed } from "@/lib/useLiveActivityFeed";
import { createBrowserClient } from "@/lib/supabase";
import { canonicalChannel } from "@/lib/provider-labels";
import { ProspectDrawer } from "./ProspectDrawer";

interface RawEvent {
  id: string;
  lead_id: string;
  channel: string;
  action: string;
  sent_at: string;
  leadName: string;
  company: string;
  status: string | null;
}

function channelIcon(channel: string) {
  const label = canonicalChannel(channel ?? "");
  const Icon =
    label === "Email"    ? Mail :
    label === "LinkedIn" ? Linkedin :
    label === "SMS"      ? MessageSquare :
    label === "Voice AI" ? Phone :
    Mail;
  return <Icon className="w-4 h-4 text-gray-400" strokeWidth={1.75} />;
}

function statusIcon(action: string, status: string | null) {
  const a = action.toLowerCase();
  const s = (status ?? "").toLowerCase();
  if (a.includes("repl") || s.includes("repl")) return <MessageCircle className="w-3.5 h-3.5 text-emerald-400" />;
  if (s.includes("bounc") || s === "failed") return <XCircle className="w-3.5 h-3.5 text-red-400" />;
  if (s.includes("convert") || s === "sent") return <CheckCircle className="w-3.5 h-3.5 text-gray-400" />;
  return <Circle className="w-3.5 h-3.5 text-gray-600" />;
}

async function fetchRawEvents(clientId: string, limit: number): Promise<RawEvent[]> {
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
  const leadIds = Array.from(new Set(rows.map((r) => String(r.lead_id)).filter(Boolean)));

  const nameByLead = new Map<string, { name: string; company: string }>();
  if (leadIds.length) {
    const { data: bu } = await client
      .from("business_universe")
      .select("id, display_name, dm_name")
      .in("id", leadIds);
    for (const b of ((bu ?? []) as Array<Record<string, unknown>>)) {
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
    return {
      id,
      lead_id: leadId,
      channel: String(r.channel ?? ""),
      action: r.replied_at ? "replied" : "sent",
      sent_at: String(r.sent_at ?? ""),
      leadName: n.name,
      company: n.company,
      status: (r.final_outcome as string | null) ?? null,
    };
  });
}

export function ActivityFeedFull({ limit = 100 }: { limit?: number }) {
  const { clientId } = useClient();
  const live = useLiveActivityFeed({ limit });
  const [activeLead, setActiveLead] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["activity-raw", clientId, limit, live.status],
    queryFn: () => fetchRawEvents(clientId!, limit),
    enabled: !!clientId,
    staleTime: 15_000,
  });

  const events = useMemo(() => data ?? [], [data]);

  return (
    <>
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
          <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500">
            Activity
          </div>
          <div className="text-[10px] font-mono text-gray-500">
            {live.isLive ? (
              <span className="inline-flex items-center gap-1 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE
              </span>
            ) : live.status === "polling" ? (
              "POLLING"
            ) : (
              "CONNECTING"
            )}
          </div>
        </div>
        {events.length === 0 ? (
          <div className="px-4 py-10 text-center text-sm text-gray-500 italic">
            {isLoading ? "Loading activity…" : "No activity yet."}
          </div>
        ) : (
          <ul className="divide-y divide-gray-800">
            {events.map((e) => (
              <li
                key={e.id}
                onClick={() => setActiveLead(e.lead_id)}
                className="px-4 py-3 flex items-center gap-3 hover:bg-gray-800/60 cursor-pointer"
              >
                <span className="shrink-0 text-gray-500 font-mono text-[10px] w-16">
                  {new Date(e.sent_at).toLocaleTimeString([], {
                    hour: "numeric", minute: "2-digit",
                  })}
                </span>
                {channelIcon(e.channel)}
                <span className="flex-1 min-w-0 text-sm text-gray-200 truncate">
                  <span className="text-gray-100">{e.leadName}</span>
                  <span className="text-gray-500"> · {e.company}</span>
                </span>
                <span className="shrink-0 inline-flex items-center gap-1.5 text-[11px] font-mono text-gray-400 uppercase tracking-wider">
                  {statusIcon(e.action, e.status)}
                  {e.action}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ProspectDrawer leadId={activeLead} onClose={() => setActiveLead(null)} />
    </>
  );
}
