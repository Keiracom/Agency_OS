/**
 * FILE: frontend/hooks/use-campaigns.ts
 * PURPOSE: React Query hooks for campaigns
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-004
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useClient } from "./use-client";
import {
  getCampaigns,
  getCampaign,
  createCampaign,
  updateCampaign,
  updateCampaignStatus,
  activateCampaign,
  pauseCampaign,
  deleteCampaign,
  getCampaignLeads,
  getCampaignSequences,
} from "@/lib/api/campaigns";
import type {
  Campaign,
  CampaignCreate,
  CampaignUpdate,
  CampaignStatus,
  PaginationParams,
} from "@/lib/api/types";

interface CampaignFilters {
  status?: CampaignStatus;
  search?: string;
}

/**
 * Hook to fetch paginated campaigns list
 */
export function useCampaigns(params?: PaginationParams & CampaignFilters) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["campaigns", clientId, params],
    queryFn: () => getCampaigns(clientId!, params),
    enabled: !!clientId,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch single campaign
 */
export function useCampaign(campaignId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["campaign", clientId, campaignId],
    queryFn: () => getCampaign(clientId!, campaignId!),
    enabled: !!clientId && !!campaignId,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch campaign leads
 */
export function useCampaignLeads(campaignId: string | undefined, params?: PaginationParams) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["campaign-leads", clientId, campaignId, params],
    queryFn: () => getCampaignLeads(clientId!, campaignId!, params),
    enabled: !!clientId && !!campaignId,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch campaign sequences
 */
export function useCampaignSequences(campaignId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["campaign-sequences", clientId, campaignId],
    queryFn: () => getCampaignSequences(clientId!, campaignId!),
    enabled: !!clientId && !!campaignId,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to create a campaign
 */
export function useCreateCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CampaignCreate) => createCampaign(clientId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}

/**
 * Hook to update a campaign
 */
export function useUpdateCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      campaignId,
      data,
    }: {
      campaignId: string;
      data: CampaignUpdate;
    }) => updateCampaign(clientId!, campaignId, data),
    onSuccess: (data, { campaignId }) => {
      queryClient.setQueryData(["campaign", clientId, campaignId], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
    },
  });
}

/**
 * Hook to update campaign status
 */
export function useUpdateCampaignStatus() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      campaignId,
      status,
    }: {
      campaignId: string;
      status: CampaignStatus;
    }) => updateCampaignStatus(clientId!, campaignId, status),
    onSuccess: (data, { campaignId }) => {
      queryClient.setQueryData(["campaign", clientId, campaignId], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}

/**
 * Hook to activate a campaign
 */
export function useActivateCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaignId: string) => activateCampaign(clientId!, campaignId),
    onSuccess: (data, campaignId) => {
      queryClient.setQueryData(["campaign", clientId, campaignId], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}

/**
 * Hook to pause a campaign
 */
export function usePauseCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaignId: string) => pauseCampaign(clientId!, campaignId),
    onSuccess: (data, campaignId) => {
      queryClient.setQueryData(["campaign", clientId, campaignId], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}

/**
 * Hook to delete a campaign
 */
export function useDeleteCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaignId: string) => deleteCampaign(clientId!, campaignId),
    onSuccess: (_, campaignId) => {
      queryClient.removeQueries({ queryKey: ["campaign", clientId, campaignId] });
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}
