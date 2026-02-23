"use client";

/**
 * FILE: frontend/components/leads/CommunicationTimeline.tsx
 * PURPOSE: Chronological communication timeline for lead detail page
 * SPRINT: Dashboard Sprint 2 - Step 6/8 Animated Lead Scoreboard
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail,
  Send,
  Eye,
  Reply,
  Linkedin,
  Phone,
  MessageSquare,
  Calendar,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

// Event types
export type TimelineEventType = 
  | "email_sent"
  | "email_opened"
  | "email_replied"
  | "linkedin_connected"
  | "sms_sent"
  | "call_made"
  | "meeting_booked";

export interface TimelineEvent {
  id: string;
  type: TimelineEventType;
  timestamp: Date;
  title: string;
  preview?: string;
  fullContent?: string;
  metadata?: Record<string, string>;
}

interface TimelineEventCardProps {
  event: TimelineEvent;
  isLast: boolean;
}

/**
 * Get styling for each event type
 */
function getEventStyle(type: TimelineEventType): { 
  icon: React.ReactNode; 
  bg: string; 
  border: string;
  highlight?: boolean;
} {
  switch (type) {
    case "email_sent":
      return { 
        icon: <Send className="w-4 h-4" />, 
        bg: "rgba(124, 58, 237, 0.15)", 
        border: "#7C3AED" 
      };
    case "email_opened":
      return { 
        icon: <Eye className="w-4 h-4" />, 
        bg: "rgba(59, 130, 246, 0.15)", 
        border: "#3B82F6" 
      };
    case "email_replied":
      return { 
        icon: <Reply className="w-4 h-4" />, 
        bg: "rgba(16, 185, 129, 0.15)", 
        border: "#10B981" 
      };
    case "linkedin_connected":
      return { 
        icon: <Linkedin className="w-4 h-4" />, 
        bg: "rgba(0, 119, 181, 0.15)", 
        border: "#0077B5" 
      };
    case "sms_sent":
      return { 
        icon: <MessageSquare className="w-4 h-4" />, 
        bg: "rgba(20, 184, 166, 0.15)", 
        border: "#14B8A6" 
      };
    case "call_made":
      return { 
        icon: <Phone className="w-4 h-4" />, 
        bg: "rgba(245, 158, 11, 0.15)", 
        border: "#F59E0B" 
      };
    case "meeting_booked":
      return { 
        icon: <Calendar className="w-4 h-4" />, 
        bg: "rgba(212, 149, 106, 0.2)", 
        border: "#D4956A",
        highlight: true 
      };
    default:
      return { 
        icon: <Mail className="w-4 h-4" />, 
        bg: "rgba(107, 114, 128, 0.15)", 
        border: "#6B7280" 
      };
  }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(date: Date): { date: string; time: string } {
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  const isYesterday = new Date(now.setDate(now.getDate() - 1)).toDateString() === date.toDateString();

  let dateStr: string;
  if (isToday) {
    dateStr = "Today";
  } else if (isYesterday) {
    dateStr = "Yesterday";
  } else {
    dateStr = date.toLocaleDateString("en-AU", { 
      month: "short", 
      day: "numeric",
      year: date.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined
    });
  }

  const timeStr = date.toLocaleTimeString("en-AU", { 
    hour: "numeric", 
    minute: "2-digit",
    hour12: true 
  });

  return { date: dateStr, time: timeStr };
}

/**
 * Individual timeline event card (expandable)
 */
function TimelineEventCard({ event, isLast }: TimelineEventCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const style = getEventStyle(event.type);
  const { date, time } = formatTimestamp(event.timestamp);

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      {!isLast && (
        <div 
          className="absolute left-[18px] top-10 bottom-0 w-0.5"
          style={{ backgroundColor: "rgba(255,255,255,0.08)" }}
        />
      )}

      {/* Event icon */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="relative z-10 w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ 
          backgroundColor: style.bg,
          boxShadow: style.highlight ? `0 0 20px ${style.border}40` : "none"
        }}
      >
        <span style={{ color: style.border }}>{style.icon}</span>
      </motion.div>

      {/* Event content */}
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
        className={`flex-1 pb-6 ${event.fullContent ? "cursor-pointer" : ""}`}
        onClick={() => event.fullContent && setIsExpanded(!isExpanded)}
      >
        {/* Meeting booked highlight wrapper */}
        <div 
          className={`p-4 rounded-xl transition-all ${
            style.highlight ? "ring-2 ring-amber-600/50 ring-offset-2 ring-offset-transparent" : ""
          }`}
          style={{
            backgroundColor: style.highlight 
              ? "rgba(212, 149, 106, 0.1)" 
              : "rgba(255,255,255,0.02)",
            border: style.highlight 
              ? "1px solid rgba(212, 149, 106, 0.3)" 
              : "1px solid rgba(255,255,255,0.05)",
          }}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p 
                  className="font-medium text-sm"
                  style={{ color: style.highlight ? "#D4956A" : "#F5F5F4" }}
                >
                  {event.title}
                </p>
                {style.highlight && (
                  <motion.span
                    animate={{ 
                      boxShadow: [
                        "0 0 0 0 rgba(212, 149, 106, 0.4)",
                        "0 0 0 8px rgba(212, 149, 106, 0)",
                      ]
                    }}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                    className="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                    style={{
                      backgroundColor: "rgba(212, 149, 106, 0.2)",
                      color: "#D4956A"
                    }}
                  >
                    🎉 Booked
                  </motion.span>
                )}
              </div>
              {event.preview && (
                <p className="text-xs text-text-muted mt-1 line-clamp-2">
                  {event.preview}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-xs text-text-muted font-mono">
                {date} · {time}
              </span>
              {event.fullContent && (
                <motion.span
                  animate={{ rotate: isExpanded ? 180 : 0 }}
                  className="text-text-muted"
                >
                  <ChevronDown className="w-4 h-4" />
                </motion.span>
              )}
            </div>
          </div>

          {/* Expandable content */}
          <AnimatePresence>
            {isExpanded && event.fullContent && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div 
                  className="mt-3 pt-3 border-t text-sm text-text-secondary whitespace-pre-wrap"
                  style={{ borderColor: "rgba(255,255,255,0.08)" }}
                >
                  {event.fullContent}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Metadata */}
          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {Object.entries(event.metadata).map(([key, value]) => (
                <span
                  key={key}
                  className="text-[10px] px-2 py-1 rounded"
                  style={{ 
                    backgroundColor: "rgba(255,255,255,0.05)",
                    color: "#A09890"
                  }}
                >
                  {key}: {value}
                </span>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

/**
 * Empty state component with animated pulse
 */
export function TimelineEmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-16 px-8 text-center"
    >
      {/* Animated pulse circle */}
      <motion.div
        className="relative mb-6"
        animate={{
          scale: [1, 1.05, 1],
        }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      >
        {/* Outer pulse ring */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{ backgroundColor: "rgba(212, 149, 106, 0.1)" }}
          animate={{
            scale: [1, 1.8],
            opacity: [0.6, 0],
          }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeOut" }}
        />
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{ backgroundColor: "rgba(212, 149, 106, 0.1)" }}
          animate={{
            scale: [1, 1.5],
            opacity: [0.4, 0],
          }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeOut", delay: 0.3 }}
        />
        
        {/* Inner icon */}
        <div 
          className="w-16 h-16 rounded-full flex items-center justify-center relative z-10"
          style={{ 
            backgroundColor: "rgba(212, 149, 106, 0.15)",
            border: "2px solid rgba(212, 149, 106, 0.3)"
          }}
        >
          <motion.span
            animate={{ rotate: [0, 360] }}
            transition={{ repeat: Infinity, duration: 8, ease: "linear" }}
            style={{ color: "#D4956A" }}
          >
            <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
            </svg>
          </motion.span>
        </div>
      </motion.div>

      {/* Message */}
      <h3 
        className="text-lg font-serif font-semibold mb-2"
        style={{ color: "#D4956A" }}
      >
        Siege Waterfall is enriching your leads
      </h3>
      <p className="text-sm text-text-muted max-w-sm">
        We&apos;re gathering intelligence and preparing outreach sequences. 
        Check back shortly for activity updates.
      </p>

      {/* Animated dots */}
      <div className="flex gap-1 mt-4">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: "#D4956A" }}
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ 
              repeat: Infinity, 
              duration: 1.5, 
              delay: i * 0.2 
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}

/**
 * Full communication timeline component
 */
export interface CommunicationTimelineProps {
  events: TimelineEvent[];
  showEmptyState?: boolean;
}

export function CommunicationTimeline({ events, showEmptyState = true }: CommunicationTimelineProps) {
  // Sort events by timestamp descending (most recent first)
  const sortedEvents = [...events].sort(
    (a, b) => b.timestamp.getTime() - a.timestamp.getTime()
  );

  if (sortedEvents.length === 0 && showEmptyState) {
    return <TimelineEmptyState />;
  }

  return (
    <div className="space-y-0">
      {sortedEvents.map((event, index) => (
        <TimelineEventCard
          key={event.id}
          event={event}
          isLast={index === sortedEvents.length - 1}
        />
      ))}
    </div>
  );
}
