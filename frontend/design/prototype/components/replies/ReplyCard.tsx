"use client";

import { Mail, Linkedin, MessageSquare, Phone } from "lucide-react";

/**
 * Channel type for replies
 */
export type ReplyChannel = "email" | "linkedin" | "sms" | "voice";

/**
 * Intent classification for replies
 */
export type ReplyIntent = "positive" | "negative" | "neutral" | "question";

/**
 * ALS Tier type
 */
export type ALSTier = "hot" | "warm" | "cool" | "cold" | "dead";

/**
 * ReplyCard props
 */
export interface ReplyCardProps {
  /** Unique reply ID */
  id: string;
  /** Lead's full name */
  leadName: string;
  /** Lead's company name */
  leadCompany: string;
  /** Communication channel */
  channel: ReplyChannel;
  /** Email subject or message topic */
  subject: string;
  /** Preview of the message content */
  preview: string;
  /** When the reply was received */
  timestamp: string;
  /** AI-classified intent */
  intent: ReplyIntent;
  /** Lead's ALS tier */
  tierBadge: ALSTier;
  /** Whether the reply is unread */
  isUnread?: boolean;
  /** Whether this card is currently selected */
  isSelected?: boolean;
  /** Click handler */
  onClick?: () => void;
}

/**
 * Channel icon mapping with design system colors
 */
const channelConfig: Record<
  ReplyChannel,
  { icon: React.ComponentType<{ className?: string }>; color: string; bgColor: string }
> = {
  email: { icon: Mail, color: "#3B82F6", bgColor: "#DBEAFE" },
  linkedin: { icon: Linkedin, color: "#0077B5", bgColor: "#E0F2FE" },
  sms: { icon: MessageSquare, color: "#10B981", bgColor: "#D1FAE5" },
  voice: { icon: Phone, color: "#8B5CF6", bgColor: "#EDE9FE" },
};

/**
 * Intent badge styling with design system colors
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
 * ALS Tier badge styling with design system colors
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
 * ReplyCard - Individual reply item in the inbox list
 *
 * Features:
 * - Channel icon with color coding (email, LinkedIn, SMS, voice)
 * - Lead name and company
 * - Subject/preview text with truncation
 * - Intent badge (Positive/Negative/Neutral/Question)
 * - ALS tier badge (Hot/Warm/Cool/Cold/Dead)
 * - Timestamp
 * - Unread styling with bold text and blue dot
 * - Selected state with blue left border
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Card background: #FFFFFF (card-bg)
 * - Card border: #E2E8F0 (card-border)
 * - Text primary: #1E293B (text-primary)
 * - Text secondary: #64748B (text-secondary)
 * - Text muted: #94A3B8 (text-muted)
 * - Selected accent: #3B82F6 (accent-blue)
 */
export function ReplyCard({
  id,
  leadName,
  leadCompany,
  channel,
  subject,
  preview,
  timestamp,
  intent,
  tierBadge,
  isUnread = false,
  isSelected = false,
  onClick,
}: ReplyCardProps) {
  const channelInfo = channelConfig[channel];
  const intentInfo = intentConfig[intent];
  const tierInfo = tierConfig[tierBadge];
  const ChannelIcon = channelInfo.icon;

  return (
    <div
      onClick={onClick}
      className={`
        relative px-4 py-4 border-b border-[#E2E8F0] cursor-pointer transition-colors
        ${isSelected ? "bg-[#EFF6FF] border-l-4 border-l-[#3B82F6]" : "bg-white hover:bg-[#F8FAFC]"}
        ${isUnread ? "bg-[#F8FAFC]" : ""}
      `}
    >
      {/* Unread indicator */}
      {isUnread && !isSelected && (
        <div className="absolute left-2 top-1/2 -translate-y-1/2 w-2 h-2 bg-[#3B82F6] rounded-full" />
      )}

      <div className="flex items-start gap-3">
        {/* Channel Icon */}
        <div
          className="flex-shrink-0 p-2 rounded-lg"
          style={{ backgroundColor: channelInfo.bgColor }}
        >
          <span style={{ color: channelInfo.color }}>
            <ChannelIcon className="h-4 w-4" />
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header row: Lead info + timestamp */}
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`truncate text-sm ${
                  isUnread ? "font-semibold text-[#1E293B]" : "font-medium text-[#1E293B]"
                }`}
              >
                {leadName}
              </span>
              <span className="text-sm text-[#64748B] truncate">
                {leadCompany}
              </span>
            </div>
            <span className="flex-shrink-0 text-xs text-[#94A3B8]">
              {timestamp}
            </span>
          </div>

          {/* Subject line */}
          <p
            className={`text-sm truncate mb-1 ${
              isUnread ? "font-medium text-[#1E293B]" : "text-[#64748B]"
            }`}
          >
            {subject}
          </p>

          {/* Preview */}
          <p className="text-sm text-[#94A3B8] truncate mb-2">{preview}</p>

          {/* Badges row */}
          <div className="flex items-center gap-2">
            {/* Intent Badge */}
            <span
              className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{
                backgroundColor: intentInfo.bgColor,
                color: intentInfo.textColor,
              }}
            >
              {intentInfo.label}
            </span>

            {/* Tier Badge */}
            <span
              className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{
                backgroundColor: tierInfo.bgColor,
                color: tierInfo.textColor,
              }}
            >
              {tierInfo.label}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ReplyCard;
