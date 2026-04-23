/**
 * FILE: frontend/lib/hooks/useApprovalQueue.ts
 * PURPOSE: Approval Queue list + per-touch action mutations (approve/reject/defer)
 * PHASE: PHASE-2.1-APPROVAL-KILLSWITCH
 *
 * Queries real Supabase tables. No mock data — returns empty array on any error.
 *
 * Sources:
 *   scheduled_touches  (status='pending')   — canonical queue
 *   business_universe                        — prospect name + company
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useClient } from "@/hooks/use-client";
import { createBrowserClient } from "@/lib/supabase";

export interface PendingTouch {
  id: string;
  leadId: string;
  channel: string;
  scheduledAt: string;
  sequenceStep: number | null;
  contentPreview: string | null;
  prospectName: string;
  company: string;
}

async function fetchPending(clientId: string): Promise<PendingTouch[]> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;

  const { data: touches, error } = await client
    .from("scheduled_touches")
    .select("id, lead_id, channel, scheduled_at, sequence_step, content")
    .eq("client_id", clientId)
    .eq("status", "pending")
    .order("scheduled_at", { ascending: true })
    .limit(200);
  if (error) {
    console.error("[useApprovalQueue] scheduled_touches failed", error);
    return [];
  }

  const rows = (touches ?? []) as Array<Record<string, unknown>>;
  const leadIds = Array.from(new Set(rows.map((r) => String(r.lead_id)).filter(Boolean)));

  const byLead = new Map<string, { name: string; company: string }>();
  if (leadIds.length) {
    const { data: bu } = await client
      .from("business_universe")
      .select("id, display_name, dm_name")
      .in("id", leadIds);
    for (const b of ((bu ?? []) as Array<Record<string, unknown>>)) {
      byLead.set(String(b.id), {
        name: (b.dm_name as string | null) ?? "Unknown",
        company: (b.display_name as string | null) ?? "—",
      });
    }
  }

  return rows.map((r) => {
    const leadId = String(r.lead_id);
    const n = byLead.get(leadId) ?? { name: "Unknown", company: "—" };
    const content = (r.content as Record<string, unknown> | null) ?? null;
    return {
      id: String(r.id),
      leadId,
      channel: String(r.channel ?? ""),
      scheduledAt: String(r.scheduled_at ?? ""),
      sequenceStep: (r.sequence_step as number | null) ?? null,
      contentPreview: ((content?.subject as string | undefined)
        ?? (content?.text as string | undefined)
        ?? (content?.preview as string | undefined)
        ?? null),
      prospectName: n.name,
      company: n.company,
    };
  });
}

export type ApprovalAction = "approve" | "reject" | "defer";

async function postAction(body: { touch_id: string; action: ApprovalAction }) {
  // Operator identity is established by the session cookie / JWT set at login.
  // No client-side HMAC — the dashboard is same-origin and the session cookie
  // is the authoritative gate. Backend enforces RLS + session auth.
  const res = await fetch("/api/v1/outreach/approval", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json().catch(() => ({}));
}

export function useApprovalQueue() {
  const { clientId } = useClient();
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["approval-queue", clientId],
    queryFn: () => fetchPending(clientId!),
    enabled: !!clientId,
    staleTime: 15_000,
    refetchInterval: 60_000,
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ["approval-queue", clientId] });

  const approve = useMutation({
    mutationFn: (touchId: string) => postAction({ touch_id: touchId, action: "approve" }),
    onSuccess: invalidate,
  });
  const reject = useMutation({
    mutationFn: (touchId: string) => postAction({ touch_id: touchId, action: "reject" }),
    onSuccess: invalidate,
  });
  const defer = useMutation({
    mutationFn: (touchId: string) => postAction({ touch_id: touchId, action: "defer" }),
    onSuccess: invalidate,
  });
  const releaseAll = useMutation({
    mutationFn: async (ids: string[]) => {
      const results = await Promise.allSettled(
        ids.map((id) => postAction({ touch_id: id, action: "approve" })),
      );
      return { ok: results.filter((r) => r.status === "fulfilled").length, total: ids.length };
    },
    onSuccess: invalidate,
  });

  return {
    touches: data ?? [],
    isLoading,
    error,
    approve,
    reject,
    defer,
    releaseAll,
    refetch: invalidate,
  };
}
