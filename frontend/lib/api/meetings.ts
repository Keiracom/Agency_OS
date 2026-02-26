/**
 * FILE: frontend/lib/api/meetings.ts
 * PURPOSE: Meetings API fetchers
 * PHASE: 14 (Frontend-Backend Connection)
 * STATUS: Real data via Next.js API routes
 */

export interface Meeting {
  id: string;
  lead_id: string;
  lead_name: string;
  lead_company: string | null;
  scheduled_at: string | null;
  duration_minutes: number;
  meeting_type: "discovery" | "demo" | "follow_up" | "close" | "onboarding" | "other";
  calendar_link: string | null;
  status: "scheduled" | "completed" | "cancelled" | "no_show";
  created_at: string;
  // Additional fields from real data
  client_id?: string;
  campaign_id?: string | null;
  booked_at?: string;
  confirmed?: boolean;
  showed_up?: boolean | null;
  meeting_outcome?: string | null;
  converting_channel?: string | null;
  touches_before_booking?: number | null;
  days_to_booking?: number | null;
}

interface MeetingListResponse {
  items: Meeting[];
  total: number;
}

interface APIResponse {
  success: boolean;
  data: Array<{
    id: string;
    client_id: string;
    lead_id: string;
    campaign_id: string | null;
    booked_at: string;
    scheduled_at: string;
    meeting_type: string;
    confirmed: boolean;
    showed_up: boolean | null;
    meeting_outcome: string | null;
    converting_channel: string | null;
    touches_before_booking: number | null;
    days_to_booking: number | null;
    duration_minutes: number;
    meeting_link: string | null;
    lead_name: string;
    lead_company: string | null;
    lead_email: string | null;
  }>;
  total: number;
  upcoming: number;
}

/**
 * Get meetings for a client
 * Note: clientId is passed for compatibility but auth is handled server-side
 */
export async function getMeetings(
  _clientId: string,
  params?: { upcoming?: boolean; limit?: number }
): Promise<MeetingListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.upcoming) searchParams.set("upcoming", "true");
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const query = searchParams.toString();
  const response = await fetch(`/api/meetings${query ? `?${query}` : ""}`);
  
  if (!response.ok) {
    throw new Error("Failed to fetch meetings");
  }

  const json: APIResponse = await response.json();
  
  if (!json.success) {
    throw new Error("Failed to fetch meetings");
  }

  // Transform to expected format
  const items: Meeting[] = json.data.map((m) => ({
    id: m.id,
    lead_id: m.lead_id,
    lead_name: m.lead_name,
    lead_company: m.lead_company,
    scheduled_at: m.scheduled_at,
    duration_minutes: m.duration_minutes,
    meeting_type: m.meeting_type as Meeting["meeting_type"],
    calendar_link: m.meeting_link,
    status: deriveStatus(m.scheduled_at, m.meeting_outcome, m.showed_up),
    created_at: m.booked_at,
    // Additional fields
    client_id: m.client_id,
    campaign_id: m.campaign_id,
    booked_at: m.booked_at,
    confirmed: m.confirmed,
    showed_up: m.showed_up,
    meeting_outcome: m.meeting_outcome,
    converting_channel: m.converting_channel,
    touches_before_booking: m.touches_before_booking,
    days_to_booking: m.days_to_booking,
  }));

  return {
    items,
    total: json.total,
  };
}

/**
 * Derive status from meeting data
 */
function deriveStatus(
  scheduledAt: string,
  outcome: string | null,
  showedUp: boolean | null
): Meeting["status"] {
  if (outcome === "cancelled") return "cancelled";
  if (outcome === "no_show" || showedUp === false) return "no_show";
  if (outcome && outcome !== "pending") return "completed";
  
  const now = new Date();
  const scheduled = new Date(scheduledAt);
  
  if (scheduled > now) return "scheduled";
  return "completed"; // Past meetings without outcome assumed completed
}
