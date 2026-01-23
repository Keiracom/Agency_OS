/**
 * FILE: frontend/lib/api/reports.ts
 * PURPOSE: Report/metrics API fetchers
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-002
 */

import api from "./index";
import type {
  DashboardStats,
  DashboardMetricsResponse,
  CampaignPerformance,
  ChannelMetrics,
  ALSDistribution,
  Activity,
  DailyActivity,
  ALSTier,
  ContentArchiveResponse,
  ContentArchiveFilters,
  BestOfShowcaseResponse,
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
 * Backend response for client endpoint (includes credits_remaining)
 */
interface BackendClientResponse {
  id: string;
  name: string;
  tier: string;
  subscription_status: string;
  credits_remaining: number;
  // ... other fields
}

/**
 * Get dashboard statistics for a client
 */
export async function getDashboardStats(clientId: string): Promise<DashboardStats> {
  try {
    // Fetch both metrics and client data in parallel for credits_remaining
    const [metricsResponse, clientResponse] = await Promise.all([
      api.get<BackendClientMetrics>(`/api/v1/reports/clients/${clientId}`),
      api.get<BackendClientResponse>(`/api/v1/clients/${clientId}`).catch(() => null),
    ]);

    // Get credits from client endpoint (where it actually lives)
    const creditsRemaining = clientResponse?.credits_remaining ?? 0;

    // Transform BackendClientMetrics → DashboardStats
    // NOTE: leads_contacted should ideally count distinct leads with at least one
    // "sent" activity. Currently using total_leads as proxy since backend reporter
    // engine doesn't track contacted separately. Backend work needed to add
    // leads_contacted to ClientMetricsResponse or calculate from activities.
    return {
      total_leads: metricsResponse.total_leads ?? 0,
      leads_contacted: metricsResponse.total_leads ?? 0, // TODO: Backend needs leads_contacted field - count distinct leads with sent activities
      leads_replied: metricsResponse.total_replies ?? 0,
      leads_converted: metricsResponse.total_conversions ?? 0,
      active_campaigns: metricsResponse.active_campaigns ?? 0,
      credits_remaining: creditsRemaining,
      reply_rate: metricsResponse.overall_reply_rate ?? 0,
      conversion_rate: metricsResponse.overall_conversion_rate ?? 0,
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

// ============================================
// Client Activities Response Types
// ============================================

interface BackendClientActivityItem {
  id: string;
  channel: string;
  action: string;
  timestamp: string;
  lead_name: string | null;
  lead_email: string | null;
  lead_company: string | null;
  campaign_name: string | null;
  subject: string | null;
  content_preview: string | null;
  intent: string | null;
}

interface BackendClientActivitiesResponse {
  items: BackendClientActivityItem[];
  total: number;
  has_more: boolean;
}

/**
 * Get recent activity feed for a client
 */
export async function getActivityFeed(
  clientId: string,
  params?: { limit?: number; offset?: number; channel?: string; action?: string }
): Promise<Activity[]> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.offset) searchParams.set("offset", params.offset.toString());
    if (params?.channel) searchParams.set("channel", params.channel);
    if (params?.action) searchParams.set("action", params.action);

    const queryString = searchParams.toString();
    const url = `/api/v1/reports/clients/${clientId}/activities${queryString ? `?${queryString}` : ""}`;

    const response = await api.get<BackendClientActivitiesResponse>(url);

    // Transform backend response to Activity type
    return response.items.map((item): Activity => ({
      id: item.id,
      client_id: clientId,
      campaign_id: "", // Not returned by this endpoint
      lead_id: "", // Not returned by this endpoint
      channel: item.channel as Activity["channel"],
      action: item.action,
      provider_message_id: null,
      metadata: {},
      created_at: item.timestamp,
      timestamp: item.timestamp,
      subject: item.subject,
      content_preview: item.content_preview,
      intent: item.intent,
      lead_name: item.lead_name,
      lead_email: item.lead_email,
      lead_company: item.lead_company,
      campaign_name: item.campaign_name,
    }));
  } catch (error) {
    console.error("[getActivityFeed] Failed to fetch activity feed:", error);
    return [];
  }
}

// ============================================
// Content Archive API (Phase H - Item 46)
// ============================================

/**
 * Get paginated content archive for a client
 */
export async function getContentArchive(
  clientId: string,
  filters?: ContentArchiveFilters
): Promise<ContentArchiveResponse> {
  try {
    const searchParams = new URLSearchParams();

    if (filters?.page) searchParams.set("page", filters.page.toString());
    if (filters?.page_size) searchParams.set("page_size", filters.page_size.toString());
    if (filters?.channel) searchParams.set("channel", filters.channel);
    if (filters?.action) searchParams.set("action", filters.action);
    if (filters?.campaign_id) searchParams.set("campaign_id", filters.campaign_id);
    if (filters?.search) searchParams.set("search", filters.search);
    if (filters?.start_date) searchParams.set("start_date", filters.start_date);
    if (filters?.end_date) searchParams.set("end_date", filters.end_date);

    const queryString = searchParams.toString();
    const url = `/api/v1/reports/clients/${clientId}/archive/content${queryString ? `?${queryString}` : ""}`;

    const response = await api.get<ContentArchiveResponse>(url);
    return response;
  } catch (error) {
    console.error("[getContentArchive] Failed to fetch content archive:", error);
    return {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
      has_more: false,
    };
  }
}

/**
 * Backend response for campaign performance list endpoint
 */
interface BackendCampaignPerformanceItem {
  campaign_id: string;
  campaign_name: string;
  status: string;
  total_leads: number;
  contacted: number;
  replied: number;
  converted: number;
  reply_rate: number;
  conversion_rate: number;
}

interface BackendCampaignPerformanceResponse {
  client_id: string;
  campaigns: BackendCampaignPerformanceItem[];
  start_date: string | null;
  end_date: string | null;
}

/**
 * Get campaign performance metrics for all campaigns of a client
 *
 * Returns performance metrics including:
 * - total_leads: Leads assigned to campaign
 * - contacted: Leads that have been sent outreach
 * - replied: Leads that have replied
 * - converted: Leads that have converted (meetings booked)
 * - reply_rate: replied / contacted percentage
 * - conversion_rate: converted / contacted percentage
 */
export async function getCampaignPerformance(
  clientId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<CampaignPerformance[]> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.start_date) searchParams.set("start_date", params.start_date);
    if (params?.end_date) searchParams.set("end_date", params.end_date);

    const queryString = searchParams.toString();
    const url = `/api/v1/reports/clients/${clientId}/campaigns/performance${queryString ? `?${queryString}` : ""}`;

    const response = await api.get<BackendCampaignPerformanceResponse>(url);

    // Transform backend response to CampaignPerformance array
    return response.campaigns.map((item): CampaignPerformance => ({
      campaign_id: item.campaign_id,
      campaign_name: item.campaign_name,
      status: item.status as CampaignPerformance["status"],
      total_leads: item.total_leads,
      contacted: item.contacted,
      replied: item.replied,
      converted: item.converted,
      reply_rate: item.reply_rate,
      conversion_rate: item.conversion_rate,
    }));
  } catch (error) {
    console.error("[getCampaignPerformance] Failed to fetch campaign performance:", error);
    return [];
  }
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

