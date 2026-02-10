/**
 * StatsRow.tsx - Dashboard Statistics Row
 * Sprint 2 - Ported from dashboard-v3.html
 *
 * Simple 4-card stats grid for Command Center dashboard.
 * Uses theme tokens from tailwind.config.js
 */

"use client";

import { Users, Mail, Calendar, TrendingUp } from "lucide-react";

// ============================================
// Types
// ============================================

export interface StatsRowProps {
  /** Number of leads this month */
  leads: number;
  /** Number of emails sent */
  emails: number;
  /** Number of meetings booked */
  meetings: number;
  /** Response rate percentage */
  responseRate: number;
}

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  colorClass: string;
}

// ============================================
// StatCard Component
// ============================================

function StatCard({ label, value, icon, colorClass }: StatCardProps) {
  return (
    <div className="bg-bg-surface border border-border-default rounded-xl p-5 hover:bg-bg-surface-hover transition-colors">
      <div className="flex items-start justify-between mb-2">
        <span className="text-sm text-text-secondary">{label}</span>
        <div className="text-text-muted">{icon}</div>
      </div>
      <div className={`text-3xl font-bold font-mono ${colorClass}`}>
        {value}
      </div>
    </div>
  );
}

// ============================================
// StatsRow Component
// ============================================

export function StatsRow({ leads, emails, meetings, responseRate }: StatsRowProps) {
  return (
    <div className="grid grid-cols-4 gap-4 mb-8">
      <StatCard
        label="Leads This Month"
        value={leads}
        icon={<Users className="w-5 h-5" />}
        colorClass="text-accent-primary"
      />
      <StatCard
        label="Emails Sent"
        value={emails.toLocaleString()}
        icon={<Mail className="w-5 h-5" />}
        colorClass="text-accent-blue"
      />
      <StatCard
        label="Meetings Booked"
        value={meetings}
        icon={<Calendar className="w-5 h-5" />}
        colorClass="text-status-success"
      />
      <StatCard
        label="Response Rate"
        value={`${responseRate}%`}
        icon={<TrendingUp className="w-5 h-5" />}
        colorClass="text-status-warning"
      />
    </div>
  );
}

export default StatsRow;
