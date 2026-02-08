"use client";

/**
 * ActivityFeed.tsx - Real-time Activity Feed Component
 * Phase: Operation Modular Cockpit
 *
 * Features:
 * - Live activity stream (emails, replies, calls, meetings)
 * - Channel icons for each activity type
 * - Relative timestamps ("2m ago", "1h ago")
 * - Click to view details modal
 * - Auto-scroll with new items
 * - Explicit "Pause" button to stop auto-scroll
 * - Pulse animation on new items
 * - Bloomberg dark mode + glassmorphic styling
 */

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Mail,
  Linkedin,
  Phone,
  MessageSquare,
  Calendar,
  Send,
  Eye,
  MousePointer,
  Reply,
  UserPlus,
  PhoneCall,
  CheckCircle2,
  XCircle,
  Pause,
  Play,
  X,
  ExternalLink,
  Clock,
} from "lucide-react";

// ============================================
// Types
// ============================================

type ActivityType =
  | "email_sent"
  | "email_opened"
  | "email_clicked"
  | "email_replied"
  | "linkedin_connection"
  | "linkedin_message"
  | "voice_call"
  | "meeting_booked"
  | "sms_sent"
  | "sms_replied";

type ActivityStatus = "success" | "failed" | "pending";

interface Activity {
  id: string;
  type: ActivityType;
  title: string;
  description: string;
  contactName: string;
  contactCompany?: string;
  contactEmail?: string;
  timestamp: Date;
  status: ActivityStatus;
  metadata?: Record<string, string | number | boolean>;
  isNew?: boolean;
}

interface ActivityFeedProps {
  /** Activities from API - if undefined, shows mock data */
  activities?: Activity[];
  /** Maximum activities to display */
  maxVisible?: number;
  /** Auto-refresh interval in ms (0 to disable) */
  refreshInterval?: number;
  /** Callback when activity is clicked */
  onActivityClick?: (activity: Activity) => void;
  /** Custom className */
  className?: string;
}

// ============================================
// Mock Data
// ============================================

const generateMockActivities = (): Activity[] => [
  {
    id: "1",
    type: "meeting_booked",
    title: "Meeting Booked",
    description: "Demo call scheduled for Thursday 2:00 PM AEST",
    contactName: "Sarah Chen",
    contactCompany: "Pixel Studios",
    contactEmail: "sarah@pixelstudios.com",
    timestamp: new Date(Date.now() - 1000 * 60 * 2), // 2 min ago
    status: "success",
    metadata: { duration: "30 min", platform: "Google Meet" },
    isNew: true,
  },
  {
    id: "2",
    type: "email_replied",
    title: "Reply Received",
    description: '"Thanks for reaching out! I\'d love to learn more about your solution..."',
    contactName: "Marcus Williams",
    contactCompany: "TechFlow Inc",
    contactEmail: "marcus@techflow.io",
    timestamp: new Date(Date.now() - 1000 * 60 * 8), // 8 min ago
    status: "success",
    metadata: { sentiment: "positive", priority: "high" },
  },
  {
    id: "3",
    type: "voice_call",
    title: "Voice Call Completed",
    description: "AI call completed - positive response, follow-up scheduled",
    contactName: "David Park",
    contactCompany: "Innovate Labs",
    contactEmail: "david@innovatelabs.co",
    timestamp: new Date(Date.now() - 1000 * 60 * 15), // 15 min ago
    status: "success",
    metadata: { duration: "4:32", outcome: "interested" },
  },
  {
    id: "4",
    type: "linkedin_connection",
    title: "Connection Accepted",
    description: "Your connection request was accepted",
    contactName: "Emily Torres",
    contactCompany: "Growth Partners",
    contactEmail: "emily@growthpartners.com",
    timestamp: new Date(Date.now() - 1000 * 60 * 32), // 32 min ago
    status: "success",
  },
  {
    id: "5",
    type: "email_opened",
    title: "Email Opened",
    description: 'Subject: "Quick question about your Q2 goals"',
    contactName: "James Cooper",
    contactCompany: "Velocity Digital",
    contactEmail: "james@velocitydigital.com",
    timestamp: new Date(Date.now() - 1000 * 60 * 45), // 45 min ago
    status: "success",
    metadata: { opens: 3 },
  },
  {
    id: "6",
    type: "email_clicked",
    title: "Link Clicked",
    description: "Clicked: Pricing page",
    contactName: "Lisa Zhang",
    contactCompany: "CloudFirst",
    contactEmail: "lisa@cloudfirst.io",
    timestamp: new Date(Date.now() - 1000 * 60 * 58), // 58 min ago
    status: "success",
  },
  {
    id: "7",
    type: "sms_sent",
    title: "SMS Delivered",
    description: "Follow-up SMS delivered successfully",
    contactName: "Michael Brown",
    contactCompany: "StartupXYZ",
    contactEmail: "michael@startupxyz.com",
    timestamp: new Date(Date.now() - 1000 * 60 * 72), // 1h 12m ago
    status: "success",
  },
  {
    id: "8",
    type: "email_sent",
    title: "Email Sent",
    description: 'Sequence Step 2: "Following up on our conversation"',
    contactName: "Anna Kowalski",
    contactCompany: "DataDriven Co",
    contactEmail: "anna@datadriven.co",
    timestamp: new Date(Date.now() - 1000 * 60 * 95), // 1h 35m ago
    status: "success",
  },
  {
    id: "9",
    type: "linkedin_message",
    title: "LinkedIn Message Sent",
    description: "Personalized outreach message delivered",
    contactName: "Robert Kim",
    contactCompany: "Scale Ventures",
    contactEmail: "robert@scaleventures.com",
    timestamp: new Date(Date.now() - 1000 * 60 * 120), // 2h ago
    status: "success",
  },
  {
    id: "10",
    type: "email_replied",
    title: "Out of Office",
    description: '"I\'m currently out of the office until Monday..."',
    contactName: "Jennifer Lee",
    contactCompany: "Bright Ideas Inc",
    contactEmail: "jennifer@brightideas.com",
    timestamp: new Date(Date.now() - 1000 * 60 * 180), // 3h ago
    status: "pending",
    metadata: { autoReply: true },
  },
];

