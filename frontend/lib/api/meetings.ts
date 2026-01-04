/**
 * FILE: frontend/lib/api/meetings.ts
 * PURPOSE: Meetings API fetchers
 * PHASE: 14 (Missing UI)
 * TASK: MUI-002
 */

import api from "./index";

export interface Meeting {
  id: string;
  lead_id: string;
  lead_name: string;
  lead_company: string | null;
  scheduled_at: string | null;
  duration_minutes: number;
  meeting_type: "discovery" | "demo" | "follow_up";
  calendar_link: string | null;
  status: "scheduled" | "completed" | "cancelled" | "no_show";
  created_at: string;
}

interface MeetingListResponse {
  items: Meeting[];
  total: number;
}

/**
 * Get meetings for a client
 */
export async function getMeetings(
  clientId: string,
  params?: { upcoming?: boolean; limit?: number }
): Promise<MeetingListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.upcoming) searchParams.set("upcoming", "true");
  if (params?.limit) searchParams.set("limit", params.limit.toString());

  const query = searchParams.toString();
  return api.get<MeetingListResponse>(
    `/api/v1/clients/${clientId}/meetings${query ? `?${query}` : ""}`
  );
}
