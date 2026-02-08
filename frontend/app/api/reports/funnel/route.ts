/**
 * FILE: app/api/reports/funnel/route.ts
 * PURPOSE: Funnel visualization data - lead journey from sourced to closed
 * TODO: Replace mock data with Supabase lead status aggregations
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface FunnelStage {
  stage: string;
  label: string;
  count: number;
  percentage: number;
  conversionFromPrevious: number;
  value: number; // AUD pipeline value
  avgDaysInStage: number;
}

export interface FunnelReport {
  stages: FunnelStage[];
  period: string;
  totalLeads: number;
  totalPipelineValue: number;
  overallConversion: number; // sourced to meeting %
  avgCycleTime: number; // days
}

export interface FunnelReportResponse {
  success: boolean;
  data: FunnelReport;
}

// Mock data
const mockFunnelStages: FunnelStage[] = [
  {
    stage: "sourced",
    label: "Sourced",
    count: 1250,
    percentage: 100,
    conversionFromPrevious: 100,
    value: 0,
    avgDaysInStage: 1,
  },
  {
    stage: "enriched",
    label: "Enriched",
    count: 1180,
    percentage: 94.4,
    conversionFromPrevious: 94.4,
    value: 0,
    avgDaysInStage: 0.5,
  },
  {
    stage: "contacted",
    label: "Contacted",
    count: 980,
    percentage: 78.4,
    conversionFromPrevious: 83.1,
    value: 0,
    avgDaysInStage: 2,
  },
  {
    stage: "engaged",
    label: "Engaged",
    count: 156,
    percentage: 12.5,
    conversionFromPrevious: 15.9,
    value: 780000, // 156 leads * $5k avg deal
    avgDaysInStage: 5,
  },
  {
    stage: "replied",
    label: "Replied",
    count: 84,
    percentage: 6.7,
    conversionFromPrevious: 53.8,
    value: 420000,
    avgDaysInStage: 3,
  },
  {
    stage: "meeting",
    label: "Meeting Booked",
    count: 28,
    percentage: 2.2,
    conversionFromPrevious: 33.3,
    value: 280000,
    avgDaysInStage: 7,
  },
  {
    stage: "proposal",
    label: "Proposal Sent",
    count: 18,
    percentage: 1.4,
    conversionFromPrevious: 64.3,
    value: 270000,
    avgDaysInStage: 5,
  },
  {
    stage: "closed",
    label: "Closed Won",
    count: 8,
    percentage: 0.6,
    conversionFromPrevious: 44.4,
    value: 120000,
    avgDaysInStage: 0,
  },
];

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const period = searchParams.get("period") || "30d"; // 7d, 30d, 90d, all

    // TODO: Supabase integration
    // const supabase = createClient(...)
    // const startDate = getStartDateForPeriod(period)
    // const { data } = await supabase.rpc('get_funnel_metrics', { start_date: startDate })
    // OR aggregate from leads table:
    // const { data: leadCounts } = await supabase
    //   .from('leads')
    //   .select('status')
    //   .gte('created_at', startDate)
    // Group and calculate conversions...

    const report: FunnelReport = {
      stages: mockFunnelStages,
      period,
      totalLeads: mockFunnelStages[0].count,
      totalPipelineValue: mockFunnelStages.reduce((sum, s) => sum + s.value, 0),
      overallConversion: (mockFunnelStages[5].count / mockFunnelStages[0].count) * 100, // to meeting
      avgCycleTime: 23, // days from sourced to meeting
    };

    return NextResponse.json({
      success: true,
      data: report,
    } as FunnelReportResponse);
  } catch (error) {
    console.error("Funnel report error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to generate funnel report" },
      { status: 500 }
    );
  }
}
