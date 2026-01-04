# SKILL.md — Frontend-Backend Connection

**Skill:** Connect Next.js Frontend to FastAPI Backend  
**Author:** CTO (Claude)  
**Version:** 1.0  
**Created:** December 27, 2025  
**Phase:** 13

---

## Purpose

Replace all mock/hardcoded data in the Next.js frontend with real API calls to the FastAPI backend. Currently, many dashboard pages display static mock data. This phase connects them to live endpoints.

---

## Prerequisites

- Phase 10 (Deployment) ✅ Complete
- Phase 11 (ICP Discovery) ✅ Complete  
- Phase 12A (Campaign Generation) ✅ Complete
- Backend deployed and accessible at `NEXT_PUBLIC_API_URL`
- Supabase Auth working (login/logout functional)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vercel)                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
│  │   Pages     │   │   Hooks     │   │   lib/api   │        │
│  │ (use hooks) │──▶│ (useQuery)  │──▶│ (fetchers)  │        │
│  └─────────────┘   └─────────────┘   └──────┬──────┘        │
└──────────────────────────────────────────────┼──────────────┘
                                               │
                                               ▼ HTTP + JWT
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Railway)                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
│  │   Routes    │──▶│   Engines   │──▶│  Supabase   │        │
│  └─────────────┘   └─────────────┘   └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Data Fetching | TanStack Query (React Query) v5 | Already installed |
| HTTP Client | Native fetch | With auth headers |
| State | React Query cache | No Redux needed |
| Auth | Supabase Auth | JWT in headers |
| Toast | `@/hooks/use-toast` | Already exists |

---

## File Structure (New Files to Create)

```
frontend/
├── lib/
│   ├── api/
│   │   ├── index.ts           # API client setup + auth
│   │   ├── campaigns.ts       # Campaign API functions
│   │   ├── leads.ts           # Lead API functions
│   │   ├── reports.ts         # Report API functions
│   │   ├── admin.ts           # Admin API functions
│   │   └── types.ts           # Shared API types
│   └── supabase.ts            # Already exists
├── hooks/
│   ├── use-toast.ts           # Already exists
│   ├── use-campaigns.ts       # Campaign hooks
│   ├── use-leads.ts           # Lead hooks
│   ├── use-reports.ts         # Report hooks
│   ├── use-admin.ts           # Admin hooks
│   └── use-client.ts          # Client context hook
└── providers/
    └── query-provider.tsx     # React Query provider (may exist)
```

---

## Required Files (Phase 13)

| Task ID | File | Purpose |
|---------|------|---------|
| FBC-001 | `frontend/lib/api/index.ts` | API client with auth |
| FBC-001 | `frontend/lib/api/types.ts` | Shared TypeScript types |
| FBC-001 | `frontend/hooks/use-client.ts` | Client context hook |
| FBC-002 | `frontend/lib/api/campaigns.ts` | Campaign API fetchers |
| FBC-002 | `frontend/hooks/use-campaigns.ts` | Campaign React Query hooks |
| FBC-003 | `frontend/lib/api/leads.ts` | Lead API fetchers |
| FBC-003 | `frontend/hooks/use-leads.ts` | Lead React Query hooks |
| FBC-004 | `frontend/lib/api/reports.ts` | Report API fetchers |
| FBC-004 | `frontend/hooks/use-reports.ts` | Report React Query hooks |
| FBC-005 | `frontend/lib/api/admin.ts` | Admin API fetchers |
| FBC-005 | `frontend/hooks/use-admin.ts` | Admin React Query hooks |
| FBC-006 | Page updates | Connect pages to hooks |
| FBC-007 | Error/loading states | Consistent UX patterns |

---

## Implementation Order

```
1. FBC-001: API Foundation (api client, types, client hook)
2. FBC-002: Dashboard Home (stats, activity feed)
3. FBC-003: Leads Pages (list, detail)
4. FBC-004: Campaigns Pages (list, detail, create)
5. FBC-005: Reports Page
6. FBC-006: Admin Dashboard (if time permits)
7. FBC-007: Polish (error boundaries, loading skeletons)
```

---

## Task 1: API Foundation (FBC-001)

### File: `frontend/lib/api/index.ts`

