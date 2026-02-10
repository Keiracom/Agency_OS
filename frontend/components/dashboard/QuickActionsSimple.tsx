/**
 * QuickActionsSimple.tsx - Quick Action Buttons
 * Sprint 2 - Ported from dashboard-v3.html
 *
 * Simple quick actions component for Command Center dashboard.
 * Replaces the bloated 300+ line version for Sprint 2.
 */

"use client";

import Link from "next/link";
import { Zap, Users, Settings, type LucideIcon } from "lucide-react";

// ============================================
// Types
// ============================================

export type IconName = "zap" | "users" | "settings";

export interface QuickActionItem {
  id: string;
  label: string;
  icon: IconName;
  href: string;
}

export interface QuickActionsProps {
  actions: QuickActionItem[];
}

// ============================================
// Icon Mapping
// ============================================

const iconMap: Record<IconName, LucideIcon> = {
  zap: Zap,
  users: Users,
  settings: Settings,
};

// ============================================
// ActionButton Component
// ============================================

function ActionButton({ action }: { action: QuickActionItem }) {
  const Icon = iconMap[action.icon];

  return (
    <Link
      href={action.href}
      className="flex items-center gap-3 px-4 py-3.5 bg-bg-elevated border border-border-default rounded-lg mb-2.5 last:mb-0 hover:border-accent-primary hover:bg-accent-primary/5 transition-all group"
    >
      <Icon className="w-5 h-5 text-accent-primary" />
      <span className="text-sm font-medium text-text-primary group-hover:text-text-primary">
        {action.label}
      </span>
    </Link>
  );
}

// ============================================
// QuickActions Component
// ============================================

export function QuickActionsSimple({ actions }: QuickActionsProps) {
  return (
    <div className="bg-bg-surface border border-border-default rounded-2xl p-6">
      <div className="mb-5">
        <h3 className="text-base font-semibold text-text-primary">Quick Actions</h3>
      </div>
      <div>
        {actions.length > 0 ? (
          actions.map((action) => <ActionButton key={action.id} action={action} />)
        ) : (
          <p className="text-sm text-text-muted py-4 text-center">
            No actions available
          </p>
        )}
      </div>
    </div>
  );
}

export default QuickActionsSimple;
