/**
 * FILE: app/api/reports/weekly/route.ts
 * PURPOSE: Weekly metrics report for dashboard
 * TODO: Replace mock data with Supabase aggregations
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface DailyMetric {
  date: string;
  sent: number;
  opened: number;
  replied: number;
  meetings: number;
}

export interface WeeklyReport {
  weekStart: string;
  weekEnd: string;
  dailyMetrics: DailyMetric[];
  totals: {
    sent: number;
    opened: number;
    replied: number;
    meetings: number;
    openRate: number;
    replyRate: number;
    meetingRate: number;
  };
  weekOverWeekChange: {
    sent: number;
    replied: number;
    meetings: number;
  };
  topPerformingChannel: string;
  topPerformingSequence: string;
}

export interface WeeklyReportResponse {
  success: boolean;
  data: WeeklyReport;
}

// Helper to generate dates
function getDateDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().split("T")[0];
}

// Mock data
function generateMockWeeklyReport(): WeeklyReport {
  const dailyMetrics: DailyMetric[] = [];
  
  for (let i = 6; i >= 0; i--) {
    dailyMetrics.push({
      date: getDateDaysAgo(i),
      sent: 150 + Math.floor(Math.random() * 100),
      opened: 40 + Math.floor(Math.random() * 30),
      replied: 3 + Math.floor(Math.random() * 8),
      meetings: Math.floor(Math.random() * 3),
    });
  }

  const totals = {
    sent: dailyMetrics.reduce((sum, d) => sum + d.sent, 0),
    opened: dailyMetrics.reduce((sum, d) => sum + d.opened, 0),
    replied: dailyMetrics.reduce((sum, d) => sum + d.replied, 0),
    meetings: dailyMetrics.reduce((sum, d) => sum + d.meetings, 0),
    openRate: 0,
    replyRate: 0,
    meetingRate: 0,
  };

  totals.openRate = Math.round((totals.opened / totals.sent) * 1000) / 10;
  totals.replyRate = Math.round((totals.replied / totals.sent) * 1000) / 10;
  totals.meetingRate = Math.round((totals.meetings / totals.sent) * 1000) / 10;

  return {
    weekStart: getDateDaysAgo(6),
    weekEnd: getDateDaysAgo(0),
    dailyMetrics,
    totals,
    weekOverWeekChange: {
      sent: 12, // percentage
      replied: 23,
      meetings: -8,
    },
    topPerformingChannel: "Email",
    topPerformingSequence: "CEO Outreach v2",
  };
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const weekOffset = parseInt(searchParams.get("weekOffset") || "0"); // 0 = current, 1 = last week, etc.

    // TODO: Supabase integration
    // const supabase = createClient(...)
    // const weekStart = getWeekStart(weekOffset)
    // const weekEnd = getWeekEnd(weekOffset)
    // const { data: dailyMetrics } = await supabase.rpc('get_daily_metrics', { start: weekStart, end: weekEnd })
    // const { data: prevWeek } = await supabase.rpc('get_weekly_totals', { week_offset: weekOffset + 1 })
    // Calculate week over week changes...

    const report = generateMockWeeklyReport();

    return NextResponse.json({
      success: true,
      data: report,
    } as WeeklyReportResponse);
  } catch (error) {
    console.error("Weekly report error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to generate weekly report" },
      { status: 500 }
    );
  }
}
