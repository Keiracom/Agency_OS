"use client";

/**
 * ActivityFeed.tsx - Recent activity list
 * Design System: frontend/design/prototype/DESIGN_SYSTEM.md
 *
 * Features:
 * - Channel icon with colors from design system
 * - Lead name and company
 * - Action description
 * - Relative timestamp
 * - "Live" badge that pulses
 * - Hover state on items
 */

import { Mail, Linkedin, MessageSquare, Phone, FileText } from "lucide-react";

type ActivityChannel = "email" | "linkedin" | "sms" | "voice" | "mail";

interface Activity {
  id: string;
  channel: ActivityChannel;
  leadName: string;
  company: string;
  action: string;
  timestamp: string;
}

interface ActivityFeedProps {
  activities: Activity[];
}

const channelConfig: Record<ActivityChannel, { icon: typeof Mail; bgColor: string; textColor: string }> = {
  email: { icon: Mail, bgColor: "bg-[#DBEAFE]", textColor: "text-[#3B82F6]" },
  linkedin: { icon: Linkedin, bgColor: "bg-[#E0F2FE]", textColor: "text-[#0077B5]" },
  sms: { icon: MessageSquare, bgColor: "bg-[#D1FAE5]", textColor: "text-[#10B981]" },
  voice: { icon: Phone, bgColor: "bg-[#EDE9FE]", textColor: "text-[#8B5CF6]" },
  mail: { icon: FileText, bgColor: "bg-[#FEF3C7]", textColor: "text-[#F59E0B]" },
};

export function ActivityFeed({ activities }: ActivityFeedProps) {
  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      {/* Header with Live badge */}
      <div className="px-6 py-4 border-b border-[#E2E8F0] flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
          Recent Activity
        </h2>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#10B981]"></span>
          </span>
          <span className="text-xs font-medium text-[#10B981]">Live</span>
        </div>
      </div>

      {/* Activity list */}
      <div className="divide-y divide-[#E2E8F0]">
        {activities.map((activity) => {
          const config = channelConfig[activity.channel];
          const IconComponent = config.icon;

          return (
            <div
              key={activity.id}
              className="px-6 py-4 hover:bg-[#F8FAFC] transition-colors cursor-pointer"
            >
              <div className="flex items-start gap-3">
                {/* Channel icon */}
                <div className={`${config.bgColor} p-2 rounded-lg flex-shrink-0`}>
                  <IconComponent className={`h-4 w-4 ${config.textColor}`} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[#1E293B] truncate">
                      {activity.leadName}
                    </span>
                    <span className="text-[#64748B]">at</span>
                    <span className="text-[#64748B] truncate">{activity.company}</span>
                  </div>
                  <p className="text-sm text-[#64748B] mt-0.5">{activity.action}</p>
                </div>

                {/* Timestamp */}
                <span className="text-xs text-[#94A3B8] flex-shrink-0">
                  {activity.timestamp}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
