/**
 * FILE: frontend/components/campaigns/CampaignTabs.tsx
 * PURPOSE: Tab navigation for campaign detail page
 * PHASE: Phase I Dashboard Redesign
 *
 * Features:
 * - Overview: Metrics, settings
 * - Sequences: Email sequence builder
 * - Leads: Leads in this campaign
 * - Activity: Recent actions
 */

"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  GitBranch,
  Users,
  Activity,
} from "lucide-react";

// ============================================
// Types
// ============================================

export type CampaignTab = "overview" | "sequences" | "leads" | "activity";

export interface CampaignTabsProps {
  /** Campaign ID */
  campaignId: string;
  /** Currently active tab */
  activeTab: CampaignTab;
  /** Callback when tab changes */
  onTabChange: (tab: CampaignTab) => void;
  /** Additional class names */
  className?: string;
}

// ============================================
// Tab Configuration
// ============================================

const TABS: Array<{
  id: CampaignTab;
  label: string;
  icon: React.ReactNode;
  description: string;
}> = [
  {
    id: "overview",
    label: "Overview",
    icon: <BarChart3 className="h-4 w-4" />,
    description: "Metrics, settings",
  },
  {
    id: "sequences",
    label: "Sequences",
    icon: <GitBranch className="h-4 w-4" />,
    description: "Email sequence builder",
  },
  {
    id: "leads",
    label: "Leads",
    icon: <Users className="h-4 w-4" />,
    description: "Leads in this campaign",
  },
  {
    id: "activity",
    label: "Activity",
    icon: <Activity className="h-4 w-4" />,
    description: "Recent actions",
  },
];

// ============================================
// Main Component
// ============================================

/**
 * CampaignTabs provides tab navigation for the campaign detail page.
 *
 * Tabs:
 * - Overview: Campaign metrics and settings
 * - Sequences: Sequence builder for email steps
 * - Leads: List of leads in this campaign
 * - Activity: Recent activity feed
 */
export function CampaignTabs({
  campaignId,
  activeTab,
  onTabChange,
  className,
}: CampaignTabsProps) {
  return (
    <div
      className={cn(
        "flex border-b border-border",
        className
      )}
      role="tablist"
      aria-label="Campaign sections"
    >
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            aria-controls={`campaign-${campaignId}-${tab.id}-panel`}
            id={`campaign-${campaignId}-${tab.id}-tab`}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors",
              "border-b-2 -mb-px",
              "hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              isActive
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground"
            )}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export default CampaignTabs;
