"use client";

/**
 * Bloomberg-style Activity Feed
 * Matches: dashboard-v3.html activity-feed design
 */

import { Mail, Linkedin, CheckCircle, LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ActivityItem {
  id: string;
  channel: "email" | "linkedin" | "meeting";
  text: string;
  timestamp: string;
}

interface ActivityFeedProps {
  activities: ActivityItem[];
  className?: string;
  maxItems?: number;
}

const channelConfig: Record<string, { icon: LucideIcon; bgClass: string; iconClass: string }> = {
  email: {
    icon: Mail,
    bgClass: "bg-[#3B82F6]/15",
    iconClass: "text-[#3B82F6]",
  },
  linkedin: {
    icon: Linkedin,
    bgClass: "bg-[#7C3AED]/15",
    iconClass: "text-[#7C3AED]",
  },
  meeting: {
    icon: CheckCircle,
    bgClass: "bg-[#10B981]/15",
    iconClass: "text-[#10B981]",
  },
};

export function ActivityFeed({ activities, className, maxItems = 5 }: ActivityFeedProps) {
  const displayActivities = activities.slice(0, maxItems);

  return (
    <div className={cn("bg-[#12121A] border border-[#2A2A3A] rounded-2xl", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#2A2A3A]">
        <h3 className="font-semibold text-white">Recent Activity</h3>
        <a href="#" className="text-sm text-[#7C3AED] hover:text-[#9D5CFF] transition-colors">
          View all
        </a>
      </div>

      {/* Activity List */}
      <div className="divide-y divide-[#2A2A3A]">
        {displayActivities.length === 0 ? (
          <div className="px-6 py-8 text-center">
            <p className="text-[#6B6B7B]">No recent activity</p>
          </div>
        ) : (
          displayActivities.map((activity) => {
            const config = channelConfig[activity.channel] || channelConfig.email;
            const Icon = config.icon;
            
            return (
              <div key={activity.id} className="flex items-start gap-3 px-6 py-3">
                <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0", config.bgClass)}>
                  <Icon className={cn("w-[18px] h-[18px]", config.iconClass)} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white">{activity.text}</p>
                  <p className="text-xs text-[#6B6B7B] mt-0.5">{activity.timestamp}</p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
