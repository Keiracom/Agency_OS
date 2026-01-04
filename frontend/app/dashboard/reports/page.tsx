/**
 * FILE: frontend/app/dashboard/reports/page.tsx
 * PURPOSE: Reports and analytics page with real data
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-006
 */

"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Download, Calendar } from "lucide-react";
import {
  useDashboardStats,
  useChannelMetrics,
  useCampaignPerformance,
} from "@/hooks/use-reports";
import { StatsGridSkeleton, TableSkeleton } from "@/components/ui/loading-skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import type { ChannelMetrics, CampaignPerformance } from "@/lib/api/types";

export default function ReportsPage() {
  const { data: stats, isLoading: statsLoading, error: statsError } = useDashboardStats();
  const { data: channelMetrics, isLoading: channelsLoading, error: channelsError, refetch: refetchChannels } = useChannelMetrics();
  const { data: campaignPerformance, isLoading: campaignsLoading, error: campaignsError, refetch: refetchCampaigns } = useCampaignPerformance();

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground">
            Analytics and performance metrics for your campaigns
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Calendar className="mr-2 h-4 w-4" />
            Last 30 days
          </Button>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      {statsLoading ? (
        <StatsGridSkeleton />
      ) : statsError ? (
        <ErrorState error={statsError} title="Failed to load stats" />
      ) : stats ? (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Total Leads</p>
              <p className="text-3xl font-bold mt-1">{stats.total_leads.toLocaleString()}</p>
              <p className="text-sm text-muted-foreground mt-1">Across all campaigns</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Contacted</p>
              <p className="text-3xl font-bold mt-1">{stats.leads_contacted.toLocaleString()}</p>
              <p className="text-sm text-muted-foreground mt-1">
                {stats.total_leads > 0 ? ((stats.leads_contacted / stats.total_leads) * 100).toFixed(1) : 0}% of leads
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Replies</p>
              <p className="text-3xl font-bold mt-1">{stats.leads_replied.toLocaleString()}</p>
              <p className="text-sm text-green-600 mt-1">{stats.reply_rate.toFixed(1)}% reply rate</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">Conversions</p>
              <p className="text-3xl font-bold mt-1">{stats.leads_converted.toLocaleString()}</p>
              <p className="text-sm text-green-600 mt-1">{stats.conversion_rate.toFixed(1)}% conversion rate</p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Channel Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Channel Performance</CardTitle>
          <CardDescription>Metrics broken down by outreach channel</CardDescription>
        </CardHeader>
        <CardContent>
          {channelsLoading ? (
            <TableSkeleton rows={4} />
          ) : channelsError ? (
            <ErrorState error={channelsError} onRetry={refetchChannels} title="Failed to load channel metrics" />
          ) : !channelMetrics || channelMetrics.length === 0 ? (
            <EmptyState
              title="No channel data yet"
              description="Channel metrics will appear once your campaigns start sending messages"
            />
          ) : (
            <div className="rounded-md border">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="p-3 text-left text-sm font-medium">Channel</th>
                    <th className="p-3 text-right text-sm font-medium">Sent</th>
                    <th className="p-3 text-right text-sm font-medium">Delivered</th>
                    <th className="p-3 text-right text-sm font-medium">Opened</th>
                    <th className="p-3 text-right text-sm font-medium">Replied</th>
                    <th className="p-3 text-right text-sm font-medium">Reply Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {channelMetrics.map((row: ChannelMetrics) => (
                    <tr key={row.channel} className="border-b">
                      <td className="p-3 font-medium capitalize">{row.channel}</td>
                      <td className="p-3 text-right">{row.sent.toLocaleString()}</td>
                      <td className="p-3 text-right">{row.delivered.toLocaleString()}</td>
                      <td className="p-3 text-right">{row.opened > 0 ? row.opened.toLocaleString() : "N/A"}</td>
                      <td className="p-3 text-right">{row.replied.toLocaleString()}</td>
                      <td className="p-3 text-right">
                        <Badge variant={row.reply_rate >= 3 ? "active" : "secondary"}>
                          {row.reply_rate.toFixed(1)}%
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Campaign Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Campaign Performance</CardTitle>
          <CardDescription>Compare performance across all campaigns</CardDescription>
        </CardHeader>
        <CardContent>
          {campaignsLoading ? (
            <TableSkeleton rows={4} />
          ) : campaignsError ? (
            <ErrorState error={campaignsError} onRetry={refetchCampaigns} title="Failed to load campaign metrics" />
          ) : !campaignPerformance || campaignPerformance.length === 0 ? (
            <EmptyState
              title="No campaign data yet"
              description="Create and run campaigns to see performance metrics"
            />
          ) : (
            <div className="rounded-md border">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="p-3 text-left text-sm font-medium">Campaign</th>
                    <th className="p-3 text-left text-sm font-medium">Status</th>
                    <th className="p-3 text-right text-sm font-medium">Leads</th>
                    <th className="p-3 text-right text-sm font-medium">Contacted</th>
                    <th className="p-3 text-right text-sm font-medium">Replied</th>
                    <th className="p-3 text-right text-sm font-medium">Converted</th>
                    <th className="p-3 text-right text-sm font-medium">Conv. Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {campaignPerformance.map((campaign: CampaignPerformance) => (
                    <tr key={campaign.campaign_id} className="border-b">
                      <td className="p-3 font-medium">{campaign.campaign_name}</td>
                      <td className="p-3">
                        <Badge variant={campaign.status as "active" | "paused" | "draft"} className="capitalize">
                          {campaign.status}
                        </Badge>
                      </td>
                      <td className="p-3 text-right">{campaign.total_leads.toLocaleString()}</td>
                      <td className="p-3 text-right">{campaign.contacted.toLocaleString()}</td>
                      <td className="p-3 text-right">{campaign.replied.toLocaleString()}</td>
                      <td className="p-3 text-right">{campaign.converted.toLocaleString()}</td>
                      <td className="p-3 text-right">
                        <Badge variant="outline">
                          {campaign.conversion_rate.toFixed(1)}%
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
