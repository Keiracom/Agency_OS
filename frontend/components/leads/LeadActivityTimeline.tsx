/**
 * FILE: frontend/components/leads/LeadActivityTimeline.tsx
 * PURPOSE: Reusable timeline component for displaying lead activity history
 * PHASE: Frontend Components
 * TASK: Fix #27 - LeadActivityTimeline Component
 */

"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Mail,
  Phone,
  Linkedin,
  MessageSquare,
  Package,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  Send,
  Reply,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Filter,
  MousePointerClick,
  AlertCircle,
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { Activity, ChannelType } from "@/lib/api/types";

// ============================================
// Types
// ============================================

interface LeadActivityTimelineProps {
  activities: Activity[];
  isLoading?: boolean;
  className?: string;
  maxHeight?: string;
  showFilter?: boolean;
  showHeader?: boolean;
  title?: string;
  emptyMessage?: string;
}

// ============================================
// Constants
// ============================================

const activityIcons: Record<string, React.ReactNode> = {
  // Email actions
  email_sent: <Send className="h-4 w-4" />,
  email_delivered: <CheckCircle className="h-4 w-4" />,
  email_opened: <Eye className="h-4 w-4" />,
  email_clicked: <MousePointerClick className="h-4 w-4" />,
  email_replied: <Reply className="h-4 w-4" />,
  email_bounced: <XCircle className="h-4 w-4" />,
  sent: <Send className="h-4 w-4" />,
  delivered: <CheckCircle className="h-4 w-4" />,
  opened: <Eye className="h-4 w-4" />,
  clicked: <MousePointerClick className="h-4 w-4" />,
  replied: <Reply className="h-4 w-4" />,
  bounced: <XCircle className="h-4 w-4" />,
  // SMS actions
  sms_sent: <MessageSquare className="h-4 w-4" />,
  sms_delivered: <CheckCircle className="h-4 w-4" />,
  sms_replied: <Reply className="h-4 w-4" />,
  // Voice actions
  call_initiated: <Phone className="h-4 w-4" />,
  call_completed: <CheckCircle className="h-4 w-4" />,
  call_no_answer: <XCircle className="h-4 w-4" />,
  called: <Phone className="h-4 w-4" />,
  answered: <CheckCircle className="h-4 w-4" />,
  voicemail: <AlertCircle className="h-4 w-4" />,
  // LinkedIn actions
  linkedin_viewed: <Eye className="h-4 w-4" />,
  linkedin_connected: <Linkedin className="h-4 w-4" />,
  linkedin_messaged: <Send className="h-4 w-4" />,
  linkedin_sent: <Send className="h-4 w-4" />,
  linkedin_accepted: <CheckCircle className="h-4 w-4" />,
  linkedin_replied: <Reply className="h-4 w-4" />,
  // Mail actions
  mail_sent: <Package className="h-4 w-4" />,
  mail_delivered: <CheckCircle className="h-4 w-4" />,
  // System actions
  status_change: <Clock className="h-4 w-4" />,
  converted: <CheckCircle className="h-4 w-4" />,
  unsubscribed: <XCircle className="h-4 w-4" />,
};

const channelIcons: Record<string, React.ReactNode> = {
  email: <Mail className="h-4 w-4" />,
  sms: <MessageSquare className="h-4 w-4" />,
  voice: <Phone className="h-4 w-4" />,
  linkedin: <Linkedin className="h-4 w-4" />,
  mail: <Package className="h-4 w-4" />,
  system: <Clock className="h-4 w-4" />,
};

const channelColors: Record<string, string> = {
  email: "bg-blue-500",
  sms: "bg-green-500",
  voice: "bg-purple-500",
  linkedin: "bg-sky-500",
  mail: "bg-amber-500",
  system: "bg-gray-500",
};

