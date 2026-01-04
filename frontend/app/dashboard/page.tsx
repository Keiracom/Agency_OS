/**
 * FILE: frontend/app/dashboard/page.tsx
 * PURPOSE: Dashboard home with activity feed and metrics
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-006
 */

"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Target,
  Users,
  MessageSquare,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Mail,
  Phone,
  Linkedin,
  CreditCard,
} from "lucide-react";
import { useDashboardStats, useActivityFeed, useALSDistribution } from "@/hooks/use-reports";
import { StatsGridSkeleton, ActivityFeedSkeleton, CardListSkeleton } from "@/components/ui/loading-skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { MeetingsWidget } from "@/components/dashboard/meetings-widget";
import type { Activity, ALSTier } from "@/lib/api/types";

const channelIcon: Record<string, typeof Mail> = {
  email: Mail,
  sms: Phone,
  linkedin: Linkedin,
};

const tierColors: Record<ALSTier, string> = {
  hot: "bg-red-500",
  warm: "bg-orange-500",
  cool: "bg-blue-500",
  cold: "bg-gray-400",
  dead: "bg-gray-200",
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useDashboardStats();
  const { data: activities, isLoading: activitiesLoading, error: activitiesError } = useActivityFeed(10);
  const { data: alsDistribution, isLoading: alsLoading, error: alsError } = useALSDistribution();

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back! Here&apos;s what&apos;s happening with your campaigns.
        </p>
      </div>

      {/* Stats Grid */}
      {statsLoading ? (
        <StatsGridSkeleton />
      ) : statsError ? (
        <ErrorState error={statsError} onRetry={refetchStats} title="Failed to load stats" />
      ) : stats ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Campaigns</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.active_campaigns}</div>
              <p className="text-xs text-muted-foreground">Running campaigns</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Leads</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_leads.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                {stats.leads_contacted.toLocaleString()} contacted
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Reply Rate</CardTitle>
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.reply_rate.toFixed(1)}%</div>
              <div className="flex items-center text-xs text-muted-foreground">
                {stats.leads_replied.toLocaleString()} replies received
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Conversions</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.conversion_rate.toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground">
                {stats.leads_converted.toLocaleString()} converted
              </p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Activity Feed + ALS Distribution + Meetings */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Activity Feed */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest interactions across all campaigns
            </CardDescription>
          </CardHeader>
          <CardContent>
            {activitiesLoading ? (
              <ActivityFeedSkeleton count={5} />
            ) : activitiesError ? (
              <ErrorState error={activitiesError} title="Failed to load activity" />
            ) : !activities || activities.length === 0 ? (
              <EmptyState
                title="No recent activity"
                description="Activity will appear here as your campaigns run"
              />
            ) : (
              <div className="space-y-4">
                {activities.map((activity: Activity) => {
                  const ChannelIcon = channelIcon[activity.channel] || Users;

                  return (
                    <div
                      key={activity.id}
                      className="flex items-start gap-4 rounded-lg border p-4"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
                        <ChannelIcon className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">
                            {activity.lead?.first_name} {activity.lead?.last_name}
                          </span>
                          {activity.lead?.company && (
                            <span className="text-sm text-muted-foreground">
                              at {activity.lead.company}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-1">
                          {activity.action}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatTimeAgo(activity.created_at)}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Meetings Widget */}
        <MeetingsWidget />
      </div>

      {/* ALS Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>ALS Tier Distribution</CardTitle>
          <CardDescription>
            Lead quality breakdown across all campaigns
          </CardDescription>
        </CardHeader>
        <CardContent>
          {alsLoading ? (
            <div className="grid grid-cols-5 gap-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="animate-pulse space-y-2">
                  <div className="h-5 w-full rounded bg-muted" />
                  <div className="h-2 w-full rounded bg-muted" />
                </div>
              ))}
            </div>
          ) : alsError ? (
            <ErrorState error={alsError} title="Failed to load distribution" />
          ) : !alsDistribution || alsDistribution.length === 0 ? (
            <EmptyState
              title="No leads yet"
              description="Add leads to your campaigns to see tier distribution"
            />
          ) : (
            <div className="grid grid-cols-5 gap-4">
              {alsDistribution.map((item) => (
                <div key={item.tier} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <Badge
                      variant={item.tier as "hot" | "warm" | "cool" | "cold" | "dead"}
                    >
                      {item.tier.charAt(0).toUpperCase() + item.tier.slice(1)}
                    </Badge>
                    <span className="font-medium">{item.percentage.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted">
                    <div
                      className={`h-2 rounded-full ${tierColors[item.tier]}`}
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground text-center">
                    {item.count.toLocaleString()} leads
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
