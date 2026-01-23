"use client";

/**
 * ActivityTicker.tsx - Bloomberg-style Activity Ticker
 * Phase 21: Deep Research & UI
 *
 * Scrolling ticker showing real-time platform activity:
 * - Email opens, clicks, replies
 * - LinkedIn connections, messages
 * - Voice AI calls, meetings booked
 * - SMS delivered
 */

import { useEffect, useState, useRef, useMemo } from "react";
import {
  Mail,
  MessageSquare,
  Phone,
  Linkedin,
  Calendar,
  MousePointer,
  Eye,
  Send,
  CheckCircle2,
  XCircle,
} from "lucide-react";

interface Activity {
  id: string;
  type:
    | "email_sent"
    | "email_opened"
    | "email_clicked"
    | "email_replied"
    | "linkedin_connection"
    | "linkedin_message"
    | "voice_call"
    | "meeting_booked"
    | "sms_delivered"
    | "sms_replied";
  message: string;
  timestamp: Date;
  status?: "success" | "failed" | "pending";
}

interface ActivityTickerProps {
  /** Real activities from API. If undefined/empty, shows demo data with indicator */
  activities?: Activity[];
  speed?: "slow" | "normal" | "fast";
  direction?: "up" | "down";
  showTimestamp?: boolean;
  maxVisible?: number;
}

// Mock activities for demonstration
const mockActivities: Activity[] = [
  {
    id: "1",
    type: "email_opened",
    message: "Sarah Williams opened your email",
    timestamp: new Date(Date.now() - 1000 * 60 * 2),
    status: "success",
  },
  {
    id: "2",
    type: "linkedin_connection",
    message: "Marcus Chen accepted connection",
    timestamp: new Date(Date.now() - 1000 * 60 * 5),
    status: "success",
  },
  {
    id: "3",
    type: "meeting_booked",
    message: "Meeting booked: Pixel Studios - Thu 2pm",
    timestamp: new Date(Date.now() - 1000 * 60 * 8),
    status: "success",
  },
  {
    id: "4",
    type: "email_replied",
    message: "James Cooper replied: 'Interested in a demo'",
    timestamp: new Date(Date.now() - 1000 * 60 * 12),
    status: "success",
  },
  {
    id: "5",
    type: "voice_call",
    message: "Voice AI: Call completed with Tech Dynamics",
    timestamp: new Date(Date.now() - 1000 * 60 * 15),
    status: "success",
  },
  {
    id: "6",
    type: "sms_delivered",
    message: "SMS delivered to Emma Thompson",
    timestamp: new Date(Date.now() - 1000 * 60 * 18),
    status: "success",
  },
  {
    id: "7",
    type: "email_clicked",
    message: "David Park clicked pricing link",
    timestamp: new Date(Date.now() - 1000 * 60 * 22),
    status: "success",
  },
  {
    id: "8",
    type: "linkedin_message",
    message: "LinkedIn message sent to Alex Rivera",
    timestamp: new Date(Date.now() - 1000 * 60 * 25),
    status: "success",
  },
];

const getActivityIcon = (type: Activity["type"]) => {
  switch (type) {
    case "email_sent":
      return <Send className="h-3.5 w-3.5" />;
    case "email_opened":
      return <Eye className="h-3.5 w-3.5" />;
    case "email_clicked":
      return <MousePointer className="h-3.5 w-3.5" />;
    case "email_replied":
      return <Mail className="h-3.5 w-3.5" />;
    case "linkedin_connection":
    case "linkedin_message":
      return <Linkedin className="h-3.5 w-3.5" />;
    case "voice_call":
      return <Phone className="h-3.5 w-3.5" />;
    case "meeting_booked":
      return <Calendar className="h-3.5 w-3.5" />;
    case "sms_delivered":
    case "sms_replied":
      return <MessageSquare className="h-3.5 w-3.5" />;
    default:
      return <CheckCircle2 className="h-3.5 w-3.5" />;
  }
};

