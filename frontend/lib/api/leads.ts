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

// ============================================
// Deep Research API
// ============================================

export interface DeepResearchData {
  lead_id: string;
  status: "not_started" | "in_progress" | "complete" | "failed";
  icebreaker_hook: string | null;
  profile_summary: string | null;
  recent_activity: string | null;
  posts_found: number;
  confidence: number | null;
  run_at: string | null;
  social_posts: {
    id: string;
    source: string;
    content: string;
    date: string | null;
    hook: string | null;
  }[];
  error: string | null;
}

export interface TriggerResearchResponse {
  lead_id: string;
  status: "queued" | "already_complete" | "not_eligible" | "complete" | "failed";
  message: string;
  als_score: number | null;
  als_tier: string | null;
}

export interface ScoreLeadResponse {
  lead_id: string;
  als_score: number;
  als_tier: string;
  als_breakdown: Record<string, number>;
  deep_research_triggered: boolean;
  message: string;
}

/**
 * Get deep research data for a lead
 */
export async function getLeadResearch(
  clientId: string,
  leadId: string
): Promise<DeepResearchData> {
  return api.get<DeepResearchData>(
    `/api/v1/clients/${clientId}/leads/${leadId}/research`
  );
}

/**
 * Trigger deep research for a lead
 */
export async function triggerLeadResearch(
  clientId: string,
  leadId: string,
  force: boolean = false
): Promise<TriggerResearchResponse> {
  const query = force ? "?force=true" : "";
  return api.post<TriggerResearchResponse>(
    `/api/v1/clients/${clientId}/leads/${leadId}/research${query}`
  );
}

/**
 * Score a lead and optionally auto-trigger deep research
 */
export async function scoreLead(
  clientId: string,
  leadId: string,
  autoResearch: boolean = true
): Promise<ScoreLeadResponse> {
  const query = autoResearch ? "" : "?auto_research=false";
  return api.post<ScoreLeadResponse>(
    `/api/v1/clients/${clientId}/leads/${leadId}/score${query}`
  );
}
