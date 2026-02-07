/**
 * FILE: frontend/hooks/use-activity-feed.ts
 * PURPOSE: React Query hook for activity feed (P0 - Heartbeat)
 * Phase: Operation Modular Cockpit
 * 
 * Maps backend activity data to human-readable activity feed items.
 * Supports real-time polling for live activity ticker.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useClient } from "./use-client";
import type { Activity, ChannelType, ALSTier } from "@/lib/api/types";

// ============================================
// Types
// ============================================

export type ActivityType =
  | "email_sent"
  | "email_opened"
  | "email_clicked"
  | "email_replied"
  | "linkedin_connection"
  | "linkedin_message"
  | "voice_call"
  | "meeting_booked"
  | "sms_delivered"
  | "sms_replied"
  | "reply"
  | "open"
  | "click"
  | "connect";

export interface ActivityFeedItem {
  id: string;
  type: ActivityType;
  channel: ChannelType;
  leadName: string;
  company: string;
  action: string;
  createdAt: Date;
  tier: ALSTier;
  campaignId?: string;
  campaignName?: string;
  status?: "success" | "failed" | "pending";
}

interface UseActivityFeedOptions {
  /** Maximum number of activities to fetch */
  limit?: number;
  /** Campaign ID to filter by (for tenant isolation) */
  campaignId?: string;
  /** Polling interval in ms (0 = disabled) */
  pollInterval?: number;
  /** Enable/disable the query */
  enabled?: boolean;
}

// ============================================
// API Fetch Function
// ============================================

async function fetchActivity(
  clientId: string,
  limit: number,
  campaignId?: string
): Promise<Activity[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    ...(campaignId && { campaign_id: campaignId }),
  });

  // Note: Backend uses /reports/clients/{id}/activities
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reports/clients/${clientId}/activities?${params}`,
    {
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch activity: ${response.statusText}`);
  }

  const data = await response.json();
  // Handle both array response and paginated response
  return Array.isArray(data) ? data : data.items ?? [];
}

// ============================================
// Transform Functions
// ============================================

/**
 * Map backend action to human-readable ActivityType
 */
function mapActionToType(action: string, channel: ChannelType): ActivityType {
  const actionLower = action.toLowerCase();
  
  if (channel === "email") {
    if (actionLower.includes("sent")) return "email_sent";
    if (actionLower.includes("open")) return "email_opened";
    if (actionLower.includes("click")) return "email_clicked";
    if (actionLower.includes("repl")) return "email_replied";
    return "email_sent";
  }
  
  if (channel === "linkedin") {
    if (actionLower.includes("connect")) return "linkedin_connection";
    if (actionLower.includes("message")) return "linkedin_message";
    return "linkedin_message";
  }
  
  if (channel === "sms") {
    if (actionLower.includes("repl")) return "sms_replied";
    return "sms_delivered";
  }
  
  if (channel === "voice") {
    if (actionLower.includes("meeting") || actionLower.includes("book")) {
      return "meeting_booked";
    }
    return "voice_call";
  }
  
  // Fallback based on action keywords
  if (actionLower.includes("meeting") || actionLower.includes("book")) {
    return "meeting_booked";
  }
  if (actionLower.includes("repl")) return "reply";
  if (actionLower.includes("open")) return "open";
  if (actionLower.includes("click")) return "click";
  if (actionLower.includes("connect")) return "connect";
  
  return "email_sent";
}

/**
 * Generate human-readable action text
 */
function formatActionText(activity: Activity): string {
  const { action, channel } = activity;
  const leadName = activity.lead_name ?? activity.lead?.first_name ?? "Lead";
  const company = activity.lead_company ?? activity.lead?.company ?? "";
  
  const actionLower = action.toLowerCase();
  
  // Check for specific patterns in action or details
  if (actionLower.includes("meeting") || actionLower.includes("book")) {
    return `Meeting booked${company ? ` with ${company}` : ""}`;
  }
  
  if (actionLower.includes("reply") || actionLower.includes("responded")) {
    const preview = activity.content_preview ?? activity.details ?? "";
    return preview ? `Replied: "${preview.slice(0, 50)}..."` : "Sent a reply";
  }
  
  if (actionLower.includes("open")) {
    const subject = activity.subject ?? "";
    return subject ? `Opened email: ${subject}` : "Opened your email";
  }
  
  if (actionLower.includes("click")) {
    return "Clicked link in email";
  }
  
  if (channel === "linkedin") {
    if (actionLower.includes("connect")) {
      return "Accepted connection request";
    }
    return "LinkedIn message sent";
  }
  
  if (channel === "sms") {
    return "SMS delivered";
  }
  
  if (channel === "voice") {
    return "Voice call completed";
  }
  
  // Fallback
  return activity.details ?? action;
}

/**
 * Transform backend Activity to ActivityFeedItem
 */
function transformActivity(activity: Activity): ActivityFeedItem {
  const channel = activity.channel ?? "email";
  const tier = (activity.lead?.als_tier ?? "cool") as ALSTier;
  
  return {
    id: activity.id,
    type: mapActionToType(activity.action, channel),
    channel,
    leadName: activity.lead_name ?? 
              activity.lead?.first_name ?? 
              activity.lead_email?.split("@")[0] ?? 
              "Unknown",
    company: activity.lead_company ?? 
             activity.lead?.company ?? 
             "",
    action: formatActionText(activity),
    createdAt: new Date(activity.created_at),
    tier,
    campaignId: activity.campaign_id,
    campaignName: activity.campaign_name ?? activity.campaign?.name,
    status: "success", // Default to success for completed activities
  };
}

// ============================================
// Hook
// ============================================

/**
 * Hook to fetch and transform activity feed data
 * 
 * @example
 * ```tsx
 * const { activities, isLoading, isLive } = useActivityFeed({ limit: 10 });
 * ```
 */
export function useActivityFeed(options: UseActivityFeedOptions = {}) {
  const {
    limit = 10,
    campaignId,
    pollInterval = 0,
    enabled = true,
  } = options;
  
  const { clientId } = useClient();

  const query = useQuery({
    queryKey: ["activity", clientId, limit, campaignId],
    queryFn: () => fetchActivity(clientId!, limit, campaignId),
    enabled: enabled && !!clientId,
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: pollInterval > 0 ? pollInterval : false,
  });

  // Transform activities
  const activities: ActivityFeedItem[] = (query.data ?? []).map(transformActivity);

  return {
    /** Transformed activity feed items */
    activities,
    /** Raw activity data from API */
    rawActivities: query.data ?? [],
    /** Loading state */
    isLoading: query.isLoading,
    /** Fetching state (includes background refetch) */
    isFetching: query.isFetching,
    /** Error state */
    error: query.error,
    /** Whether the feed is actively polling */
    isLive: pollInterval > 0 && !query.error,
    /** Manually refetch */
    refetch: query.refetch,
  };
}

/**
 * Hook for live activity ticker with auto-polling
 */
export function useLiveActivityFeed(limit = 10, campaignId?: string) {
  return useActivityFeed({
    limit,
    campaignId,
    pollInterval: 30000, // Poll every 30 seconds
    enabled: true,
  });
}

export default useActivityFeed;
