/**
 * FILE: frontend/lib/api/reports.ts
 * PURPOSE: Report/metrics API fetchers
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-002
 */

import api from "./index";
import type {
  DashboardStats,
  CampaignPerformance,
  ChannelMetrics,
  ALSDistribution,
  Activity,
  DailyActivity,
  ALSTier,
} from "./types";

// ============================================
// Backend Response Types (for transformation)
// ============================================

interface BackendClientMetrics {
  client_id: string;
  client_name: string;
  total_campaigns: number;
  active_campaigns: number;
  total_leads: number;
  total_replies: number;
  total_conversions: number;
  overall_reply_rate: number;
  overall_conversion_rate: number;
  campaigns: unknown[];
  channel_performance: Record<string, unknown>;
  start_date?: string;
  end_date?: string;
}

interface BackendTierDistribution {
  count: number;
  percentage: number;
}

interface BackendALSDistribution {
  hot: BackendTierDistribution;
  warm: BackendTierDistribution;
  cool: BackendTierDistribution;
  cold: BackendTierDistribution;
  dead: BackendTierDistribution;
  total: number;
  campaign_id?: string;
  client_id?: string;
}

interface BackendDailyMetrics {
  date: string;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  conversions: number;
}

interface BackendDailyActivity {
  campaign_id?: string;
  client_id?: string;
  start_date: string;
  end_date: string;
  days: BackendDailyMetrics[];
  totals: {
    sent: number;
    delivered: number;
    opened: number;
    clicked: number;
    replied: number;
    bounced: number;
  };
}

// ============================================
// API Functions
// ============================================

/**
 * Get dashboard statistics for a client
 */
export async function getDashboardStats(clientId: string): Promise<DashboardStats> {
  try {
    const response = await api.get<BackendClientMetrics>(`/api/v1/reports/clients/${clientId}`);

    // Transform BackendClientMetrics → DashboardStats
    return {
      total_leads: response.total_leads ?? 0,
      leads_contacted: response.total_leads ?? 0, // TODO: wire to backend - needs separate field
      leads_replied: response.total_replies ?? 0,
      leads_converted: response.total_conversions ?? 0,
      active_campaigns: response.active_campaigns ?? 0,
      credits_remaining: 2250, // TODO: wire to backend - needs client credits endpoint
      reply_rate: response.overall_reply_rate ?? 0,
      conversion_rate: response.overall_conversion_rate ?? 0,
    };
  } catch (error) {
    console.error("[getDashboardStats] Failed to fetch dashboard stats:", error);
    // Return safe defaults on error
    return {
      total_leads: 0,
      leads_contacted: 0,
      leads_replied: 0,
      leads_converted: 0,
      active_campaigns: 0,
      credits_remaining: 0,
      reply_rate: 0,
      conversion_rate: 0,
    };
  }
}

/**
 * Get recent activity feed
 */
export async function getActivityFeed(
  clientId: string,
  params?: { limit?: number }
): Promise<Activity[]> {
  // TODO: wire to backend - endpoint /api/v1/clients/{client_id}/activities does not exist yet
  console.warn("[getActivityFeed] Endpoint not implemented, returning empty array");
  void clientId; // Acknowledge unused param
  void params;
  return [];
}

/**
 * Get campaign performance metrics
 */
export async function getCampaignPerformance(
  clientId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<CampaignPerformance[]> {
  // TODO: wire to backend - endpoint /api/v1/reports/clients/{client_id}/campaigns does not exist
  // Backend only has /api/v1/reports/campaigns/{campaign_id} for individual campaigns
  console.warn("[getCampaignPerformance] Endpoint not implemented, returning empty array");
  void clientId;
  void params;
  return [];
}

/**
 * Get channel metrics
 */
export async function getChannelMetrics(
  clientId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<ChannelMetrics[]> {
  // TODO: wire to backend - no dedicated channel metrics endpoint
  // Channel data is nested in ClientMetricsResponse.channel_performance
  console.warn("[getChannelMetrics] Endpoint not implemented, returning empty array");
  void clientId;
  void params;
  return [];
}

/**
 * Get ALS tier distribution
 */
export async function getALSDistribution(clientId: string): Promise<ALSDistribution[]> {
  try {
    const response = await api.get<BackendALSDistribution>(
      `/api/v1/reports/leads/distribution?client_id=${clientId}`
    );

    // Transform object → array
    const tiers: ALSTier[] = ["hot", "warm", "cool", "cold", "dead"];
    return tiers.map((tier) => ({
      tier,
      count: response[tier]?.count ?? 0,
      percentage: response[tier]?.percentage ?? 0,
    }));
  } catch (error) {
    console.error("[getALSDistribution] Failed to fetch ALS distribution:", error);
    // Return safe defaults on error
    return [
      { tier: "hot", count: 0, percentage: 0 },
      { tier: "warm", count: 0, percentage: 0 },
      { tier: "cool", count: 0, percentage: 0 },
      { tier: "cold", count: 0, percentage: 0 },
      { tier: "dead", count: 0, percentage: 0 },
    ];
  }
}

/**
 * Get daily activity summary
 */
export async function getDailyActivity(
  clientId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<DailyActivity[]> {
  try {
    const searchParams = new URLSearchParams();
    searchParams.set("client_id", clientId);
    if (params?.start_date) searchParams.set("start_date", params.start_date);
    if (params?.end_date) searchParams.set("end_date", params.end_date);

    const response = await api.get<BackendDailyActivity>(
      `/api/v1/reports/activity/daily?${searchParams.toString()}`
    );

    // Transform BackendDailyActivity → DailyActivity[]
    if (!response.days || !Array.isArray(response.days)) {
      return [];
    }

    return response.days.map((day) => ({
      date: day.date,
      emails_sent: day.sent ?? 0, // Backend aggregates all channels into 'sent'
      sms_sent: 0, // TODO: wire to backend - needs per-channel breakdown
      linkedin_sent: 0, // TODO: wire to backend - needs per-channel breakdown
      replies_received: day.replied ?? 0,
      meetings_booked: day.conversions ?? 0, // Using conversions as proxy for meetings
    }));
  } catch (error) {
    console.error("[getDailyActivity] Failed to fetch daily activity:", error);
    return [];
  }
}
