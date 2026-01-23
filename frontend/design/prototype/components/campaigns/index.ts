/**
 * Campaign Components - Campaign management UI building blocks
 *
 * These components provide the campaign management functionality for Agency OS:
 * - PrioritySlider: Standalone priority allocation slider
 * - CampaignAllocationManager: Container managing all campaign priority sliders
 * - CampaignMetricsPanel: Campaign stats display with metric cards
 * - CampaignTabs: Tab navigation for campaign detail page
 * - SequenceBuilder: Visual sequence editor with timeline view
 * - CampaignList: Full campaigns page with search, filters, and allocation
 * - CampaignDetail: Campaign detail page with metrics, tabs, and settings
 * - CampaignNew: New campaign creation form
 *
 * Design Philosophy (from CAMPAIGNS.md):
 * - Priority sliders, not lead counts (clients think in effort distribution)
 * - Auto-balance to 100% (adjusting one campaign proportionally adjusts others)
 * - Min 10%, Max 80% (prevent campaigns from being starved or monopolized)
 * - AI Suggested badge (mark AI-generated campaigns distinctly)
 * - Outcome focus (show meetings booked and reply rates, not lead counts)
 *
 * Usage:
 * ```tsx
 * import {
 *   PrioritySlider,
 *   CampaignAllocationManager,
 *   CampaignMetricsPanel,
 *   CampaignTabs,
 *   SequenceBuilder,
 *   CampaignList,
 *   CampaignDetail,
 *   CampaignNew,
 * } from './campaigns';
 *
 * // Full page components (use DashboardShell internally)
 * <CampaignList />
 * <CampaignDetail />
 * <CampaignNew />
 *
 * // Individual components for composition
 * <PrioritySlider value={40} onChange={handleChange} />
 * <CampaignMetricsPanel meetings={12} showRate={85} replyRate={3.8} activeSequences={5} />
 * <CampaignTabs activeTab="overview" onTabChange={handleTabChange} />
 * <SequenceBuilder sequences={sequences} />
 * ```
 */

// Standalone components
export { PrioritySlider } from "./PrioritySlider";
export type { PrioritySliderProps } from "./PrioritySlider";

export { CampaignAllocationManager } from "./CampaignAllocationManager";
export type {
  CampaignAllocationManagerProps,
  CampaignWithPriority,
} from "./CampaignAllocationManager";

export { CampaignMetricsPanel } from "./CampaignMetricsPanel";
export type { CampaignMetricsPanelProps } from "./CampaignMetricsPanel";

export { CampaignTabs } from "./CampaignTabs";
export type { CampaignTabsProps, CampaignTab } from "./CampaignTabs";

export { SequenceBuilder } from "./SequenceBuilder";
export type { SequenceBuilderProps, SequenceStep } from "./SequenceBuilder";

// Page components
export { CampaignList } from "./CampaignList";
export { CampaignDetail } from "./CampaignDetail";
export { CampaignNew } from "./CampaignNew";
