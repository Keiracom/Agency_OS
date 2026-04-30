/**
 * NotificationsPanel.tsx - Notifications Dropdown Component
 * Phase: Operation Modular Cockpit
 * 
 * Full-featured notifications panel with:
 * - Multiple notification types (reply, meeting, milestone, alert)
 * - Unread count badge
 * - Mark as read / Mark all read
 * - Click to navigate
 * - Empty state
 * 
 * Bloomberg dark mode + glassmorphic styling.
 */

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Bell,
  MessageSquare,
  Calendar,
  Target,
  AlertTriangle,
  Check,
  CheckCheck,
  ExternalLink,
  Inbox,
  Sparkles,
  X,
  type LucideIcon,
} from "lucide-react";

// ============================================
// Types
// ============================================

export type NotificationType = "reply" | "meeting" | "milestone" | "alert";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  /** URL or route to navigate to on click */
  href?: string;
  /** Additional metadata */
  meta?: {
    campaignId?: string;
    leadId?: string;
    meetingId?: string;
    severity?: "info" | "warning" | "critical";
  };
}

export interface NotificationsPanelProps {
  /** Notifications list */
  notifications?: Notification[];
  /** Handler when notification is clicked */
  onNotificationClick?: (notification: Notification) => void;
  /** Handler for marking single notification as read */
  onMarkRead?: (notificationId: string) => void;
  /** Handler for marking all as read */
  onMarkAllRead?: () => void;
  /** Handler for clearing a notification */
  onDismiss?: (notificationId: string) => void;
  /** Custom className for the container */
  className?: string;
  /** Whether panel is controlled externally */
  isOpen?: boolean;
  /** Callback when open state changes */
  onOpenChange?: (open: boolean) => void;
}

// ============================================
// Notification Type Configuration
// ============================================

interface NotificationTypeConfig {
  icon: LucideIcon;
  bgColor: string;
  iconColor: string;
  label: string;
}

const notificationTypeConfig: Record<NotificationType, NotificationTypeConfig> = {
  reply: {
    icon: MessageSquare,
    bgColor: "bg-panel/20",
    iconColor: "text-ink-2",
    label: "New Reply",
  },
  meeting: {
    icon: Calendar,
    bgColor: "bg-amber/20",
    iconColor: "text-amber",
    label: "Meeting Booked",
  },
  milestone: {
    icon: Target,
    bgColor: "bg-amber/20",
    iconColor: "text-amber",
    label: "Campaign Milestone",
  },
  alert: {
    icon: AlertTriangle,
    bgColor: "bg-amber-500/20",
    iconColor: "text-amber-400",
    label: "System Alert",
  },
};

// ============================================
// Mock Data
// ============================================

export const mockNotifications: Notification[] = [
  {
    id: "notif-1",
    type: "reply",
    title: "New reply from Sarah Chen",
    message: "Thanks for reaching out! I'd love to learn more about your solution...",
    timestamp: new Date(Date.now() - 5 * 60 * 1000), // 5 mins ago
    read: false,
    href: "/dashboard/inbox?replyId=rep-123",
    meta: { leadId: "lead-456", campaignId: "camp-789" },
  },
  {
    id: "notif-2",
    type: "meeting",
    title: "Meeting booked with TechCorp",
    message: "Marcus Johnson scheduled a demo for tomorrow at 2:00 PM AEST",
    timestamp: new Date(Date.now() - 32 * 60 * 1000), // 32 mins ago
    read: false,
    href: "/dashboard/calendar?meetingId=meet-101",
    meta: { meetingId: "meet-101", campaignId: "camp-789" },
  },
  {
    id: "notif-3",
    type: "milestone",
    title: "Campaign hit 100 responses!",
    message: "Your 'SaaS Decision Makers Q1' campaign reached a major milestone",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    read: false,
    href: "/dashboard/campaigns/camp-789",
    meta: { campaignId: "camp-789" },
  },
  {
    id: "notif-4",
    type: "alert",
    title: "Email warmup complete",
    message: "Your new sender domain keiracom.io is now fully warmed and ready",
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
    read: true,
    meta: { severity: "info" },
  },
  {
    id: "notif-5",
    type: "reply",
    title: "Positive reply from DataFlow Inc",
    message: "We're interested in scheduling a call next week...",
    timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000), // 6 hours ago
    read: true,
    href: "/dashboard/inbox?replyId=rep-124",
    meta: { leadId: "lead-457" },
  },
  {
    id: "notif-6",
    type: "alert",
    title: "Bounce rate warning",
    message: "Campaign 'Enterprise Outreach' has a 5.2% bounce rate. Consider cleaning your list.",
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
    read: true,
    href: "/dashboard/campaigns/camp-456",
    meta: { severity: "warning", campaignId: "camp-456" },
  },
];

