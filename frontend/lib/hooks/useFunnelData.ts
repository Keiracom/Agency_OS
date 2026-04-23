/**
 * FILE: frontend/lib/hooks/useFunnelData.ts
 * PURPOSE: Funnel stage counts for the cycle funnel bar — Home v10
 * PHASE: PHASE-2.1-HOME-V10-PORT
 *
 * All counts from real Supabase queries. Returns 0 on error per stage.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useClient } from "@/hooks/use-client";
import { createBrowserClient } from "@/lib/supabase";

export interface FunnelStage {
  key: "discovered" | "contacted" | "replied" | "meeting" | "won";
  label: string;
  count: number;
}

export interface FunnelData {
  stages: FunnelStage[];
  total: number;
  contactedPercent: number;
  isLoading: boolean;
  error: unknown;
}

async function fetchFunnel(clientId: string): Promise<Omit<FunnelData, "isLoading" | "error">> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = createBrowserClient() as any;

  // ── discovered ─────────────────────────────────────────────────────────
  let discovered = 0;
  try {
    const { count } = await client
      .from("business_universe")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId);
    discovered = count ?? 0;
  } catch (e) {
    console.error("[useFunnelData] discovered failed", e);
  }

  // ── contacted ──────────────────────────────────────────────────────────
  let contacted = 0;
  try {
    const { count, error } = await client
      .from("business_universe")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .neq("outreach_status", "pending");
    if (error) throw error;
    contacted = count ?? 0;
  } catch {
    try {
      const { data } = await client
        .from("cis_outreach_outcomes")
        .select("prospect_id")
        .eq("client_id", clientId);
      contacted = new Set((data ?? []).map((r: { prospect_id: string }) => r.prospect_id)).size;
    } catch (fb) {
      console.error("[useFunnelData] contacted fallback failed", fb);
    }
  }

  // ── replied ────────────────────────────────────────────────────────────
  let replied = 0;
  try {
    const { count, error } = await client
      .from("business_universe")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .eq("outreach_status", "replied");
    if (error) throw error;
    replied = count ?? 0;
  } catch {
    try {
      const { data } = await client
        .from("replies")
        .select("prospect_id")
        .eq("client_id", clientId);
      replied = new Set((data ?? []).map((r: { prospect_id: string }) => r.prospect_id)).size;
    } catch (fb) {
      console.error("[useFunnelData] replied fallback failed", fb);
    }
  }

  // ── meeting ────────────────────────────────────────────────────────────
  let meeting = 0;
  try {
    const { count } = await client
      .from("dm_meetings")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .in("status", ["scheduled", "completed"]);
    meeting = count ?? 0;
  } catch (e) {
    console.error("[useFunnelData] meeting failed", e);
  }

  // ── won ────────────────────────────────────────────────────────────────
  let won = 0;
  try {
    const { count, error } = await client
      .from("dm_meetings")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .eq("outcome", "won");
    if (!error) won = count ?? 0;
  } catch (e) {
    console.error("[useFunnelData] won failed", e);
  }

  const stages: FunnelStage[] = [
    { key: "discovered", label: "Discovered", count: discovered },
    { key: "contacted",  label: "Contacted",  count: contacted  },
    { key: "replied",    label: "Replied",     count: replied    },
    { key: "meeting",    label: "Meeting",     count: meeting    },
    { key: "won",        label: "Won",         count: won        },
  ];

  const contactedPercent =
    discovered > 0 ? Math.round((contacted / discovered) * 100) : 0;

  return { stages, total: discovered, contactedPercent };
}

export function useFunnelData(): FunnelData {
  const { clientId } = useClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["funnel-data-v10", clientId],
    queryFn: () => fetchFunnel(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
    refetchInterval: 300_000,
  });

  const empty: FunnelStage[] = [
    { key: "discovered", label: "Discovered", count: 0 },
    { key: "contacted",  label: "Contacted",  count: 0 },
    { key: "replied",    label: "Replied",     count: 0 },
    { key: "meeting",    label: "Meeting",     count: 0 },
    { key: "won",        label: "Won",         count: 0 },
  ];

  return {
    stages: data?.stages ?? empty,
    total: data?.total ?? 0,
    contactedPercent: data?.contactedPercent ?? 0,
    isLoading,
    error,
  };
}
