/**
 * FILE: frontend/hooks/use-reports.ts
 * PURPOSE: React Query hooks for reports/metrics
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-002
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useClient } from "./use-client";
import {
  getDashboardStats,
  getActivityFeed,
  getCampaignPerformance,
  getChannelMetrics,
  getALSDistribution,
  getDailyActivity,
} from "@/lib/api/reports";

/**
 * Hook to fetch dashboard statistics
 */
export function useDashboardStats() {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["dashboard-stats", clientId],
    queryFn: () => getDashboardStats(clientId!),
    enabled: !!clientId,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

/**
 * Hook to fetch activity feed
 */
export function useActivityFeed(limit = 20) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["activity-feed", clientId, limit],
    queryFn: () => getActivityFeed(clientId!, { limit }),
    enabled: !!clientId,
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
}

/**
 * Hook to fetch campaign performance
 */
export function useCampaignPerformance(params?: {
  startDate?: string;
  endDate?: string;
}) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["campaign-performance", clientId, params],
    queryFn: () =>
      getCampaignPerformance(clientId!, {
        start_date: params?.startDate,
        end_date: params?.endDate,
      }),
    enabled: !!clientId,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to fetch channel metrics
 */
export function useChannelMetrics(params?: {
  startDate?: string;
  endDate?: string;
}) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["channel-metrics", clientId, params],
    queryFn: () =>
      getChannelMetrics(clientId!, {
        start_date: params?.startDate,
        end_date: params?.endDate,
      }),
    enabled: !!clientId,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to fetch ALS distribution
 */
export function useALSDistribution() {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["als-distribution", clientId],
    queryFn: () => getALSDistribution(clientId!),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch daily activity summary
 */
export function useDailyActivity(params?: {
  startDate?: string;
  endDate?: string;
}) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["daily-activity", clientId, params],
    queryFn: () =>
      getDailyActivity(clientId!, {
        start_date: params?.startDate,
        end_date: params?.endDate,
      }),
    enabled: !!clientId,
    staleTime: 60 * 1000, // 1 minute
  });
}
