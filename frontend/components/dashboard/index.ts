/**
 * Dashboard Components Index
 * Phase: Operation Modular Cockpit
 * 
 * Exports all dashboard components for easy importing.
 */

// Navigation
export { Sidebar, type PageKey } from "./Sidebar";

// Stats & Metrics
export { StatsGrid, StatCard } from "./StatsGrid";

// Activity
export { ActivityTicker } from "./ActivityTicker";
export { LiveActivityFeed } from "./LiveActivityFeed";

// Leads
export { LeadTable } from "./LeadTable";
export { TierBadge } from "./TierBadge";

// Shared UI
export { ChannelIcon } from "./ChannelIcon";

// Modals & Overlays
export { NewCampaignModal } from "./NewCampaignModal";
export { ProcessingOverlay } from "./ProcessingOverlay";

// Maya Assistant
export { MayaCompanion } from "./MayaCompanion";

// Existing components (from previous implementation)
export { BestOfShowcase } from "./BestOfShowcase";
export { CapacityGauge } from "./CapacityGauge";
export { CoPilotView } from "./CoPilotView";
export { EmergencyPauseButton } from "./EmergencyPauseButton";
export { HeroMetricsCard } from "./HeroMetricsCard";
export { OnTrackIndicator } from "./OnTrackIndicator";

// Re-export hook types for convenience
export type {
  ActivityFeedItem,
  ActivityType,
} from "@/hooks/use-activity-feed";

export type {
  DashboardStatsData,
} from "@/hooks/use-dashboard-stats";
