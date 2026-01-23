/**
 * Activity Item - Shows recent outreach activity
 * Open in Codux to adjust icon colors, spacing
 */

"use client";

import { Mail, Linkedin, MessageSquare, Phone, Calendar } from "lucide-react";

type Channel = "email" | "linkedin" | "sms" | "voice" | "meeting";

interface ActivityItemProps {
  channel: Channel;
  name: string;
  company?: string;
  action: string;
  timestamp: string;
}

const channelConfig: Record<Channel, { icon: typeof Mail; bg: string }> = {
  email: { icon: Mail, bg: "bg-[#3B82F6]" },
  linkedin: { icon: Linkedin, bg: "bg-[#0A66C2]" },
  sms: { icon: MessageSquare, bg: "bg-[#10B981]" },
  voice: { icon: Phone, bg: "bg-[#8B5CF6]" },
  meeting: { icon: Calendar, bg: "bg-[#F59E0B]" },
};

export function ActivityItem({ channel, name, company, action, timestamp }: ActivityItemProps) {
  const config = channelConfig[channel];
  const Icon = config.icon;

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-[#F8FAFC] transition-colors">
      {/* Icon */}
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${config.bg}`}>
        <Icon className="h-5 w-5 text-white" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-[#1E293B] truncate">{name}</span>
          {company && (
            <>
              <span className="text-[#94A3B8]">at</span>
              <span className="text-[#64748B] truncate">{company}</span>
            </>
          )}
        </div>
        <p className="text-sm text-[#94A3B8] truncate">{action}</p>
      </div>

      {/* Timestamp */}
      <span className="text-xs text-[#94A3B8] whitespace-nowrap">{timestamp}</span>
    </div>
  );
}

export default ActivityItem;
