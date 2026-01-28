"use client";

/**
 * Premium Activity Card
 * 
 * Glassmorphism activity feed with subtle glow effects.
 * Matches the EqtyLab dark premium aesthetic.
 */

import { Mail, MessageSquare, Linkedin, Phone, Send } from "lucide-react";

interface Activity {
  id: string;
  channel: "email" | "sms" | "linkedin" | "voice";
  action: string;
  leadName: string;
  company: string;
  timestamp: string;
}

const channelIcons = {
  email: Mail,
  sms: MessageSquare,
  linkedin: Linkedin,
  voice: Phone,
};

const channelColors = {
  email: "text-blue-400 bg-blue-400/10",
  sms: "text-green-400 bg-green-400/10",
  linkedin: "text-sky-400 bg-sky-400/10",
  voice: "text-purple-400 bg-purple-400/10",
};

interface PremiumActivityCardProps {
  activities?: Activity[];
  title?: string;
}

const mockActivities: Activity[] = [
  { id: "1", channel: "email", action: "opened", leadName: "Sarah Chen", company: "TechCorp", timestamp: "2m ago" },
  { id: "2", channel: "linkedin", action: "connected", leadName: "Mike Johnson", company: "StartupXYZ", timestamp: "15m ago" },
  { id: "3", channel: "email", action: "replied", leadName: "Lisa Park", company: "Acme Inc", timestamp: "1h ago" },
  { id: "4", channel: "voice", action: "scheduled", leadName: "James Wilson", company: "GlobalTech", timestamp: "2h ago" },
];

export function PremiumActivityCard({ 
  activities = mockActivities,
  title = "Recent Activity" 
}: PremiumActivityCardProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-[#0a0a0f]">
        <div 
          className="absolute top-0 right-0 w-[300px] h-[300px] opacity-20"
          style={{
            background: "radial-gradient(circle at top right, rgba(16,185,129,0.3), transparent 60%)",
            filter: "blur(60px)",
          }}
        />
      </div>

      {/* Glass card */}
      <div className="relative z-10 backdrop-blur-xl bg-white/[0.02] border border-white/[0.06] rounded-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h3 className="text-sm font-medium text-gray-300">{title}</h3>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-emerald-400">Live</span>
          </div>
        </div>

        {/* Activity list */}
        <div className="divide-y divide-white/[0.04]">
          {activities.map((activity) => {
            const Icon = channelIcons[activity.channel];
            const colorClass = channelColors[activity.channel];
            
            return (
              <div 
                key={activity.id}
                className="flex items-center gap-4 px-6 py-4 hover:bg-white/[0.02] transition-colors"
              >
                {/* Channel icon */}
                <div className={`p-2 rounded-lg ${colorClass}`}>
                  <Icon className="w-4 h-4" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white truncate">
                    <span className="font-medium">{activity.leadName}</span>
                    <span className="text-gray-500"> {activity.action}</span>
                  </p>
                  <p className="text-xs text-gray-500 truncate">{activity.company}</p>
                </div>

                {/* Timestamp */}
                <span className="text-xs text-gray-600 whitespace-nowrap">
                  {activity.timestamp}
                </span>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/[0.04]">
          <button className="flex items-center gap-2 text-xs text-gray-500 hover:text-emerald-400 transition-colors">
            <Send className="w-3 h-3" />
            View all activity
          </button>
        </div>
      </div>
    </div>
  );
}

export default PremiumActivityCard;