```typescript
/**
 * FILE: frontend/lib/api/index.ts
 * PURPOSE: Centralized API client with authentication
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-001
 */

import { createBrowserClient } from "@/lib/supabase";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = "APIError";
  }
}

/**
 * Get the current user's JWT token from Supabase
 */
async function getAuthToken(): Promise<string | null> {
  const supabase = createBrowserClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || null;
}

/**
 * Make an authenticated API request
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAuthToken();
  
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    throw new APIError(response.status, response.statusText, errorData);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

/**
 * Convenience methods
 */
export const api = {
  get: <T>(endpoint: string) => apiRequest<T>(endpoint, { method: "GET" }),
  
  post: <T>(endpoint: string, data?: unknown) =>
    apiRequest<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),
  
  put: <T>(endpoint: string, data?: unknown) =>
    apiRequest<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    }),
  
  patch: <T>(endpoint: string, data?: unknown) =>
    apiRequest<T>(endpoint, {
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    }),
  
  delete: <T>(endpoint: string) => apiRequest<T>(endpoint, { method: "DELETE" }),
};

export default api;
```

### File: `frontend/lib/api/types.ts`

```typescript
/**
 * FILE: frontend/lib/api/types.ts
 * PURPOSE: Shared TypeScript types matching backend Pydantic models
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-001
 */

// ============================================
// Common Types
// ============================================

export type UUID = string;

export type TierType = "ignition" | "velocity" | "dominance";
export type SubscriptionStatus = "trialing" | "active" | "past_due" | "cancelled" | "paused";
export type MembershipRole = "owner" | "admin" | "member" | "viewer";
export type PermissionMode = "autopilot" | "co_pilot" | "manual";
export type CampaignStatus = "draft" | "active" | "paused" | "completed";
export type LeadStatus = "new" | "enriched" | "scored" | "in_sequence" | "converted" | "unsubscribed" | "bounced";
export type ChannelType = "email" | "sms" | "linkedin" | "voice" | "mail";
export type ALSTier = "hot" | "warm" | "cool" | "cold" | "dead";

// ============================================
// Pagination
// ============================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

// ============================================
// Client
// ============================================

export interface Client {
  id: UUID;
  name: string;
  tier: TierType;
  subscription_status: SubscriptionStatus;
  credits_remaining: number;
  default_permission_mode: PermissionMode;
  created_at: string;
  updated_at: string;
}

// ============================================
// Campaign
// ============================================

export interface Campaign {
  id: UUID;
  client_id: UUID;
  name: string;
  description: string | null;
  status: CampaignStatus;
  permission_mode: PermissionMode | null;
  
  // Allocations
  allocation_email: number;
  allocation_sms: number;
  allocation_linkedin: number;
  allocation_voice: number;
  allocation_mail: number;
  
  // Scheduling
  daily_limit: number;
  start_date: string | null;
  end_date: string | null;
  
  // Metrics
  total_leads: number;
  leads_contacted: number;
  leads_replied: number;
  leads_converted: number;
  reply_rate: number;
  conversion_rate: number;
  
  created_at: string;
  updated_at: string;
}

export interface CampaignCreate {
  name: string;
  description?: string;
  permission_mode?: PermissionMode;
}

export interface CampaignUpdate {
  name?: string;
  description?: string;
  permission_mode?: PermissionMode;
  status?: CampaignStatus;
}

// ============================================
// Lead
// ============================================

export interface Lead {
  id: UUID;
  client_id: UUID;
  campaign_id: UUID;
  email: string;
  phone: string | null;
  first_name: string | null;
  last_name: string | null;
  title: string | null;
  company: string | null;
  linkedin_url: string | null;
  domain: string | null;
  
  // ALS Score
  als_score: number | null;
  als_tier: ALSTier | null;
  als_data_quality: number | null;
  als_authority: number | null;
  als_company_fit: number | null;
  als_timing: number | null;
  als_risk: number | null;
  
  // Organization
  organization_industry: string | null;
  organization_employee_count: number | null;
  organization_country: string | null;
  
  status: LeadStatus;
  created_at: string;
  updated_at: string;
}

export interface LeadFilters {
  campaign_id?: UUID;
  status?: LeadStatus;
  tier?: ALSTier;
  search?: string;
}

// ============================================
// Activity
// ============================================

export interface Activity {
  id: UUID;
  client_id: UUID;
  campaign_id: UUID;
  lead_id: UUID;
  channel: ChannelType;
  action: string;
  provider_message_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  
  // Joined data (optional)
  lead?: Lead;
  campaign?: Campaign;
}

// ============================================
// Reports
// ============================================

export interface DashboardStats {
  total_leads: number;
  leads_contacted: number;
  leads_replied: number;
  leads_converted: number;
  active_campaigns: number;
  credits_remaining: number;
  reply_rate: number;
  conversion_rate: number;
}

export interface CampaignPerformance {
  campaign_id: UUID;
  campaign_name: string;
  status: CampaignStatus;
  total_leads: number;
  contacted: number;
  replied: number;
  converted: number;
  reply_rate: number;
  conversion_rate: number;
}

export interface ChannelMetrics {
  channel: ChannelType;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  delivery_rate: number;
  open_rate: number;
  click_rate: number;
  reply_rate: number;
}

export interface ALSDistribution {
  tier: ALSTier;
  count: number;
  percentage: number;
}

// ============================================
// Admin
// ============================================

export interface AdminStats {
  total_clients: number;
  active_clients: number;
  mrr_aud: number;
  arr_aud: number;
  total_campaigns: number;
  active_campaigns: number;
  total_leads: number;
  leads_this_month: number;
  ai_spend_today_aud: number;
  ai_spend_month_aud: number;
}

export interface SystemHealth {
  api: "healthy" | "degraded" | "down";
  database: "healthy" | "degraded" | "down";
  redis: "healthy" | "degraded" | "down";
  prefect: "healthy" | "degraded" | "down";
  overall: "healthy" | "degraded" | "down";
}

export interface ClientHealth {
  id: UUID;
  name: string;
  tier: TierType;
  subscription_status: SubscriptionStatus;
  health_score: number; // 0-100
  active_campaigns: number;
  total_leads: number;
  last_activity_at: string | null;
}
```