const getActivityColor = (type: Activity["type"]) => {
  switch (type) {
    case "email_sent":
    case "email_opened":
    case "email_clicked":
    case "email_replied":
      return "text-blue-400 bg-blue-500/10";
    case "linkedin_connection":
    case "linkedin_message":
      return "text-sky-400 bg-sky-500/10";
    case "voice_call":
    case "meeting_booked":
      return "text-green-400 bg-green-500/10";
    case "sms_delivered":
    case "sms_replied":
      return "text-purple-400 bg-purple-500/10";
    default:
      return "text-gray-400 bg-gray-500/10";
  }
};

const formatTimestamp = (date: Date): string => {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / (1000 * 60));

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  return date.toLocaleDateString("en-AU", { month: "short", day: "numeric" });
};

export function ActivityTicker({
  activities,
  speed = "normal",
  direction = "up",
  showTimestamp = true,
  maxVisible = 6,
}: ActivityTickerProps) {
  // Determine if we're using demo data (no activities provided or empty array)
  const isDemo = !activities || activities.length === 0;
  const effectiveActivities = isDemo ? mockActivities : activities;

  const [displayActivities, setDisplayActivities] = useState<Activity[]>(effectiveActivities);
  const [isPaused, setIsPaused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Update displayActivities when activities prop changes
  useEffect(() => {
    setDisplayActivities(effectiveActivities);
  }, [activities, isDemo]);

  // Rotate activities for continuous scrolling effect
  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(
      () => {
        setDisplayActivities((prev) => {
          if (direction === "up") {
            const [first, ...rest] = prev;
            return [...rest, first];
          } else {
            const last = prev[prev.length - 1];
            return [last, ...prev.slice(0, -1)];
          }
        });
      },
      speed === "slow" ? 4000 : speed === "fast" ? 2000 : 3000
    );

    return () => clearInterval(interval);
  }, [isPaused, speed, direction]);

  return (
    <div
      ref={containerRef}
      className="bg-[#0f0f13] border border-white/10 rounded-lg overflow-hidden"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-[#1a1a1f]">
        <div className="flex items-center gap-2">
          {isDemo ? (
            <>
              <div className="relative flex h-2 w-2">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500" />
              </div>
              <span className="text-xs font-medium text-yellow-400 uppercase tracking-wider">
                Demo Mode
              </span>
            </>
          ) : (
            <>
              <div className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
              </div>
              <span className="text-xs font-medium text-white uppercase tracking-wider">
                Live Activity
              </span>
            </>
          )}
        </div>
        <span className="text-[10px] text-gray-500">
          {effectiveActivities.length} events{isDemo ? " (sample)" : ""}
        </span>
      </div>

      {/* Activity List */}
      <div className="divide-y divide-white/5">
        {displayActivities.slice(0, maxVisible).map((activity, index) => (
          <div
            key={`${activity.id}-${index}`}
            className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors"
          >
            {/* Icon */}
            <div
              className={`flex-shrink-0 p-1.5 rounded-md ${getActivityColor(
                activity.type
              )}`}
            >
              {getActivityIcon(activity.type)}
            </div>

            {/* Message */}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-200 truncate">{activity.message}</p>
            </div>

            {/* Timestamp */}
            {showTimestamp && (
              <span className="flex-shrink-0 text-[10px] text-gray-500">
                {formatTimestamp(activity.timestamp)}
              </span>
            )}

            {/* Status indicator */}
            {activity.status && (
              <div className="flex-shrink-0">
                {activity.status === "success" ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                ) : activity.status === "failed" ? (
                  <XCircle className="h-3.5 w-3.5 text-red-500" />
                ) : (
                  <div className="h-3.5 w-3.5 rounded-full border-2 border-gray-500 border-t-transparent animate-spin" />
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer gradient */}
      <div className="h-8 bg-gradient-to-t from-[#0f0f13] to-transparent -mt-8 pointer-events-none relative z-10" />
    </div>
  );
}

export default ActivityTicker;
