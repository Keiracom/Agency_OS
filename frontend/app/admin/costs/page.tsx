/**
 * FILE: frontend/app/admin/costs/page.tsx
 * PURPOSE: Costs overview for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Costs Overview
 */

"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Cpu, Send, ArrowRight, TrendingUp, TrendingDown } from "lucide-react";
import { createBrowserClient } from "@/lib/supabase";

// Phase 4 admin Tier A wiring (2026-05-10): replaces hardcoded mockCosts
// with live aggregates from sdk_usage_log (AI) + vendor_usage_log (channels).
// Same source as /admin/ops cost cards (PR #656). MTD = month-to-date.
// Per-AI-agent + per-channel breakdowns map agent_type prefixes + vendor IDs
// to the existing UI category labels (content/reply/cmo for AI, channel
// names for vendor). Last-month + projected-EOM derived from same tables.
type CostsData = {
  totalMTD: number;
  aiCosts: number;
  channelCosts: number;
  lastMonth: number;
  projectedEOM: number;
  byCategory: {
    ai: { content: number; reply: number; cmo: number };
    channels: { email: number; sms: number; linkedin: number; voice: number; mail: number };
  };
};

function startOfMonth(d: Date): string {
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString();
}

function endOfPriorMonth(d: Date): string {
  return new Date(d.getFullYear(), d.getMonth(), 0, 23, 59, 59).toISOString();
}

function startOfPriorMonth(d: Date): string {
  return new Date(d.getFullYear(), d.getMonth() - 1, 1).toISOString();
}

async function fetchAdminCosts(): Promise<CostsData> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const now = new Date();
  const monthStart = startOfMonth(now);
  const priorStart = startOfPriorMonth(now);
  const priorEnd = endOfPriorMonth(now);
  const dayOfMonth = now.getDate();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();

  const [{ data: sdkMTD }, { data: vendorMTD }, { data: sdkPrior }, { data: vendorPrior }] = await Promise.all([
    client
      .from("sdk_usage_log")
      .select("agent_type, cost_aud")
      .gte("created_at", monthStart),
    client
      .from("vendor_usage_log")
      .select("vendor, cost_aud")
      .gte("created_at", monthStart),
    client
      .from("sdk_usage_log")
      .select("cost_aud")
      .gte("created_at", priorStart)
      .lte("created_at", priorEnd),
    client
      .from("vendor_usage_log")
      .select("cost_aud")
      .gte("created_at", priorStart)
      .lte("created_at", priorEnd),
  ]);

  const sumCost = (rows: Array<{ cost_aud: string | number }> | null) =>
    (rows ?? []).reduce((s, r) => s + (typeof r.cost_aud === "string" ? Number(r.cost_aud) : r.cost_aud || 0), 0);

  const aiCosts = sumCost(sdkMTD ?? []);
  const channelCosts = sumCost(vendorMTD ?? []);
  const totalMTD = aiCosts + channelCosts;
  const lastMonth = sumCost(sdkPrior ?? []) + sumCost(vendorPrior ?? []);
  const projectedEOM = dayOfMonth > 0 ? (totalMTD / dayOfMonth) * daysInMonth : totalMTD;

  // AI breakdown by agent_type prefix
  const aiBreakdown = { content: 0, reply: 0, cmo: 0 };
  for (const row of (sdkMTD ?? []) as Array<{ agent_type: string | null; cost_aud: string | number }>) {
    const cost = typeof row.cost_aud === "string" ? Number(row.cost_aud) : row.cost_aud || 0;
    const at = row.agent_type ?? "";
    if (at.includes("comprehend") || at.includes("analyse") || at.includes("identify")) aiBreakdown.content += cost;
    else if (at.includes("reply") || at.includes("dm_verify")) aiBreakdown.reply += cost;
    else if (at.includes("cmo") || at.includes("smart_prompt")) aiBreakdown.cmo += cost;
    else aiBreakdown.content += cost; // default bucket
  }

  // Channel breakdown by vendor
  const channelBreakdown = { email: 0, sms: 0, linkedin: 0, voice: 0, mail: 0 };
  for (const row of (vendorMTD ?? []) as Array<{ vendor: string | null; cost_aud: string | number }>) {
    const cost = typeof row.cost_aud === "string" ? Number(row.cost_aud) : row.cost_aud || 0;
    const v = (row.vendor ?? "").toLowerCase();
    if (v.includes("salesforge") || v.includes("resend") || v.includes("postmark")) channelBreakdown.email += cost;
    else if (v.includes("telnyx") || v.includes("twilio")) channelBreakdown.sms += cost;
    else if (v.includes("unipile") || v.includes("heyreach") || v.includes("linkedin")) channelBreakdown.linkedin += cost;
    else if (v.includes("vapi") || v.includes("voice") || v.includes("eleven")) channelBreakdown.voice += cost;
    else if (v.includes("mail") || v.includes("postal")) channelBreakdown.mail += cost;
    else channelBreakdown.email += cost; // default bucket for enrichment vendors etc.
  }

  return {
    totalMTD,
    aiCosts,
    channelCosts,
    lastMonth,
    projectedEOM,
    byCategory: { ai: aiBreakdown, channels: channelBreakdown },
  };
}

