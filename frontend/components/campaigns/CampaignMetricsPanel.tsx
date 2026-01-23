/**
 * FILE: frontend/components/campaigns/CampaignMetricsPanel.tsx
 * PURPOSE: Campaign performance metrics display panel
 * PHASE: Phase I Dashboard Redesign (Item 57)
 *
 * Features:
 * - Meetings booked (hero metric from meetings table)
 * - Show rate percentage (meetings showed / total meetings)
 * - Reply rate percentage
 * - Active sequences count (leads currently in outreach)
 * - Channel allocation breakdown with stacked bar
 * - Performance indicator badge
 * - Responsive grid layout with compact mode
 *
 * Design Rules (from metrics.md):
 * - Show outcomes, not implementation details
 * - Percentages: one decimal for rates
 * - Use outcome-focused terminology ("Meetings" not "Leads converted")
 */

"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Mail,
  MessageSquare,
  Linkedin,
  Phone,
  Send,
  Users,
  MessageCircle,
  TrendingUp,
  Target,
} from "lucide-react";
import type { Campaign, ChannelType } from "@/lib/api/types";

// ============================================
// Types
// ============================================

export interface CampaignMetricsPanelProps {
  /** Campaign to display metrics for */
  campaign: Campaign;
  /** Additional class names */
  className?: string;
  /** Compact mode for smaller displays */
  compact?: boolean;
}

// ============================================
// Channel Configuration
// ============================================

const CHANNEL_CONFIG: Record<
  ChannelType,
  { label: string; icon: React.ReactNode; color: string }
> = {
  email: {
    label: "Email",
    icon: <Mail className="h-4 w-4" />,
    color: "bg-blue-500",
  },
  sms: {
    label: "SMS",
    icon: <MessageSquare className="h-4 w-4" />,
    color: "bg-green-500",
  },
  linkedin: {
    label: "LinkedIn",
    icon: <Linkedin className="h-4 w-4" />,
    color: "bg-sky-500",
  },
  voice: {
    label: "Voice",
    icon: <Phone className="h-4 w-4" />,
    color: "bg-purple-500",
  },
  mail: {
    label: "Direct Mail",
    icon: <Send className="h-4 w-4" />,
    color: "bg-amber-500",
  },
};

// ============================================
// Helper Functions
// ============================================

/**
 * Format percentage with one decimal place
 */
function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

/**
 * Format large numbers with commas
 */
function formatNumber(value: number): string {
  return value.toLocaleString();
}

/**
 * Get performance status based on reply rate
 */
function getPerformanceStatus(replyRate: number): {
  label: string;
  color: string;
} {
  if (replyRate >= 5) {
    return { label: "Excellent", color: "text-green-600 dark:text-green-400" };
  } else if (replyRate >= 3) {
    return { label: "Good", color: "text-blue-600 dark:text-blue-400" };
  } else if (replyRate >= 1) {
    return { label: "Average", color: "text-amber-600 dark:text-amber-400" };
  }
  return { label: "Needs attention", color: "text-red-600 dark:text-red-400" };
}

// ============================================
// Main Component
// ============================================

/**
 * CampaignMetricsPanel displays key performance metrics for a campaign.
 *
 * Shows:
 * - Meetings booked (hero metric)
 * - Show rate percentage
 * - Reply rate percentage
 * - Active sequences count
 * - Channel allocation breakdown
 */
export function CampaignMetricsPanel({
  campaign,
  className,
  compact = false,
}: CampaignMetricsPanelProps) {
  const performance = getPerformanceStatus(campaign.reply_rate);

  // Calculate channel allocations
  const channelAllocations = [
    { channel: "email" as ChannelType, value: campaign.allocation_email },
    { channel: "sms" as ChannelType, value: campaign.allocation_sms },
    { channel: "linkedin" as ChannelType, value: campaign.allocation_linkedin },
    { channel: "voice" as ChannelType, value: campaign.allocation_voice },
    { channel: "mail" as ChannelType, value: campaign.allocation_mail },
  ].filter((a) => a.value > 0);

  const totalAllocation = channelAllocations.reduce((sum, a) => sum + a.value, 0);

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Campaign Performance</CardTitle>
          <Badge
            variant="outline"
            className={cn("font-medium", performance.color)}
          >
            {performance.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Hero Metrics Grid */}
        <div
          className={cn(
            "grid gap-4",
            compact ? "grid-cols-2" : "grid-cols-2 md:grid-cols-4"
          )}
        >
          {/* Meetings Booked - Hero Metric */}
          <MetricCard
            icon={<Target className="h-5 w-5 text-green-500" />}
            label="Meetings"
            value={formatNumber(campaign.meetings_booked)}
            compact={compact}
          />

          {/* Show Rate */}
          <MetricCard
            icon={<TrendingUp className="h-5 w-5 text-purple-500" />}
            label="Show Rate"
            value={formatPercent(campaign.show_rate)}
            compact={compact}
          />

          {/* Reply Rate */}
          <MetricCard
            icon={<MessageCircle className="h-5 w-5 text-blue-500" />}
            label="Reply Rate"
            value={formatPercent(campaign.reply_rate)}
            compact={compact}
          />

          {/* Active Sequences */}
          <MetricCard
            icon={<Users className="h-5 w-5 text-amber-500" />}
            label="In Sequence"
            value={formatNumber(campaign.active_sequences)}
            compact={compact}
          />
        </div>

        {/* Activity Summary */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {formatNumber(campaign.leads_replied)} replies from{" "}
            {formatNumber(campaign.leads_contacted)} contacted
          </span>
          <span className="text-muted-foreground">
            {formatNumber(campaign.leads_converted)} conversions
          </span>
        </div>

        {/* Channel Allocation */}
        {channelAllocations.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">
              Channel Mix
            </h4>

            {/* Stacked bar */}
            <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
              {channelAllocations.map((allocation) => {
                const config = CHANNEL_CONFIG[allocation.channel];
                const widthPercent =
                  totalAllocation > 0
                    ? (allocation.value / totalAllocation) * 100
                    : 0;
                return (
                  <div
                    key={allocation.channel}
                    className={cn("h-full", config.color)}
                    style={{ width: `${widthPercent}%` }}
                    title={`${config.label}: ${allocation.value}%`}
                  />
                );
              })}
            </div>

            {/* Channel legend */}
            <div className="flex flex-wrap gap-3">
              {channelAllocations.map((allocation) => {
                const config = CHANNEL_CONFIG[allocation.channel];
                return (
                  <div
                    key={allocation.channel}
                    className="flex items-center gap-1.5 text-sm"
                  >
                    <div
                      className={cn("h-2.5 w-2.5 rounded-full", config.color)}
                    />
                    <span className="text-muted-foreground">
                      {config.label}
                    </span>
                    <span className="font-medium">{allocation.value}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty channel state */}
        {channelAllocations.length === 0 && (
          <div className="rounded-lg border border-dashed p-4 text-center">
            <p className="text-sm text-muted-foreground">
              No channel allocations configured
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================
// Metric Card Sub-component
// ============================================

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  compact?: boolean;
}

function MetricCard({ icon, label, value, compact }: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-3",
        compact ? "space-y-1" : "space-y-2"
      )}
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-xs font-medium text-muted-foreground">
          {label}
        </span>
      </div>
      <p className={cn("font-bold", compact ? "text-lg" : "text-2xl")}>
        {value}
      </p>
    </div>
  );
}

export default CampaignMetricsPanel;
