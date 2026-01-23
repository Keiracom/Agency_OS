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

export interface LeadCreate {
  email: string;
  campaign_id: UUID;
  phone?: string;
  first_name?: string;
  last_name?: string;
  title?: string;
  company?: string;
  linkedin_url?: string;
}

export interface LeadUpdate {
  email?: string;
  phone?: string;
  first_name?: string;
  last_name?: string;
  title?: string;
  company?: string;
  linkedin_url?: string;
  status?: LeadStatus;
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

  // Activity details (from metadata or API)
  sequence_step?: number | null;
  subject?: string | null;
  content_preview?: string | null;
  intent?: string | null;

  // Admin activity fields
  client_name?: string;
  details?: string;
  timestamp?: string;

  // Client activity feed fields (from /clients/{id}/activities)
  lead_name?: string | null;
  lead_email?: string | null;
  lead_company?: string | null;
  campaign_name?: string | null;

  // Joined data (optional)
  lead?: Lead;
  campaign?: Campaign;
}

// ============================================
// Content Archive (Phase H - Item 46)
// ============================================

export interface ArchiveContentItem {
  id: UUID;
  channel: string;
  action: string;
  timestamp: string;
  // Lead context
  lead_id: UUID;
  lead_name: string | null;
  lead_email: string | null;
  lead_company: string | null;
  // Campaign context
  campaign_id: UUID;
  campaign_name: string | null;
  // Content
  subject: string | null;
  content_preview: string | null;
  full_message_body: string | null;
  links_included: string[] | null;
  personalization_fields_used: string[] | null;
  // Template/AI info
  template_id: UUID | null;
  ai_model_used: string | null;
  // Engagement metrics
  email_opened: boolean;
  email_open_count: number;
  email_clicked: boolean;
  email_click_count: number;
  // Sequence context
  sequence_step: number | null;
  touch_number: number | null;
}

export interface ContentArchiveResponse {
  items: ArchiveContentItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_more: boolean;
}

export interface ContentArchiveFilters {
  page?: number;
  page_size?: number;
  channel?: string;
  action?: string;
  campaign_id?: string;
  search?: string;
  start_date?: string;
  end_date?: string;
}

// ============================================
// Best Of Showcase (Phase H - Item 47)
// ============================================

export interface BestOfContentItem {
  id: UUID;
  channel: string;
  timestamp: string;
  // Lead context
  lead_name: string | null;
  lead_email: string | null;
  lead_company: string | null;
  // Campaign context
  campaign_name: string | null;
  // Content
  subject: string | null;
  content_preview: string | null;
  full_message_body: string | null;
  // Performance metrics
  email_open_count: number;
  email_click_count: number;
  got_reply: boolean;
  got_conversion: boolean;
  // Why it's "best"
  performance_reason: string;
  performance_score: number;
}

export interface BestOfShowcaseResponse {
  items: BestOfContentItem[];
  total_high_performers: number;
  period_days: number;
}

// ============================================
// Dashboard Metrics (Outcome-Focused)
// ============================================

export type OnTrackStatus = "ahead" | "on_track" | "behind";

export interface DashboardOutcomes {
  meetings_booked: number;
  show_rate: number;
  meetings_showed: number;
  deals_created: number;
  status: OnTrackStatus;
}

export interface DashboardComparison {
  meetings_vs_last_month: number;
  meetings_vs_last_month_pct: number;
  tier_target_low: number;
  tier_target_high: number;
}

export interface DashboardActivityMetrics {
  prospects_in_pipeline: number;
  active_sequences: number;
  replies_this_month: number;
  reply_rate: number;
}

export interface DashboardCampaignSummary {
  id: UUID;
  name: string;
  priority_pct: number;
  meetings_booked: number;
  reply_rate: number;
  show_rate: number;
}

export interface DashboardMetricsResponse {
  period: string;
  outcomes: DashboardOutcomes;
  comparison: DashboardComparison;
  activity: DashboardActivityMetrics;
  campaigns: DashboardCampaignSummary[];
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

export interface DailyActivity {
  date: string;
  emails_sent: number;
  sms_sent: number;
  linkedin_sent: number;
  replies_received: number;
  meetings_booked: number;
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

  // Admin dashboard stats
  mrr?: number;
  mrr_change?: number;
  new_clients_this_month?: number;
  leads_today?: number;
  leads_change?: number;
  ai_spend_today?: number;
  ai_spend_limit?: number;
}

export interface SystemHealth {
  api: "healthy" | "degraded" | "down";
  database: "healthy" | "degraded" | "down";
  redis: "healthy" | "degraded" | "down";
  prefect: "healthy" | "degraded" | "down";
  overall: "healthy" | "degraded" | "down";

  // Detailed services array from API
  services: Array<{
    name: string;
    status: "healthy" | "degraded" | "down";
    latency_ms?: number | null;
    message?: string | null;
  }>;
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

  // Admin client fields
  mrr?: number;
  campaigns_count?: number;
  leads_count?: number;
  last_activity?: string | null;
}

export interface AISpendBreakdown {
  today_aud: number;
  month_aud: number;
  by_agent: Record<string, number>;
  by_client: Record<string, number>;
}

// ============================================
// ICP (Ideal Customer Profile)
// ============================================

export interface ICPProfile {
  target_industries: string[];
  target_locations: string[];
  target_company_sizes: string[];
  target_job_titles: string[];
  target_keywords: string[];
  exclusion_keywords: string[];
  value_proposition: string | null;
  messaging_context: string | null;
  last_extracted_at: string | null;
}

// ============================================
// Webhook
// ============================================

export interface WebhookConfig {
  id: UUID;
  client_id: UUID;
  url: string;
  events: string[];
  is_active: boolean;
  secret: string;
  created_at: string;
  updated_at: string;
}
