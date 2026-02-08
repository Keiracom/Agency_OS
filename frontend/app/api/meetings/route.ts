/**
 * FILE: app/api/meetings/route.ts
 * PURPOSE: Meeting list for dashboard - upcoming and past meetings
 * TODO: Replace mock data with Supabase + calendar integration (Cal.com/Calendly)
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface Meeting {
  id: string;
  leadId: string;
  leadName: string;
  companyName: string;
  leadTitle: string;
  leadEmail: string;
  type: "discovery" | "demo" | "follow_up" | "proposal";
  status: "scheduled" | "completed" | "cancelled" | "no_show";
  scheduledAt: string;
  duration: number; // minutes
  source: "email" | "linkedin" | "voice" | "sms";
  notes?: string;
  meetingUrl?: string;
  calendarEventId?: string;
}

export interface MeetingsResponse {
  success: boolean;
  data: Meeting[];
  total: number;
  upcoming: number;
}

// Mock data
const mockMeetings: Meeting[] = [
  {
    id: "mtg_001",
    leadId: "lead_101",
    leadName: "Marcus Thompson",
    companyName: "GrowthLab Agency",
    leadTitle: "CEO",
    leadEmail: "marcus@growthlab.com.au",
    type: "discovery",
    status: "scheduled",
    scheduledAt: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
    duration: 30,
    source: "email",
    meetingUrl: "https://meet.google.com/abc-defg-hij",
    notes: "Interested in full-service outbound",
  },
  {
    id: "mtg_002",
    leadId: "lead_102",
    leadName: "Jessica Lee",
    companyName: "Spark Creative",
    leadTitle: "Marketing Director",
    leadEmail: "jessica@sparkcreative.com.au",
    type: "demo",
    status: "scheduled",
    scheduledAt: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
    duration: 45,
    source: "linkedin",
    meetingUrl: "https://meet.google.com/xyz-uvwx-abc",
  },
  {
    id: "mtg_003",
    leadId: "lead_103",
    leadName: "Tom Richards",
    companyName: "Digital First Agency",
    leadTitle: "Founder",
    leadEmail: "tom@digitalfirst.com.au",
    type: "discovery",
    status: "completed",
    scheduledAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    duration: 30,
    source: "voice",
    notes: "Very interested - sending proposal",
  },
  {
    id: "mtg_004",
    leadId: "lead_104",
    leadName: "Anna Kowalski",
    companyName: "Bright Ideas Marketing",
    leadTitle: "CEO",
    leadEmail: "anna@brightideas.com.au",
    type: "proposal",
    status: "scheduled",
    scheduledAt: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(),
    duration: 60,
    source: "email",
  },
];

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status"); // scheduled, completed, cancelled
    const limit = parseInt(searchParams.get("limit") || "20");
    const upcoming = searchParams.get("upcoming") === "true";

    // TODO: Supabase integration
    // const supabase = createClient(...)
    // let query = supabase.from('meetings').select('*, leads(name, company_name, title, email)')
    // if (status) query = query.eq('status', status)
    // if (upcoming) query = query.gte('scheduled_at', new Date().toISOString()).eq('status', 'scheduled')
    // const { data, error } = await query.order('scheduled_at', { ascending: true }).limit(limit)

    let filtered = [...mockMeetings];
    
    if (status) {
      filtered = filtered.filter((m) => m.status === status);
    }
    
    if (upcoming) {
      const now = new Date();
      filtered = filtered.filter(
        (m) => m.status === "scheduled" && new Date(m.scheduledAt) > now
      );
    }

    const upcomingCount = mockMeetings.filter(
      (m) => m.status === "scheduled" && new Date(m.scheduledAt) > new Date()
    ).length;

    return NextResponse.json({
      success: true,
      data: filtered.slice(0, limit),
      total: filtered.length,
      upcoming: upcomingCount,
    } as MeetingsResponse);
  } catch (error) {
    console.error("Meetings error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch meetings" },
      { status: 500 }
    );
  }
}
