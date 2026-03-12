/**
 * FILE: frontend/hooks/use-leads.ts
 * PURPOSE: React Query hooks for leads
 * PHASE: 14 (Wire Frontend to Real Data)
 * TASK: FBC-003
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useClient } from "./use-client";
import { getLeads, getLead, createLead, updateLead } from "@/lib/api/leads";
import type {
  Lead,
  LeadCreate,
  LeadUpdate,
  LeadFilters,
  PaginationParams,
} from "@/lib/api/types";

/**
 * Hook to fetch paginated leads for the current client.
 * Returns unwrapped { leads, total, isLoading, error, refresh }.
 */
export function useLeads(params?: PaginationParams & LeadFilters) {
  const { clientId } = useClient();

  const query = useQuery({
    queryKey: ["leads", clientId, params],
    queryFn: () => getLeads(clientId!, params),
    enabled: !!clientId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });

  return {
    leads: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refresh: query.refetch,
  };
}

/**
 * Hook to fetch a single lead by ID.
 */
export function useLead(leadId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["lead", clientId, leadId],
    queryFn: () => getLead(clientId!, leadId!),
    enabled: !!clientId && !!leadId,
    staleTime: 60 * 1000,
  });
}

/**
 * Hook to create a new lead.
 */
export function useCreateLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: LeadCreate) => createLead(clientId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
    },
  });
}

/**
 * Hook to update an existing lead.
 */
export function useUpdateLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leadId, data }: { leadId: string; data: LeadUpdate }) =>
      updateLead(clientId!, leadId, data),
    onSuccess: (updatedLead, { leadId }) => {
      queryClient.setQueryData(["lead", clientId, leadId], updatedLead);
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
    },
  });
}

export type { Lead };