const channelBadgeColors: Record<string, string> = {
  email: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  sms: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  voice: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  linkedin: "bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-400",
  mail: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  system: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

const allChannels: ChannelType[] = ["email", "sms", "linkedin", "voice", "mail"];

// ============================================
// Helper Functions
// ============================================

function getActivityIcon(action: string, channel: string): React.ReactNode {
  // Try action-specific icon first (e.g., "email_sent")
  const channelAction = `${channel}_${action}`;
  if (activityIcons[channelAction]) {
    return activityIcons[channelAction];
  }
  // Fall back to generic action icon
  if (activityIcons[action]) {
    return activityIcons[action];
  }
  // Fall back to channel icon
  return channelIcons[channel] || <Clock className="h-4 w-4" />;
}

function formatActionLabel(action: string): string {
  return action
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

// ============================================
// Sub-components
// ============================================

function TimelineItemSkeleton() {
  return (
    <div className="flex gap-4 animate-pulse">
      <div className="flex flex-col items-center">
        <div className="h-3 w-3 rounded-full bg-muted" />
        <div className="w-0.5 flex-1 bg-muted my-1" />
      </div>
      <div className="flex-1 pb-4">
        <div className="h-4 w-32 bg-muted rounded mb-2" />
        <div className="h-3 w-24 bg-muted rounded" />
      </div>
    </div>
  );
}

function TimelineItem({
  activity,
  isLast,
}: {
  activity: Activity;
  isLast: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  const hasContent = activity.content_preview && activity.content_preview.length > 0;
  const isSent = activity.action.includes("sent");
  const isReceived = activity.action.includes("replied") || activity.action.includes("received");

  const handleCopy = async () => {
    if (activity.content_preview) {
      await navigator.clipboard.writeText(activity.content_preview);
      setCopied(true);
      toast({ title: "Copied to clipboard" });
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const channelColor = channelColors[activity.channel] || "bg-gray-500";
  const timestamp = new Date(activity.created_at);

  return (
    <div className="flex gap-4">
      {/* Timeline indicator */}
      <div className="flex flex-col items-center">
        <div className={cn("h-3 w-3 rounded-full", channelColor)} />
        {!isLast && <div className="w-0.5 flex-1 bg-muted my-1" />}
      </div>

      {/* Content */}
      <div className={cn("flex-1 pb-4", isReceived && "pl-0")}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">
              {getActivityIcon(activity.action, activity.channel)}
            </span>
            <span className="font-medium text-sm">
              {formatActionLabel(activity.action)}
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {activity.intent && (
              <Badge variant="outline" className="capitalize text-xs">
                {activity.intent.replace("_", " ")}
              </Badge>
            )}
            <Badge
              variant="secondary"
              className={cn("text-xs capitalize", channelBadgeColors[activity.channel])}
            >
              {activity.channel}
            </Badge>
          </div>
        </div>

        {/* Timestamp */}
        <p className="text-xs text-muted-foreground mt-1">
          {formatDistanceToNow(timestamp, { addSuffix: true })}
          <span className="mx-1">-</span>
          {format(timestamp, "MMM d, yyyy 'at' h:mm a")}
        </p>

        {/* Sequence step */}
        {activity.sequence_step && (
          <p className="text-xs text-muted-foreground mt-1">
            Step {activity.sequence_step} in sequence
          </p>
        )}

        {/* Subject line for emails */}
        {activity.subject && (
          <p className="text-sm font-medium mt-2">
            Subject: {activity.subject}
          </p>
        )}

        {/* Content preview with expand */}
        {hasContent && (
          <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-2">
            <div
              className={cn(
                "rounded-lg p-3 text-sm",
                isReceived
                  ? "bg-blue-50 dark:bg-blue-950 border-l-4 border-blue-500"
                  : "bg-muted"
              )}
            >
              {/* Preview (always shown) */}
              <p className={cn("whitespace-pre-wrap", !isOpen && "line-clamp-2")}>
                {isOpen
                  ? activity.content_preview
                  : (activity.content_preview?.slice(0, 100) ?? "") +
                    ((activity.content_preview?.length ?? 0) > 100 ? "..." : "")}
              </p>

              {/* Actions */}
              <div className="flex items-center gap-2 mt-2">
                {(activity.content_preview?.length ?? 0) > 100 && (
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-7 text-xs">
                      {isOpen ? (
                        <>
                          <ChevronUp className="h-3 w-3 mr-1" />
                          Show less
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-3 w-3 mr-1" />
                          Show more
                        </>
                      )}
                    </Button>
                  </CollapsibleTrigger>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <Check className="h-3 w-3 mr-1" />
                  ) : (
                    <Copy className="h-3 w-3 mr-1" />
                  )}
                  Copy
                </Button>
              </div>
            </div>
          </Collapsible>
        )}
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function LeadActivityTimeline({
  activities,
  isLoading = false,
  className,
  maxHeight = "400px",
  showFilter = true,
  showHeader = true,
  title = "Activity Timeline",
  emptyMessage = "No activity yet",
}: LeadActivityTimelineProps) {
  const [selectedChannels, setSelectedChannels] = useState<Set<ChannelType>>(
    new Set(allChannels)
  );

  // Filter activities by selected channels
  const filteredActivities = useMemo(() => {
    if (selectedChannels.size === allChannels.length) {
      return activities;
    }
    return activities.filter((activity) =>
      selectedChannels.has(activity.channel as ChannelType)
    );
  }, [activities, selectedChannels]);

  const toggleChannel = (channel: ChannelType) => {
    const newSelected = new Set(selectedChannels);
    if (newSelected.has(channel)) {
      newSelected.delete(channel);
    } else {
      newSelected.add(channel);
    }
    // Ensure at least one channel is selected
    if (newSelected.size > 0) {
      setSelectedChannels(newSelected);
    }
  };

  const selectAllChannels = () => {
    setSelectedChannels(new Set(allChannels));
  };

  // Loading state
  if (isLoading) {
    return (
      <Card className={className}>
        {showHeader && (
          <CardHeader>
            <CardTitle className="text-base">{title}</CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <div className="space-y-0">
            {[1, 2, 3].map((i) => (
              <TimelineItemSkeleton key={i} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Empty state
  if (!activities || activities.length === 0) {
    return (
      <Card className={className}>
        {showHeader && (
          <CardHeader>
            <CardTitle className="text-base">{title}</CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <EmptyState
            icon={MessageSquare}
            title={emptyMessage}
            description="Outreach activity will appear here once the campaign starts"
            className="py-8"
          />
        </CardContent>
      </Card>
    );
  }

  // Filtered empty state
  if (filteredActivities.length === 0) {
    return (
      <Card className={className}>
        {showHeader && (
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base">{title}</CardTitle>
            {showFilter && (
              <ChannelFilter
                selectedChannels={selectedChannels}
                onToggleChannel={toggleChannel}
                onSelectAll={selectAllChannels}
              />
            )}
          </CardHeader>
        )}
        <CardContent>
          <EmptyState
            icon={Filter}
            title="No matching activities"
            description="Try adjusting your filter to see more activities"
            className="py-8"
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      {showHeader && (
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              {filteredActivities.length} activities
              {filteredActivities.length !== activities.length && (
                <span> (filtered from {activities.length})</span>
              )}
            </p>
          </div>
          {showFilter && (
            <ChannelFilter
              selectedChannels={selectedChannels}
              onToggleChannel={toggleChannel}
              onSelectAll={selectAllChannels}
            />
          )}
        </CardHeader>
      )}
      <CardContent>
        <div
          className="overflow-y-auto pr-2"
          style={{ maxHeight }}
        >
          <div className="space-y-0">
            {filteredActivities.map((activity, index) => (
              <TimelineItem
                key={activity.id}
                activity={activity}
                isLast={index === filteredActivities.length - 1}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================
// Filter Component
// ============================================

function ChannelFilter({
  selectedChannels,
  onToggleChannel,
  onSelectAll,
}: {
  selectedChannels: Set<ChannelType>;
  onToggleChannel: (channel: ChannelType) => void;
  onSelectAll: () => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 gap-1">
          <Filter className="h-3.5 w-3.5" />
          <span className="sr-only sm:not-sr-only sm:whitespace-nowrap">
            Filter
          </span>
          {selectedChannels.size < allChannels.length && (
            <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
              {selectedChannels.size}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[150px]">
        <DropdownMenuLabel>Filter by channel</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {allChannels.map((channel) => (
          <DropdownMenuCheckboxItem
            key={channel}
            checked={selectedChannels.has(channel)}
            onCheckedChange={() => onToggleChannel(channel)}
          >
            <span className="flex items-center gap-2">
              <span className={cn("h-2 w-2 rounded-full", channelColors[channel])} />
              <span className="capitalize">{channel}</span>
            </span>
          </DropdownMenuCheckboxItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuCheckboxItem
          checked={selectedChannels.size === allChannels.length}
          onCheckedChange={onSelectAll}
        >
          Select all
        </DropdownMenuCheckboxItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default LeadActivityTimeline;
