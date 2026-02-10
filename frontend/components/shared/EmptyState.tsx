/**
 * EmptyState.tsx - Reusable empty state component
 * Sprint 4 - Used across all dashboard pages for new customers
 * 
 * Maya AI assistant is referenced in appropriate contexts.
 */

"use client";

import { ReactNode } from "react";
import { 
  LayoutDashboard, 
  Users, 
  Megaphone, 
  MessageSquare, 
  BarChart3,
  Sparkles,
  ArrowRight,
  Zap
} from "lucide-react";

// ============================================
// Types
// ============================================

export type EmptyStatePage = 
  | "dashboard" 
  | "leads" 
  | "campaigns" 
  | "replies" 
  | "reports";

interface EmptyStateProps {
  page: EmptyStatePage;
  className?: string;
}

// ============================================
// Page-specific Content
// ============================================

interface EmptyStateContent {
  icon: ReactNode;
  title: string;
  description: string;
  mayaMessage?: string;
  action?: {
    label: string;
    href: string;
  };
}

const emptyStateContent: Record<EmptyStatePage, EmptyStateContent> = {
  dashboard: {
    icon: <LayoutDashboard className="w-12 h-12" />,
    title: "Welcome to Your Command Center",
    description: "This is where you'll see your key metrics, pipeline health, and AI insights once you start your first campaign.",
    mayaMessage: "Hi! I'm Maya, your AI assistant. I'm setting up your personalized dashboard. Once your first campaign launches, you'll see real-time metrics here.",
    action: {
      label: "Create Your First Campaign",
      href: "/campaigns",
    },
  },
  leads: {
    icon: <Users className="w-12 h-12" />,
    title: "No Leads Yet",
    description: "Your leads will appear here as they're enriched and scored by our AI. Start a campaign to begin building your pipeline.",
    mayaMessage: "I'll automatically score and prioritize your leads as they come in. Hot leads will be flagged for immediate action!",
    action: {
      label: "Start Prospecting",
      href: "/campaigns",
    },
  },
  campaigns: {
    icon: <Megaphone className="w-12 h-12" />,
    title: "Launch Your First Campaign",
    description: "Create a multi-channel campaign to start reaching your ideal customers across email, LinkedIn, SMS, voice, and direct mail.",
    mayaMessage: "I'm ready to help you craft personalized outreach sequences. Let's get your first campaign live!",
    action: {
      label: "Create Campaign",
      href: "/campaigns/new",
    },
  },
  replies: {
    icon: <MessageSquare className="w-12 h-12" />,
    title: "Your Inbox is Empty",
    description: "When leads respond to your campaigns, their messages will appear here. I'll help you craft the perfect follow-up.",
    mayaMessage: "Once replies start coming in, I'll analyze sentiment and suggest responses to help you book more meetings.",
    action: {
      label: "View Campaigns",
      href: "/campaigns",
    },
  },
  reports: {
    icon: <BarChart3 className="w-12 h-12" />,
    title: "Analytics Coming Soon",
    description: "Once your campaigns are running, you'll see detailed performance analytics, channel comparisons, and ROI metrics here.",
    mayaMessage: "I'm preparing your analytics dashboard. After your first week of campaigning, I'll have insights ready for you!",
    action: {
      label: "Launch a Campaign",
      href: "/campaigns",
    },
  },
};

// ============================================
// Component
// ============================================

export function EmptyState({ page, className = "" }: EmptyStateProps) {
  const content = emptyStateContent[page];

  return (
    <div className={`flex flex-col items-center justify-center py-20 px-6 ${className}`}>
      {/* Icon */}
      <div className="w-24 h-24 rounded-2xl bg-bg-surface border border-border-subtle flex items-center justify-center text-text-muted mb-6">
        {content.icon}
      </div>

      {/* Title */}
      <h2 className="text-2xl font-bold text-text-primary mb-3 text-center">
        {content.title}
      </h2>

      {/* Description */}
      <p className="text-text-secondary text-center max-w-md mb-8">
        {content.description}
      </p>

      {/* Maya AI Message */}
      {content.mayaMessage && (
        <div className="flex items-start gap-4 max-w-lg mb-8 p-4 rounded-xl bg-gradient-to-r from-accent-primary/10 to-accent-blue/10 border border-accent-primary/20">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-primary to-accent-blue flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-accent-primary">Maya</span>
              <span className="text-xs text-text-muted">AI Assistant</span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">
              {content.mayaMessage}
            </p>
          </div>
        </div>
      )}

      {/* Action Button */}
      {content.action && (
        <a
          href={content.action.href}
          className="inline-flex items-center gap-2 px-6 py-3 bg-accent-primary hover:bg-accent-primary-hover text-white font-semibold rounded-lg transition-all hover:-translate-y-0.5"
        >
          <Zap className="w-4 h-4" />
          {content.action.label}
          <ArrowRight className="w-4 h-4" />
        </a>
      )}
    </div>
  );
}

export default EmptyState;
