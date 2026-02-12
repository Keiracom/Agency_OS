/**
 * Mock data for Analytics Terminal - Reports Page
 * Sprint 3c - Bloomberg Terminal aesthetic
 * Australian context with AUD currency
 */

// ============================================
// Types
// ============================================

export type DateRange = 'thisMonth' | 'lastMonth' | 'quarter' | 'custom';
export type ChannelType = 'email' | 'linkedin' | 'sms' | 'voice' | 'mail';
export type TierType = 'hot' | 'warm' | 'cool' | 'cold';

export interface HeroMetric {
  id: string;
  label: string;
  value: number;
  suffix?: string;
  prefix?: string;
  change: number;
  changeLabel: string;
  accentColor: string;
}

export interface ChannelData {
  channel: ChannelType;
  name: string;
  volume: number;
  volumeLabel: string;
  replyRate: number;
  meetings: number;
}

export interface MonthlyData {
  month: string;
  value: number;
}

export interface FunnelStage {
  stage: string;
  label: string;
  count: number;
  description: string;
  percentage: number;
}

export interface LeadSourceData {
  id: string;
  name: string;
  count: number;
  percentage: number;
}

export interface TierData {
  tier: TierType;
  count: number;
  conversionRate: number;
}

export interface ObjectionData {
  objection: string;
  count: number;
  recoveryRate: number;
}

// ============================================
// Hero Metrics (AUD)
// ============================================

export const heroMetrics: HeroMetric[] = [
  {
    id: 'meetings',
    label: 'Meetings Booked',
    value: 52,
    change: 23,
    changeLabel: 'vs last period',
    accentColor: 'amber',
  },
  {
    id: 'pipeline',
    label: 'Pipeline Generated',
    value: 221,
    suffix: 'K',
    prefix: '$',
    change: 31,
    changeLabel: 'vs last period',
    accentColor: 'teal',
  },
  {
    id: 'showRate',
    label: 'Show Rate',
    value: 68,
    suffix: '%',
    change: 5,
    changeLabel: 'above benchmark',
    accentColor: 'blue',
  },
  {
    id: 'roi',
    label: 'Return on Investment',
    value: 8.2,
    suffix: 'x',
    change: 1.4,
    changeLabel: 'vs last quarter',
    accentColor: 'green',
  },
];

// ============================================
// Channel Performance Data
// ============================================

export const channelData: ChannelData[] = [
  { channel: 'email', name: 'Email', volume: 3420, volumeLabel: 'Sent', replyRate: 4.6, meetings: 18 },
  { channel: 'linkedin', name: 'LinkedIn', volume: 890, volumeLabel: 'Requests', replyRate: 7.5, meetings: 12 },
  { channel: 'sms', name: 'SMS', volume: 520, volumeLabel: 'Sent', replyRate: 27.3, meetings: 8 },
  { channel: 'voice', name: 'Voice AI', volume: 180, volumeLabel: 'Calls', replyRate: 23.3, meetings: 11 },
  { channel: 'mail', name: 'Direct Mail', volume: 45, volumeLabel: 'Sent', replyRate: 6.7, meetings: 3 },
];

// ============================================
// Meetings Over Time
// ============================================

export const meetingsData: MonthlyData[] = [
  { month: 'Sep', value: 6 },
  { month: 'Oct', value: 8 },
  { month: 'Nov', value: 7 },
  { month: 'Dec', value: 10 },
  { month: 'Jan', value: 9 },
  { month: 'Feb', value: 12 },
];

// ============================================
// Conversion Funnel
// ============================================

export const funnelData: FunnelStage[] = [
  { stage: 'contacted', label: 'Contacted', count: 5055, description: 'Total Touches', percentage: 100 },
  { stage: 'engaged', label: 'Engaged', count: 2123, description: 'Opens/Views', percentage: 42 },
  { stage: 'replied', label: 'Replied', count: 404, description: 'Positive', percentage: 8 },
  { stage: 'booked', label: 'Booked', count: 52, description: 'Meetings', percentage: 1 },
];

// ============================================
// Response Rates
// ============================================

export const responseRates = [
  { label: 'Overall', value: 8.5, color: 'amber' },
  { label: 'SMS', value: 27, color: 'teal' },
  { label: 'Voice', value: 23, color: 'green' },
];

// ============================================
// What's Working Insights
// ============================================

export const whoConverts = [
  { label: 'CEO/Founder', value: '2.3x ↑' },
  { label: 'Marketing Dir', value: '1.8x ↑' },
];

export const bestTiming = [
  { label: 'Day', value: 'Tuesday' },
  { label: 'Hour', value: '10am AEST' },
];

export const discoveryInsight = {
  label: 'This Week',
  text: 'Leads with "Growth" in title convert 2.1x better. Auto-adjusting targeting.',
};

// ============================================
// Lead Sources
// ============================================

export const leadSources: LeadSourceData[] = [
  { id: 'data-partner', name: 'Data Partner', count: 847, percentage: 65 },
  { id: 'linkedin', name: 'LinkedIn', count: 286, percentage: 22 },
  { id: 'referral', name: 'Referral', count: 104, percentage: 8 },
  { id: 'website', name: 'Website', count: 65, percentage: 5 },
];

// ============================================
// Tier Conversion Data
// ============================================

export const tierData: TierData[] = [
  { tier: 'hot', count: 312, conversionRate: 8.7 },
  { tier: 'warm', count: 589, conversionRate: 3.2 },
  { tier: 'cool', count: 234, conversionRate: 1.1 },
  { tier: 'cold', count: 167, conversionRate: 0.4 },
];

// ============================================
// Voice Performance Data
// ============================================

export const voiceStats = {
  totalCalls: 180,
  avgDuration: '2:34',
  connectRate: 68,
  bookingRate: 23.3,
};

export const objectionData: ObjectionData[] = [
  { objection: '"Not interested"', count: 45, recoveryRate: 12 },
  { objection: '"Send info first"', count: 38, recoveryRate: 31 },
  { objection: '"Too busy"', count: 29, recoveryRate: 24 },
  { objection: '"Already have solution"', count: 22, recoveryRate: 9 },
];

// ============================================
// ROI Summary (AUD)
// ============================================

export const roiSummary = {
  spend: 27000,
  pipeline: 221000,
  roi: 8.2,
};

// ============================================
// Date Range Options
// ============================================

export const dateRangeOptions = [
  { value: 'thisMonth', label: 'This Month' },
  { value: 'lastMonth', label: 'Last Month' },
  { value: 'quarter', label: 'Quarter' },
  { value: 'custom', label: 'Custom' },
];
