"use client";

import {
  Mail,
  Linkedin,
  MessageSquare,
  Phone,
  Reply,
  Forward,
  Archive,
  Sparkles,
  Building2,
  User,
  Clock,
  ExternalLink,
} from "lucide-react";
import { ReplyChannel, ReplyIntent, ALSTier } from "./ReplyCard";

/**
 * Thread message type
 */
export interface ThreadMessage {
  /** Message ID */
  id: string;
  /** Sender: "lead" or "agency" */
  sender: "lead" | "agency";
  /** Message content */
  content: string;
  /** Timestamp */
  timestamp: string;
}

/**
 * Full reply object type
 */
export interface Reply {
  /** Unique reply ID */
  id: string;
  /** Lead's full name */
  leadName: string;
  /** Lead's company name */
  leadCompany: string;
  /** Lead's job title */
  leadTitle?: string;
  /** Lead's email */
  leadEmail?: string;
  /** Lead's LinkedIn URL */
  leadLinkedIn?: string;
  /** Communication channel */
  channel: ReplyChannel;
  /** Email subject or message topic */
  subject: string;
  /** Preview of the message content */
  preview: string;
  /** Full message content */
  content: string;
  /** When the reply was received */
  timestamp: string;
  /** AI-classified intent */
  intent: ReplyIntent;
  /** Lead's ALS tier */
  tierBadge: ALSTier;
  /** Lead's ALS score */
  alsScore: number;
  /** Whether the reply is unread */
  isUnread?: boolean;
  /** Thread history */
  threadHistory?: ThreadMessage[];
  /** AI suggested response */
  aiSuggestedResponse?: string;
  /** Campaign name */
  campaignName?: string;
}

/**
 * ReplyDetail props
 */
export interface ReplyDetailProps {
  /** Full reply object */
  reply: Reply;
  /** Handler for reply action */
  onReply?: () => void;
  /** Handler for forward action */
  onForward?: () => void;
  /** Handler for archive action */
  onArchive?: () => void;
}

/**
 * Channel icon and color mapping
 */
const channelConfig: Record<
  ReplyChannel,
  { icon: React.ComponentType<{ className?: string }>; color: string; bgColor: string; label: string }
> = {
  email: { icon: Mail, color: "#3B82F6", bgColor: "#DBEAFE", label: "Email" },
  linkedin: { icon: Linkedin, color: "#0077B5", bgColor: "#E0F2FE", label: "LinkedIn" },
  sms: { icon: MessageSquare, color: "#10B981", bgColor: "#D1FAE5", label: "SMS" },
  voice: { icon: Phone, color: "#8B5CF6", bgColor: "#EDE9FE", label: "Voice" },
};

/**
 * Intent badge styling
 */
const intentConfig: Record<
  ReplyIntent,
  { label: string; textColor: string; bgColor: string }
> = {
  positive: { label: "Positive", textColor: "#059669", bgColor: "#D1FAE5" },
  negative: { label: "Negative", textColor: "#DC2626", bgColor: "#FEE2E2" },
  neutral: { label: "Neutral", textColor: "#64748B", bgColor: "#F1F5F9" },
  question: { label: "Question", textColor: "#7C3AED", bgColor: "#EDE9FE" },
};

/**
 * Tier badge styling
 */
const tierConfig: Record<
  ALSTier,
  { label: string; textColor: string; bgColor: string }
> = {
  hot: { label: "Hot", textColor: "#FFFFFF", bgColor: "#EF4444" },
  warm: { label: "Warm", textColor: "#FFFFFF", bgColor: "#F97316" },
  cool: { label: "Cool", textColor: "#FFFFFF", bgColor: "#3B82F6" },
  cold: { label: "Cold", textColor: "#FFFFFF", bgColor: "#6B7280" },
  dead: { label: "Dead", textColor: "#374151", bgColor: "#D1D5DB" },
};

/**
 * ReplyDetail - Full reply view panel
 *
 * Features:
 * - Lead info header with name, company, title
 * - Channel badge with icon
 * - Full message content
 * - Thread history (previous messages in conversation)
 * - Quick actions (Reply, Forward, Archive)
 * - AI suggested response card
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Card background: #FFFFFF (card-bg)
 * - Card border: #E2E8F0 (card-border)
 * - Accent blue: #3B82F6 (accent-blue)
 * - Accent purple: #8B5CF6 (accent-purple) - for AI suggestions
 * - Text primary: #1E293B (text-primary)
 * - Text secondary: #64748B (text-secondary)
 */
