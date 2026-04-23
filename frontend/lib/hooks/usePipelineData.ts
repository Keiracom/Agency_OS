/**
 * FILE: frontend/lib/hooks/usePipelineData.ts
 * PURPOSE: Pipeline stage columns + prospect list for Pipeline v10 route
 * PHASE: PHASE-2.1-PIPELINE-MEETINGS
 *
 * Queries real Supabase tables. No mock data — returns empty arrays on any error.
 *
 * Sources:
 *   business_universe       — canonical prospect rows + stage (outreach_status)
 *   cis_outreach_outcomes   — last-touch channel + timestamp per lead
 *   scheduled_touches       — next pending touch per lead
 */

"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useClient } from "@/hooks/use-client";
import { createBrowserClient } from "@/lib/supabase";
import { useRealtimeSubscription } from "@/lib/hooks/useRealtimeSubscription";

export type PipelineStage =
  | "discovered"
  | "enriched"
  | "contacted"
  | "replied"
  | "meeting"
  | "converted";

export interface PipelineProspect {
  id: string;
  name: string;
  company: string;
  stage: PipelineStage;
  lastChannel: string | null;
  lastTouchAt: string | null;
  nextChannel: string | null;
  nextTouchAt: string | null;
  vrGrade: string | null;
  score: number | null;
}

export interface PipelineData {
  prospects: PipelineProspect[];
  counts: Record<PipelineStage, number>;
  isLoading: boolean;
  error: unknown;
}

const STAGE_ORDER: PipelineStage[] = [
  "discovered", "enriched", "contacted", "replied", "meeting", "converted",
];

function emptyCounts(): Record<PipelineStage, number> {
  return STAGE_ORDER.reduce((acc, s) => ({ ...acc, [s]: 0 }), {} as Record<PipelineStage, number>);
}

function normaliseStage(raw: string | null | undefined, hasMeeting: boolean): PipelineStage {
  if (hasMeeting) return "meeting";
  const v = (raw ?? "").toLowerCase();
  if (v === "converted" || v === "won") return "converted";
  if (v === "meeting_booked" || v === "meeting") return "meeting";
  if (v === "replied" || v === "positive" || v === "engaged") return "replied";
  if (v === "active" || v === "contacted" || v === "sequencing") return "contacted";
  if (v === "enriched" || v === "qualified") return "enriched";
  return "discovered";
}

function gradeFromScore(score: number | null): string | null {
  if (score === null || score === undefined) return null;
  if (score >= 85) return "A";
  if (score >= 70) return "B";
  if (score >= 50) return "C";
  if (score >= 30) return "D";
  return "F";
}

async function fetchPipeline(clientId: string): Promise<Omit<PipelineData, "isLoading" | "error">> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;

  let bu: Array<Record<string, unknown>> = [];
  try {
    const { data, error } = await client
      .from("business_universe")
      .select("id, display_name, dm_name, dm_title, outreach_status, propensity_score, meeting_booked_at")
      .eq("client_id", clientId)
      .limit(500);
    if (error) throw error;
    bu = data ?? [];
  } catch (e) {
    console.error("[usePipelineData] business_universe failed", e);
    return { prospects: [], counts: emptyCounts() };
  }

  const ids = bu.map((r) => String(r.id));

  // Last touch per lead
  const lastTouchByLead = new Map<string, { channel: string; sent_at: string }>();
  if (ids.length > 0) {
    try {
      const { data } = await client
        .from("cis_outreach_outcomes")
        .select("lead_id, channel, sent_at")
        .in("lead_id", ids)
        .order("sent_at", { ascending: false });
      for (const row of (data ?? []) as Array<{ lead_id: string; channel: string; sent_at: string }>) {
        if (!lastTouchByLead.has(row.lead_id)) {
          lastTouchByLead.set(row.lead_id, { channel: row.channel, sent_at: row.sent_at });
        }
      }
    } catch (e) {
      console.warn("[usePipelineData] cis_outreach_outcomes skipped", e);
    }
  }

  // Next pending touch per lead
  const nextTouchByLead = new Map<string, { channel: string; scheduled_at: string }>();
  if (ids.length > 0) {
    try {
      const { data } = await client
        .from("scheduled_touches")
        .select("lead_id, channel, scheduled_at")
        .in("lead_id", ids)
        .eq("status", "pending")
        .order("scheduled_at", { ascending: true });
      for (const row of (data ?? []) as Array<{ lead_id: string; channel: string; scheduled_at: string }>) {
        if (!nextTouchByLead.has(row.lead_id)) {
          nextTouchByLead.set(row.lead_id, { channel: row.channel, scheduled_at: row.scheduled_at });
        }
      }
    } catch (e) {
      console.warn("[usePipelineData] scheduled_touches skipped", e);
    }
  }

  const prospects: PipelineProspect[] = bu.map((r) => {
    const id = String(r.id);
    const last = lastTouchByLead.get(id) ?? null;
    const next = nextTouchByLead.get(id) ?? null;
    const score = typeof r.propensity_score === "number" ? r.propensity_score : null;
    return {
      id,
      name: (r.dm_name as string | null) ?? "Unknown",
      company: (r.display_name as string | null) ?? "—",
      stage: normaliseStage(r.outreach_status as string | null, !!r.meeting_booked_at),
      lastChannel: last?.channel ?? null,
      lastTouchAt: last?.sent_at ?? null,
      nextChannel: next?.channel ?? null,
      nextTouchAt: next?.scheduled_at ?? null,
      vrGrade: gradeFromScore(score),
      score,
    };
  });

  const counts = emptyCounts();
  for (const p of prospects) counts[p.stage] += 1;

  return { prospects, counts };
}

export function usePipelineData(): PipelineData {
  const { clientId } = useClient();
  const qc = useQueryClient();
  const queryKey = ["pipeline-v10", clientId];

  const { data, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => fetchPipeline(clientId!),
    enabled: !!clientId,
    staleTime: 30_000,
    // Long backstop — realtime drives refresh.
    refetchInterval: 300_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey });

  useRealtimeSubscription({
    table: "business_universe",
    filter: clientId ? `client_id=eq.${clientId}` : undefined,
    enabled: !!clientId,
    onInsert: invalidate,
    onUpdate: invalidate,
    onPoll:   invalidate,
  });
  useRealtimeSubscription({
    table: "cis_outreach_outcomes",
    filter: clientId ? `client_id=eq.${clientId}` : undefined,
    enabled: !!clientId,
    onInsert: invalidate,
    onPoll:   invalidate,
  });
  return {
    prospects: data?.prospects ?? [],
    counts: data?.counts ?? emptyCounts(),
    isLoading,
    error,
  };
}
