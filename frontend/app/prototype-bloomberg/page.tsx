"use client";

/**
 * Bloomberg Terminal Dashboard
 * Matches: dashboard-v3.html design exactly
 * Theme: #0A0A12 base, #7C3AED purple accent
 * 
 * Features:
 * - ICP Extraction Progress Bar
 * - Stats Grid (4 cards)
 * - Activity Feed
 * - Quick Actions
 * - Maya AI Companion
 */

import { useState, useEffect } from "react";
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
  LucideIcon,
} from "lucide-react";

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
      { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/prototype-bloomberg" },
      { key: "leads", label: "Leads", icon: Users, href: "/prototype-bloomberg/leads" },
      { key: "campaigns", label: "Campaigns", icon: Zap, href: "/prototype-bloomberg/campaigns" },
      { key: "replies", label: "Replies", icon: MessageSquare, href: "/prototype-bloomberg/replies" },
    ],
  },
  {
    title: "Analytics",
    items: [
      { key: "reports", label: "Reports", icon: BarChart3, href: "/prototype-bloomberg/reports" },
    ],
  },
  {
    title: "Settings",
    items: [
      { key: "settings", label: "Settings", icon: Settings, href: "/prototype-bloomberg/settings" },
      { key: "billing", label: "Billing", icon: CreditCard, href: "/prototype-bloomberg/billing" },
    ],
  },
];

function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/prototype-bloomberg") {
      return pathname === "/prototype-bloomberg";
    }
    return pathname.startsWith(href);
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
// EXTRACTION BAR COMPONENT
// ============================================================================

const extractionSteps = [
  { progress: 35, status: "Scraping website & extracting portfolio" },
  { progress: 45, status: "Extracting services & value proposition" },
  { progress: 60, status: "Finding portfolio companies" },
  { progress: 75, status: "Enriching portfolio data via Siege Waterfall" },
  { progress: 90, status: "Deriving ideal client profile" },
  { progress: 100, status: "Complete! Campaign suggestions ready" },
];

