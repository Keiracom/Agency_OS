/**
 * FILE: frontend/components/campaigns/CampaignPriorityCard.tsx
 * PURPOSE: Individual campaign card with priority slider and metrics
 * PHASE: Phase I Dashboard Redesign (Item 54)
 *
 * Layout:
 * - Header: Campaign name + icon + badge (AI SUGGESTED / CUSTOM)
 * - Body: PrioritySlider component
 * - Metrics: Meetings, reply rate, show rate
 * - Footer: Channels + Status
 *
 * Visual States:
 * - Default: Standard card styling
 * - Changed: Yellow border when hasChanges=true
 * - Disabled: Faded when status is paused/draft
 */

"use client";

import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Bot, FileText, Mail, Linkedin, Phone, MessageSquare } from "lucide-react";
import { PrioritySlider } from "./PrioritySlider";
import type { CampaignStatus } from "@/lib/api/types";

export type CampaignType = "ai" | "custom";

export interface CampaignCardMetrics {
  /** Meetings booked this month */
  meetingsBooked?: number;
  /** Reply rate percentage */
  replyRate?: number;
  /** Show rate percentage */
  showRate?: number;
}

export interface CampaignCardChannel {
  email?: boolean;
  linkedin?: boolean;
  sms?: boolean;
  voice?: boolean;
}

export interface CampaignPriorityCardProps {
  /** Campaign ID */
  id: string;
  /** Campaign name */
  name: string;
  /** Campaign type (AI-suggested or custom) */
  type: CampaignType;
  /** Campaign status */
  status: CampaignStatus;
  /** Current priority percentage (10-80) */
  priorityPct: number;
  /** Active channels */
  channels: CampaignCardChannel;
  /** Campaign metrics for this month */
  metrics?: CampaignCardMetrics;
  /** Whether this card has pending changes */
  hasChanges?: boolean;
  /** Callback when priority changes */
  onPriorityChange?: (campaignId: string, newValue: number) => void;
  /** Additional class names */
  className?: string;
}

/**
 * Campaign priority card with slider and metrics.
 *
 * Used in CampaignPriorityPanel to display individual campaigns
 * with their allocation slider and performance metrics.
 */
export function CampaignPriorityCard({
  id,
  name,
  type,
  status,
  priorityPct,
  channels,
  metrics,
  hasChanges = false,
  onPriorityChange,
  className,
}: CampaignPriorityCardProps) {
  const isInteractive = status === "active";

  const handlePriorityChange = (newValue: number) => {
    onPriorityChange?.(id, newValue);
  };

  return (
    <Card
      className={cn(
        "w-full transition-all",
        // Yellow border when changes are pending
        hasChanges && "ring-2 ring-amber-400 border-amber-400",
        // Faded when paused/draft
        !isInteractive && "opacity-60",
        className
      )}
    >
      <CardContent className="pt-4 pb-4 space-y-4">
        {/* Header: Name + Badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CampaignTypeIcon type={type} />
            <h3 className="font-medium text-base">{name}</h3>
          </div>
          <CampaignTypeBadge type={type} />
        </div>

        {/* Priority Slider */}
        <PrioritySlider
          value={priorityPct}
          onChange={handlePriorityChange}
          campaignName={name}
          disabled={!isInteractive}
        />

        {/* Metrics Row */}
        {metrics && <MetricsRow metrics={metrics} />}

        {/* Footer: Channels + Status */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <ChannelsList channels={channels} />
          <StatusBadge status={status} />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Campaign type icon (AI or Custom)
 */
function CampaignTypeIcon({ type }: { type: CampaignType }) {
  if (type === "ai") {
    return <Bot className="h-5 w-5 text-primary" />;
  }
  return <FileText className="h-5 w-5 text-muted-foreground" />;
}

/**
 * Campaign type badge
 */
function CampaignTypeBadge({ type }: { type: CampaignType }) {
  if (type === "ai") {
    return (
      <Badge variant="secondary" className="text-xs">
        AI SUGGESTED
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="text-xs">
      CUSTOM
    </Badge>
  );
}

/**
 * Metrics row showing campaign performance
 */
function MetricsRow({ metrics }: { metrics: CampaignCardMetrics }) {
  const items: string[] = [];

  if (metrics.meetingsBooked !== undefined) {
    items.push(
      `${metrics.meetingsBooked} meeting${metrics.meetingsBooked !== 1 ? "s" : ""} booked`
    );
  }

  if (metrics.replyRate !== undefined) {
    items.push(`${metrics.replyRate.toFixed(1)}% reply rate`);
  }

  if (metrics.showRate !== undefined) {
    items.push(`${metrics.showRate.toFixed(0)}% show rate`);
  }

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="bg-muted/50 rounded-md p-3">
      <p className="text-xs text-muted-foreground mb-1">This Month</p>
      <p className="text-sm">{items.join("  •  ")}</p>
    </div>
  );
}

/**
 * List of active channels
 */
function ChannelsList({ channels }: { channels: CampaignCardChannel }) {
  const activeChannels: { name: string; icon: React.ReactNode }[] = [];

  if (channels.email) {
    activeChannels.push({ name: "Email", icon: <Mail className="h-3 w-3" /> });
  }
  if (channels.linkedin) {
    activeChannels.push({ name: "LinkedIn", icon: <Linkedin className="h-3 w-3" /> });
  }
  if (channels.sms) {
    activeChannels.push({ name: "SMS", icon: <MessageSquare className="h-3 w-3" /> });
  }
  if (channels.voice) {
    activeChannels.push({ name: "Voice", icon: <Phone className="h-3 w-3" /> });
  }

  if (activeChannels.length === 0) {
    return <span>No channels</span>;
  }

  return (
    <div className="flex items-center gap-1">
      <span>Channels:</span>
      <div className="flex items-center gap-2">
        {activeChannels.map(({ name, icon }) => (
          <span key={name} className="flex items-center gap-1" title={name}>
            {icon}
            <span className="hidden sm:inline">{name}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Campaign status badge
 */
function StatusBadge({ status }: { status: CampaignStatus }) {
  const statusConfig: Record<
    CampaignStatus,
    { label: string; className: string }
  > = {
    active: {
      label: "Active",
      className: "text-green-600",
    },
    paused: {
      label: "Paused",
      className: "text-amber-600",
    },
    draft: {
      label: "Draft",
      className: "text-muted-foreground",
    },
    completed: {
      label: "Completed",
      className: "text-blue-600",
    },
  };

  const config = statusConfig[status] || statusConfig.draft;

  return (
    <span className={cn("font-medium", config.className)}>
      Status: {config.label}
    </span>
  );
}

export default CampaignPriorityCard;
