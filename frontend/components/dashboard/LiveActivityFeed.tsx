"use client";

/**
 * LiveActivityFeed.tsx - Real-time Activity Feed Component
 * Phase H - Item 45: Live Activity Feed
 *
 * Wrapper component that fetches real activity data and transforms it
 * for the ActivityTicker component. Shows actual client activities
 * from the backend API.
 */

import { useMemo } from "react";
import { useActivityFeed } from "@/hooks/use-reports";
import { ActivityTicker } from "./ActivityTicker";
import type { Activity as APIActivity } from "@/lib/api/types";

// ActivityTicker's internal Activity type
interface TickerActivity {
  id: string;
  type:
    | "email_sent"
    | "email_opened"
    | "email_clicked"
    | "email_replied"
    | "linkedin_connection"
    | "linkedin_message"
    | "voice_call"
    | "meeting_booked"
    | "sms_delivered"
    | "sms_replied";
  message: string;
  timestamp: Date;
  status?: "success" | "failed" | "pending";
}

interface LiveActivityFeedProps {
  speed?: "slow" | "normal" | "fast";
  direction?: "up" | "down";
  showTimestamp?: boolean;
  maxVisible?: number;
  limit?: number;
}

/**
 * Transform backend channel + action into ActivityTicker type
 */
function mapToTickerType(
  channel: string,
  action: string
): TickerActivity["type"] {
  const channelLower = channel.toLowerCase();
  const actionLower = action.toLowerCase();

  if (channelLower === "email") {
    if (actionLower === "sent" || actionLower === "delivered")
      return "email_sent";
    if (actionLower === "opened") return "email_opened";
    if (actionLower === "clicked") return "email_clicked";
    if (actionLower === "replied") return "email_replied";
    return "email_sent";
  }

  if (channelLower === "linkedin") {
    if (actionLower === "accepted" || actionLower === "connected")
      return "linkedin_connection";
    return "linkedin_message";
  }

  if (channelLower === "voice") {
    if (actionLower === "converted" || actionLower === "meeting_booked")
      return "meeting_booked";
    return "voice_call";
  }

  if (channelLower === "sms") {
    if (actionLower === "replied") return "sms_replied";
    return "sms_delivered";
  }

  // Default fallback
  return "email_sent";
}

/**
 * Build a human-readable message from activity data
 */
function buildActivityMessage(activity: APIActivity): string {
  const name = activity.lead_name || activity.lead_email || "Unknown contact";
  const company = activity.lead_company;
  const subject = activity.subject;
  const action = activity.action.toLowerCase();
  const channel = activity.channel.toLowerCase();

  // Build message based on channel and action
  if (channel === "email") {
    if (action === "sent" || action === "delivered") {
      return subject
        ? `Email sent to ${name}: "${subject}"`
        : `Email sent to ${name}`;
    }
    if (action === "opened") {
      return `${name} opened your email`;
    }
    if (action === "clicked") {
      return `${name} clicked a link`;
    }
    if (action === "replied") {
      const preview = activity.content_preview
        ? `"${activity.content_preview.slice(0, 50)}${activity.content_preview.length > 50 ? "..." : ""}"`
        : "";
      return preview ? `${name} replied: ${preview}` : `${name} replied`;
    }
    if (action === "bounced") {
      return `Email to ${name} bounced`;
    }
  }

  if (channel === "linkedin") {
    if (action === "accepted" || action === "connected") {
      return `${name} accepted connection`;
    }
    if (action === "sent") {
      return `LinkedIn message sent to ${name}`;
    }
    if (action === "replied") {
      return `${name} replied on LinkedIn`;
    }
  }

  if (channel === "voice") {
    if (action === "called" || action === "sent") {
      return company
        ? `Voice AI: Call to ${company}`
        : `Voice AI: Call to ${name}`;
    }
    if (action === "answered" || action === "completed") {
      return company
        ? `Voice AI: Call completed with ${company}`
        : `Voice AI: Call completed with ${name}`;
    }
    if (action === "converted" || action === "meeting_booked") {
      return company ? `Meeting booked: ${company}` : `Meeting booked: ${name}`;
    }
  }

  if (channel === "sms") {
    if (action === "sent" || action === "delivered") {
      return `SMS delivered to ${name}`;
    }
    if (action === "replied") {
      return `${name} replied to SMS`;
    }
  }

  // Generic fallback
  return `${action} - ${name}`;
}

/**
 * Determine status from action type
 */
function getStatusFromAction(
  action: string
): "success" | "failed" | "pending" | undefined {
  const actionLower = action.toLowerCase();

  if (["bounced", "failed", "error", "unsubscribed"].includes(actionLower)) {
    return "failed";
  }

  if (["pending", "queued", "scheduled"].includes(actionLower)) {
    return "pending";
  }

  return "success";
}

/**
 * Transform API activities to ActivityTicker format
 */
function transformActivities(apiActivities: APIActivity[]): TickerActivity[] {
  return apiActivities.map((activity) => ({
    id: activity.id,
    type: mapToTickerType(activity.channel, activity.action),
    message: buildActivityMessage(activity),
    timestamp: new Date(activity.timestamp || activity.created_at),
    status: getStatusFromAction(activity.action),
  }));
}

/**
 * LiveActivityFeed component - fetches real data and renders ActivityTicker
 */
export function LiveActivityFeed({
  speed = "normal",
  direction = "up",
  showTimestamp = true,
  maxVisible = 6,
  limit = 20,
}: LiveActivityFeedProps) {
  const { data: activities, isLoading, error } = useActivityFeed(limit);

  // Transform API activities to ticker format
  const tickerActivities = useMemo(() => {
    if (!activities || activities.length === 0) {
      return undefined; // Will trigger demo mode in ActivityTicker
    }
    return transformActivities(activities);
  }, [activities]);

  // Pass activities to ticker (undefined will show demo mode)
  return (
    <ActivityTicker
      activities={tickerActivities}
      speed={speed}
      direction={direction}
      showTimestamp={showTimestamp}
      maxVisible={maxVisible}
    />
  );
}

export default LiveActivityFeed;
