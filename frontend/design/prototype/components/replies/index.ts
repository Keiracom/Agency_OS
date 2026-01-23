/**
 * Replies Components - Reply inbox and management components
 *
 * These components provide the reply inbox functionality for Agency OS:
 * - ReplyCard: Individual reply item in the list
 * - ReplyDetail: Full reply view with thread history and actions
 * - ReplyFilters: Channel, intent, date, and search filters
 * - ReplyInbox: Full page component with split view
 *
 * Usage:
 * ```tsx
 * import { ReplyInbox, ReplyCard, ReplyDetail, ReplyFilters } from './replies';
 *
 * // Full inbox page
 * <ReplyInbox onNavigate={handleNav} />
 *
 * // Or use individual components
 * <ReplyCard
 *   id="1"
 *   leadName="Sarah Chen"
 *   leadCompany="TechFlow"
 *   channel="email"
 *   subject="Re: Partnership"
 *   preview="Thanks for reaching out..."
 *   timestamp="2 hours ago"
 *   intent="positive"
 *   tierBadge="hot"
 *   isUnread={true}
 *   onClick={() => handleSelect("1")}
 * />
 * ```
 */

// ReplyCard - Individual reply list item
export { ReplyCard } from "./ReplyCard";
export type { ReplyCardProps, ReplyChannel, ReplyIntent, ALSTier } from "./ReplyCard";

// ReplyDetail - Full reply view panel
export { ReplyDetail } from "./ReplyDetail";
export type { ReplyDetailProps, Reply, ThreadMessage } from "./ReplyDetail";

// ReplyFilters - Filter controls
export { ReplyFilters } from "./ReplyFilters";
export type { ReplyFiltersProps } from "./ReplyFilters";

// ReplyInbox - Full page component
export { ReplyInbox } from "./ReplyInbox";
export type { ReplyInboxProps } from "./ReplyInbox";
