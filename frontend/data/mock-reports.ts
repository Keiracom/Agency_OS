/**
 * Mock data for Reports page
 * Sprint 4 - Analytics Terminal
 * Will be replaced with real API calls
 */

// ============================================
// Types
// ============================================

export type DateRange = 'thisMonth' | 'lastMonth' | 'quarter' | 'custom';
export type ChannelType = 'email' | 'linkedin' | 'sms' | 'voice' | 'mail';
export type FunnelStage = 'contacted' | 'engaged' | 'replied' | 'booked';
export type TierType = 'hot' | 'warm' | 'cool' | 'cold';

export interface ExecMetric {
  id: string;
  label: string;
  value: number;
  suffix?: string;
  prefix?: string;
  change: number;
  changeLabel: string;
  color: 'purple' | 'teal' | 'blue' | 'success';
}

export interface ChannelPerformance {
  channel: ChannelType;
  name: string;
  sent: number;
  sentLabel: string;
  replyRate: number;
  meetings: number;
}

export interface MonthlyMeetings {
  month: string;
  value: number;
}

export interface FunnelStageData {
  stage: FunnelStage;
  label: string;
  count: number;
  description: string;
  percentage: number;
}

export interface LeadSource {
  id: string;
  name: string;
  icon: 'data-partner' | 'linkedin' | 'referral' | 'website';
  count: number;
  percentage: number;
  color: 'purple' | 'blue' | 'teal' | 'amber';
}

export interface TierBreakdown {
  tier: TierType;
  count: number;
  conversionRate: number;
}

export interface ResponseRate {
  label: string;
  value: number;
  color: 'purple' | 'teal' | 'success';
}

export interface InsightItem {
  label: string;
  value: string;
}

export interface InsightBox {
  title: string;
  items: InsightItem[];
}

// ============================================
// Executive Summary Metrics
// ============================================

export const execMetrics: ExecMetric[] = [
  {
    id: 'meetings',
    label: 'Meetings Booked',
    value: 52,
    change: 23,
    changeLabel: 'vs last period',
    color: 'purple',
  },
  {
    id: 'pipeline',
    label: 'Pipeline Generated',
    value: 221,
    suffix: 'K',
    prefix: '$',
    change: 31,
    changeLabel: 'vs last period',
    color: 'teal',
  },
  {
    id: 'showRate',
    label: 'Show Rate',
    value: 68,
    suffix: '%',
    change: 5,
    changeLabel: 'above benchmark',
    color: 'blue',
  },
  {
    id: 'roi',
    label: 'Return on Investment',
    value: 8.2,
    suffix: 'x',
    change: 1.4,
    changeLabel: 'vs last quarter',
    color: 'success',
  },
];

// ============================================
// Channel Performance Data
// ============================================

export const channelPerformance: ChannelPerformance[] = [
  {
    channel: 'email',
    name: 'Email',
    sent: 3420,
    sentLabel: 'Sent',
    replyRate: 4.6,
    meetings: 18,
  },
  {
    channel: 'linkedin',
    name: 'LinkedIn',
    sent: 890,
    sentLabel: 'Requests',
    replyRate: 7.5,
    meetings: 12,
  },
  {
    channel: 'sms',
    name: 'SMS',
    sent: 520,
    sentLabel: 'Sent',
    replyRate: 27.3,
    meetings: 8,
  },
  {
    channel: 'voice',
    name: 'Voice AI',
    sent: 180,
    sentLabel: 'Calls',
    replyRate: 23.3,
    meetings: 11,
  },
  {
    channel: 'mail',
    name: 'Direct Mail',
    sent: 45,
    sentLabel: 'Sent',
    replyRate: 6.7,
    meetings: 3,
  },
];

// ============================================
// Monthly Meetings Data
// ============================================

export const monthlyMeetings: MonthlyMeetings[] = [
  { month: 'Sep', value: 6 },
  { month: 'Oct', value: 8 },
  { month: 'Nov', value: 7 },
  { month: 'Dec', value: 10 },
  { month: 'Jan', value: 9 },
  { month: 'Feb', value: 12 },
];

// ============================================
// Conversion Funnel Data
// ============================================

export const funnelStages: FunnelStageData[] = [
  {
    stage: 'contacted',
    label: 'Contacted',
    count: 5055,
    description: 'Total Touches',
    percentage: 100,
  },
  {
    stage: 'engaged',
    label: 'Engaged',
    count: 2123,
    description: 'Opens/Views',
    percentage: 42,
  },
  {
    stage: 'replied',
    label: 'Replied',
    count: 404,
    description: 'Positive',
    percentage: 8,
  },
  {
    stage: 'booked',
    label: 'Booked',
    count: 52,
    description: 'Meetings',
    percentage: 1,
  },
];

// ============================================
// Lead Sources Data
// ============================================

export const leadSources: LeadSource[] = [
  {
    id: 'data-partner',
    name: 'Data Partner',
    icon: 'data-partner',
    count: 847,
    percentage: 65,
    color: 'purple',
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    icon: 'linkedin',
    count: 286,
    percentage: 22,
    color: 'blue',
  },
  {
    id: 'referral',
    name: 'Referral',
    icon: 'referral',
    count: 104,
    percentage: 8,
    color: 'teal',
  },
  {
    id: 'website',
    name: 'Website',
    icon: 'website',
    count: 65,
    percentage: 5,
    color: 'amber',
  },
];

// ============================================
// Tier Breakdown Data
// ============================================

export const tierBreakdown: TierBreakdown[] = [
  { tier: 'hot', count: 312, conversionRate: 8.7 },
  { tier: 'warm', count: 589, conversionRate: 3.2 },
  { tier: 'cool', count: 234, conversionRate: 1.1 },
  { tier: 'cold', count: 167, conversionRate: 0.4 },
];

// ============================================
// Response Rates Data
// ============================================

export const responseRates: ResponseRate[] = [
  { label: 'Overall', value: 8.5, color: 'purple' },
  { label: 'SMS', value: 27, color: 'teal' },
  { label: 'Voice', value: 23, color: 'success' },
];

// ============================================
// Insights Data
// ============================================

export const insightBoxes: InsightBox[] = [
  {
    title: 'Who Converts',
    items: [
      { label: 'CEO/Founder', value: '2.3x ↑' },
      { label: 'Marketing Dir', value: '1.8x ↑' },
    ],
  },
  {
    title: 'Best Timing',
    items: [
      { label: 'Day', value: 'Tuesday' },
      { label: 'Hour', value: '10am' },
    ],
  },
];

export const discoveryInsight = {
  label: 'This Week',
  text: 'Leads with "Growth" in title convert 2.1x better. Auto-adjusting targeting.',
};

// ============================================
// Date Range Options
// ============================================

export const dateRangeOptions: { value: DateRange; label: string }[] = [
  { value: 'thisMonth', label: 'This Month' },
  { value: 'lastMonth', label: 'Last Month' },
  { value: 'quarter', label: 'Quarter' },
  { value: 'custom', label: 'Custom' },
];
