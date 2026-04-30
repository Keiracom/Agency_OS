/**
 * Dashboard Components Index
 * Phase: Operation Modular Cockpit
 * 
 * Exports all dashboard components for easy importing.
 */

// Navigation & Layout
export { 
  Header, 
  type HeaderProps, 
  type Notification as HeaderNotification, 
  type UserMenuAction 
} from "./Header";
export {
  UserDropdown,
  type UserDropdownProps,
  type UserData,
} from "./UserDropdown";
export {
  NotificationsPanel,
  useNotifications,
  mockNotifications,
  type Notification,
  type NotificationType,
  type NotificationsPanelProps,
} from "./NotificationsPanel";
export {
  GlobalSearch,
  useGlobalSearch,
  type GlobalSearchProps,
  type SearchResult,
  type SearchCategory,
} from "./GlobalSearch";

// Stats & Metrics

// Campaigns
export {
  CampaignCards,
  CampaignCard,
  CampaignComparison,
  OverviewStats,
  MOCK_CAMPAIGNS,
  MOCK_OVERVIEW_STATS,
  type Campaign,
  type CampaignStatus,
  type CampaignChannel,
  type CampaignMetrics,
} from "./CampaignCards";

export {
  CampaignDetail,
  type Campaign as CampaignDetailData,
  type SequenceStep,
  type ChannelStats,
  type ABTest,
  type FunnelStep,
  type Lead as CampaignLead,
  type ActivityItem,
} from "./CampaignDetail";

export {
  CampaignWizard,
  type WizardState,
  type ICPOption,
  type FilterGroup,
  type CampaignGoal,
  type ToneType,
  type MessageGeneration,
  type LaunchSchedule,
} from "./CampaignWizard";

// Activity

// Leads
export { LeadTable } from "./LeadTable";
export { TierBadge } from "./TierBadge";
export { LeadDetailModal } from "./LeadDetailModal";

// Scheduling
export {
  MeetingScheduler,
  type MeetingSchedulerProps,
  type ScheduledMeeting,
  type MeetingType,
  type MeetingDuration,
  type LeadInfo,
  type TimeSlot,
} from "./MeetingScheduler";

// Shared UI
export { ChannelIcon } from "./ChannelIcon";

// Modals & Overlays
export { NewCampaignModal } from "./NewCampaignModal";
export { ProcessingOverlay } from "./ProcessingOverlay";

// Maya Assistant
export {
  MayaCompanion,
  type MayaStep,
  type MayaMessage,
  type ContextualSuggestion,
  type PageContext,
  type MayaCompanionProps,
} from "./MayaCompanion";

// Quick Actions
export {
  QuickActions,
  type QuickAction,
  type QuickActionsProps,
} from "./QuickActions";

// Settings

// Channel Integrations
export { ChannelIntegrations, type ChannelIntegrationsProps } from "./ChannelIntegrations";

// Billing
export { default as BillingPage } from "./BillingPage";

// Reports & Analytics

// Replies & Inbox
export { RepliesInbox } from "./RepliesInbox";
export { ReplyDetail } from "./ReplyDetail";
export type {
  InboxConversation,
  ConversationMessage,
  AISuggestion,
  IntentType,
  SentimentType,
} from "./RepliesInbox";
export type { ConversationDetail } from "./ReplyDetail";

// Existing components (from previous implementation)
export { BestOfShowcase } from "./BestOfShowcase";
export { CapacityGauge } from "./CapacityGauge";
export { CoPilotView } from "./CoPilotView";
export { EmergencyPauseButton } from "./EmergencyPauseButton";
export { OnTrackIndicator } from "./OnTrackIndicator";

// Re-export hook types for convenience
export type {
  ActivityFeedItem,
  ActivityType,
} from "@/hooks/use-activity-feed";

export type {
  DashboardStatsData,
} from "@/hooks/use-dashboard-stats";
