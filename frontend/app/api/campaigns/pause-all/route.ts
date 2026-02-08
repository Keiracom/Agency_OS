/**
 * FILE: app/api/campaigns/pause-all/route.ts
 * PURPOSE: Emergency pause - stops all active campaigns immediately
 * TODO: Integrate with Salesforge, Unipile, Vapi to pause all sequences
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface PauseAllRequest {
  reason?: string;
  resumeAt?: string; // ISO datetime for auto-resume
  excludeCampaignIds?: string[]; // campaigns to keep running
}

export interface CampaignPauseResult {
  campaignId: string;
  campaignName: string;
  channel: "email" | "linkedin" | "sms" | "voice";
  status: "paused" | "already_paused" | "error";
  error?: string;
}

export interface PauseAllResponse {
  success: boolean;
  pausedAt: string;
  pausedBy: string;
  reason?: string;
  resumeAt?: string;
  results: CampaignPauseResult[];
  summary: {
    total: number;
    paused: number;
    alreadyPaused: number;
    errors: number;
  };
}

// Mock active campaigns
const mockActiveCampaigns = [
  { id: "camp_001", name: "CEO Outreach v2", channel: "email" as const, status: "active" },
  { id: "camp_002", name: "LinkedIn Decision Makers", channel: "linkedin" as const, status: "active" },
  { id: "camp_003", name: "SMS Follow-up", channel: "sms" as const, status: "active" },
  { id: "camp_004", name: "Voice AI Qualification", channel: "voice" as const, status: "active" },
  { id: "camp_005", name: "Agency Directors Email", channel: "email" as const, status: "paused" },
];

export async function POST(request: NextRequest) {
  try {
    const body: PauseAllRequest = await request.json();
    const { reason, resumeAt, excludeCampaignIds = [] } = body;

    // TODO: Supabase integration
    // 1. Get all active campaigns
    // const supabase = createClient(...)
    // const { data: campaigns } = await supabase
    //   .from('campaigns')
    //   .select('*')
    //   .eq('status', 'active')
    //   .not('id', 'in', `(${excludeCampaignIds.join(',')})`)

    // 2. Pause each campaign via respective API
    // - Salesforge: POST /campaigns/{id}/pause
    // - Unipile: pause LinkedIn sequences
    // - Vapi: pause voice campaigns
    // - Twilio: pause SMS sequences

    // 3. Update Supabase
    // await supabase
    //   .from('campaigns')
    //   .update({ status: 'paused', paused_at: new Date().toISOString(), pause_reason: reason })
    //   .in('id', campaignIds)

    // 4. Log the emergency action
    // await supabase.from('audit_log').insert({
    //   action: 'emergency_pause_all',
    //   reason,
    //   affected_campaigns: campaignIds,
    //   performed_by: 'user_id',
    //   timestamp: new Date().toISOString(),
    // })

    // Mock: Pause all active campaigns
    const results: CampaignPauseResult[] = mockActiveCampaigns
      .filter((c) => !excludeCampaignIds.includes(c.id))
      .map((campaign) => ({
        campaignId: campaign.id,
        campaignName: campaign.name,
        channel: campaign.channel,
        status: campaign.status === "active" ? "paused" as const : "already_paused" as const,
      }));

    const summary = {
      total: results.length,
      paused: results.filter((r) => r.status === "paused").length,
      alreadyPaused: results.filter((r) => r.status === "already_paused").length,
      errors: results.filter((r) => r.status === "error").length,
    };

    console.log(`🚨 EMERGENCY PAUSE: ${summary.paused} campaigns paused. Reason: ${reason || "Not specified"}`);

    return NextResponse.json({
      success: true,
      pausedAt: new Date().toISOString(),
      pausedBy: "current_user", // TODO: Get from auth context
      reason,
      resumeAt,
      results,
      summary,
    } as PauseAllResponse);
  } catch (error) {
    console.error("Emergency pause error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to pause campaigns" },
      { status: 500 }
    );
  }
}
