/**
 * FILE: frontend/lib/hooks/useProspectDetail.ts
 * PURPOSE: Full prospect state for the right-drawer — contact, enrichment, touches, replies
 * PHASE: PHASE-2.1-PROSPECT-DRAWER-FEED
 *
 * Queries real Supabase tables. No mock data — returns nulls/empty arrays on any error.
 *
 * Sources:
 *   business_universe       — identity + contact + enrichment snapshot
 *   cis_outreach_outcomes   — touches sent with channel/sent_at/status
 *   scheduled_touches       — pending upcoming touches
 *   activities              — reply history (action='replied')
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { createBrowserClient } from "@/lib/supabase";

export interface ProspectContact {
  email: string | null;
  phone: string | null;
  linkedinUrl: string | null;
}

export interface ProspectEnrichment {
  abn: string | null;
  industry: string | null;
  employeeCount: number | null;
  website: string | null;
  location: string | null;
}

export interface TouchEvent {
  id: string;
  channel: string;
  sentAt: string;
  status: string | null;
  sequenceStep: number | null;
  replied: boolean;
  preview: string | null;
}

export interface ScheduledTouch {
  id: string;
  channel: string;
  scheduledAt: string;
  sequenceStep: number | null;
  status: string;
}

export interface ReplyEvent {
  id: string;
  channel: string | null;
  receivedAt: string;
  intent: string | null;
  preview: string | null;
}

export interface ProspectDetail {
  leadId: string;
  name: string;
  company: string;
  vrGrade: string | null;
  score: number | null;
  contact: ProspectContact;
  enrichment: ProspectEnrichment;
  touches: TouchEvent[];
  scheduled: ScheduledTouch[];
  replies: ReplyEvent[];
}

function gradeFromScore(score: number | null): string | null {
  if (score === null || score === undefined) return null;
  if (score >= 85) return "A";
  if (score >= 70) return "B";
  if (score >= 50) return "C";
  if (score >= 30) return "D";
  return "F";
}

async function fetchDetail(leadId: string): Promise<ProspectDetail | null> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;

  const buRes = await client
    .from("business_universe")
    .select(
      "id, display_name, dm_name, dm_title, dm_email, dm_phone, dm_mobile, dm_linkedin_url, " +
      "abn, gmb_category, company_employee_count_exact, website, suburb, state, propensity_score",
    )
    .eq("id", leadId)
    .maybeSingle();
  const bu = buRes?.data as Record<string, unknown> | null;
  if (!bu) return null;

  let touches: TouchEvent[] = [];
  try {
    const { data } = await client
      .from("cis_outreach_outcomes")
      .select("id, channel, sent_at, final_outcome, sequence_step, replied_at, subject_hash")
      .eq("lead_id", leadId)
      .order("sent_at", { ascending: true })
      .limit(50);
    touches = ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
      id: String(r.id),
      channel: String(r.channel ?? ""),
      sentAt: String(r.sent_at ?? ""),
      status: (r.final_outcome as string | null) ?? null,
      sequenceStep: (r.sequence_step as number | null) ?? null,
      replied: !!r.replied_at,
      preview: (r.subject_hash as string | null) ?? null,
    }));
  } catch (e) {
    console.warn("[useProspectDetail] touches skipped", e);
  }

  let scheduled: ScheduledTouch[] = [];
  try {
    const { data } = await client
      .from("scheduled_touches")
      .select("id, channel, scheduled_at, sequence_step, status")
      .eq("lead_id", leadId)
      .in("status", ["pending", "paused"])
      .order("scheduled_at", { ascending: true })
      .limit(20);
    scheduled = ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
      id: String(r.id),
      channel: String(r.channel ?? ""),
      scheduledAt: String(r.scheduled_at ?? ""),
      sequenceStep: (r.sequence_step as number | null) ?? null,
      status: String(r.status ?? "pending"),
    }));
  } catch (e) {
    console.warn("[useProspectDetail] scheduled skipped", e);
  }

  let replies: ReplyEvent[] = [];
  try {
    const { data } = await client
      .from("activities")
      .select("id, channel, created_at, intent, preview")
      .eq("lead_id", leadId)
      .eq("action", "replied")
      .order("created_at", { ascending: false })
      .limit(20);
    replies = ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
      id: String(r.id),
      channel: (r.channel as string | null) ?? null,
      receivedAt: String(r.created_at ?? ""),
      intent: (r.intent as string | null) ?? null,
      preview: (r.preview as string | null) ?? null,
    }));
  } catch (e) {
    console.warn("[useProspectDetail] replies skipped", e);
  }

  const score = typeof bu.propensity_score === "number" ? (bu.propensity_score as number) : null;
  const emp = bu.company_employee_count_exact;
  const locParts = [bu.suburb as string | null, bu.state as string | null].filter(Boolean);

  return {
    leadId: String(bu.id),
    name: (bu.dm_name as string | null) ?? "Unknown",
    company: (bu.display_name as string | null) ?? "—",
    vrGrade: gradeFromScore(score),
    score,
    contact: {
      email: (bu.dm_email as string | null) ?? null,
      phone: ((bu.dm_phone as string | null) ?? (bu.dm_mobile as string | null)) ?? null,
      linkedinUrl: (bu.dm_linkedin_url as string | null) ?? null,
    },
    enrichment: {
      abn: (bu.abn as string | null) ?? null,
      industry: (bu.gmb_category as string | null) ?? null,
      employeeCount: typeof emp === "number" ? emp : null,
      website: (bu.website as string | null) ?? null,
      location: locParts.length ? locParts.join(", ") : null,
    },
    touches,
    scheduled,
    replies,
  };
}

export function useProspectDetail(leadId: string | null) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["prospect-detail", leadId],
    queryFn: () => fetchDetail(leadId!),
    enabled: !!leadId,
    staleTime: 30_000,
  });
  return { prospect: data ?? null, isLoading, error, refetch };
}