### File: `frontend/hooks/use-client.ts`

```typescript
/**
 * FILE: frontend/hooks/use-client.ts
 * PURPOSE: Hook to get current client context
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-001
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { createBrowserClient } from "@/lib/supabase";
import api from "@/lib/api";
import type { Client } from "@/lib/api/types";

interface ClientWithMembership {
  client: Client;
  role: "owner" | "admin" | "member" | "viewer";
}

/**
 * Fetch the current user's primary client
 */
async function fetchCurrentClient(): Promise<ClientWithMembership | null> {
  const supabase = createBrowserClient();
  const { data: { user } } = await supabase.auth.getUser();
  
  if (!user) return null;
  
  // Get user's primary membership (first accepted membership)
  const { data: membership } = await supabase
    .from("memberships")
    .select(`
      role,
      client_id,
      clients (*)
    `)
    .eq("user_id", user.id)
    .not("accepted_at", "is", null)
    .order("created_at", { ascending: true })
    .limit(1)
    .single();
  
  if (!membership || !membership.clients) return null;
  
  return {
    client: membership.clients as unknown as Client,
    role: membership.role,
  };
}

/**
 * Hook to get current client context
 * 
 * Usage:
 * ```tsx
 * const { client, role, isLoading } = useClient();
 * if (client) {
 *   console.log(client.id, client.name);
 * }
 * ```
 */
export function useClient() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["current-client"],
    queryFn: fetchCurrentClient,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  return {
    client: data?.client || null,
    clientId: data?.client?.id || null,
    role: data?.role || null,
    isLoading,
    error,
    refetch,
    
    // Role checks
    isOwner: data?.role === "owner",
    isAdmin: data?.role === "owner" || data?.role === "admin",
    isMember: data?.role !== "viewer",
  };
}
```

---

## Task 2: Dashboard Home (FBC-002)

### File: `frontend/lib/api/reports.ts`

```typescript
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
  PaginatedResponse,
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
```

### File: `frontend/hooks/use-reports.ts`

```typescript
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
  getActivityFeed,
  getCampaignPerformance,
  getChannelMetrics,
  getALSDistribution,
} from "@/lib/api/reports";

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
```

---

## Task 3: Leads Pages (FBC-003)

### File: `frontend/lib/api/leads.ts`

```typescript
/**
 * FILE: frontend/lib/api/leads.ts
 * PURPOSE: Lead API fetchers
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-003
 */

import api from "./index";
import type {
  Lead,
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
export async function enrichLead(
  clientId: string,
  leadId: string
): Promise<Lead> {
  return api.post<Lead>(`/api/v1/clients/${clientId}/leads/${leadId}/enrich`);
}

/**
 * Update lead
 */
export async function updateLead(
  clientId: string,
  leadId: string,
  data: Partial<Lead>
): Promise<Lead> {
  return api.put<Lead>(`/api/v1/clients/${clientId}/leads/${leadId}`, data);
}

/**
 * Delete lead (soft delete)
 */
export async function deleteLead(
  clientId: string,
  leadId: string
): Promise<void> {
  return api.delete(`/api/v1/clients/${clientId}/leads/${leadId}`);
}
```

