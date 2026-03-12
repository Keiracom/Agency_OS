/**
 * FILE: frontend/hooks/use-lead-detail.ts
 * PURPOSE: React Query hook for a single lead's detail
 * PHASE: 14 (Wire Frontend to Real Data)
 * TASK: FBC-003
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { getLead } from "@/lib/api/leads";
import type { Lead } from "@/lib/api/types";

/**
 * Hook to fetch a single lead by ID
 */
export function useLeadDetail(
  clientId: string | null | undefined,
  leadId: string | undefined
) {
  const query = useQuery({
    queryKey: ["lead", clientId, leadId],
    queryFn: () => getLead(clientId!, leadId!),
    enabled: !!clientId && !!leadId,
    staleTime: 60 * 1000, // 1 minute
  });

  return {
    lead: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error,
  };
}

export type { Lead };
