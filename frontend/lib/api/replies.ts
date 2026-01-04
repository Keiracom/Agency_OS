/**
 * FILE: frontend/lib/api/replies.ts
 * PURPOSE: Replies API fetchers
 * PHASE: 14 (Missing UI)
 * TASK: MUI-001
 */

import api from "./index";
import type { ChannelType } from "./types";

export type IntentType =
  | "meeting_request"
  | "interested"
  | "question"
  | "not_interested"
  | "unsubscribe"
  | "out_of_office"
  | "auto_reply";

export interface ReplyLead {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
  company: string | null;
}

export interface Reply {
  id: string;
  lead_id: string;
  lead: ReplyLead | null;
  campaign_id: string;
  campaign_name: string | null;
  channel: ChannelType;
  intent: IntentType | null;
  intent_confidence: number | null;
  content: string | null;
  subject: string | null;
  received_at: string;
  handled: boolean;
  handled_at: string | null;
}

interface ReplyListResponse {
  items: Reply[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReplyFilters {
  intent?: IntentType;
  channel?: ChannelType;
  handled?: boolean;
  campaign_id?: string;
  page?: number;
  page_size?: number;
}

/**
 * Get paginated list of replies
 */
export async function getReplies(
  clientId: string,
  params?: ReplyFilters
): Promise<ReplyListResponse> {
  const searchParams = new URLSearchParams();

  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString());
  if (params?.intent) searchParams.set("intent", params.intent);
  if (params?.channel) searchParams.set("channel", params.channel);
  if (params?.handled !== undefined) searchParams.set("handled", params.handled.toString());
  if (params?.campaign_id) searchParams.set("campaign_id", params.campaign_id);

  const query = searchParams.toString();
  return api.get<ReplyListResponse>(
    `/api/v1/clients/${clientId}/replies${query ? `?${query}` : ""}`
  );
}

/**
 * Get single reply by ID
 */
export async function getReply(clientId: string, replyId: string): Promise<Reply> {
  return api.get<Reply>(`/api/v1/clients/${clientId}/replies/${replyId}`);
}

/**
 * Mark reply as handled/unhandled
 */
export async function markReplyHandled(
  clientId: string,
  replyId: string,
  handled: boolean
): Promise<Reply> {
  return api.patch<Reply>(`/api/v1/clients/${clientId}/replies/${replyId}/handled`, {
    handled,
  });
}