function ExtractionBar() {
  const [progress, setProgress] = useState(35);
  const [status, setStatus] = useState(extractionSteps[0].status);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    let stepIndex = 0;
    const interval = setInterval(() => {
      stepIndex++;
      if (stepIndex >= extractionSteps.length) {
        clearInterval(interval);
        setIsComplete(true);
        return;
      }

      const step = extractionSteps[stepIndex];
      setProgress(step.progress);
      setStatus(step.status);

      if (step.progress >= 100) {
        setIsComplete(true);
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="rounded-xl p-4 flex items-center gap-5 transition-all duration-500"
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
        <p className="text-sm truncate" style={{ color: theme.textSecondary }}>{status}</p>
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
}

const colorMap = {
  purple: theme.accentPurpleLight,
  green: theme.accentGreen,
  blue: theme.accentBlue,
  orange: theme.accentOrange,
};

function StatCard({ label, value, color }: StatCardProps) {
  return (
    <div
      className="rounded-xl p-5"
      style={{ 
        background: theme.bgSecondary, 
        border: `1px solid ${theme.borderColor}` 
      }}
    >
      <p className="text-sm mb-2" style={{ color: theme.textSecondary }}>{label}</p>
      <p 
        className="text-3xl font-bold font-mono"
        style={{ color: colorMap[color] }}
      >
        {value}
      </p>
    </div>
  );
}

// ============================================================================
// ACTIVITY FEED COMPONENT
// ============================================================================

interface ActivityItemData {
  id: string;
  channel: "email" | "linkedin" | "meeting";
  text: string;
  timestamp: string;
}

const channelConfig = {
  email: { icon: Mail, bgColor: `${theme.accentBlue}20`, iconColor: theme.accentBlue },
  linkedin: { icon: Linkedin, bgColor: `${theme.accentPurple}20`, iconColor: theme.accentPurple },
  meeting: { icon: CheckCircle, bgColor: `${theme.accentGreen}20`, iconColor: theme.accentGreen },
};

const demoActivities: ActivityItemData[] = [
  { id: "1", channel: "email", text: "Email warmup started for 3 domains", timestamp: "Just now" },
  { id: "2", channel: "linkedin", text: "LinkedIn account connected", timestamp: "2 minutes ago" },
  { id: "3", channel: "meeting", text: "Onboarding started", timestamp: "5 minutes ago" },
];

function ActivityFeed() {
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
        <a 
          href="#" 
          className="text-sm transition-colors"
          style={{ color: theme.accentPurple }}
        >
          View all
        </a>
      </div>

      <div className="divide-y" style={{ borderColor: theme.borderColor }}>
        {demoActivities.map((activity) => {
          const config = channelConfig[activity.channel];
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
                <p className="text-sm text-white">{activity.text}</p>
                <p className="text-xs mt-0.5" style={{ color: theme.textMuted }}>{activity.timestamp}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// QUICK ACTIONS COMPONENT
// ============================================================================

function QuickActions() {
  const actions = [
    { label: "Create Campaign", icon: Zap, href: "/prototype-bloomberg/campaigns" },
    { label: "View Leads", icon: Users, href: "/prototype-bloomberg/leads" },
    { label: "Settings", icon: Settings, href: "/prototype-bloomberg/settings" },
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
// MAYA COMPANION COMPONENT
// ============================================================================

const mayaSteps = [
  {
    content: "Welcome to Agency OS! 👋 I'm Maya, your digital employee. I'm currently analyzing your website to understand your agency and find your ideal clients. This usually takes 2-3 minutes.",
    action: "Got it",
  },
  {
    content: "While I analyze your website, I'm also setting up your email domains and phone numbers. These are pre-warmed and ready to use! 🚀",
    action: "Continue",
  },
  {
    content: "Once the analysis is complete, I'll suggest campaigns based on your ideal client profile. You'll see them on the Campaigns page.",
    action: "Show me",
  },
  {
    content: "That's the basics! I'll be here in the corner whenever you need help. Click my avatar anytime to chat. 💬",
    action: "Finish tour",
  },
];

function MayaCompanion() {
  const [isOpen, setIsOpen] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPulsing, setIsPulsing] = useState(true);

  const currentMayaStep = mayaSteps[currentStep];

  const handleNext = () => {
    const nextStep = currentStep + 1;
    
    if (nextStep >= mayaSteps.length) {
      setIsOpen(false);
      setIsPulsing(false);
      return;
    }

    setCurrentStep(nextStep);
  };

  const handleDismiss = () => {
    setIsOpen(false);
    setIsPulsing(false);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Bubble */}
      {isOpen && currentMayaStep && (
        <div 
          className="absolute bottom-full right-0 mb-4 w-80 rounded-2xl p-5 shadow-2xl animate-in slide-in-from-bottom-3 fade-in duration-300"
          style={{ 
            background: theme.bgSecondary, 
            border: `1px solid ${theme.borderColor}`,
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)"
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-3 mb-3">
            <div 
              className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold shadow-lg"
              style={{ 
                background: `linear-gradient(135deg, ${theme.accentPurple} 0%, ${theme.accentPurpleLight} 100%)`,
                boxShadow: "0 4px 12px rgba(124, 58, 237, 0.3)"
              }}
            >
              M
            </div>
            <div>
              <p className="font-semibold text-white text-sm">Maya</p>
              <p className="text-xs" style={{ color: theme.textMuted }}>Your Digital Employee</p>
            </div>
          </div>

          {/* Content */}
          <p 
            className="text-sm leading-relaxed mb-4"
            style={{ color: theme.textSecondary }}
          >
            {currentMayaStep.content}
          </p>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={handleNext}
              className="flex-1 px-4 py-2.5 text-white text-sm font-medium rounded-lg transition-colors hover:opacity-90"
              style={{ background: theme.accentPurple }}
            >
              {currentMayaStep.action}
            </button>
            <button
              onClick={handleDismiss}
              className="px-4 py-2.5 text-sm font-medium rounded-lg transition-colors"
              style={{ 
                background: theme.bgTertiary, 
                color: theme.textSecondary,
                border: `1px solid ${theme.borderColor}`
              }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-16 h-16 rounded-full border-[3px] shadow-lg flex items-center justify-center text-white text-2xl font-bold transition-transform hover:scale-105"
        style={{ 
          background: `linear-gradient(135deg, ${theme.accentPurple} 0%, ${theme.accentPurpleLight} 100%)`,
          borderColor: theme.bgSecondary,
          boxShadow: `0 8px 24px rgba(124, 58, 237, 0.4)`,
          animation: isPulsing ? "maya-pulse 2s infinite" : undefined,
        }}
      >
        M
      </button>

      <style jsx>{`
        @keyframes maya-pulse {
          0%, 100% {
            box-shadow: 0 8px 24px rgba(124, 58, 237, 0.4);
          }
          50% {
            box-shadow: 0 8px 32px rgba(124, 58, 237, 0.6), 0 0 0 8px rgba(124, 58, 237, 0.1);
          }
        }
      `}</style>
    </div>
  );
}

// ============================================================================
// MAIN DASHBOARD PAGE
// ============================================================================

export default function BloombergDashboard() {
  const stats = [
    { label: "Leads This Month", value: "0", color: "purple" as const },
    { label: "Emails Sent", value: "0", color: "blue" as const },
    { label: "Meetings Booked", value: "0", color: "green" as const },
    { label: "Response Rate", value: "--%", color: "orange" as const },
  ];

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
        <div className="mb-6">
          <ExtractionBar />
        </div>

        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-[28px] font-bold text-white mb-2">Command Center</h1>
          <p style={{ color: theme.textSecondary }}>
            Welcome back. Here&apos;s what&apos;s happening with your outreach.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {stats.map((stat, index) => (
            <StatCard key={index} {...stat} />
          ))}
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2">
            <ActivityFeed />
          </div>
          <div>
            <QuickActions />
          </div>
        </div>
      </main>

      {/* Maya Companion */}
      <MayaCompanion />
    </div>
  );
}
