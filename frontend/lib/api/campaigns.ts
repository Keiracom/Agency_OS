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

/**
 * Get campaign sequences
 */
export async function getCampaignSequences(
  clientId: string,
  campaignId: string
): Promise<unknown[]> {
  return api.get(`/api/v1/clients/${clientId}/campaigns/${campaignId}/sequences`);
}
