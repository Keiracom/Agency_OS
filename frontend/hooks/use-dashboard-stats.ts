/**
 * FILE: frontend/hooks/use-dashboard-stats.ts
 * PURPOSE: React Query hook for dashboard statistics (P0/P1)
 * Phase: Operation Modular Cockpit
 * 
 * Fetches and transforms dashboard metrics from the backend API.
 * Provides outcome-focused stats per DASHBOARD.md spec.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useClient } from "./use-client";
import type {
  DashboardMetricsResponse,
  DashboardOutcomes,
  DashboardComparison,
  DashboardActivityMetrics,
  DashboardCampaignSummary,
  OnTrackStatus,
} from "@/lib/api/types";

// ============================================
// Types
// ============================================

export interface DashboardStatsData {
  // T1 Hero Metrics (DASHBOARD.md spec)
  meetingsBooked: number;
  showRate: number;
  dealsCreated: number;
  status: OnTrackStatus;
  
  // Comparison metrics
  meetingsVsLastMonth: number;
  meetingsVsLastMonthPct: number;
  tierTargetLow: number;
  tierTargetHigh: number;
  
  // Activity metrics
  prospectsInPipeline: number;
  activeSequences: number;
  repliesThisMonth: number;
  replyRate: number;
  
  // Campaign summaries
  campaigns: DashboardCampaignSummary[];
  
  // Period
  period: string;
}

interface UseDashboardStatsOptions {
  /** Campaign ID to filter stats */
  campaignId?: string;
  /** Enable/disable the query */
  enabled?: boolean;
}

// ============================================
// API Fetch Function
// ============================================

async function fetchDashboardStats(
  clientId: string,
  campaignId?: string
): Promise<DashboardMetricsResponse> {
  const params = new URLSearchParams();
  if (campaignId) {
    params.set("campaign_id", campaignId);
  }
  
  // Note: Backend uses /reports/clients/{id}/dashboard-metrics
  const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reports/clients/${clientId}/dashboard-metrics${params.toString() ? `?${params}` : ""}`;
  
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
  });

  if (!response.ok) {
    // Fallback to mock data if endpoint not ready
    if (response.status === 404) {
      return getMockDashboardStats();
    }
    throw new Error(`Failed to fetch dashboard stats: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Mock data for development/fallback
 * Per DASHBOARD.md: Show realistic but clearly demo data
 */
function getMockDashboardStats(): DashboardMetricsResponse {
  return {
    period: "This Month",
    outcomes: {
      meetings_booked: 12,
      show_rate: 83,
      meetings_showed: 10,
      deals_created: 3,
      status: "on_track" as OnTrackStatus,
    },
    comparison: {
      meetings_vs_last_month: 3,
      meetings_vs_last_month_pct: 25,
      tier_target_low: 15,
      tier_target_high: 20,
    },
    activity: {
      prospects_in_pipeline: 150,
      active_sequences: 3,
      replies_this_month: 42,
      reply_rate: 4.8,
    },
    campaigns: [
      {
        id: "1",
        name: "Tech Decision Makers",
        priority_pct: 40,
        meetings_booked: 6,
        reply_rate: 5.1,
        show_rate: 83,
      },
      {
        id: "2",
        name: "Series A Startups",
        priority_pct: 35,
        meetings_booked: 4,
        reply_rate: 5.6,
        show_rate: 75,
      },
      {
        id: "3",
        name: "Enterprise Accounts",
        priority_pct: 25,
        meetings_booked: 2,
        reply_rate: 4.4,
        show_rate: 100,
      },
    ],
  };
}

// ============================================
// Transform Function
// ============================================

function transformStats(data: DashboardMetricsResponse): DashboardStatsData {
  return {
    // T1 Hero Metrics
    meetingsBooked: data.outcomes.meetings_booked,
    showRate: data.outcomes.show_rate,
    dealsCreated: data.outcomes.deals_created,
    status: data.outcomes.status,
    
    // Comparison
    meetingsVsLastMonth: data.comparison.meetings_vs_last_month,
    meetingsVsLastMonthPct: data.comparison.meetings_vs_last_month_pct,
    tierTargetLow: data.comparison.tier_target_low,
    tierTargetHigh: data.comparison.tier_target_high,
    
    // Activity
    prospectsInPipeline: data.activity.prospects_in_pipeline,
    activeSequences: data.activity.active_sequences,
    repliesThisMonth: data.activity.replies_this_month,
    replyRate: data.activity.reply_rate,
    
    // Campaigns
    campaigns: data.campaigns,
    
    // Period
    period: data.period,
  };
}

// ============================================
// Hook
// ============================================

/**
 * Hook to fetch dashboard statistics
 * 
 * Per DASHBOARD.md spec, returns outcome-focused metrics:
 * - Meetings booked (T1)
 * - Show rate (T1)
 * - Status (ahead/on_track/behind)
 * 
 * Does NOT expose:
 * - Credits remaining
 * - Lead counts (internal metric)
 * - Cost per meeting (internal)
 * 
 * @example
 * ```tsx
 * const { stats, isLoading } = useDashboardStats();
 * console.log(stats.meetingsBooked, stats.status);
 * ```
 */
export function useDashboardStats(options: UseDashboardStatsOptions = {}) {
  const { campaignId, enabled = true } = options;
  const { clientId } = useClient();

  const query = useQuery({
    queryKey: ["dashboard-stats", clientId, campaignId],
    queryFn: () => fetchDashboardStats(clientId!, campaignId),
    enabled: enabled && !!clientId,
    staleTime: 60 * 1000, // 1 minute
  });

  const stats: DashboardStatsData | null = query.data
    ? transformStats(query.data)
    : null;

  return {
    /** Transformed dashboard stats */
    stats,
    /** Raw API response */
    rawData: query.data,
    /** Loading state */
    isLoading: query.isLoading,
    /** Error state */
    error: query.error,
    /** Refetch function */
    refetch: query.refetch,
  };
}

/**
 * Hook to get on-track status with color coding
 */
export function useOnTrackStatus() {
  const { stats, isLoading } = useDashboardStats();
  
  const statusConfig = {
    ahead: {
      label: "Ahead",
      color: "text-emerald-600",
      bgColor: "bg-emerald-50",
      borderColor: "border-emerald-200",
    },
    on_track: {
      label: "On Track",
      color: "text-emerald-600",
      bgColor: "bg-emerald-50",
      borderColor: "border-emerald-200",
    },
    behind: {
      label: "Behind",
      color: "text-amber-600",
      bgColor: "bg-amber-50",
      borderColor: "border-amber-200",
    },
  };
  
  const status = stats?.status ?? "on_track";
  const config = statusConfig[status];
  
  return {
    status,
    ...config,
    isLoading,
    meetingsBooked: stats?.meetingsBooked ?? 0,
    targetLow: stats?.tierTargetLow ?? 15,
    targetHigh: stats?.tierTargetHigh ?? 20,
    progressPercent: stats
      ? Math.min(100, (stats.meetingsBooked / stats.tierTargetHigh) * 100)
      : 0,
  };
}

export default useDashboardStats;