### File: `frontend/hooks/use-leads.ts`

```typescript
/**
 * FILE: frontend/hooks/use-leads.ts
 * PURPOSE: React Query hooks for leads
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-003
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useClient } from "./use-client";
import {
  getLeads,
  getLead,
  getLeadActivities,
  enrichLead,
  updateLead,
  deleteLead,
} from "@/lib/api/leads";
import type { Lead, LeadFilters, PaginationParams } from "@/lib/api/types";

/**
 * Hook to fetch paginated leads list
 */
export function useLeads(params?: PaginationParams & LeadFilters) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["leads", clientId, params],
    queryFn: () => getLeads(clientId!, params),
    enabled: !!clientId,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch single lead
 */
export function useLead(leadId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["lead", clientId, leadId],
    queryFn: () => getLead(clientId!, leadId!),
    enabled: !!clientId && !!leadId,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch lead activities (timeline)
 */
export function useLeadActivities(leadId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["lead-activities", clientId, leadId],
    queryFn: () => getLeadActivities(clientId!, leadId!),
    enabled: !!clientId && !!leadId,
    staleTime: 10 * 1000, // 10 seconds
  });
}

/**
 * Hook to enrich a lead
 */
export function useEnrichLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (leadId: string) => enrichLead(clientId!, leadId),
    onSuccess: (data, leadId) => {
      // Update the lead in cache
      queryClient.setQueryData(["lead", clientId, leadId], data);
      // Invalidate leads list
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
    },
  });
}

/**
 * Hook to update a lead
 */
export function useUpdateLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ leadId, data }: { leadId: string; data: Partial<Lead> }) =>
      updateLead(clientId!, leadId, data),
    onSuccess: (data, { leadId }) => {
      queryClient.setQueryData(["lead", clientId, leadId], data);
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
    },
  });
}

/**
 * Hook to delete a lead
 */
export function useDeleteLead() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (leadId: string) => deleteLead(clientId!, leadId),
    onSuccess: (_, leadId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: ["lead", clientId, leadId] });
      // Invalidate leads list
      queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
    },
  });
}
```

---

## Task 4: Campaigns Pages (FBC-004)

### File: `frontend/lib/api/campaigns.ts`

```typescript
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
```

### File: `frontend/hooks/use-campaigns.ts`

```typescript
/**
 * FILE: frontend/hooks/use-campaigns.ts
 * PURPOSE: React Query hooks for campaigns
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-004
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useClient } from "./use-client";
import {
  getCampaigns,
  getCampaign,
  createCampaign,
  updateCampaign,
  updateCampaignStatus,
  activateCampaign,
  pauseCampaign,
  deleteCampaign,
} from "@/lib/api/campaigns";
import type {
  Campaign,
  CampaignCreate,
  CampaignUpdate,
  CampaignStatus,
  PaginationParams,
} from "@/lib/api/types";

interface CampaignFilters {
  status?: CampaignStatus;
  search?: string;
}

/**
 * Hook to fetch paginated campaigns list
 */
export function useCampaigns(params?: PaginationParams & CampaignFilters) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["campaigns", clientId, params],
    queryFn: () => getCampaigns(clientId!, params),
    enabled: !!clientId,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch single campaign
 */
export function useCampaign(campaignId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["campaign", clientId, campaignId],
    queryFn: () => getCampaign(clientId!, campaignId!),
    enabled: !!clientId && !!campaignId,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to create a campaign
 */
export function useCreateCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CampaignCreate) => createCampaign(clientId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
    },
  });
}

/**
 * Hook to update a campaign
 */
export function useUpdateCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      campaignId,
      data,
    }: {
      campaignId: string;
      data: CampaignUpdate;
    }) => updateCampaign(clientId!, campaignId, data),
    onSuccess: (data, { campaignId }) => {
      queryClient.setQueryData(["campaign", clientId, campaignId], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
    },
  });
}

/**
 * Hook to activate a campaign
 */
export function useActivateCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaignId: string) => activateCampaign(clientId!, campaignId),
    onSuccess: (data, campaignId) => {
      queryClient.setQueryData(["campaign", clientId, campaignId], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
    },
  });
}

/**
 * Hook to pause a campaign
 */
export function usePauseCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaignId: string) => pauseCampaign(clientId!, campaignId),
    onSuccess: (data, campaignId) => {
      queryClient.setQueryData(["campaign", clientId, campaignId], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
    },
  });
}

/**
 * Hook to delete a campaign
 */
export function useDeleteCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaignId: string) => deleteCampaign(clientId!, campaignId),
    onSuccess: (_, campaignId) => {
      queryClient.removeQueries({ queryKey: ["campaign", clientId, campaignId] });
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
    },
  });
}
```

