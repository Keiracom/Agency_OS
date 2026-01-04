/**
 * FILE: frontend/lib/api/leads.ts
 * PURPOSE: Lead API fetchers
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-003
 */

import api from "./index";
import type {
  Lead,
  LeadCreate,
  LeadUpdate,
  LeadFilters,
  Activity,
  PaginatedResponse,
  PaginationParams,
} from "./types";

/**
 * Get paginated list of leads
 */
export async function getLeads(
  clientId: string,
  params?: PaginationParams & LeadFilters
): Promise<PaginatedResponse<Lead>> {
  const searchParams = new URLSearchParams();

  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString());
  if (params?.campaign_id) searchParams.set("campaign_id", params.campaign_id);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.tier) searchParams.set("tier", params.tier);
  if (params?.search) searchParams.set("search", params.search);

  const query = searchParams.toString();
  return api.get<PaginatedResponse<Lead>>(
    `/api/v1/clients/${clientId}/leads${query ? `?${query}` : ""}`
  );
}

/**
 * Get single lead by ID
 */
export async function getLead(clientId: string, leadId: string): Promise<Lead> {
  return api.get<Lead>(`/api/v1/clients/${clientId}/leads/${leadId}`);
}

/**
 * Create a new lead
 */
export async function createLead(clientId: string, data: LeadCreate): Promise<Lead> {
  return api.post<Lead>(`/api/v1/clients/${clientId}/leads`, data);
}

/**
 * Bulk create leads
 */
export async function createLeadsBulk(
  clientId: string,
  leads: LeadCreate[]
): Promise<{ created: number; skipped: number; total: number }> {
  return api.post(`/api/v1/clients/${clientId}/leads/bulk`, { leads });
}

/**
 * Update a lead
 */
export async function updateLead(
  clientId: string,
  leadId: string,
  data: LeadUpdate
): Promise<Lead> {
  return api.put<Lead>(`/api/v1/clients/${clientId}/leads/${leadId}`, data);
}

/**
 * Delete lead (soft delete)
 */
export async function deleteLead(clientId: string, leadId: string): Promise<void> {
  return api.delete(`/api/v1/clients/${clientId}/leads/${leadId}`);
}

/**
 * Get lead activities (timeline)
 */
export async function getLeadActivities(
  clientId: string,
  leadId: string
): Promise<Activity[]> {
  return api.get<Activity[]>(`/api/v1/clients/${clientId}/leads/${leadId}/activities`);
}

/**
 * Trigger lead enrichment
 */
export async function enrichLead(clientId: string, leadId: string): Promise<Lead> {
  return api.post<Lead>(`/api/v1/clients/${clientId}/leads/${leadId}/enrich`);
}

/**
 * Bulk enrich leads
 */
export async function enrichLeadsBulk(
  clientId: string,
  leadIds: string[]
): Promise<{ queued: number }> {
  return api.post(`/api/v1/clients/${clientId}/leads/bulk-enrich`, { lead_ids: leadIds });
}