export function ReplyDetail({
  reply,
  onReply,
  onForward,
  onArchive,
}: ReplyDetailProps) {
  const channelInfo = channelConfig[reply.channel];
  const intentInfo = intentConfig[reply.intent];
  const tierInfo = tierConfig[reply.tierBadge];
  const ChannelIcon = channelInfo.icon;

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header Section */}
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        {/* Lead Info Row */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-4">
            {/* Avatar placeholder */}
            <div className="w-12 h-12 bg-[#E2E8F0] rounded-full flex items-center justify-center">
              <User className="h-6 w-6 text-[#64748B]" />
            </div>

            <div>
              <h2 className="text-lg font-semibold text-[#1E293B]">
                {reply.leadName}
              </h2>
              <div className="flex items-center gap-2 text-sm text-[#64748B]">
                <Building2 className="h-4 w-4" />
                <span>{reply.leadCompany}</span>
                {reply.leadTitle && (
                  <>
                    <span className="text-[#94A3B8]">-</span>
                    <span>{reply.leadTitle}</span>
                  </>
                )}
              </div>
              {reply.campaignName && (
                <p className="text-xs text-[#94A3B8] mt-1">
                  Campaign: {reply.campaignName}
                </p>
              )}
            </div>
          </div>

          {/* Badges */}
          <div className="flex items-center gap-2">
            {/* Channel Badge */}
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
              style={{ backgroundColor: channelInfo.bgColor }}
            >
              <span style={{ color: channelInfo.color }}>
                <ChannelIcon className="h-3.5 w-3.5" />
              </span>
              <span
                className="text-xs font-medium"
                style={{ color: channelInfo.color }}
              >
                {channelInfo.label}
              </span>
            </div>

            {/* Intent Badge */}
            <span
              className="px-2.5 py-1 rounded-full text-xs font-medium"
              style={{
                backgroundColor: intentInfo.bgColor,
                color: intentInfo.textColor,
              }}
            >
              {intentInfo.label}
            </span>

            {/* Tier Badge */}
            <span
              className="px-2.5 py-1 rounded-full text-xs font-medium"
              style={{
                backgroundColor: tierInfo.bgColor,
                color: tierInfo.textColor,
              }}
            >
              {tierInfo.label} ({reply.alsScore})
            </span>
          </div>
        </div>

        {/* Subject and timestamp */}
        <div className="flex items-center justify-between">
          <h3 className="text-base font-medium text-[#1E293B]">{reply.subject}</h3>
          <div className="flex items-center gap-1.5 text-sm text-[#94A3B8]">
            <Clock className="h-4 w-4" />
            <span>{reply.timestamp}</span>
          </div>
        </div>
      </div>

      {/* Content Section - scrollable */}
      <div className="flex-1 overflow-auto">
        {/* Thread History */}
        {reply.threadHistory && reply.threadHistory.length > 0 && (
          <div className="px-6 py-4 bg-[#F8FAFC] border-b border-[#E2E8F0]">
            <p className="text-xs font-medium text-[#64748B] uppercase tracking-wider mb-3">
              Previous Messages
            </p>
            <div className="space-y-3">
              {reply.threadHistory.map((message) => (
                <div
                  key={message.id}
                  className={`p-3 rounded-lg ${
                    message.sender === "agency"
                      ? "bg-[#DBEAFE] ml-4"
                      : "bg-white border border-[#E2E8F0] mr-4"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-[#64748B]">
                      {message.sender === "agency" ? "You" : reply.leadName}
                    </span>
                    <span className="text-xs text-[#94A3B8]">{message.timestamp}</span>
                  </div>
                  <p className="text-sm text-[#1E293B] whitespace-pre-wrap">
                    {message.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Current Message */}
        <div className="px-6 py-6">
          <div className="bg-[#F8FAFC] rounded-xl p-4 border border-[#E2E8F0]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-[#1E293B]">
                {reply.leadName}
              </span>
              <span className="text-xs text-[#94A3B8]">{reply.timestamp}</span>
            </div>
            <p className="text-sm text-[#1E293B] whitespace-pre-wrap leading-relaxed">
              {reply.content}
            </p>
          </div>
        </div>

        {/* AI Suggested Response */}
        {reply.aiSuggestedResponse && (
          <div className="px-6 pb-6">
            <div className="bg-[#F5F3FF] rounded-xl p-4 border border-[#DDD6FE]">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1.5 bg-[#8B5CF6] rounded-lg">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <span className="text-sm font-semibold text-[#7C3AED]">
                  AI Suggested Response
                </span>
              </div>
              <p className="text-sm text-[#1E293B] whitespace-pre-wrap leading-relaxed mb-3">
                {reply.aiSuggestedResponse}
              </p>
              <button className="text-sm font-medium text-[#7C3AED] hover:text-[#6D28D9] transition-colors">
                Use this response
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Action Bar */}
      <div className="px-6 py-4 border-t border-[#E2E8F0] bg-[#F8FAFC]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={onReply}
              className="flex items-center gap-2 px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25"
            >
              <Reply className="h-4 w-4" />
              <span>Reply</span>
            </button>
            <button
              onClick={onForward}
              className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-[#F1F5F9] text-[#64748B] font-medium rounded-lg border border-[#E2E8F0] transition-colors"
            >
              <Forward className="h-4 w-4" />
              <span>Forward</span>
            </button>
          </div>

          <button
            onClick={onArchive}
            className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-[#F1F5F9] text-[#64748B] font-medium rounded-lg border border-[#E2E8F0] transition-colors"
          >
            <Archive className="h-4 w-4" />
            <span>Archive</span>
          </button>
        </div>

        {/* Lead quick links */}
        {(reply.leadEmail || reply.leadLinkedIn) && (
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-[#E2E8F0]">
            {reply.leadEmail && (
              <a
                href={`mailto:${reply.leadEmail}`}
                className="flex items-center gap-1.5 text-sm text-[#64748B] hover:text-[#3B82F6] transition-colors"
              >
                <Mail className="h-4 w-4" />
                <span>{reply.leadEmail}</span>
              </a>
            )}
            {reply.leadLinkedIn && (
              <a
                href={reply.leadLinkedIn}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm text-[#64748B] hover:text-[#0077B5] transition-colors"
              >
                <Linkedin className="h-4 w-4" />
                <span>LinkedIn Profile</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ReplyDetail;
