/**
 * FILE: frontend/lib/api/admin.ts
 * PURPOSE: Admin API fetchers (platform admin only)
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-005
 */

import api from "./index";
import type {
  AdminStats,
  SystemHealth,
  ClientHealth,
  AISpendBreakdown,
  Activity,
  PaginatedResponse,
  PaginationParams,
} from "./types";

/**
 * Get admin dashboard stats
 */
export async function getAdminStats(): Promise<AdminStats> {
  return api.get<AdminStats>("/api/v1/admin/stats");
}

/**
 * Get system health status
 */
export async function getSystemHealth(): Promise<SystemHealth> {
  return api.get<SystemHealth>("/api/v1/admin/system/status");
}

/**
 * Get all clients with health scores
 */
export async function getClients(
  params?: PaginationParams & { search?: string; status?: string }
): Promise<PaginatedResponse<ClientHealth>> {
  const searchParams = new URLSearchParams();

  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString());
  if (params?.search) searchParams.set("search", params.search);
  if (params?.status) searchParams.set("status", params.status);

  const query = searchParams.toString();
  return api.get<PaginatedResponse<ClientHealth>>(
    `/api/v1/admin/clients${query ? `?${query}` : ""}`
  );
}

/**
 * Get single client details (admin view)
 */
export async function getClientDetails(clientId: string): Promise<ClientHealth> {
  return api.get<ClientHealth>(`/api/v1/admin/clients/${clientId}`);
}

/**
 * Get AI spend breakdown
 */
export async function getAISpend(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<AISpendBreakdown> {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set("start_date", params.start_date);
  if (params?.end_date) searchParams.set("end_date", params.end_date);

  const query = searchParams.toString();
  return api.get(`/api/v1/admin/costs/ai${query ? `?${query}` : ""}`);
}

/**
 * Get global activity feed
 */
export async function getGlobalActivity(params?: {
  limit?: number;
}): Promise<Activity[]> {
  const limit = params?.limit || 50;
  return api.get(`/api/v1/admin/activity?limit=${limit}`);
}

/**
 * Get revenue metrics
 */
export async function getRevenueMetrics(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<{
  mrr_aud: number;
  arr_aud: number;
  mrr_growth_percent: number;
  churn_rate_percent: number;
  transactions: Array<{
    id: string;
    client_name: string;
    amount_aud: number;
    type: "payment" | "refund" | "upgrade" | "downgrade";
    created_at: string;
  }>;
}> {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set("start_date", params.start_date);
  if (params?.end_date) searchParams.set("end_date", params.end_date);

  const query = searchParams.toString();
  return api.get(`/api/v1/admin/revenue${query ? `?${query}` : ""}`);
}

/**
 * Get active alerts
 */
export async function getAlerts(): Promise<
  Array<{
    id: string;
    severity: "critical" | "warning" | "info";
    title: string;
    description: string;
    created_at: string;
    acknowledged: boolean;
  }>
> {
  return api.get("/api/v1/admin/alerts");
}

/**
 * Acknowledge an alert
 */
export async function acknowledgeAlert(alertId: string): Promise<void> {
  return api.post(`/api/v1/admin/alerts/${alertId}/acknowledge`);
}

/**
 * Get suppression list
 */
export async function getSuppressionList(params?: PaginationParams & { search?: string }): Promise<
  PaginatedResponse<{
    id: string;
    email: string;
    reason: string;
    source: string;
    created_at: string;
  }>
> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString());
  if (params?.search) searchParams.set("search", params.search);

  const query = searchParams.toString();
  return api.get(`/api/v1/admin/suppression${query ? `?${query}` : ""}`);
}

/**
 * Add email to suppression list
 */
export async function addToSuppressionList(data: {
  email: string;
  reason: string;
}): Promise<void> {
  return api.post("/api/v1/admin/suppression", data);
}

/**
 * Remove from suppression list
 */
export async function removeFromSuppressionList(id: string): Promise<void> {
  return api.delete(`/api/v1/admin/suppression/${id}`);
}
