"use client";

import { useState } from "react";
import {
  Mail,
  MessageSquare,
  Linkedin,
  Phone,
  FileText,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Calendar,
} from "lucide-react";

/**
 * Channel type
 */
export type Channel = "email" | "sms" | "linkedin" | "voice" | "mail";

/**
 * Activity item
 */
export interface ActivityItem {
  /** Unique activity ID */
  id: string;
  /** Channel used */
  channel: Channel;
  /** Action description */
  action: string;
  /** Timestamp */
  timestamp: string;
  /** Subject line (for emails) */
  subject?: string;
  /** Content preview */
  contentPreview?: string;
  /** Full content */
  content?: string;
  /** Reply intent */
  intent?: "positive" | "negative" | "neutral" | "info_request";
  /** Sequence step number */
  sequenceStep?: number;
  /** Is this a reply? */
  isReply?: boolean;
  /** Meeting time (for meeting activities) */
  meetingTime?: string;
}

/**
 * LeadTimeline props
 */
export interface LeadTimelineProps {
  /** Array of activities */
  activities: ActivityItem[];
}

/**
 * Channel configuration
 */
const channelConfig: Record<
  Channel,
  { icon: React.ComponentType<{ className?: string }>; color: string; bg: string }
> = {
  email: { icon: Mail, color: "text-[#3B82F6]", bg: "bg-[#DBEAFE]" },
  sms: { icon: MessageSquare, color: "text-[#10B981]", bg: "bg-[#D1FAE5]" },
  linkedin: { icon: Linkedin, color: "text-[#0077B5]", bg: "bg-[#E0F2FE]" },
  voice: { icon: Phone, color: "text-[#8B5CF6]", bg: "bg-[#EDE9FE]" },
  mail: { icon: FileText, color: "text-[#F59E0B]", bg: "bg-[#FEF3C7]" },
};

/**
 * Intent badge configuration
 */
const intentConfig: Record<
  string,
  { label: string; bg: string; text: string }
> = {
  positive: { label: "Positive Intent", bg: "bg-[#D1FAE5]", text: "text-[#065F46]" },
  negative: { label: "Not Interested", bg: "bg-[#FEE2E2]", text: "text-[#991B1B]" },
  neutral: { label: "Neutral", bg: "bg-[#E5E7EB]", text: "text-[#374151]" },
  info_request: { label: "Info Request", bg: "bg-[#DBEAFE]", text: "text-[#1E40AF]" },
};

/**
 * Format relative time
 */
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins} minutes ago`;
  if (diffHours < 24) return `${diffHours} hours ago`;
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

/**
 * Single timeline item component
 */
function TimelineItem({ activity }: { activity: ActivityItem }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const config = channelConfig[activity.channel];
  const Icon = config.icon;

  const handleCopy = async () => {
    const textToCopy = activity.content || activity.contentPreview || activity.action;
    await navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasExpandableContent = activity.content || activity.contentPreview;

  return (
    <div className="relative pl-8">
      {/* Timeline connector line */}
      <div className="absolute left-3 top-8 bottom-0 w-0.5 bg-[#E2E8F0]" />

      {/* Icon circle */}
      <div
        className={`absolute left-0 top-1 w-6 h-6 rounded-full flex items-center justify-center ${config.bg}`}
      >
        <Icon className={`h-3.5 w-3.5 ${config.color}`} />
      </div>

      {/* Content */}
      <div
        className={`pb-6 ${
          activity.isReply
            ? "bg-[#EFF6FF] -ml-2 pl-4 pr-4 py-3 rounded-lg border-l-4 border-[#3B82F6]"
            : ""
        }`}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-[#1E293B]">
                {activity.action}
              </span>
              {activity.intent && (
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    intentConfig[activity.intent].bg
                  } ${intentConfig[activity.intent].text}`}
                >
                  {intentConfig[activity.intent].label}
                </span>
              )}
            </div>
            {activity.subject && (
              <p className="text-sm text-[#64748B] mt-0.5">
                &quot;{activity.subject}&quot;
              </p>
            )}
          </div>
          <span className="text-xs text-[#94A3B8] whitespace-nowrap">
            {formatRelativeTime(activity.timestamp)}
          </span>
        </div>

        {/* Meeting time */}
        {activity.meetingTime && (
          <div className="flex items-center gap-2 mt-2 text-sm text-[#64748B]">
            <Calendar className="h-4 w-4" />
            <span>{activity.meetingTime}</span>
          </div>
        )}

        {/* Expandable content */}
        {hasExpandableContent && (
          <div className="mt-2">
            {!isExpanded ? (
              <button
                onClick={() => setIsExpanded(true)}
                className="flex items-center gap-1 text-xs text-[#3B82F6] hover:text-[#2563EB] transition-colors"
              >
                <ChevronDown className="h-3.5 w-3.5" />
                Show content
              </button>
            ) : (
              <div className="mt-2">
                <div className="bg-white border border-[#E2E8F0] rounded-lg p-3">
                  <p className="text-sm text-[#374151] whitespace-pre-wrap">
                    {activity.content || activity.contentPreview}
                  </p>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => setIsExpanded(false)}
                    className="flex items-center gap-1 text-xs text-[#3B82F6] hover:text-[#2563EB] transition-colors"
                  >
                    <ChevronUp className="h-3.5 w-3.5" />
                    Show less
                  </button>
                  <button
                    onClick={handleCopy}
                    className="flex items-center gap-1 text-xs text-[#64748B] hover:text-[#374151] transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-[#10B981]" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * LeadTimeline - Activity timeline component
 *
 * Features:
 * - Vertical timeline with channel icons
 * - Color-coded channels
 * - Expandable content preview
 * - Copy button for content
 * - Reply highlighting
 * - Intent badges
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Email: #3B82F6 (channel-email)
 * - SMS: #10B981 (channel-sms)
 * - LinkedIn: #0077B5 (channel-linkedin)
 * - Voice: #8B5CF6 (channel-voice)
 * - Mail: #F59E0B (channel-mail)
 *
 * Usage:
 * ```tsx
 * <LeadTimeline activities={activities} />
 * ```
 */
export function LeadTimeline({ activities }: LeadTimelineProps) {
  if (activities.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
        <div className="px-6 py-4 border-b border-[#E2E8F0]">
          <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
            Activity Timeline
          </h2>
        </div>
        <div className="p-6 text-center">
          <p className="text-sm text-[#94A3B8]">No activities yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
            Activity Timeline
          </h2>
          <span className="text-xs text-[#94A3B8]">
            Click to expand
          </span>
        </div>
      </div>

      {/* Timeline */}
      <div className="p-6">
        {activities.map((activity) => (
          <TimelineItem key={activity.id} activity={activity} />
        ))}
      </div>
    </div>
  );
}

export default LeadTimeline;
