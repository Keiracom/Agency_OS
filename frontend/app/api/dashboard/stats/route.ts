/**
 * FILE: app/api/dashboard/stats/route.ts
 * PURPOSE: Hero metrics for dashboard - sent today, replies, meetings, active leads
 * TODO: Replace mock data with Supabase queries
 */

import { NextResponse } from "next/server";

// Types
export interface DashboardStats {
  sentToday: number;
  sentTodayChange: number;
  replies: number;
  repliesChange: number;
  meetingsBooked: number;
  meetingsChange: number;
  activeLeads: number;
  activeLeadsChange: number;
  period: string;
}

// Mock data matching component expectations
const mockStats: DashboardStats = {
  sentToday: 247,
  sentTodayChange: 12, // percentage change from yesterday
  replies: 18,
  repliesChange: 23,
  meetingsBooked: 4,
  meetingsChange: -5,
  activeLeads: 342,
  activeLeadsChange: 8,
  period: "today",
};

export async function GET() {
  try {
    // TODO: Supabase integration
    // const supabase = createClient(...)
    // const { data: stats } = await supabase.rpc('get_dashboard_stats')

    return NextResponse.json({
      success: true,
      data: mockStats,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Dashboard stats error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch dashboard stats" },
      { status: 500 }
    );
  }
}
