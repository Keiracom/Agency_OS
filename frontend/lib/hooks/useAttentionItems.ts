/**
 * FILE: frontend/lib/hooks/useAttentionItems.ts
 * PURPOSE: "Needs your attention" card data for Home v10
 * PHASE: PHASE-2.1-HOME-V10-PORT
 *
 * Four ordered buckets: meeting-today, positive-reply, overdue-followup, hot-prospect.
 * Each bucket catches its own errors and returns [] on failure. Total capped at 8.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useClient } from "@/hooks/use-client";
import { createBrowserClient } from "@/lib/supabase";
import { providerLabel } from "@/lib/provider-labels";

export type AttentionType =
  | "hot-prospect"
  | "overdue-followup"
  | "positive-reply"
  | "meeting-today";

export interface AttentionItem {
  id: string;
  type: AttentionType;
  icon: string;
  text: string;
  cta: string;
  href: string;
}

export interface UseAttentionItemsResult {
  items: AttentionItem[];
  isLoading: boolean;
  error: unknown;
}

/** AEST today string: YYYY-MM-DD */
function aestToday(): string {
  return new Date(
    new Date().toLocaleString("en-AU", { timeZone: "Australia/Sydney" })
  )
    .toISOString()
    .slice(0, 10);
}

/** Format an ISO time string to "10:00am" in AEST */
function formatAEST(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-AU", {
    timeZone: "Australia/Sydney",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

type Row = Record<string, unknown>;

async function fetchAttention(clientId: string): Promise<AttentionItem[]> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sb = createBrowserClient() as any;
  const today = aestToday();
  const buckets: AttentionItem[][] = [];

  // ── meeting-today ───────────────────────────────────────────────────────
  try {
    const { data } = await sb
      .from("dm_meetings")
      .select("id, prospect_name, scheduled_at")
      .eq("client_id", clientId)
      .gte("scheduled_at", `${today}T00:00:00`)
      .lt("scheduled_at", `${today}T23:59:59`)
      .order("scheduled_at", { ascending: true });

    buckets.push(
      ((data as Row[]) ?? []).map((r) => ({
        id: String(r.id),
        type: "meeting-today" as AttentionType,
        icon: "\u{1F4C5}",
        text: providerLabel(
          `${r.prospect_name ?? "Unknown"} · ${formatAEST(String(r.scheduled_at))} AEST`
        ),
        cta: "Prep briefing →",
        href: `/dashboard/meetings/${r.id}`,
      }))
    );
  } catch (e) {
    console.error("[useAttentionItems] meeting-today failed", e);
    buckets.push([]);
  }

  // ── positive-reply ──────────────────────────────────────────────────────
  try {
    const { data } = await sb
      .from("replies")
      .select("id, prospect_name, intent, actioned_at")
      .eq("client_id", clientId)
      .eq("intent", "positive")
      .is("actioned_at", null)
      .order("created_at", { ascending: false });

    buckets.push(
      ((data as Row[]) ?? []).map((r) => ({
        id: String(r.id),
        type: "positive-reply" as AttentionType,
        icon: "\u{1F4AC}",
        text: providerLabel(
          `${r.prospect_name ?? "Unknown"} replied positively — awaiting action`
        ),
        cta: "Review →",
        href: `/dashboard/replies/${r.id}`,
      }))
    );
  } catch (e) {
    console.error("[useAttentionItems] positive-reply failed", e);
    buckets.push([]);
  }

  // ── overdue-followup ────────────────────────────────────────────────────
  try {
    const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const { data } = await sb
      .from("scheduled_touches")
      .select("id, prospect_id, prospect_name, channel, scheduled_at")
      .eq("client_id", clientId)
      .eq("status", "pending")
      .lt("scheduled_at", cutoff)
      .order("scheduled_at", { ascending: true });

    buckets.push(
      ((data as Row[]) ?? []).map((r) => {
        const daysOverdue = Math.floor(
          (Date.now() - new Date(String(r.scheduled_at)).getTime()) /
            (1000 * 60 * 60 * 24)
        );
        return {
          id: String(r.id),
          type: "overdue-followup" as AttentionType,
          icon: "⏰",
          text: providerLabel(
            `${r.prospect_name ?? "Unknown"} — ${canonicalChannelLabel(String(r.channel ?? ""))} follow-up ${daysOverdue}d overdue`
          ),
          cta: "Resume →",
          href: `/dashboard/leads/${r.prospect_id}`,
        };
      })
    );
  } catch (e) {
    console.error("[useAttentionItems] overdue-followup failed", e);
    buckets.push([]);
  }

  // ── hot-prospect ────────────────────────────────────────────────────────
  try {
    const { data } = await sb
      .from("business_universe")
      .select("id, name, als_tier, hot_score, outreach_status")
      .eq("client_id", clientId)
      .eq("outreach_status", "pending")
      .or("als_tier.eq.hot,hot_score.gt.85")
      .order("hot_score", { ascending: false });

    buckets.push(
      ((data as Row[]) ?? []).map((r) => ({
        id: String(r.id),
        type: "hot-prospect" as AttentionType,
        icon: "\u{1F525}",
        text: providerLabel(
          `${r.name ?? "Unknown"} scored ${r.hot_score ?? "hot"} — ready for outreach`
        ),
        cta: "Release →",
        href: `/dashboard/leads/${r.id}`,
      }))
    );
  } catch (e) {
    console.error("[useAttentionItems] hot-prospect failed", e);
    buckets.push([]);
  }

  // Concat in order, cap at 8
  return buckets.flat().slice(0, 8);
}

/** Channel display label without exposing providers */
function canonicalChannelLabel(channel: string): string {
  const key = channel.toLowerCase();
  if (key === "email" || key === "salesforge" || key === "resend") return "Email";
  if (key === "linkedin" || key === "unipile") return "LinkedIn";
  if (key === "phone" || key === "voice" || key === "vapi") return "Call";
  if (key === "sms" || key === "telnyx") return "SMS";
  return channel || "Touch";
}

export function useAttentionItems(): UseAttentionItemsResult {
  const { clientId } = useClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["attention-items-v10", clientId],
    queryFn: () => fetchAttention(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
    refetchInterval: 300_000,
  });

  return {
    items: data ?? [],
    isLoading,
    error,
  };
}
