/**
 * ActivityFeedSimple.tsx - Recent Activity List
 * Sprint 2 - Ported from dashboard-v3.html
 *
 * Simple activity feed component for Command Center dashboard.
 * Replaces the bloated 600+ line version for Sprint 2.
 */

"use client";

import { Mail, Linkedin, CheckCircle } from "lucide-react";

// ============================================
// Types
// ============================================

export type ActivityType = "email" | "linkedin" | "meeting";

export interface ActivityItem {
  id: string;
  type: ActivityType;
  text: string;
  time: string;
}

export interface ActivityFeedProps {
  items: ActivityItem[];
  /** Optional "View all" link href */
  viewAllHref?: string;
}

// ============================================
// Icon Configuration
// ============================================

const iconConfig: Record<ActivityType, { icon: React.ReactNode; bgClass: string }> = {
  email: {
    icon: <Mail className="w-4 h-4" />,
    bgClass: "bg-accent-primary/15 text-accent-primary",
  },
  linkedin: {
    icon: <Linkedin className="w-4 h-4" />,
    bgClass: "bg-accent-blue/15 text-accent-blue",
  },
  meeting: {
    icon: <CheckCircle className="w-4 h-4" />,
    bgClass: "bg-status-success/15 text-status-success",
  },
};

// ============================================
// ActivityItem Component
// ============================================

function ActivityItemRow({ item }: { item: ActivityItem }) {
  const config = iconConfig[item.type];

  return (
    <div className="flex items-start gap-3 py-3 border-b border-border-default last:border-b-0">
      <div
        className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${config.bgClass}`}
      >
        {config.icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary truncate">{item.text}</p>
        <p className="text-xs text-text-muted mt-1">{item.time}</p>
      </div>
    </div>
  );
}

// ============================================
// ActivityFeed Component
// ============================================

export function ActivityFeedSimple({ items, viewAllHref }: ActivityFeedProps) {
  return (
    <div className="bg-bg-surface border border-border-default rounded-2xl p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base font-semibold text-text-primary">Recent Activity</h3>
        {viewAllHref && (
          <a
            href={viewAllHref}
            className="text-sm text-accent-primary hover:text-accent-primary-hover transition-colors"
          >
            View all
          </a>
        )}
      </div>
      <div className="space-y-0">
        {items.length > 0 ? (
          items.map((item) => <ActivityItemRow key={item.id} item={item} />)
        ) : (
          <p className="text-sm text-text-muted py-4 text-center">
            No recent activity
          </p>
        )}
      </div>
    </div>
  );
}

export default ActivityFeedSimple;
