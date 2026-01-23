/**
 * Lead Components - Lead management UI components for Agency OS dashboard
 *
 * These components provide the lead list and detail views:
 * - ALSTierBadge: Color-coded tier badge (Hot/Warm/Cool/Cold/Dead)
 * - ALSScorecard: Score breakdown with progress bars
 * - LeadTimeline: Activity timeline with expandable content
 * - LeadEnrichment: Enrichment data card with signals
 * - LeadQuickActions: Quick action buttons
 * - LeadStatusProgress: Status funnel progress indicator
 * - LeadBulkActions: Floating bulk action bar
 * - LeadList: Full leads list page
 * - LeadDetail: Full lead detail page
 *
 * Usage:
 * ```tsx
 * import {
 *   LeadList,
 *   LeadDetail,
 *   ALSTierBadge,
 *   ALSScorecard
 * } from './leads';
 *
 * // Full leads list page
 * <LeadList onLeadClick={(id) => navigate(`/leads/${id}`)} />
 *
 * // Lead detail page
 * <LeadDetail leadId="1" onBack={() => navigate('/leads')} />
 *
 * // Individual components
 * <ALSTierBadge tier="hot" showLabel />
 * <ALSScorecard score={87} breakdown={breakdown} />
 * ```
 */

// Badge component
// Note: ALSTier type is not exported separately to avoid conflict with replies module
// Use ALSTierBadgeProps['tier'] or import directly from './ALSTierBadge' if needed
export { ALSTierBadge } from "./ALSTierBadge";
export type { ALSTierBadgeProps } from "./ALSTierBadge";

// Scorecard component
export { ALSScorecard } from "./ALSScorecard";
export type { ALSScorecardProps, ALSBreakdown } from "./ALSScorecard";

// Timeline component
export { LeadTimeline } from "./LeadTimeline";
export type {
  LeadTimelineProps,
  ActivityItem,
  Channel,
} from "./LeadTimeline";

// Enrichment component
export { LeadEnrichment } from "./LeadEnrichment";
export type { LeadEnrichmentProps, Signal } from "./LeadEnrichment";

// Quick actions component
export { LeadQuickActions } from "./LeadQuickActions";
export type { LeadQuickActionsProps } from "./LeadQuickActions";

// Status progress component
export { LeadStatusProgress } from "./LeadStatusProgress";
export type { LeadStatusProgressProps, LeadStatus } from "./LeadStatusProgress";

// Bulk actions component
export { LeadBulkActions } from "./LeadBulkActions";
export type { LeadBulkActionsProps } from "./LeadBulkActions";

// Page components
export { LeadList } from "./LeadList";
export type { LeadListProps } from "./LeadList";

export { LeadDetail } from "./LeadDetail";
export type { LeadDetailProps } from "./LeadDetail";
