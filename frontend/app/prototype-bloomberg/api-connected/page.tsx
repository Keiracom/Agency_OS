"use client";

/**
 * Bloomberg Terminal Dashboard - API Connected Version
 * Same visual design as prototype-bloomberg but wired to real backend APIs
 * 
 * Uses hooks from:
 * - hooks/use-reports.ts (dashboard stats, activity feed)
 * - hooks/use-campaigns.ts (campaign data)
 * - hooks/use-icp-job.ts (ICP extraction status)
 */

import { useState, Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Zap,
  MessageSquare,
  BarChart3,
  Settings,
  CreditCard,
  Mail,
  Linkedin,
  CheckCircle,
  Clock,
  Loader2,
  AlertCircle,
  LucideIcon,
} from "lucide-react";

// Import existing hooks
import { useDashboardStats, useActivityFeed, useALSDistribution } from "@/hooks/use-reports";
import { useICPJob } from "@/hooks/use-icp-job";

// ============================================================================
// THEME CONSTANTS
// ============================================================================

const theme = {
  bgPrimary: "#0A0A12",
  bgSecondary: "#12121A",
  bgTertiary: "#1A1A24",
  borderColor: "#2A2A3A",
  textPrimary: "#FFFFFF",
  textSecondary: "#A0A0B0",
  textMuted: "#6B6B7B",
  accentPurple: "#7C3AED",
  accentPurpleLight: "#9D5CFF",
  accentGreen: "#10B981",
  accentBlue: "#3B82F6",
  accentOrange: "#F59E0B",
  accentRed: "#EF4444",
};

// ============================================================================
// SIDEBAR COMPONENT
// ============================================================================

interface NavItem {
  key: string;
  label: string;
  icon: LucideIcon;
  href: string;
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: "Main",
    items: [
      { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/prototype-bloomberg/api-connected" },
      { key: "leads", label: "Leads", icon: Users, href: "/dashboard/leads" },
      { key: "campaigns", label: "Campaigns", icon: Zap, href: "/dashboard/campaigns" },
      { key: "replies", label: "Replies", icon: MessageSquare, href: "/dashboard/replies" },
    ],
  },
  {
    title: "Analytics",
    items: [
      { key: "reports", label: "Reports", icon: BarChart3, href: "/dashboard/reports" },
    ],
  },
  {
    title: "Settings",
    items: [
      { key: "settings", label: "Settings", icon: Settings, href: "/dashboard/settings" },
      { key: "billing", label: "Billing", icon: CreditCard, href: "/dashboard/billing" },
    ],
  },
];