---

## Task 5: Reports Page (FBC-005)

Reports hooks already created in FBC-002. This task updates the Reports page to use them.

### Page Update Pattern

For each page that needs updating, follow this pattern:

```typescript
// BEFORE (mock data)
const stats = {
  total_leads: 1250,
  reply_rate: 12.5,
  // ...hardcoded
};

// AFTER (real data)
const { data: stats, isLoading, error } = useDashboardStats();

if (isLoading) return <LoadingSkeleton />;
if (error) return <ErrorState error={error} />;
if (!stats) return <EmptyState />;

// Use stats.total_leads, stats.reply_rate, etc.
```

---

## Task 6: Admin Dashboard (FBC-006)

### File: `frontend/lib/api/admin.ts`

```typescript
/**
 * FILE: frontend/lib/api/admin.ts
 * PURPOSE: Admin API fetchers (platform admin only)
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-006
 */

import api from "./index";
import type {
  AdminStats,
  SystemHealth,
  ClientHealth,
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
 * Get AI spend breakdown
 */
export async function getAISpend(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<{
  today_aud: number;
  month_aud: number;
  by_agent: Record<string, number>;
  by_client: Record<string, number>;
}> {
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
}): Promise<unknown[]> {
  const limit = params?.limit || 50;
  return api.get(`/api/v1/admin/activity?limit=${limit}`);
}
```

### File: `frontend/hooks/use-admin.ts`

```typescript
/**
 * FILE: frontend/hooks/use-admin.ts
 * PURPOSE: React Query hooks for admin dashboard
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-006
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getAdminStats,
  getSystemHealth,
  getClients,
  getAISpend,
  getGlobalActivity,
} from "@/lib/api/admin";
import type { PaginationParams } from "@/lib/api/types";

/**
 * Hook to fetch admin dashboard stats
 */
export function useAdminStats() {
  return useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to fetch system health
 */
export function useSystemHealth() {
  return useQuery({
    queryKey: ["system-health"],
    queryFn: getSystemHealth,
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch clients list
 */
export function useAdminClients(
  params?: PaginationParams & { search?: string; status?: string }
) {
  return useQuery({
    queryKey: ["admin-clients", params],
    queryFn: () => getClients(params),
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch AI spend
 */
export function useAISpend(params?: {
  startDate?: string;
  endDate?: string;
}) {
  return useQuery({
    queryKey: ["ai-spend", params],
    queryFn: () =>
      getAISpend({
        start_date: params?.startDate,
        end_date: params?.endDate,
      }),
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to fetch global activity
 */
export function useGlobalActivity(limit = 50) {
  return useQuery({
    queryKey: ["global-activity", limit],
    queryFn: () => getGlobalActivity({ limit }),
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 30 * 1000, // 30 seconds
  });
}
```

---

## Task 7: Error/Loading States (FBC-007)

### Shared Components to Create

```typescript
// frontend/components/ui/loading-skeleton.tsx
export function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-8 bg-muted rounded w-1/3" />
      <div className="h-32 bg-muted rounded" />
      <div className="h-32 bg-muted rounded" />
    </div>
  );
}

// frontend/components/ui/error-state.tsx
export function ErrorState({ 
  error, 
  onRetry 
}: { 
  error: Error; 
  onRetry?: () => void;
}) {
  return (
    <Card className="border-destructive">
      <CardContent className="p-6 text-center">
        <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
        <h3 className="text-lg font-semibold mb-2">Something went wrong</h3>
        <p className="text-muted-foreground mb-4">{error.message}</p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline">
            Try Again
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// frontend/components/ui/empty-state.tsx
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="text-center py-12">
      {Icon && <Icon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />}
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      {description && (
        <p className="text-muted-foreground mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}
```

---

## Pages to Update

### High Priority (Must Update)

