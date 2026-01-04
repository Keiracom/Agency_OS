/**
 * FILE: frontend/hooks/use-admin.ts
 * PURPOSE: React Query hooks for admin dashboard
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-005
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAdminStats,
  getSystemHealth,
  getClients,
  getClientDetails,
  getAISpend,
  getGlobalActivity,
  getRevenueMetrics,
  getAlerts,
  acknowledgeAlert,
  getSuppressionList,
  addToSuppressionList,
  removeFromSuppressionList,
} from "@/lib/api/admin";
import type { PaginationParams } from "@/lib/api/types";

/**
 * Hook to fetch admin dashboard stats
 */
export function useAdminStats() {
  return useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to fetch system health
 */
export function useSystemHealth() {
  return useQuery({
    queryKey: ["system-health"],
    queryFn: getSystemHealth,
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch clients list (admin view)
 */
export function useAdminClients(
  params?: PaginationParams & { search?: string; status?: string }
) {
  return useQuery({
    queryKey: ["admin-clients", params],
    queryFn: () => getClients(params),
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch single client details (admin view)
 */
export function useAdminClientDetails(clientId: string | undefined) {
  return useQuery({
    queryKey: ["admin-client", clientId],
    queryFn: () => getClientDetails(clientId!),
    enabled: !!clientId,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch AI spend
 */
export function useAISpend(params?: {
  startDate?: string;
  endDate?: string;
}) {
  return useQuery({
    queryKey: ["ai-spend", params],
    queryFn: () =>
      getAISpend({
        start_date: params?.startDate,
        end_date: params?.endDate,
      }),
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to fetch global activity
 */
export function useGlobalActivity(limit = 50) {
  return useQuery({
    queryKey: ["global-activity", limit],
    queryFn: () => getGlobalActivity({ limit }),
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch revenue metrics
 */
export function useRevenueMetrics(params?: {
  startDate?: string;
  endDate?: string;
}) {
  return useQuery({
    queryKey: ["revenue-metrics", params],
    queryFn: () =>
      getRevenueMetrics({
        start_date: params?.startDate,
        end_date: params?.endDate,
      }),
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to fetch alerts
 */
export function useAlerts() {
  return useQuery({
    queryKey: ["admin-alerts"],
    queryFn: getAlerts,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to acknowledge an alert
 */
export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: string) => acknowledgeAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-alerts"] });
    },
  });
}

/**
 * Hook to fetch suppression list
 */
export function useSuppressionList(params?: PaginationParams & { search?: string }) {
  return useQuery({
    queryKey: ["suppression-list", params],
    queryFn: () => getSuppressionList(params),
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to add to suppression list
 */
export function useAddToSuppressionList() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { email: string; reason: string }) =>
      addToSuppressionList(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppression-list"] });
    },
  });
}

/**
 * Hook to remove from suppression list
 */
export function useRemoveFromSuppressionList() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => removeFromSuppressionList(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppression-list"] });
    },
  });
}
