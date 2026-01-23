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
  getDashboardMetrics,
  getActivityFeed,
  getCampaignPerformance,
  getChannelMetrics,
  getALSDistribution,
  getDailyActivity,
  getContentArchive,
  getBestOfShowcase,
} from "@/lib/api/reports";
import type { ContentArchiveFilters } from "@/lib/api/types";

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

/**
 * Hook to fetch content archive (paginated, filterable)
 */
export function useContentArchive(filters?: ContentArchiveFilters) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["content-archive", clientId, filters],
    queryFn: () => getContentArchive(clientId!, filters),
    enabled: !!clientId,
    staleTime: 30 * 1000, // 30 seconds
    refetchOnWindowFocus: false, // Don't refetch on focus (user is browsing)
  });
}

/**
 * Hook to fetch Best Of showcase (high-performing content)
 */
export function useBestOfShowcase(params?: { limit?: number; period_days?: number }) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["best-of-showcase", clientId, params],
    queryFn: () => getBestOfShowcase(clientId!, params),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000, // 5 minutes - content doesn't change often
  });
}

/**
 * Hook to fetch outcome-focused dashboard metrics
 *
 * Returns hero metrics (meetings, show rate), comparison data,
 * activity proof, and per-campaign summaries.
 */
export function useDashboardMetrics() {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["dashboard-metrics", clientId],
    queryFn: () => getDashboardMetrics(clientId!),
    enabled: !!clientId,
    staleTime: 60 * 1000, // 1 minute - metrics should be relatively fresh
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}
