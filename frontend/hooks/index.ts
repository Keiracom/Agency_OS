/**
 * Hooks Index
 * Phase: Operation Modular Cockpit
 */

// Client & Auth
export { useClient } from "./use-client";

// Campaigns
export { useCampaigns, useCampaign, useCreateCampaign, useUpdateCampaign } from "./use-campaigns";

// Leads
export { useLeads, useLead, useCreateLead, useUpdateLead } from "./use-leads";

// Activity & Dashboard
export { useActivityFeed, useLiveActivityFeed } from "./use-activity-feed";
export { useDashboardStats, useOnTrackStatus } from "./use-dashboard-stats";

// Replies
export { useReplies, useReply, useMarkReplyHandled } from "./use-replies";

// Reports
export { 
  useDashboardStats as useReportsDashboardStats, 
  useActivityFeed as useReportsActivityFeed,
  useCampaignPerformance 
} from "./use-reports";

// LinkedIn
export { useLinkedInStatus, useLinkedInConnect, useLinkedInVerify2FA, useLinkedInDisconnect } from "./use-linkedin";

// Meetings
export { useMeetings, useUpcomingMeetings } from "./use-meetings";

// Utilities
export { useOutsideClick } from "./use-outside-click";
export { useScrollAnimation } from "./use-scroll-animation";
export { useToast } from "./use-toast";
