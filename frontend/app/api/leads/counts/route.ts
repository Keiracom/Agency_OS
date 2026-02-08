/**
 * FILE: app/api/leads/counts/route.ts
 * PURPOSE: Lead tier distribution counts (T1/T2/T3/Unscored)
 * TODO: Replace mock data with Supabase aggregations on leads table
 */

import { NextResponse } from "next/server";

// Types
export interface TierCount {
  tier: "T1" | "T2" | "T3" | "unscored";
  label: string;
  count: number;
  percentage: number;
  description: string;
  color: string;
}

export interface LeadCountsResponse {
  success: boolean;
  data: TierCount[];
  total: number;
  lastUpdated: string;
}

// Mock data
const mockTierCounts: TierCount[] = [
  {
    tier: "T1",
    label: "Tier 1 - Hot",
    count: 47,
    percentage: 13.7,
    description: "High-intent, decision-makers at ideal companies",
    color: "#22c55e", // green
  },
  {
    tier: "T2",
    label: "Tier 2 - Warm",
    count: 124,
    percentage: 36.3,
    description: "Good fit, may need nurturing",
    color: "#f59e0b", // amber
  },
  {
    tier: "T3",
    label: "Tier 3 - Cold",
    count: 98,
    percentage: 28.7,
    description: "Lower priority, long-term potential",
    color: "#3b82f6", // blue
  },
  {
    tier: "unscored",
    label: "Unscored",
    count: 73,
    percentage: 21.3,
    description: "Awaiting enrichment and scoring",
    color: "#6b7280", // gray
  },
];

export async function GET() {
  try {
    // TODO: Supabase integration
    // const supabase = createClient(...)
    // const { data } = await supabase.rpc('get_lead_tier_counts')
    // OR:
    // const { data } = await supabase
    //   .from('leads')
    //   .select('tier')
    //   .then(res => aggregate by tier)

    const total = mockTierCounts.reduce((sum, t) => sum + t.count, 0);

    return NextResponse.json({
      success: true,
      data: mockTierCounts,
      total,
      lastUpdated: new Date().toISOString(),
    } as LeadCountsResponse);
  } catch (error) {
    console.error("Lead counts error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch lead counts" },
      { status: 500 }
    );
  }
}
