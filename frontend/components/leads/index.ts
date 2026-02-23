/**
 * FILE: frontend/components/leads/index.ts
 * PURPOSE: Export all lead components
 * SPRINT: Dashboard Sprint 2 - Step 6/8 Animated Lead Scoreboard
 */

export { SplitFlapCounterBar, type SplitFlapCounterBarProps } from "./SplitFlapCounter";
export { 
  LeadScoreboardRow, 
  getALSTier, 
  getALSColour, 
  type LeadScoreboardRowProps, 
  type ALSTier 
} from "./LeadScoreboardRow";
export { 
  CommunicationTimeline, 
  TimelineEmptyState,
  type CommunicationTimelineProps,
  type TimelineEvent,
  type TimelineEventType
} from "./CommunicationTimeline";