function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    return pathname === href || pathname.startsWith(href + "/");
  };

  return (
    <aside 
      className="fixed left-0 top-0 bottom-0 w-60 border-r z-50 flex flex-col"
      style={{ background: theme.bgSecondary, borderColor: theme.borderColor }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div 
          className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg"
          style={{ 
            background: `linear-gradient(135deg, ${theme.accentPurple} 0%, ${theme.accentPurpleLight} 100%)`,
            boxShadow: "0 8px 24px rgba(124, 58, 237, 0.3)"
          }}
        >
          <svg viewBox="0 0 36 36" fill="none" className="w-5 h-5">
            <path d="M10 18L15 23L26 12" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <span className="text-lg font-bold text-white">Agency OS</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {navSections.map((section) => (
          <div key={section.title} className="mb-6">
            <div className="px-5 mb-2">
              <span 
                className="text-[11px] font-semibold uppercase tracking-wider"
                style={{ color: theme.textMuted }}
              >
                {section.title}
              </span>
            </div>
            {section.items.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.key}
                  href={item.href}
                  className="flex items-center gap-3 px-5 py-3 text-sm font-medium transition-all"
                  style={{ 
                    background: active ? `${theme.accentPurple}10` : "transparent",
                    color: active ? theme.accentPurpleLight : theme.textSecondary,
                    borderRight: active ? `2px solid ${theme.accentPurple}` : "none",
                  }}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}

// ============================================================================
// ICP EXTRACTION BAR (CONNECTED)
// ============================================================================

function ExtractionBarConnected() {
  const { status, showBanner } = useICPJob();

  if (!showBanner || !status) return null;

  const progress = status.progress || 0;
  const isComplete = status.status === "completed";
  const statusText = status.current_step || "Analyzing your agency...";

  return (
    <div
      className="rounded-xl p-4 flex items-center gap-5 transition-all duration-500 mb-6"
      style={{
        background: isComplete 
          ? `linear-gradient(135deg, ${theme.accentGreen}15 0%, ${theme.accentGreen}08 100%)`
          : `linear-gradient(135deg, ${theme.accentPurple}15 0%, ${theme.accentBlue}15 100%)`,
        border: `1px solid ${isComplete ? `${theme.accentGreen}50` : `${theme.accentPurple}50`}`,
      }}
    >
      <div 
        className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: theme.bgSecondary }}
      >
        {isComplete ? (
          <CheckCircle className="w-6 h-6" style={{ color: theme.accentGreen }} />
        ) : (
          <Clock className="w-6 h-6" style={{ color: theme.accentPurple }} />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <h4 className="font-semibold text-sm text-white mb-1">
          {isComplete ? "Analysis Complete!" : "Analyzing your agency..."}
        </h4>
        <p className="text-sm truncate" style={{ color: theme.textSecondary }}>{statusText}</p>
      </div>

      <div className="w-48">
        <div 
          className="h-2 rounded-full overflow-hidden mb-1.5"
          style={{ background: theme.bgTertiary }}
        >
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ 
              width: `${progress}%`,
              background: isComplete 
                ? theme.accentGreen 
                : `linear-gradient(90deg, ${theme.accentPurple} 0%, ${theme.accentBlue} 100%)`
            }}
          />
        </div>
        <p 
          className="text-xs text-right font-mono"
          style={{ color: theme.textMuted }}
        >
          {progress}%
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// STAT CARD COMPONENT
// ============================================================================

interface StatCardProps {
  label: string;
  value: string | number;
  color: "purple" | "green" | "blue" | "orange";
  isLoading?: boolean;
}

const colorMap = {
  purple: theme.accentPurpleLight,
  green: theme.accentGreen,
  blue: theme.accentBlue,
  orange: theme.accentOrange,
};

function StatCard({ label, value, color, isLoading }: StatCardProps) {
  return (
    <div
      className="rounded-xl p-5"
      style={{ 
        background: theme.bgSecondary, 
        border: `1px solid ${theme.borderColor}` 
      }}
    >
      <p className="text-sm mb-2" style={{ color: theme.textSecondary }}>{label}</p>
      {isLoading ? (
        <div className="flex items-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin" style={{ color: theme.textMuted }} />
        </div>
      ) : (
        <p 
          className="text-3xl font-bold font-mono"
          style={{ color: colorMap[color] }}
        >
          {value}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// STATS GRID (CONNECTED)
// ============================================================================

function StatsGridConnected() {
  const { data: stats, isLoading, error } = useDashboardStats();

  if (error) {
    return (
      <div 
        className="rounded-xl p-6 flex items-center gap-3"
        style={{ background: `${theme.accentRed}15`, border: `1px solid ${theme.accentRed}50` }}
      >
        <AlertCircle className="w-5 h-5" style={{ color: theme.accentRed }} />
        <span style={{ color: theme.accentRed }}>Failed to load stats</span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-4 gap-4 mb-8">
      <StatCard 
        label="Total Leads" 
        value={stats?.total_leads?.toLocaleString() || "0"} 
        color="purple"
        isLoading={isLoading}
      />
      <StatCard 
        label="Emails Sent" 
        value={stats?.emails_sent?.toLocaleString() || stats?.leads_contacted?.toLocaleString() || "0"} 
        color="blue"
        isLoading={isLoading}
      />
      <StatCard 
        label="Meetings Booked" 
        value={stats?.meetings_booked?.toLocaleString() || stats?.leads_converted?.toLocaleString() || "0"} 
        color="green"
        isLoading={isLoading}
      />
      <StatCard 
        label="Response Rate" 
        value={stats?.reply_rate ? `${stats.reply_rate.toFixed(1)}%` : "--%"} 
        color="orange"
        isLoading={isLoading}
      />
    </div>
  );
}

// ============================================================================
// ACTIVITY FEED (CONNECTED)
// ============================================================================

const channelConfig = {
  email: { icon: Mail, bgColor: `${theme.accentBlue}20`, iconColor: theme.accentBlue },
  linkedin: { icon: Linkedin, bgColor: `${theme.accentPurple}20`, iconColor: theme.accentPurple },
  sms: { icon: CheckCircle, bgColor: `${theme.accentGreen}20`, iconColor: theme.accentGreen },
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function ActivityFeedConnected() {
  const { data: activities, isLoading, error } = useActivityFeed(5);

  return (
    <div
      className="rounded-2xl"
      style={{ background: theme.bgSecondary, border: `1px solid ${theme.borderColor}` }}
    >
      <div 
        className="flex items-center justify-between px-6 py-4"
        style={{ borderBottom: `1px solid ${theme.borderColor}` }}
      >
        <h3 className="font-semibold text-white">Recent Activity</h3>
        <Link 
          href="/dashboard/replies" 
          className="text-sm transition-colors"
          style={{ color: theme.accentPurple }}
        >
          View all
        </Link>
      </div>

      <div className="divide-y" style={{ borderColor: theme.borderColor }}>
        {isLoading ? (
          <div className="px-6 py-8 flex justify-center">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: theme.textMuted }} />
          </div>
        ) : error ? (
          <div className="px-6 py-8 text-center">
            <p style={{ color: theme.accentRed }}>Failed to load activity</p>
          </div>
        ) : !activities || activities.length === 0 ? (
          <div className="px-6 py-8 text-center">
            <p style={{ color: theme.textMuted }}>No recent activity</p>
          </div>
        ) : (
          activities.map((activity: any) => {
            const config = channelConfig[activity.channel as keyof typeof channelConfig] || channelConfig.email;
            const Icon = config.icon;
            
            return (
              <div key={activity.id} className="flex items-start gap-3 px-6 py-3">
                <div 
                  className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: config.bgColor }}
                >
                  <Icon className="w-[18px] h-[18px]" style={{ color: config.iconColor }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white">
                    {activity.lead?.first_name} {activity.lead?.last_name}
                    {activity.lead?.company && (
                      <span style={{ color: theme.textMuted }}> at {activity.lead.company}</span>
                    )}
                  </p>
                  <p className="text-xs truncate" style={{ color: theme.textSecondary }}>
                    {activity.action}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: theme.textMuted }}>
                    {formatTimeAgo(activity.created_at)}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ============================================================================
// QUICK ACTIONS
// ============================================================================

function QuickActions() {
  const actions = [
    { label: "Create Campaign", icon: Zap, href: "/dashboard/campaigns/new" },
    { label: "View Leads", icon: Users, href: "/dashboard/leads" },
    { label: "Settings", icon: Settings, href: "/dashboard/settings" },
  ];

  return (
    <div
      className="rounded-2xl"
      style={{ background: theme.bgSecondary, border: `1px solid ${theme.borderColor}` }}
    >
      <div 
        className="px-6 py-4"
        style={{ borderBottom: `1px solid ${theme.borderColor}` }}
      >
        <h3 className="font-semibold text-white">Quick Actions</h3>
      </div>

      <div className="p-4 space-y-2.5">
        {actions.map((action, index) => (
          <Link
            key={index}
            href={action.href}
            className="flex items-center gap-3 px-4 py-3.5 rounded-xl cursor-pointer transition-all hover:border-[#7C3AED] group"
            style={{ 
              background: theme.bgTertiary, 
              border: `1px solid ${theme.borderColor}` 
            }}
          >
            <action.icon className="w-5 h-5" style={{ color: theme.accentPurple }} />
            <span className="text-sm font-medium text-white">{action.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// DASHBOARD CONTENT
// ============================================================================

function DashboardContent() {
  return (
    <div 
      className="min-h-screen"
      style={{ background: theme.bgPrimary }}
    >
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="ml-60 p-6 lg:p-8">
        {/* ICP Extraction Bar */}
        <ExtractionBarConnected />

        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-[28px] font-bold text-white mb-2">Command Center</h1>
          <p style={{ color: theme.textSecondary }}>
            Welcome back. Here&apos;s what&apos;s happening with your outreach.
          </p>
        </div>

        {/* Stats Grid - Connected to API */}
        <StatsGridConnected />

        {/* Cards Grid */}
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2">
            <ActivityFeedConnected />
          </div>
          <div>
            <QuickActions />
          </div>
        </div>
      </main>
    </div>
  );
}

// ============================================================================
// MAIN PAGE
// ============================================================================

export default function BloombergDashboardAPIConnected() {
  return (
    <Suspense fallback={
      <div 
        className="min-h-screen flex items-center justify-center"
        style={{ background: theme.bgPrimary }}
      >
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: theme.accentPurple }} />
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
