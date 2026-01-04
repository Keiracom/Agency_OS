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
} from "./types";

/**
 * Get dashboard statistics for a client
 */
export async function getDashboardStats(clientId: string): Promise<DashboardStats> {
  return api.get<DashboardStats>(`/api/v1/clients/${clientId}/reports/dashboard`);
}

/**
 * Get recent activity feed
 */
export async function getActivityFeed(
  clientId: string,
  params?: { limit?: number }
): Promise<Activity[]> {
  const limit = params?.limit || 20;
  return api.get<Activity[]>(`/api/v1/clients/${clientId}/activities?limit=${limit}`);
}

/**
 * Get campaign performance metrics
 */
export async function getCampaignPerformance(
  clientId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<CampaignPerformance[]> {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set("start_date", params.start_date);
  if (params?.end_date) searchParams.set("end_date", params.end_date);

  const query = searchParams.toString();
  return api.get<CampaignPerformance[]>(
    `/api/v1/clients/${clientId}/reports/campaigns${query ? `?${query}` : ""}`
  );
}

/**
 * Get channel metrics
 */
export async function getChannelMetrics(
  clientId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<ChannelMetrics[]> {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set("start_date", params.start_date);
  if (params?.end_date) searchParams.set("end_date", params.end_date);

  const query = searchParams.toString();
  return api.get<ChannelMetrics[]>(
    `/api/v1/clients/${clientId}/reports/channels${query ? `?${query}` : ""}`
  );
}

/**
 * Get ALS tier distribution
 */
export async function getALSDistribution(clientId: string): Promise<ALSDistribution[]> {
  return api.get<ALSDistribution[]>(`/api/v1/clients/${clientId}/reports/als-distribution`);
}

/**
 * Get daily activity summary
 */
export async function getDailyActivity(
  clientId: string,
  params?: { start_date?: string; end_date?: string }
): Promise<DailyActivity[]> {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set("start_date", params.start_date);
  if (params?.end_date) searchParams.set("end_date", params.end_date);

  const query = searchParams.toString();
  return api.get<DailyActivity[]>(
    `/api/v1/clients/${clientId}/reports/daily${query ? `?${query}` : ""}`
  );
}
