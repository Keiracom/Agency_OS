/**
 * FILE: app/api/activity/route.ts
 * PURPOSE: Live activity feed for dashboard
 * TODO: Replace mock data with Supabase real-time subscription or polling
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface ActivityItem {
  id: string;
  type: "email_sent" | "email_opened" | "reply_received" | "meeting_booked" | "lead_enriched" | "call_completed";
  leadName: string;
  companyName: string;
  channel: "email" | "linkedin" | "sms" | "voice" | "direct_mail";
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface ActivityResponse {
  success: boolean;
  data: ActivityItem[];
  hasMore: boolean;
  cursor?: string;
}

// Mock data
const mockActivity: ActivityItem[] = [
  {
    id: "act_001",
    type: "reply_received",
    leadName: "Sarah Chen",
    companyName: "TechFlow Digital",
    channel: "email",
    message: "Interested in learning more about your services",
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
  {
    id: "act_002",
    type: "meeting_booked",
    leadName: "Marcus Thompson",
    companyName: "GrowthLab Agency",
    channel: "email",
    message: "Booked 30-min discovery call for Thursday 2pm",
    timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
  },
  {
    id: "act_003",
    type: "email_opened",
    leadName: "Emma Rodriguez",
    companyName: "Pixel Perfect Studios",
    channel: "email",
    message: "Opened email: 'Quick question about your marketing'",
    timestamp: new Date(Date.now() - 22 * 60 * 1000).toISOString(),
  },
  {
    id: "act_004",
    type: "call_completed",
    leadName: "James Wilson",
    companyName: "Velocity Marketing",
    channel: "voice",
    message: "AI call completed - positive sentiment detected",
    timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
  },
  {
    id: "act_005",
    type: "lead_enriched",
    leadName: "Lisa Park",
    companyName: "Creative Surge",
    channel: "email",
    message: "Lead enriched with Apollo data - decision maker confirmed",
    timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
  },
  {
    id: "act_006",
    type: "email_sent",
    leadName: "David Kumar",
    companyName: "NextGen Digital",
    channel: "email",
    message: "Sent sequence step 2: Follow-up email",
    timestamp: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
  },
];

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get("limit") || "10");
    const cursor = searchParams.get("cursor");
    const type = searchParams.get("type"); // filter by activity type

    // TODO: Supabase integration
    // const supabase = createClient(...)
    // let query = supabase.from('activity_feed').select('*').order('timestamp', { ascending: false }).limit(limit)
    // if (cursor) query = query.lt('timestamp', cursor)
    // if (type) query = query.eq('type', type)
    // const { data, error } = await query

    let filteredActivity = [...mockActivity];
    if (type) {
      filteredActivity = filteredActivity.filter((a) => a.type === type);
    }

    const data = filteredActivity.slice(0, limit);

    return NextResponse.json({
      success: true,
      data,
      hasMore: filteredActivity.length > limit,
      cursor: data.length > 0 ? data[data.length - 1].timestamp : undefined,
    } as ActivityResponse);
  } catch (error) {
    console.error("Activity feed error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch activity feed" },
      { status: 500 }
    );
  }
}
