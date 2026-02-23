/**
 * FILE: frontend/components/dashboard-v4/types.ts
 * PURPOSE: TypeScript types for Dashboard V4 components
 * PHASE: Dashboard V4 Implementation
 */

export interface HotProspect {
  id: string;
  initials: string;
  name: string;
  company: string;
  title: string;
  signal: string;
  score: number;
  isVeryHot: boolean;
}

export interface UpcomingMeeting {
  id: string;
  date: Date;
  dayLabel: string;
  dayNumber: number;
  time: string;
  name: string;
  company: string;
  type: string;
  duration: string;
  potentialValue: number;
}

export interface WarmReply {
  id: string;
  initials: string;
  name: string;
  company: string;
  preview: string;
  leadId: string;
}

export interface QuickStat {
  value: string;
  label: string;
  change: string;
  changeDirection: "up" | "down" | "neutral";
}

export interface InsightData {
  icon: string;
  headline: string;
  detail: string;
  highlightText?: string;
}

export interface DashboardV4Data {
  hotProspects: HotProspect[];
  upcomingMeetings: UpcomingMeeting[];
  warmReplies: WarmReply[];
  quickStats: QuickStat[];
  insight: InsightData;
  meetingsThisMonth: number;
  meetingsTarget: number;
}
