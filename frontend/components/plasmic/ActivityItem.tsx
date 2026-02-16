/**
 * FILE: frontend/components/plasmic/ActivityItem.tsx
 * PURPOSE: Activity feed item - Plasmic design spec
 * DESIGN: Channel icon + content + timestamp
 */

"use client";

import { cn } from "@/lib/utils";
import { Mail, Linkedin, MessageSquare, Phone, Calendar, LucideIcon } from "lucide-react";

type Channel = "email" | "linkedin" | "sms" | "voice" | "meeting";

interface ActivityItemProps {
  channel: Channel;
  name: string;
  company?: string;
  action: string;
  timestamp: string;
  className?: string;
}

const channelConfig: Record<Channel, { icon: LucideIcon; color: string; bg: string }> = {
  email: { icon: Mail, color: "text-text-primary", bg: "bg-[#3B82F6]" },
  linkedin: { icon: Linkedin, color: "text-text-primary", bg: "bg-[#0A66C2]" },
  sms: { icon: MessageSquare, color: "text-text-primary", bg: "bg-[#10B981]" },
  voice: { icon: Phone, color: "text-text-primary", bg: "bg-[#8B5CF6]" },
  meeting: { icon: Calendar, color: "text-text-primary", bg: "bg-[#F59E0B]" },
};

export function ActivityItem({
  channel,
  name,
  company,
  action,
  timestamp,
  className,
}: ActivityItemProps) {
  const config = channelConfig[channel];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-3 rounded-lg",
        "hover:bg-bg-surface/5 transition-colors",
        className
      )}
    >
      {/* Channel Icon */}
      <div
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
          config.bg
        )}
      >
        <Icon className={cn("h-5 w-5", config.color)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-text-primary truncate">{name}</span>
          {company && (
            <>
              <span className="text-text-primary/40">at</span>
              <span className="text-text-primary/60 truncate">{company}</span>
            </>
          )}
        </div>
        <p className="text-sm text-text-primary/50 truncate">{action}</p>
      </div>

      {/* Timestamp */}
      <span className="text-xs text-text-primary/40 whitespace-nowrap">{timestamp}</span>
    </div>
  );
}

export default ActivityItem;
