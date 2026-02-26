/**
 * FILE: app/api/meetings/route.ts
 * PURPOSE: Meeting list for dashboard - upcoming and past meetings
 * PHASE: 14 (Frontend-Backend Connection)
 * STATUS: Real Supabase data
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Types matching database schema
export interface Meeting {
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
  // Joined lead data
  lead_name?: string;
  lead_company?: string;
  lead_email?: string;
}

export interface MeetingsResponse {
  success: boolean;
  data: Meeting[];
  total: number;
  upcoming: number;
}

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    
    // Get authenticated user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json(
        { success: false, error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Get user's client_id from memberships
    const { data: membership, error: membershipError } = await supabase
      .from("memberships")
      .select("client_id")
      .eq("user_id", user.id)
      .not("accepted_at", "is", null)
      .is("deleted_at", null)
      .order("created_at", { ascending: true })
      .limit(1)
      .single();

    if (membershipError || !membership) {
      return NextResponse.json(
        { success: false, error: "No client membership found" },
        { status: 403 }
      );
    }

    const clientId = membership.client_id;

    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status"); // scheduled, completed, cancelled
    const limit = parseInt(searchParams.get("limit") || "50");
    const upcoming = searchParams.get("upcoming") === "true";

    // Build query for meetings with lead data
    let query = supabase
      .from("meetings")
      .select(`
        id,
        client_id,
        lead_id,
        campaign_id,
        booked_at,
        scheduled_at,
        meeting_type,
        confirmed,
        showed_up,
        meeting_outcome,
        converting_channel,
        touches_before_booking,
        days_to_booking,
        duration_minutes,
        meeting_link,
        leads (
          name,
          company_name,
          email
        )
      `)
      .eq("client_id", clientId)
      .order("scheduled_at", { ascending: false })
      .limit(limit);

    // Filter by upcoming (scheduled in future)
    if (upcoming) {
      query = query
        .gte("scheduled_at", new Date().toISOString())
        .is("meeting_outcome", null);
    }

    // Filter by meeting outcome status
    if (status === "scheduled") {
      query = query.is("meeting_outcome", null);
    } else if (status === "completed") {
      query = query.not("meeting_outcome", "is", null);
    } else if (status === "cancelled") {
      query = query.eq("meeting_outcome", "cancelled");
    }

    const { data: meetings, error: meetingsError } = await query;

    if (meetingsError) {
      console.error("Meetings query error:", meetingsError);
      return NextResponse.json(
        { success: false, error: "Failed to fetch meetings" },
        { status: 500 }
      );
    }

    // Transform data to flatten lead info
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const transformedMeetings = (meetings || []).map((m: any) => {
      // leads can be object or array depending on query
      const leadData = Array.isArray(m.leads) ? m.leads[0] : m.leads;
      const lead = leadData as { name: string; company_name: string; email: string } | null;
      return {
        id: m.id,
        client_id: m.client_id,
        lead_id: m.lead_id,
        campaign_id: m.campaign_id,
        booked_at: m.booked_at,
        scheduled_at: m.scheduled_at,
        meeting_type: m.meeting_type,
        confirmed: m.confirmed,
        showed_up: m.showed_up,
        meeting_outcome: m.meeting_outcome,
        converting_channel: m.converting_channel,
        touches_before_booking: m.touches_before_booking,
        days_to_booking: m.days_to_booking,
        duration_minutes: m.duration_minutes,
        meeting_link: m.meeting_link,
        // Flattened lead data
        lead_name: lead?.name || "Unknown Lead",
        lead_company: lead?.company_name || null,
        lead_email: lead?.email || null,
      };
    });

    // Count upcoming meetings for the header
    const { count: upcomingCount } = await supabase
      .from("meetings")
      .select("id", { count: "exact", head: true })
      .eq("client_id", clientId)
      .gte("scheduled_at", new Date().toISOString())
      .is("meeting_outcome", null);

    return NextResponse.json({
      success: true,
      data: transformedMeetings,
      total: transformedMeetings.length,
      upcoming: upcomingCount || 0,
    } as MeetingsResponse);
  } catch (error) {
    console.error("Meetings error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch meetings" },
      { status: 500 }
    );
  }
}
