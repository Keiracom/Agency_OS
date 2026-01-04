/**
 * FILE: frontend/hooks/use-leads.ts
 * PURPOSE: React Query hooks for leads
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-003
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useClient } from "./use-client";
import {
  getLeads,
  getLead,
  createLead,
  createLeadsBulk,
  updateLead,
  deleteLead,
  getLeadActivities,
  enrichLead,
  enrichLeadsBulk,
} from "@/lib/api/leads";
import type { Lead, LeadCreate, LeadUpdate, LeadFilters, PaginationParams } from "@/lib/api/types";

/**
 * Hook to fetch paginated leads list
 */
export function useLeads(params?: PaginationParams & LeadFilters) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["leads", clientId, params],
    queryFn: () => getLeads(clientId!, params),
    enabled: !!clientId,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch single lead
 */
export function useLead(leadId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["lead", clientId, leadId],
    queryFn: () => getLead(clientId!, leadId!),
    enabled: !!clientId && !!leadId,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch lead activities (timeline)
 */
export function useLeadActivities(leadId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["lead-activities", clientId, leadId],
    queryFn: () => getLeadActivities(clientId!, leadId!),
    enabled: !!clientId && !!leadId,
    staleTime: 10 * 1000, // 10 seconds
  });
}

/**
 * Hook to create a lead
 */
export function useCreateLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: LeadCreate) => createLead(clientId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}

/**
 * Hook to bulk create leads
 */
export function useCreateLeadsBulk() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (leads: LeadCreate[]) => createLeadsBulk(clientId!, leads),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}

/**
 * Hook to update a lead
 */
export function useUpdateLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leadId, data }: { leadId: string; data: LeadUpdate }) =>
      updateLead(clientId!, leadId, data),
    onSuccess: (data, { leadId }) => {
      queryClient.setQueryData(["lead", clientId, leadId], data);
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
    },
  });
}

/**
 * Hook to delete a lead
 */
export function useDeleteLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (leadId: string) => deleteLead(clientId!, leadId),
    onSuccess: (_, leadId) => {
      queryClient.removeQueries({ queryKey: ["lead", clientId, leadId] });
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}

/**
 * Hook to enrich a lead
 */
export function useEnrichLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (leadId: string) => enrichLead(clientId!, leadId),
    onSuccess: (data, leadId) => {
      queryClient.setQueryData(["lead", clientId, leadId], data);
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
    },
  });
}

/**
 * Hook to bulk enrich leads
 */
export function useEnrichLeadsBulk() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (leadIds: string[]) => enrichLeadsBulk(clientId!, leadIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
    },
  });
}
