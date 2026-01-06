/**
 * FILE: frontend/hooks/use-deep-research.ts
 * PURPOSE: React Query hooks for deep research
 * PHASE: 20 (UI Wiring)
 * TASK: WIRE-004
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useClient } from "./use-client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface DeepResearchData {
  lead_id: string;
  status: "not_started" | "in_progress" | "complete" | "failed";
  icebreaker_hook: string | null;
  profile_summary: string | null;
  recent_activity: string | null;
  posts_found: number;
  confidence: number | null;
  run_at: string | null;
  social_posts: SocialPost[];
  error: string | null;
}

export interface SocialPost {
  id: string;
  source: string;
  content: string;
  date: string | null;
  hook: string | null;
}

export interface TriggerResponse {
  lead_id: string;
  status: "queued" | "already_complete" | "not_eligible" | "complete" | "failed";
  message: string;
  als_score: number | null;
  als_tier: string | null;
}

// API Functions
async function getLeadResearch(
  clientId: string,
  leadId: string,
  token: string
): Promise<DeepResearchData> {
  const response = await fetch(
    `${API_BASE}/api/v1/clients/${clientId}/leads/${leadId}/research`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch research: ${response.statusText}`);
  }

  return response.json();
}

async function triggerLeadResearch(
  clientId: string,
  leadId: string,
  token: string,
  force: boolean = false
): Promise<TriggerResponse> {
  const url = new URL(
    `${API_BASE}/api/v1/clients/${clientId}/leads/${leadId}/research`
  );
  if (force) {
    url.searchParams.set("force", "true");
  }

  const response = await fetch(url.toString(), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to trigger research: ${response.statusText}`);
  }

  return response.json();
}

// Hooks

/**
 * Hook to fetch deep research data for a lead
 * Polls every 5 seconds while status is "in_progress"
 */
export function useDeepResearch(leadId: string | undefined) {
  const { clientId, token } = useClient();

  const query = useQuery({
    queryKey: ["deep-research", clientId, leadId],
    queryFn: () => getLeadResearch(clientId!, leadId!, token!),
    enabled: !!clientId && !!leadId && !!token,
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: (data) => {
      // Poll every 5 seconds while in_progress
      if (data?.status === "in_progress") {
        return 5000;
      }
      return false;
    },
  });

  return {
    ...query,
    isResearching: query.data?.status === "in_progress",
    isComplete: query.data?.status === "complete",
    hasFailed: query.data?.status === "failed",
    notStarted: query.data?.status === "not_started",
  };
}

/**
 * Hook to trigger deep research for a lead
 */
export function useTriggerDeepResearch() {
  const { clientId, token } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leadId, force = false }: { leadId: string; force?: boolean }) =>
      triggerLeadResearch(clientId!, leadId, token!, force),
    onSuccess: (data, { leadId }) => {
      // Invalidate research query to trigger refetch
      queryClient.invalidateQueries({
        queryKey: ["deep-research", clientId, leadId],
      });
      // Also invalidate lead query in case ALS data changed
      queryClient.invalidateQueries({
        queryKey: ["lead", clientId, leadId],
      });
    },
  });
}

/**
 * Hook to check if a lead is eligible for deep research
 */
export function useResearchEligibility(lead: {
  als_score?: number | null;
  als_tier?: string | null;
  linkedin_url?: string | null;
  deep_research_run_at?: string | null;
} | null | undefined) {
  if (!lead) {
    return {
      isEligible: false,
      isHotLead: false,
      hasLinkedIn: false,
      alreadyResearched: false,
      reason: "No lead data",
    };
  }

  const isHotLead = (lead.als_score ?? 0) >= 85;
  const hasLinkedIn = !!lead.linkedin_url;
  const alreadyResearched = !!lead.deep_research_run_at;

  let reason = "";
  if (!hasLinkedIn) {
    reason = "No LinkedIn URL available";
  } else if (alreadyResearched) {
    reason = "Research already completed";
  } else if (!isHotLead) {
    reason = "Lead is not Hot tier (ALS < 85)";
  }

  return {
    isEligible: hasLinkedIn && !alreadyResearched,
    isHotLead,
    hasLinkedIn,
    alreadyResearched,
    reason,
  };
}
