/**
 * FILE: app/api/channels/stats/route.ts
 * PURPOSE: Per-channel performance metrics (email, linkedin, sms, voice, direct_mail)
 * TODO: Replace mock data with Supabase aggregations
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface ChannelStats {
  channel: "email" | "linkedin" | "sms" | "voice" | "direct_mail";
  displayName: string;
  sent: number;
  delivered: number;
  opened: number;
  replied: number;
  meetings: number;
  openRate: number;
  replyRate: number;
  meetingRate: number;
  costPerLead: number; // AUD
  status: "active" | "paused" | "disabled";
}

export interface ChannelStatsResponse {
  success: boolean;
  data: ChannelStats[];
  period: string;
  totals: {
    totalSent: number;
    totalReplies: number;
    totalMeetings: number;
    avgReplyRate: number;
  };
}

// Mock data
const mockChannelStats: ChannelStats[] = [
  {
    channel: "email",
    displayName: "Email",
    sent: 1250,
    delivered: 1225,
    opened: 367,
    replied: 42,
    meetings: 8,
    openRate: 29.9,
    replyRate: 3.4,
    meetingRate: 0.6,
    costPerLead: 0.85,
    status: "active",
  },
  {
    channel: "linkedin",
    displayName: "LinkedIn",
    sent: 340,
    delivered: 338,
    opened: 204,
    replied: 28,
    meetings: 5,
    openRate: 60.4,
    replyRate: 8.2,
    meetingRate: 1.5,
    costPerLead: 2.40,
    status: "active",
  },
  {
    channel: "sms",
    displayName: "SMS",
    sent: 180,
    delivered: 175,
    opened: 158,
    replied: 12,
    meetings: 2,
    openRate: 90.3,
    replyRate: 6.7,
    meetingRate: 1.1,
    costPerLead: 1.20,
    status: "active",
  },
  {
    channel: "voice",
    displayName: "Voice AI",
    sent: 95,
    delivered: 72,
    opened: 72,
    replied: 18,
    meetings: 4,
    openRate: 100.0,
    replyRate: 25.0,
    meetingRate: 5.6,
    costPerLead: 8.50,
    status: "active",
  },
  {
    channel: "direct_mail",
    displayName: "Direct Mail",
    sent: 50,
    delivered: 48,
    opened: 32,
    replied: 4,
    meetings: 1,
    openRate: 66.7,
    replyRate: 8.3,
    meetingRate: 2.1,
    costPerLead: 15.00,
    status: "paused",
  },
];

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const period = searchParams.get("period") || "30d"; // 7d, 30d, 90d
    const channel = searchParams.get("channel"); // filter to specific channel

    // TODO: Supabase integration
    // const supabase = createClient(...)
    // const startDate = getStartDateForPeriod(period)
    // const { data } = await supabase.rpc('get_channel_stats', { start_date: startDate })

    let data = [...mockChannelStats];
    if (channel) {
      data = data.filter((c) => c.channel === channel);
    }

    const totals = {
      totalSent: data.reduce((sum, c) => sum + c.sent, 0),
      totalReplies: data.reduce((sum, c) => sum + c.replied, 0),
      totalMeetings: data.reduce((sum, c) => sum + c.meetings, 0),
      avgReplyRate: data.reduce((sum, c) => sum + c.replyRate, 0) / data.length,
    };

    return NextResponse.json({
      success: true,
      data,
      period,
      totals,
    } as ChannelStatsResponse);
  } catch (error) {
    console.error("Channel stats error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch channel stats" },
      { status: 500 }
    );
  }
}
