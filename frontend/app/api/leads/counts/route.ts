/**
 * FILE: app/api/leads/counts/route.ts
 * PURPOSE: Lead tier distribution from Supabase leads.als_tier aggregation.
 *          Returns one row per als_tier value (hot/warm/cool/cold) plus an
 *          "unscored" bucket for NULL als_tier. Honest counts; no mocks.
 */

import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export type LeadTier = "hot" | "warm" | "cool" | "cold" | "unscored";

export interface TierCount {
  tier: LeadTier;
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

const TIER_META: Record<LeadTier, { label: string; description: string; color: string }> = {
  hot: { label: "Hot", description: "High-intent, decision-makers at ideal companies", color: "#EF4444" },
  warm: { label: "Warm", description: "Good fit, may need nurturing", color: "#F59E0B" },
  cool: { label: "Cool", description: "Lower priority, long-term potential", color: "#3B82F6" },
  cold: { label: "Cold", description: "Minimal signals, deprioritised", color: "#64748B" },
  unscored: { label: "Unscored", description: "Awaiting enrichment and scoring", color: "#6B7280" },
};

const ORDER: LeadTier[] = ["hot", "warm", "cool", "cold", "unscored"];

export async function GET() {
  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json(
        { success: false, error: "Unauthorized" },
        { status: 401 }
      );
    }

    const { data, error } = await supabase
      .from("leads")
      .select("als_tier");
    if (error) {
      console.error("Lead counts query error:", error);
      return NextResponse.json(
        { success: false, error: "Failed to fetch lead counts" },
        { status: 500 }
      );
    }

    const counts: Record<LeadTier, number> = {
      hot: 0,
      warm: 0,
      cool: 0,
      cold: 0,
      unscored: 0,
    };
    for (const row of data ?? []) {
      const t = (row as { als_tier: string | null }).als_tier;
      if (t && t in counts) {
        counts[t as LeadTier]++;
      } else {
        counts.unscored++;
      }
    }

    const total = ORDER.reduce((sum, t) => sum + counts[t], 0);
    const tiers: TierCount[] = ORDER.map((tier) => ({
      tier,
      label: TIER_META[tier].label,
      count: counts[tier],
      percentage: total > 0 ? Number(((counts[tier] / total) * 100).toFixed(1)) : 0,
      description: TIER_META[tier].description,
      color: TIER_META[tier].color,
    }));

    return NextResponse.json({
      success: true,
      data: tiers,
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