// ============================================
// Utility Functions
// ============================================

const formatTimestamp = (date: Date): string => {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;

  return date.toLocaleDateString("en-AU", { month: "short", day: "numeric" });
};

const getActivityIcon = (type: ActivityType) => {
  const iconMap: Record<ActivityType, React.ReactNode> = {
    email_sent: <Send className="w-4 h-4" />,
    email_opened: <Eye className="w-4 h-4" />,
    email_clicked: <MousePointer className="w-4 h-4" />,
    email_replied: <Reply className="w-4 h-4" />,
    linkedin_connection: <UserPlus className="w-4 h-4" />,
    linkedin_message: <Linkedin className="w-4 h-4" />,
    voice_call: <PhoneCall className="w-4 h-4" />,
    meeting_booked: <Calendar className="w-4 h-4" />,
    sms_sent: <MessageSquare className="w-4 h-4" />,
    sms_replied: <MessageSquare className="w-4 h-4" />,
  };
  return iconMap[type];
};

const getActivityStyles = (type: ActivityType) => {
  const styleMap: Record<ActivityType, { bg: string; text: string; glow: string }> = {
    email_sent: { bg: "bg-blue-500/20", text: "text-blue-400", glow: "shadow-blue-500/20" },
    email_opened: { bg: "bg-cyan-500/20", text: "text-cyan-400", glow: "shadow-cyan-500/20" },
    email_clicked: { bg: "bg-indigo-500/20", text: "text-indigo-400", glow: "shadow-indigo-500/20" },
    email_replied: { bg: "bg-emerald-500/20", text: "text-emerald-400", glow: "shadow-emerald-500/20" },
    linkedin_connection: { bg: "bg-sky-500/20", text: "text-sky-400", glow: "shadow-sky-500/20" },
    linkedin_message: { bg: "bg-sky-500/20", text: "text-sky-400", glow: "shadow-sky-500/20" },
    voice_call: { bg: "bg-purple-500/20", text: "text-purple-400", glow: "shadow-purple-500/20" },
    meeting_booked: { bg: "bg-amber-500/20", text: "text-amber-400", glow: "shadow-amber-500/20" },
    sms_sent: { bg: "bg-teal-500/20", text: "text-teal-400", glow: "shadow-teal-500/20" },
    sms_replied: { bg: "bg-green-500/20", text: "text-green-400", glow: "shadow-green-500/20" },
  };
  return styleMap[type];
};

