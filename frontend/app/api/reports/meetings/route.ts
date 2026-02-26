/**
 * FILE: app/api/reports/meetings/route.ts
 * PURPOSE: Meetings over time data for reports chart
 * PHASE: 14 (Frontend-Backend Connection)
 * STATUS: Real Supabase data
 */

import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export interface WeeklyMeetingData {
  week: string; // e.g., "Jan 6"
  weekStart: string; // ISO date
  value: number; // count of meetings
}

export interface MeetingsReportResponse {
  success: boolean;
  data: WeeklyMeetingData[];
}

export async function GET() {
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

    // Calculate date range for last 12 weeks
    const now = new Date();
    const twelveWeeksAgo = new Date(now);
    twelveWeeksAgo.setDate(twelveWeeksAgo.getDate() - 84); // 12 weeks * 7 days
    twelveWeeksAgo.setHours(0, 0, 0, 0);

    // Fetch all meetings booked in the last 12 weeks
    const { data: meetings, error: meetingsError } = await supabase
      .from("meetings")
      .select("booked_at")
      .eq("client_id", clientId)
      .gte("booked_at", twelveWeeksAgo.toISOString())
      .lte("booked_at", now.toISOString());

    if (meetingsError) {
      console.error("Meetings report query error:", meetingsError);
      return NextResponse.json(
        { success: false, error: "Failed to fetch meetings data" },
        { status: 500 }
      );
    }

    // Generate 12 week buckets
    const weeklyData: WeeklyMeetingData[] = [];
    
    for (let i = 11; i >= 0; i--) {
      const weekStart = new Date(now);
      weekStart.setDate(weekStart.getDate() - (i * 7));
      // Set to start of week (Monday)
      const day = weekStart.getDay();
      const diff = weekStart.getDate() - day + (day === 0 ? -6 : 1);
      weekStart.setDate(diff);
      weekStart.setHours(0, 0, 0, 0);
      
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 7);

      // Count meetings booked in this week
      const count = (meetings || []).filter(m => {
        const bookedDate = new Date(m.booked_at);
        return bookedDate >= weekStart && bookedDate < weekEnd;
      }).length;

      // Format week label (e.g., "Jan 6")
      const weekLabel = weekStart.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });

      weeklyData.push({
        week: weekLabel,
        weekStart: weekStart.toISOString(),
        value: count,
      });
    }

    return NextResponse.json({
      success: true,
      data: weeklyData,
    } as MeetingsReportResponse);
  } catch (error) {
    console.error("Meetings report error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch meetings report" },
      { status: 500 }
    );
  }
}
