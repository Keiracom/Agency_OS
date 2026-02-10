/**
 * ChannelMatrix.tsx - 5-Channel Performance Matrix
 * Sprint 4 - Reports Page
 *
 * Grid showing channel performance mini-cards with metrics.
 */

"use client";

import { Mail, Briefcase, MessageCircle, Phone, Send } from "lucide-react";
import type { ChannelPerformance, ChannelType } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface ChannelMatrixProps {
  channels: ChannelPerformance[];
  dateRange?: string;
}

// ============================================
// Channel Configuration
// ============================================

const channelConfig: Record<
  ChannelType,
  { icon: React.ReactNode; rateColor: string; barColor: string }
> = {
  email: {
    icon: <Mail className="w-6 h-6" />,
    rateColor: "text-accent-primary",
    barColor: "bg-accent-primary",
  },
  linkedin: {
    icon: <Briefcase className="w-6 h-6" />,
    rateColor: "text-accent-blue",
    barColor: "bg-accent-blue",
  },
  sms: {
    icon: <MessageCircle className="w-6 h-6" />,
    rateColor: "text-accent-teal",
    barColor: "bg-accent-teal",
  },
  voice: {
    icon: <Phone className="w-6 h-6" />,
    rateColor: "text-status-warning",
    barColor: "bg-status-warning",
  },
  mail: {
    icon: <Send className="w-6 h-6" />,
    rateColor: "text-pink-500",
    barColor: "bg-pink-500",
  },
};

// ============================================
// Component
// ============================================

export function ChannelMatrix({
  channels,
  dateRange = "Feb 1-28, 2026",
}: ChannelMatrixProps) {
  // Calculate max meetings for relative bar widths
  const maxMeetings = Math.max(...channels.map((c) => c.meetings));

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden mb-6">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <span className="text-accent-primary">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </span>
          5-Channel Performance Matrix
        </div>
        <span className="text-xs text-text-muted">{dateRange}</span>
      </div>

      {/* Channel Grid */}
      <div className="p-5">
        <div className="grid grid-cols-5 gap-3">
          {channels.map((channel) => {
            const config = channelConfig[channel.channel];
            const barWidth = (channel.meetings / maxMeetings) * 100;

            return (
              <div
                key={channel.channel}
                className="bg-bg-base rounded-lg p-4 text-center"
              >
                {/* Icon */}
                <div className="text-text-muted mb-2 flex justify-center">
                  {config.icon}
                </div>

                {/* Name */}
                <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
                  {channel.name}
                </div>

                {/* Sent */}
                <div className="mb-2">
                  <div className="text-xl font-bold font-mono text-text-primary">
                    {channel.sent.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-text-muted">
                    {channel.sentLabel}
                  </div>
                </div>

                {/* Reply Rate */}
                <div className="mb-2">
                  <div className={`text-xl font-bold font-mono ${config.rateColor}`}>
                    {channel.replyRate}%
                  </div>
                  <div className="text-[10px] text-text-muted">Reply Rate</div>
                </div>

                {/* Meetings */}
                <div className="mb-2">
                  <div className="text-xl font-bold font-mono text-status-success">
                    {channel.meetings}
                  </div>
                  <div className="text-[10px] text-text-muted">Meetings</div>
                </div>

                {/* Bar */}
                <div className="h-1 bg-bg-surface rounded-full mt-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${config.barColor}`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default ChannelMatrix;