const getStatusIcon = (status: ActivityStatus) => {
  switch (status) {
    case "success":
      return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
    case "failed":
      return <XCircle className="w-3.5 h-3.5 text-red-400" />;
    case "pending":
      return (
        <div className="w-3.5 h-3.5 rounded-full border-2 border-amber-400 border-t-transparent animate-spin" />
      );
  }
};

// ============================================
// Detail Modal Component
// ============================================

interface DetailModalProps {
  activity: Activity;
  onClose: () => void;
}

function DetailModal({ activity, onClose }: DetailModalProps) {
  const styles = getActivityStyles(activity.type);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl shadow-black/40 w-full max-w-md mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-lg ${styles.bg} ${styles.text} shadow-lg ${styles.glow}`}
            >
              {getActivityIcon(activity.type)}
            </div>
            <div>
              <h3 className="text-white font-semibold">{activity.title}</h3>
              <p className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatTimestamp(activity.timestamp)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="px-5 py-4 space-y-4">
          {/* Contact Info */}
          <div className="bg-white/5 rounded-lg p-4 border border-white/5">
            <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
              Contact
            </h4>
            <div className="space-y-1.5">
              <p className="text-white font-medium">{activity.contactName}</p>
              {activity.contactCompany && (
                <p className="text-sm text-slate-300">{activity.contactCompany}</p>
              )}
              {activity.contactEmail && (
                <p className="text-sm text-slate-400">{activity.contactEmail}</p>
              )}
            </div>
          </div>

          {/* Activity Details */}
          <div>
            <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
              Details
            </h4>
            <p className="text-slate-200">{activity.description}</p>
          </div>

          {/* Metadata */}
          {activity.metadata && Object.keys(activity.metadata).length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                Additional Info
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(activity.metadata).map(([key, value]) => (
                  <div
                    key={key}
                    className="bg-white/5 rounded-lg px-3 py-2 border border-white/5"
                  >
                    <span className="text-xs text-slate-400 capitalize">
                      {key.replace(/_/g, " ")}
                    </span>
                    <p className="text-sm text-white">{String(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Status */}
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2">
              {getStatusIcon(activity.status)}
              <span className="text-sm text-slate-300 capitalize">{activity.status}</span>
            </div>
            <button className="flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 transition-colors">
              View Full Record
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Activity Item Component
// ============================================

interface ActivityItemProps {
  activity: Activity;
  onClick: () => void;
}

function ActivityItem({ activity, onClick }: ActivityItemProps) {
  const styles = getActivityStyles(activity.type);

  return (
    <div
      onClick={onClick}
      className={`
        group flex items-center gap-3 px-4 py-3 
        hover:bg-white/5 cursor-pointer transition-all duration-200
        border-b border-white/5 last:border-b-0
        ${activity.isNew ? "animate-pulse-once bg-white/[0.03]" : ""}
      `}
    >
      {/* Icon */}
      <div
        className={`
          flex-shrink-0 p-2 rounded-lg transition-all duration-200
          ${styles.bg} ${styles.text}
          group-hover:shadow-lg group-hover:${styles.glow}
          ${activity.isNew ? "ring-2 ring-white/20 ring-offset-2 ring-offset-slate-900" : ""}
        `}
      >
        {getActivityIcon(activity.type)}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-white truncate">
            {activity.contactName}
          </p>
          {activity.contactCompany && (
            <span className="text-xs text-slate-500 truncate hidden sm:inline">
              · {activity.contactCompany}
            </span>
          )}
          {activity.isNew && (
            <span className="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 rounded">
              New
            </span>
          )}
        </div>
        <p className="text-xs text-slate-400 truncate mt-0.5">
          {activity.title}: {activity.description}
        </p>
      </div>

      {/* Timestamp & Status */}
      <div className="flex-shrink-0 flex items-center gap-2">
        <span className="text-[11px] text-slate-500 tabular-nums">
          {formatTimestamp(activity.timestamp)}
        </span>
        {getStatusIcon(activity.status)}
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function ActivityFeed({
  activities: propActivities,
  maxVisible = 8,
  refreshInterval = 30000,
  onActivityClick,
  className = "",
}: ActivityFeedProps) {
  const [activities, setActivities] = useState<Activity[]>(() =>
    propActivities ?? generateMockActivities()
  );
  const [isPaused, setIsPaused] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDemo = !propActivities;

  // Update activities when prop changes
  useEffect(() => {
    if (propActivities) {
      setActivities(propActivities);
    }
  }, [propActivities]);

  // Simulate new activities arriving (demo mode only)
  useEffect(() => {
    if (isPaused || !isDemo || refreshInterval === 0) return;

    const interval = setInterval(() => {
      const newActivity: Activity = {
        id: `new-${Date.now()}`,
        type: ["email_opened", "email_replied", "linkedin_connection", "voice_call"][
          Math.floor(Math.random() * 4)
        ] as ActivityType,
        title: "New Activity",
        description: "Something just happened in your campaign",
        contactName: ["Alex Rivera", "Sam Johnson", "Chris Lee", "Morgan Davis"][
          Math.floor(Math.random() * 4)
        ],
        contactCompany: ["Acme Corp", "TechStart", "Innovation Labs", "Growth Co"][
          Math.floor(Math.random() * 4)
        ],
        timestamp: new Date(),
        status: "success",
        isNew: true,
      };

      setActivities((prev) => {
        // Remove isNew flag from previous items
        const updated = prev.map((a) => ({ ...a, isNew: false }));
        return [newActivity, ...updated].slice(0, 20);
      });

      // Auto-scroll to top if not paused
      if (containerRef.current) {
        containerRef.current.scrollTo({ top: 0, behavior: "smooth" });
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [isPaused, isDemo, refreshInterval]);

  const handleActivityClick = useCallback(
    (activity: Activity) => {
      setSelectedActivity(activity);
      onActivityClick?.(activity);
    },
    [onActivityClick]
  );

  const liveCount = activities.filter((a) => {
    const fiveMinAgo = Date.now() - 5 * 60 * 1000;
    return a.timestamp.getTime() > fiveMinAgo;
  }).length;

  return (
    <>
      <div
        className={`
          bg-slate-900/40 backdrop-blur-md rounded-xl 
          border border-white/10 shadow-xl shadow-black/20
          overflow-hidden flex flex-col
          ${className}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-slate-900/60">
          <div className="flex items-center gap-3">
            {/* Live Indicator */}
            <div className="flex items-center gap-2">
              {isDemo ? (
                <div className="w-2 h-2 rounded-full bg-amber-500" />
              ) : (
                <div className="relative w-2 h-2">
                  <span className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-75" />
                  <span className="relative block w-2 h-2 rounded-full bg-emerald-500" />
                </div>
              )}
              <span className="text-xs font-semibold text-white uppercase tracking-wider">
                {isDemo ? "Demo" : "Live"} Activity
              </span>
            </div>

            {/* Activity Counter */}
            <span className="text-[10px] text-slate-500 bg-white/5 px-2 py-0.5 rounded-full">
              {liveCount} in last 5m
            </span>
          </div>

          {/* Controls */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`
              flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
              transition-all duration-200
              ${
                isPaused
                  ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                  : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
              }
            `}
          >
            {isPaused ? (
              <>
                <Play className="w-3.5 h-3.5" />
                Resume
              </>
            ) : (
              <>
                <Pause className="w-3.5 h-3.5" />
                Pause
              </>
            )}
          </button>
        </div>

        {/* Activity List */}
        <div
          ref={containerRef}
          className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
          style={{ maxHeight: `${maxVisible * 56}px` }}
        >
          {activities.slice(0, maxVisible * 2).map((activity) => (
            <ActivityItem
              key={activity.id}
              activity={activity}
              onClick={() => handleActivityClick(activity)}
            />
          ))}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-white/10 bg-slate-900/60">
          <p className="text-[10px] text-slate-500 text-center">
            {activities.length} total activities · {isPaused ? "Paused" : "Auto-updating"}
          </p>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedActivity && (
        <DetailModal
          activity={selectedActivity}
          onClose={() => setSelectedActivity(null)}
        />
      )}

      {/* Pulse Animation Styles */}
      <style jsx global>{`
        @keyframes pulse-once {
          0% {
            background-color: rgba(255, 255, 255, 0.08);
          }
          50% {
            background-color: rgba(255, 255, 255, 0.12);
          }
          100% {
            background-color: rgba(255, 255, 255, 0.02);
          }
        }
        .animate-pulse-once {
          animation: pulse-once 2s ease-out;
        }
      `}</style>
    </>
  );
}

export default ActivityFeed;
