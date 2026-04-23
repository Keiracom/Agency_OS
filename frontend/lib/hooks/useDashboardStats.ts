/**
 * FILE: frontend/lib/hooks/useDashboardStats.ts
 * PURPOSE: BDR hero + sum-row stats for Home v10
 * PHASE: PHASE-2.1-HOME-V10-PORT
 *
 * Queries real Supabase tables. No mock data — returns 0 on any error.
 */

"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useClient } from "@/hooks/use-client";
import { createBrowserClient } from "@/lib/supabase";
import { useRealtimeSubscription } from "@/lib/hooks/useRealtimeSubscription";

export interface DashboardStats {
  prospectsContacted: number;
  repliesReceived: number;
  meetingsBooked: number;
  meetingsTarget: number;
  winRatePercent: number;
  deltas: {
    contactedThisWeek: number;
    repliesThisWeek: number;
    meetingsThisWeek: number;
  };
  cycleDay: number;
  cycleLength: number;
  isLoading: boolean;
  error: unknown;
}

const WEEK_AGO = () => new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

async function fetchStats(clientId: string): Promise<Omit<DashboardStats, "isLoading" | "error">> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;

  // ── prospectsContacted (with fallback) ─────────────────────────────────
  let prospectsContacted = 0;
  let contactedThisWeek = 0;
  try {
    const { count, error } = await client
      .from("business_universe")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .in("outreach_status", ["active", "replied", "converted"]);
    if (error) throw error;
    prospectsContacted = count ?? 0;

    const { count: wc } = await client
      .from("business_universe")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .in("outreach_status", ["active", "replied", "converted"])
      .gte("created_at", WEEK_AGO());
    contactedThisWeek = wc ?? 0;
  } catch {
    // Primary failed — try fallback via cis_outreach_outcomes
    try {
      const { data } = await client
        .from("cis_outreach_outcomes")
        .select("prospect_id")
        .eq("client_id", clientId);
      const unique = new Set((data ?? []).map((r: { prospect_id: string }) => r.prospect_id));
      prospectsContacted = unique.size;

      const { data: wd } = await client
        .from("cis_outreach_outcomes")
        .select("prospect_id")
        .eq("client_id", clientId)
        .gte("created_at", WEEK_AGO());
      const uniqueW = new Set((wd ?? []).map((r: { prospect_id: string }) => r.prospect_id));
      contactedThisWeek = uniqueW.size;
    } catch (fb) {
      console.error("[useDashboardStats] prospectsContacted fallback failed", fb);
    }
  }

  // ── repliesReceived ────────────────────────────────────────────────────
  let repliesReceived = 0;
  let repliesThisWeek = 0;
  try {
    const { count } = await client
      .from("replies")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId);
    repliesReceived = count ?? 0;

    const { count: wc } = await client
      .from("replies")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .gte("created_at", WEEK_AGO());
    repliesThisWeek = wc ?? 0;
  } catch (e) {
    console.error("[useDashboardStats] repliesReceived failed", e);
  }

  // ── meetingsBooked ─────────────────────────────────────────────────────
  let meetingsBooked = 0;
  let meetingsThisWeek = 0;
  try {
    const { count } = await client
      .from("dm_meetings")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .in("status", ["scheduled", "completed"]);
    meetingsBooked = count ?? 0;

    const { count: wc } = await client
      .from("dm_meetings")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .in("status", ["scheduled", "completed"])
      .gte("created_at", WEEK_AGO());
    meetingsThisWeek = wc ?? 0;
  } catch (e) {
    console.error("[useDashboardStats] meetingsBooked failed", e);
  }

  // ── cycle ──────────────────────────────────────────────────────────────
  let cycleDay = 0;
  let cycleLength = 30;
  try {
    const { data: cycleRow } = await client
      .from("cycles")
      .select("cycle_day_1_date, cycle_length_days")
      .eq("client_id", clientId)
      .eq("status", "active")
      .order("created_at", { ascending: false })
      .limit(1)
      .single();
    if (cycleRow) {
      const start = new Date(cycleRow.cycle_day_1_date).getTime();
      cycleDay = Math.floor((Date.now() - start) / (1000 * 60 * 60 * 24)) + 1;
      cycleLength = cycleRow.cycle_length_days ?? 30;
    }
  } catch {
    // No active cycle — leave defaults
  }

  const winRatePercent =
    prospectsContacted > 0
      ? Math.round((meetingsBooked / prospectsContacted) * 1000) / 10
      : 0;

  return {
    prospectsContacted,
    repliesReceived,
    meetingsBooked,
    meetingsTarget: 10,
    winRatePercent,
    deltas: { contactedThisWeek, repliesThisWeek, meetingsThisWeek },
    cycleDay,
    cycleLength,
  };
}

export function useDashboardStats(): DashboardStats {
  const { clientId } = useClient();
  const qc = useQueryClient();
  const queryKey = ["dashboard-stats-v10", clientId];

  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => fetchStats(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
    // Longer backstop — realtime is primary refresh mechanism.
    refetchInterval: 300_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey });

  // Realtime: any new outcome or scheduled-touch state change refreshes stats.
  useRealtimeSubscription({
    table: "cis_outreach_outcomes",
    filter: clientId ? `client_id=eq.${clientId}` : undefined,
    enabled: !!clientId,
    onInsert: invalidate,
    onUpdate: invalidate,
    onPoll:   invalidate,
  });
  useRealtimeSubscription({
    table: "scheduled_touches",
    filter: clientId ? `client_id=eq.${clientId}` : undefined,
    enabled: !!clientId,
    onInsert: invalidate,
    onUpdate: invalidate,
    onPoll:   invalidate,
  });

  return {
    prospectsContacted: data?.prospectsContacted ?? 0,
    repliesReceived: data?.repliesReceived ?? 0,
    meetingsBooked: data?.meetingsBooked ?? 0,
    meetingsTarget: data?.meetingsTarget ?? 10,
    winRatePercent: data?.winRatePercent ?? 0,
    deltas: data?.deltas ?? { contactedThisWeek: 0, repliesThisWeek: 0, meetingsThisWeek: 0 },
    cycleDay: data?.cycleDay ?? 0,
    cycleLength: data?.cycleLength ?? 30,
    isLoading,
    error,
  };
}
