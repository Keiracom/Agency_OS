/**
 * FILE: frontend/lib/api/campaigns.ts
 * PURPOSE: Campaign API fetchers
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-004
 */

import api from "./index";
import type {
  Campaign,
  CampaignCreate,
  CampaignUpdate,
  CampaignStatus,
  Lead,
  PaginatedResponse,
  PaginationParams,
  SequenceStep,
  SequenceStepCreate,
  SequenceStepUpdate,
} from "./types";

interface CampaignFilters {
  status?: CampaignStatus;
  search?: string;
}

/**
 * Get paginated list of campaigns
 */
export async function getCampaigns(
  clientId: string,
  params?: PaginationParams & CampaignFilters
): Promise<PaginatedResponse<Campaign>> {
  const searchParams = new URLSearchParams();

  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString());
  if (params?.status) searchParams.set("status", params.status);
  if (params?.search) searchParams.set("search", params.search);

  const query = searchParams.toString();
  return api.get<PaginatedResponse<Campaign>>(
    `/api/v1/clients/${clientId}/campaigns${query ? `?${query}` : ""}`
  );
}

/**
 * Get single campaign by ID
 */
export async function getCampaign(
  clientId: string,
  campaignId: string
): Promise<Campaign> {
  return api.get<Campaign>(`/api/v1/clients/${clientId}/campaigns/${campaignId}`);
}

/**
 * Create new campaign
 */
export async function createCampaign(
  clientId: string,
  data: CampaignCreate
): Promise<Campaign> {
  return api.post<Campaign>(`/api/v1/clients/${clientId}/campaigns`, data);
}

/**
 * Update campaign
 */
export async function updateCampaign(
  clientId: string,
  campaignId: string,
  data: CampaignUpdate
): Promise<Campaign> {
  return api.put<Campaign>(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}`,
    data
  );
}

/**
 * Update campaign status
 */
export async function updateCampaignStatus(
  clientId: string,
  campaignId: string,
  status: CampaignStatus
): Promise<Campaign> {
  return api.patch<Campaign>(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}/status`,
    { status }
  );
}

/**
 * Activate campaign
 */
export async function activateCampaign(
  clientId: string,
  campaignId: string
): Promise<Campaign> {
  return api.post<Campaign>(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}/activate`
  );
}

/**
 * Pause campaign
 */
export async function pauseCampaign(
  clientId: string,
  campaignId: string
): Promise<Campaign> {
  return api.post<Campaign>(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}/pause`
  );
}

// ============================================
// Phase H, Item 43: Emergency Pause
// ============================================

export interface EmergencyPauseResponse {
  paused: boolean;
  paused_at: string | null;
  pause_reason: string | null;
  campaigns_affected: number;
}

/**
 * Emergency pause ALL outreach for a client
 * This is the "big red button" that immediately stops all automated outreach
 */
export async function emergencyPauseAll(
  clientId: string,
  reason?: string
): Promise<EmergencyPauseResponse> {
  return api.post<EmergencyPauseResponse>(
    `/api/v1/clients/${clientId}/pause-all`,
    { reason }
  );
}

/**
 * Resume all outreach after emergency pause
 * Clears client-level pause. Campaigns remain paused and must be individually reactivated.
 */
export async function resumeAllOutreach(
  clientId: string
): Promise<EmergencyPauseResponse> {
  return api.post<EmergencyPauseResponse>(
    `/api/v1/clients/${clientId}/resume-all`
  );
}

/**
 * Delete campaign (soft delete)
 */
export async function deleteCampaign(
  clientId: string,
  campaignId: string
): Promise<void> {
  return api.delete(`/api/v1/clients/${clientId}/campaigns/${campaignId}`);
}

/**
 * Get leads for a campaign
 */
export async function getCampaignLeads(
  clientId: string,
  campaignId: string,
  params?: PaginationParams
): Promise<PaginatedResponse<Lead>> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString());

  const query = searchParams.toString();
  return api.get<PaginatedResponse<Lead>>(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}/leads${query ? `?${query}` : ""}`
  );
}

// ============================================
// Phase I, Item 56: Sequence Steps
// ============================================

/**
 * Get campaign sequences
 */
export async function getCampaignSequences(
  clientId: string,
  campaignId: string
): Promise<SequenceStep[]> {
  return api.get<SequenceStep[]>(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}/sequences`
  );
}

/**
 * Create a sequence step
 */
export async function createSequenceStep(
  clientId: string,
  campaignId: string,
  data: SequenceStepCreate
): Promise<SequenceStep> {
  return api.post<SequenceStep>(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}/sequences`,
    data
  );
}

/**
 * Update a sequence step
 */
export async function updateSequenceStep(
  clientId: string,
  campaignId: string,
  stepNumber: number,
  data: SequenceStepUpdate
): Promise<SequenceStep> {
  return api.put<SequenceStep>(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}/sequences/${stepNumber}`,
    data
  );
}

/**
 * Delete a sequence step
 */
export async function deleteSequenceStep(
  clientId: string,
  campaignId: string,
  stepNumber: number
): Promise<void> {
  return api.delete(
    `/api/v1/clients/${clientId}/campaigns/${campaignId}/sequences/${stepNumber}`
  );
}

// ============================================
// Phase I, Item 51: Campaign Allocation
// ============================================

export interface CampaignAllocation {
  campaign_id: string;
  priority_pct: number;
}

export interface AllocateCampaignsRequest {
  allocations: CampaignAllocation[];
}

export interface AllocateCampaignsResponse {
  status: string;
  message: string;
  allocations: {
    campaign_id: string;
    campaign_name: string;
    old_priority_pct: number;
    new_priority_pct: number;
  }[];
}

/**
 * Allocate priority percentages across campaigns
 *
 * Updates lead_allocation_pct on each campaign and triggers
 * pool population flow in the background.
 *
 * Validation:
 * - Percentages must sum to 100%
 * - Each campaign: minimum 10%, maximum 80%
 */
export async function allocateCampaigns(
  clientId: string,
  allocations: CampaignAllocation[]
): Promise<AllocateCampaignsResponse> {
  return api.post<AllocateCampaignsResponse>(
    `/api/v1/clients/${clientId}/campaigns/allocate`,
    { allocations }
  );
}