// ============================================
// Utility Functions
// ============================================

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString("en-AU", { 
    month: "short", 
    day: "numeric" 
  });
}

// ============================================
// Sub-components
// ============================================

function NotificationItem({
  notification,
  onClick,
  onMarkRead,
  onDismiss,
}: {
  notification: Notification;
  onClick?: (n: Notification) => void;
  onMarkRead?: (id: string) => void;
  onDismiss?: (id: string) => void;
}) {
  const config = notificationTypeConfig[notification.type];
  const Icon = config.icon;
  const isUnread = !notification.read;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!notification.read && onMarkRead) {
      onMarkRead(notification.id);
    }
    onClick?.(notification);
  };

  const handleMarkRead = (e: React.MouseEvent) => {
    e.stopPropagation();
    onMarkRead?.(notification.id);
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDismiss?.(notification.id);
  };

  return (
    <div
      onClick={handleClick}
      className={`
        group relative px-4 py-3.5
        cursor-pointer
        transition-all duration-200
        border-b border-white/5 last:border-0
        hover:bg-bg-panel/5
        ${isUnread ? "bg-panel/5" : ""}
      `}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`p-2 rounded-lg ${config.bgColor} flex-shrink-0`}>
          <Icon className={`w-4 h-4 ${config.iconColor}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p 
              className={`
                text-sm font-medium truncate
                ${isUnread ? "text-ink" : "text-ink-2"}
              `}
            >
              {notification.title}
            </p>
            
            {/* Unread indicator */}
            {isUnread && (
              <div className="w-2 h-2 bg-panel rounded-full flex-shrink-0 mt-1.5 animate-pulse" />
            )}
          </div>
          
          <p className="text-xs text-ink-3 line-clamp-2 mt-0.5">
            {notification.message}
          </p>
          
          <div className="flex items-center gap-2 mt-1.5">
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${config.bgColor} ${config.iconColor}`}>
              {config.label}
            </span>
            <span className="text-[10px] text-ink-3">
              {formatRelativeTime(notification.timestamp)}
            </span>
          </div>
        </div>

        {/* Hover actions */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {isUnread && onMarkRead && (
            <button
              onClick={handleMarkRead}
              className="p-1.5 rounded-lg hover:bg-bg-panel/10 text-ink-2 hover:text-amber transition-colors"
              title="Mark as read"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
          )}
          {notification.href && (
            <button
              onClick={handleClick}
              className="p-1.5 rounded-lg hover:bg-bg-panel/10 text-ink-2 hover:text-ink-2 transition-colors"
              title="View details"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          )}
          {onDismiss && (
            <button
              onClick={handleDismiss}
              className="p-1.5 rounded-lg hover:bg-bg-panel/10 text-ink-2 hover:text-amber transition-colors"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="px-4 py-12 text-center">
      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-bg-panel/5 flex items-center justify-center">
        <Inbox className="w-8 h-8 text-ink-3" />
      </div>
      <h3 className="text-sm font-medium text-ink-2 mb-1">
        All caught up!
      </h3>
      <p className="text-xs text-ink-3">
        No new notifications
      </p>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function NotificationsPanel({
  notifications = mockNotifications,
  onNotificationClick,
  onMarkRead,
  onMarkAllRead,
  onDismiss,
  className = "",
  isOpen: controlledIsOpen,
  onOpenChange,
}: NotificationsPanelProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Support controlled and uncontrolled open state
  const isControlled = controlledIsOpen !== undefined;
  const isOpen = isControlled ? controlledIsOpen : internalIsOpen;

  const setIsOpen = useCallback((open: boolean) => {
    if (!isControlled) {
      setInternalIsOpen(open);
    }
    onOpenChange?.(open);
  }, [isControlled, onOpenChange]);

  // Calculate counts
  const unreadCount = notifications.filter((n) => !n.read).length;
  const hasNotifications = notifications.length > 0;

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, setIsOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, setIsOpen]);

  const handleNotificationClick = (notification: Notification) => {
    if (notification.href && typeof window !== "undefined") {
      // In a real app, use router.push(notification.href)
      // For now, we'll just call the callback
    }
    onNotificationClick?.(notification);
    setIsOpen(false);
  };

  const handleMarkAllRead = () => {
    onMarkAllRead?.();
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}
        aria-expanded={isOpen}
        className={`
          relative p-2.5 rounded-xl
          bg-bg-panel/5 backdrop-blur-xl border border-white/10
          text-ink-2 hover:text-ink hover:bg-bg-panel/10
          transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-amber/50
          ${isOpen ? "bg-bg-panel/10 text-ink ring-2 ring-amber/30" : ""}
        `}
      >
        <Bell className="w-5 h-5" />
        
        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1 bg-amber rounded-full flex items-center justify-center text-[10px] font-bold text-ink animate-pulse">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div 
          className="
            absolute right-0 top-full mt-2 w-96
            bg-bg-cream/95 backdrop-blur-xl 
            border border-white/10 
            rounded-2xl shadow-2xl shadow-black/50
            overflow-hidden z-50
            animate-in fade-in slide-in-from-top-2 duration-200
          "
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-bg-panel/5">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-ink-2" />
              <h3 className="text-sm font-semibold text-ink">
                Notifications
              </h3>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 text-[10px] font-medium bg-panel/20 text-ink-2 rounded-full">
                  {unreadCount} new
                </span>
              )}
            </div>
            
            {unreadCount > 0 && onMarkAllRead && (
              <button
                onClick={handleMarkAllRead}
                className="
                  flex items-center gap-1.5 px-2.5 py-1 rounded-lg
                  text-xs text-ink-2 hover:text-amber-light 
                  hover:bg-panel/10 transition-colors
                "
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {/* Notifications List */}
          <div className="max-h-[400px] overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            {!hasNotifications ? (
              <EmptyState />
            ) : (
              notifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onClick={handleNotificationClick}
                  onMarkRead={onMarkRead}
                  onDismiss={onDismiss}
                />
              ))
            )}
          </div>

          {/* Footer */}
          {hasNotifications && (
            <div className="px-4 py-2.5 border-t border-white/10 bg-bg-panel/5">
              <button
                onClick={() => {
                  // In real app: router.push("/dashboard/notifications")
                  setIsOpen(false);
                }}
                className="
                  w-full py-2 rounded-lg
                  text-xs font-medium text-ink-2 hover:text-ink
                  hover:bg-bg-panel/5 transition-colors
                "
              >
                View all notifications
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================
// Hook for managing notifications state
// ============================================

export function useNotifications(initialNotifications: Notification[] = mockNotifications) {
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications);

  const markAsRead = useCallback((notificationId: string) => {
    setNotifications((prev) =>
      prev.map((n) =>
        n.id === notificationId ? { ...n, read: true } : n
      )
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) =>
      prev.map((n) => ({ ...n, read: true }))
    );
  }, []);

  const dismiss = useCallback((notificationId: string) => {
    setNotifications((prev) =>
      prev.filter((n) => n.id !== notificationId)
    );
  }, []);

  const addNotification = useCallback((notification: Omit<Notification, "id" | "timestamp" | "read">) => {
    const newNotification: Notification = {
      ...notification,
      id: `notif-${Date.now()}`,
      timestamp: new Date(),
      read: false,
    };
    setNotifications((prev) => [newNotification, ...prev]);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    dismiss,
    addNotification,
    setNotifications,
  };
}

export default NotificationsPanel;
