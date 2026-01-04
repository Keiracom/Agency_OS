/**
 * FILE: frontend/components/landing/ActivityFeed.tsx
 * PURPOSE: Animated activity feed showing live-looking notifications
 * PHASE: 21
 */

"use client";

import { useState, useEffect } from "react";
import { Mail, Linkedin, Phone, MessageSquare, FileText } from "lucide-react";

interface ActivityItem {
  id: string;
  channel: "email" | "linkedin" | "sms" | "voice" | "mail";
  action: string;
  name: string;
  status?: "success" | "pending";
}

interface ActivityFeedProps {
  items?: ActivityItem[];
  maxVisible?: number;
  rotateInterval?: number;
  className?: string;
}

const defaultActivities: ActivityItem[] = [
  { id: "1", channel: "email", action: "Email opened by", name: "Sarah Williams", status: "success" },
  { id: "2", channel: "linkedin", action: "Connection accepted:", name: "Marcus Chen", status: "success" },
  { id: "3", channel: "voice", action: "Meeting booked with", name: "Pixel Studios", status: "success" },
  { id: "4", channel: "sms", action: "SMS delivered to", name: "James Cooper", status: "success" },
  { id: "5", channel: "email", action: "Reply received from", name: "Emma Thompson", status: "success" },
  { id: "6", channel: "linkedin", action: "Message sent to", name: "David Park", status: "pending" },
  { id: "7", channel: "voice", action: "Call completed with", name: "Melbourne Digital", status: "success" },
  { id: "8", channel: "mail", action: "Direct mail sent to", name: "Studio Twenty", status: "pending" },
];

const channelConfig = {
  email: { icon: Mail, color: "text-blue-400", bg: "bg-blue-500/20" },
  linkedin: { icon: Linkedin, color: "text-blue-400", bg: "bg-blue-500/20" },
  sms: { icon: MessageSquare, color: "text-purple-400", bg: "bg-purple-500/20" },
  voice: { icon: Phone, color: "text-green-400", bg: "bg-green-500/20" },
  mail: { icon: FileText, color: "text-orange-400", bg: "bg-orange-500/20" },
};

export default function ActivityFeed({
  items = defaultActivities,
  maxVisible = 5,
  rotateInterval = 3000,
  className = "",
}: ActivityFeedProps) {
  const [visibleItems, setVisibleItems] = useState<ActivityItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    // Initialize with first batch
    setVisibleItems(items.slice(0, maxVisible));
  }, [items, maxVisible]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prev) => {
        const nextIndex = (prev + 1) % items.length;

        // Rotate in new item
        setVisibleItems((current) => {
          const newItem = items[nextIndex];
          const filtered = current.filter((item) => item.id !== newItem.id);
          return [newItem, ...filtered].slice(0, maxVisible);
        });

        return nextIndex;
      });
    }, rotateInterval);

    return () => clearInterval(timer);
  }, [items, maxVisible, rotateInterval]);

  return (
    <div className={`rounded-lg bg-white/5 backdrop-blur-[20px] border border-white/10 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
        </span>
        <span className="text-sm font-medium text-white">Live Activity</span>
      </div>

      {/* Activity Items */}
      <div className="divide-y divide-white/5">
        {visibleItems.map((item, index) => {
          const config = channelConfig[item.channel];
          const Icon = config.icon;

          return (
            <div
              key={`${item.id}-${index}`}
              className="px-4 py-3 flex items-center gap-3 transition-all duration-300"
              style={{
                animation: index === 0 ? "slideIn 0.3s ease-out" : undefined,
              }}
            >
              <div className={`p-2 rounded-lg ${config.bg}`}>
                <Icon className={`w-4 h-4 ${config.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white/80 truncate">
                  {item.action} <span className="font-medium text-white">{item.name}</span>
                </p>
              </div>
              {item.status === "success" && (
                <span className="text-xs text-green-400">Just now</span>
              )}
            </div>
          );
        })}
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
}
