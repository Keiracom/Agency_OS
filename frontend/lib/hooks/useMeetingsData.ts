/**
 * FILE: frontend/lib/hooks/useMeetingsData.ts
 * PURPOSE: Booked-meetings list + per-meeting prospect details for Meetings v10 route
 * PHASE: PHASE-2.1-PIPELINE-MEETINGS
 *
 * Queries real Supabase tables. No mock data — returns empty array on any error.
 *
 * Sources:
 *   activities               — rows where action='meeting_booked'
 *   business_universe        — joined for company + DM name/title + VR score
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useClient } from "@/hooks/use-client";
import { createBrowserClient } from "@/lib/supabase";

export interface MeetingRow {
  id: string;
  leadId: string;
  company: string;
  dmName: string;
  dmTitle: string | null;
  channel: string | null;
  scheduledAt: string;
  meetingLink: string | null;
  meetingType: string | null;
  vrGrade: string | null;
  score: number | null;
  notes: string | null;
}

function gradeFromScore(score: number | null): string | null {
  if (score === null || score === undefined) return null;
  if (score >= 85) return "A";
  if (score >= 70) return "B";
  if (score >= 50) return "C";
  if (score >= 30) return "D";
  return "F";
}

async function fetchMeetings(clientId: string): Promise<MeetingRow[]> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;

  let activities: Array<Record<string, unknown>> = [];
  try {
    const { data, error } = await client
      .from("activities")
      .select("id, lead_id, channel, scheduled_at, meeting_link, meeting_type, notes")
      .eq("client_id", clientId)
      .eq("action", "meeting_booked")
      .order("scheduled_at", { ascending: true })
      .limit(200);
    if (error) throw error;
    activities = data ?? [];
  } catch (e) {
    console.error("[useMeetingsData] activities failed", e);
    return [];
  }

  const leadIds = activities.map((a) => String(a.lead_id)).filter(Boolean);
  const buById = new Map<string, Record<string, unknown>>();
  if (leadIds.length > 0) {
    try {
      const { data } = await client
        .from("business_universe")
        .select("id, display_name, dm_name, dm_title, propensity_score")
        .in("id", leadIds);
      for (const row of (data ?? []) as Array<Record<string, unknown>>) {
        buById.set(String(row.id), row);
      }
    } catch (e) {
      console.warn("[useMeetingsData] business_universe join skipped", e);
    }
  }

  return activities.map((a) => {
    const bu = buById.get(String(a.lead_id)) ?? {};
    const score = typeof bu.propensity_score === "number" ? (bu.propensity_score as number) : null;
    return {
      id: String(a.id),
      leadId: String(a.lead_id),
      company: (bu.display_name as string | null) ?? "—",
      dmName: (bu.dm_name as string | null) ?? "Unknown",
      dmTitle: (bu.dm_title as string | null) ?? null,
      channel: (a.channel as string | null) ?? null,
      scheduledAt: String(a.scheduled_at ?? ""),
      meetingLink: (a.meeting_link as string | null) ?? null,
      meetingType: (a.meeting_type as string | null) ?? null,
      vrGrade: gradeFromScore(score),
      score,
      notes: (a.notes as string | null) ?? null,
    } satisfies MeetingRow;
  });
}

export function useMeetingsData() {
  const { clientId } = useClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["meetings-v10", clientId],
    queryFn: () => fetchMeetings(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
    refetchInterval: 300_000,
  });
  return { meetings: data ?? [], isLoading, error };
}