const EMPTY_COSTS: CostsData = {
  totalMTD: 0,
  aiCosts: 0,
  channelCosts: 0,
  lastMonth: 0,
  projectedEOM: 0,
  byCategory: {
    ai: { content: 0, reply: 0, cmo: 0 },
    channels: { email: 0, sms: 0, linkedin: 0, voice: 0, mail: 0 },
  },
};

export default function AdminCostsOverviewPage() {
  const { data: mockCosts = EMPTY_COSTS } = useQuery({
    queryKey: ["admin-costs"],
    queryFn: fetchAdminCosts,
    staleTime: 30 * 1000,
  });

  const changePercent = mockCosts.lastMonth > 0
    ? ((mockCosts.totalMTD - mockCosts.lastMonth) / mockCosts.lastMonth) * 100
    : 0;
  const aiPercent = mockCosts.totalMTD > 0
    ? Math.round((mockCosts.aiCosts / mockCosts.totalMTD) * 100)
    : 0;
  const channelPercent = 100 - aiPercent;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Costs Overview</h1>
        <p className="text-muted-foreground">
          Platform-wide cost tracking and analysis
        </p>
      </div>

      {/* Total Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total MTD
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${mockCosts.totalMTD.toLocaleString()}</div>
            <div className="flex items-center gap-1 mt-1">
              {changePercent > 0 ? (
                <TrendingUp className="h-4 w-4 text-amber" />
              ) : (
                <TrendingDown className="h-4 w-4 text-amber" />
              )}
              <span className={changePercent > 0 ? "text-amber" : "text-amber"}>
                {changePercent > 0 ? "+" : ""}
                {changePercent.toFixed(1)}% vs last month
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Last Month
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${mockCosts.lastMonth.toLocaleString()}</div>
            <p className="text-sm text-muted-foreground mt-1">November 2025</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Projected EOM
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${mockCosts.projectedEOM.toLocaleString()}</div>
            <p className="text-sm text-muted-foreground mt-1">Based on current run rate</p>
          </CardContent>
        </Card>
      </div>

      {/* Cost Breakdown */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* AI Costs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Cpu className="h-5 w-5" />
                  AI Costs
                </CardTitle>
                <CardDescription>Anthropic API usage</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/admin/costs/ai">
                  View Details
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-4">
              ${mockCosts.aiCosts.toLocaleString()}
              <span className="text-sm font-normal text-muted-foreground ml-2">
                ({aiPercent}% of total)
              </span>
            </div>
            <div className="space-y-3">
              {Object.entries(mockCosts.byCategory.ai).map(([agent, cost]) => (
                <div key={agent} className="flex items-center justify-between">
                  <span className="capitalize">{agent} Agent</span>
                  <span className="font-medium">${cost}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Channel Costs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Send className="h-5 w-5" />
                  Channel Costs
                </CardTitle>
                <CardDescription>Outreach platform usage</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/admin/costs/channels">
                  View Details
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-4">
              ${mockCosts.channelCosts.toLocaleString()}
              <span className="text-sm font-normal text-muted-foreground ml-2">
                ({channelPercent}% of total)
              </span>
            </div>
            <div className="space-y-3">
              {Object.entries(mockCosts.byCategory.channels).map(([channel, cost]) => (
                <div key={channel} className="flex items-center justify-between">
                  <span className="capitalize">{channel}</span>
                  <span className="font-medium">${cost}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cost Distribution Visual */}
      <Card>
        <CardHeader>
          <CardTitle>Cost Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-8 rounded-lg overflow-hidden">
            <div
              className="bg-amber flex items-center justify-center text-ink text-sm font-medium"
              style={{ width: `${aiPercent}%` }}
            >
              AI {aiPercent}%
            </div>
            <div
              className="bg-panel flex items-center justify-center text-ink text-sm font-medium"
              style={{ width: `${channelPercent}%` }}
            >
              Channels {channelPercent}%
            </div>
          </div>
          <div className="flex justify-between mt-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded bg-amber" />
              AI Costs (Anthropic)
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded bg-panel" />
              Channel Costs (Email, SMS, LinkedIn, Voice, Mail)
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