// ============================================
// Best Of Showcase API (Phase H - Item 47)
// ============================================

/**
 * Get high-performing content for Best Of showcase
 */
export async function getBestOfShowcase(
  clientId: string,
  params?: { limit?: number; period_days?: number }
): Promise<BestOfShowcaseResponse> {
  try {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.period_days) searchParams.set("period_days", params.period_days.toString());

    const queryString = searchParams.toString();
    const url = `/api/v1/reports/clients/${clientId}/best-of${queryString ? `?${queryString}` : ""}`;

    const response = await api.get<BestOfShowcaseResponse>(url);
    return response;
  } catch (error) {
    console.error("[getBestOfShowcase] Failed to fetch best of showcase:", error);
    return {
      items: [],
      total_high_performers: 0,
      period_days: 30,
    };
  }
}

// ============================================
// Dashboard Metrics API (Outcome-Focused)
// ============================================

/**
 * Get outcome-focused dashboard metrics for a client
 *
 * Returns hero metrics (meetings, show rate), comparison data,
 * activity proof, and per-campaign summaries.
 *
 * NOTE: This endpoint intentionally excludes commodity metrics.
 */
export async function getDashboardMetrics(
  clientId: string
): Promise<DashboardMetricsResponse> {
  try {
    const response = await api.get<DashboardMetricsResponse>(
      `/api/v1/reports/clients/${clientId}/dashboard-metrics`
    );
    return response;
  } catch (error) {
    console.error("[getDashboardMetrics] Failed to fetch dashboard metrics:", error);
    // Return safe defaults on error
    return {
      period: new Date().toISOString().slice(0, 7), // "YYYY-MM"
      outcomes: {
        meetings_booked: 0,
        show_rate: 0,
        meetings_showed: 0,
        deals_created: 0,
        status: "on_track",
      },
      comparison: {
        meetings_vs_last_month: 0,
        meetings_vs_last_month_pct: 0,
        tier_target_low: 5,
        tier_target_high: 15,
      },
      activity: {
        prospects_in_pipeline: 0,
        active_sequences: 0,
        replies_this_month: 0,
        reply_rate: 0,
      },
      campaigns: [],
    };
  }
}
