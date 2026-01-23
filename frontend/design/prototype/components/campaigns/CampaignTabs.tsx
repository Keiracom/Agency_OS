"use client";

/**
 * Tab type for campaign detail navigation
 */
export type CampaignTab = "overview" | "sequences" | "leads" | "activity";

/**
 * CampaignTabs props
 */
export interface CampaignTabsProps {
  /** Currently active tab */
  activeTab: CampaignTab;
  /** Callback when tab changes */
  onTabChange: (tab: CampaignTab) => void;
}

/**
 * Tab configuration
 */
interface TabConfig {
  id: CampaignTab;
  label: string;
}

const tabs: TabConfig[] = [
  { id: "overview", label: "Overview" },
  { id: "sequences", label: "Sequences" },
  { id: "leads", label: "Leads" },
  { id: "activity", label: "Activity" },
];

/**
 * CampaignTabs - Tab navigation for campaign detail page
 *
 * Features:
 * - 4 tabs: Overview, Sequences, Leads, Activity
 * - Underline style active indicator
 * - Hover state
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Active tab: #3B82F6 (accent-blue)
 * - Inactive tab: #64748B (text-secondary)
 * - Border: #E2E8F0
 */
export function CampaignTabs({ activeTab, onTabChange }: CampaignTabsProps) {
  return (
    <div className="border-b border-[#E2E8F0]">
      <nav className="flex gap-8" aria-label="Campaign tabs">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                relative pb-4 text-sm font-medium transition-colors
                ${
                  isActive
                    ? "text-[#3B82F6]"
                    : "text-[#64748B] hover:text-[#1E293B]"
                }
              `}
              aria-current={isActive ? "page" : undefined}
            >
              {tab.label}
              {/* Active indicator */}
              {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#3B82F6] rounded-full" />
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

export default CampaignTabs;