| Page | File | Current State | Target State |
|------|------|---------------|--------------|
| Dashboard Home | `app/dashboard/page.tsx` | Mock stats | `useDashboardStats()` + `useActivityFeed()` |
| Campaigns List | `app/dashboard/campaigns/page.tsx` | Mock list | `useCampaigns()` |
| Campaign Detail | `app/dashboard/campaigns/[id]/page.tsx` | Mock data | `useCampaign(id)` |
| Leads List | `app/dashboard/leads/page.tsx` | Mock list | `useLeads()` |
| Lead Detail | `app/dashboard/leads/[id]/page.tsx` | Mock data | `useLead(id)` + `useLeadActivities(id)` |
| Reports | `app/dashboard/reports/page.tsx` | Mock charts | `useChannelMetrics()` + `useCampaignPerformance()` |

### Medium Priority (Admin)

| Page | File | Current State | Target State |
|------|------|---------------|--------------|
| Admin Command Center | `app/admin/page.tsx` | Mock KPIs | `useAdminStats()` + `useSystemHealth()` |
| Admin Clients | `app/admin/clients/page.tsx` | Mock list | `useAdminClients()` |
| Admin Costs | `app/admin/costs/page.tsx` | Mock data | `useAISpend()` |

---

## API Endpoint Mapping

| Frontend Hook | Backend Endpoint | Method |
|---------------|------------------|--------|
| `useDashboardStats()` | `/api/v1/clients/{id}/reports/dashboard` | GET |
| `useActivityFeed()` | `/api/v1/clients/{id}/activities` | GET |
| `useCampaigns()` | `/api/v1/clients/{id}/campaigns` | GET |
| `useCampaign(id)` | `/api/v1/clients/{id}/campaigns/{id}` | GET |
| `useCreateCampaign()` | `/api/v1/clients/{id}/campaigns` | POST |
| `useLeads()` | `/api/v1/clients/{id}/leads` | GET |
| `useLead(id)` | `/api/v1/clients/{id}/leads/{id}` | GET |
| `useLeadActivities(id)` | `/api/v1/clients/{id}/leads/{id}/activities` | GET |
| `useChannelMetrics()` | `/api/v1/clients/{id}/reports/channels` | GET |
| `useAdminStats()` | `/api/v1/admin/stats` | GET |
| `useSystemHealth()` | `/api/v1/admin/system/status` | GET |

---

## Environment Variables Required

```env
# Frontend (.env.local or Vercel)
NEXT_PUBLIC_API_URL=https://agency-os-production.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

---

## Testing Checklist

For each connected page, verify:

- [ ] Loading state shows skeleton/spinner
- [ ] Error state shows message + retry button
- [ ] Empty state shows appropriate message
- [ ] Data displays correctly when loaded
- [ ] Mutations (create/update/delete) work
- [ ] Cache invalidates after mutations
- [ ] Toast notifications show on success/error
- [ ] Pagination works (if applicable)
- [ ] Filters work (if applicable)
- [ ] Refresh button fetches fresh data

---

## QA Checks (Specific to Phase 13)

| Check | Severity | Pattern |
|-------|----------|---------|
| Uses `useClient()` for clientId | CRITICAL | No hardcoded client IDs |
| Handles loading state | HIGH | `isLoading` check |
| Handles error state | HIGH | `error` check |
| Uses React Query | HIGH | `useQuery` / `useMutation` |
| Invalidates cache on mutation | MEDIUM | `queryClient.invalidateQueries` |
| Shows toast on error | MEDIUM | `toast({ variant: "destructive" })` |
| No `fetch()` in components | MEDIUM | Use hooks only |

---

## Success Criteria

### Phase 13 Complete When:

- [ ] All 7 tasks marked 🟢 in PROGRESS.md
- [ ] API client (`lib/api/index.ts`) handles auth + errors
- [ ] All hooks created and exported
- [ ] Dashboard home shows real stats + activity
- [ ] Leads list/detail shows real data
- [ ] Campaigns list/detail shows real data
- [ ] Reports page shows real metrics
- [ ] Admin dashboard shows real stats (if enabled)
- [ ] No mock data in production pages
- [ ] Error boundaries catch failures gracefully

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Token expired | Refresh page (Supabase handles refresh) |
| 403 Forbidden | Wrong client ID | Check `useClient()` returns correct client |
| CORS errors | Backend config | Add frontend URL to allowed origins |
| Data not updating | Stale cache | Reduce `staleTime` or call `refetch()` |
| Infinite loading | Query never enabled | Check `enabled: !!clientId` |

---

## Dependencies to Install (if missing)

```bash
cd frontend
npm install @tanstack/react-query
```

Note: React Query should already be installed based on existing code patterns.

---

**END OF FRONTEND-BACKEND SKILL**
