// Mock data for Campaigns page
// Source: frontend/design/html-prototypes/dashboard-campaigns.html

export type ChannelType = 'email' | 'linkedin' | 'voice' | 'sms';
export type CampaignStatus = 'active' | 'paused' | 'draft' | 'complete';
export type SequenceStepStatus = 'completed' | 'active' | 'upcoming';

export interface MetricData {
  value: number | string;
  label: string;
  change: number;
  isPercentage?: boolean;
}

export interface SequenceStep {
  day: number;
  channel: ChannelType;
  label: string;
  status: SequenceStepStatus;
  stats: string;
}

export interface Campaign {
  id: string;
  name: string;
  isAI: boolean;
  channels: ChannelType[];
  status: CampaignStatus;
  priority: number;
  metrics: MetricData[];
  sequence: SequenceStep[];
  aiInsight?: string;
}

export interface BestContent {
  channel: ChannelType;
  text: string;
  result: string;
}

export interface Recommendation {
  id: string;
  text: string;
}

// Channel emoji mapping
export const channelEmoji: Record<ChannelType, string> = {
  email: '📧',
  linkedin: '💼',
  voice: '📞',
  sms: '💬',
};

// Status badge styles
export const statusStyles: Record<CampaignStatus, { bg: string; text: string; dot: string }> = {
  active: { bg: 'bg-emerald-50', text: 'text-emerald-600', dot: '●' },
  paused: { bg: 'bg-amber-50', text: 'text-amber-600', dot: '◐' },
  draft: { bg: 'bg-slate-100', text: 'text-slate-600', dot: '○' },
  complete: { bg: 'bg-blue-50', text: 'text-blue-600', dot: '✓' },
};

// Mock campaign data (from HTML prototype)
export const mockCampaigns: Campaign[] = [
  {
    id: 'camp-1',
    name: 'Tech Decision Makers',
    isAI: true,
    channels: ['email', 'linkedin', 'voice'],
    status: 'active',
    priority: 40,
    metrics: [
      { value: 6, label: 'Meetings', change: 2 },
      { value: '3.8%', label: 'Reply Rate', change: 0.5, isPercentage: true },
      { value: '61%', label: 'Open Rate', change: -3, isPercentage: true },
      { value: '85%', label: 'Show Rate', change: 5, isPercentage: true },
      { value: 72, label: 'Avg ALS', change: 4 },
    ],
    sequence: [
      { day: 0, channel: 'email', label: 'Email', status: 'completed', stats: '312 sent │ 61% open' },
      { day: 3, channel: 'voice', label: 'Voice', status: 'completed', stats: '198 calls │ 34% connect' },
      { day: 5, channel: 'linkedin', label: 'LinkedIn', status: 'active', stats: '89 sent │ 42% accept' },
      { day: 8, channel: 'email', label: 'Follow-up', status: 'upcoming', stats: 'Upcoming' },
      { day: 12, channel: 'sms', label: 'SMS', status: 'upcoming', stats: 'Hot leads only' },
    ],
    aiInsight: 'Voice calls on Tuesday 10am AEST are booking 2.3x more meetings than other times.',
  },
  {
    id: 'camp-2',
    name: 'SaaS Founders Outreach',
    isAI: true,
    channels: ['email', 'linkedin'],
    status: 'active',
    priority: 60,
    metrics: [
      { value: 4, label: 'Meetings', change: 1 },
      { value: '4.2%', label: 'Reply Rate', change: 0.8, isPercentage: true },
      { value: '58%', label: 'Open Rate', change: 2, isPercentage: true },
      { value: '90%', label: 'Show Rate', change: 0, isPercentage: true },
      { value: 68, label: 'Avg ALS', change: 2 },
    ],
    sequence: [
      { day: 0, channel: 'email', label: 'Email', status: 'completed', stats: '245 sent │ 58% open' },
      { day: 4, channel: 'linkedin', label: 'LinkedIn', status: 'active', stats: '156 sent │ 38% accept' },
      { day: 7, channel: 'email', label: 'Follow-up', status: 'upcoming', stats: 'Upcoming' },
    ],
    aiInsight: 'Founders respond 40% more to case study mentions.',
  },
  {
    id: 'camp-3',
    name: 'Enterprise IT Directors',
    isAI: false,
    channels: ['email', 'voice', 'sms'],
    status: 'paused',
    priority: 25,
    metrics: [
      { value: 2, label: 'Meetings', change: 0 },
      { value: '2.1%', label: 'Reply Rate', change: -0.3, isPercentage: true },
      { value: '45%', label: 'Open Rate', change: -5, isPercentage: true },
      { value: '75%', label: 'Show Rate', change: -10, isPercentage: true },
      { value: 55, label: 'Avg ALS', change: -3 },
    ],
    sequence: [
      { day: 0, channel: 'email', label: 'Email', status: 'completed', stats: '180 sent │ 45% open' },
      { day: 5, channel: 'voice', label: 'Voice', status: 'completed', stats: '67 calls │ 22% connect' },
      { day: 10, channel: 'sms', label: 'SMS', status: 'upcoming', stats: 'Paused' },
    ],
  },
];

export const mockBestContent: BestContent[] = [
  { channel: 'email', text: '"Question about TechCorp\'s growth" → Sarah Chen', result: 'Replied, booked meeting' },
  { channel: 'email', text: '"Saw your Series B announcement" → Multiple', result: '5x opened, clicked CTA' },
  { channel: 'voice', text: 'Tuesday 10am calls', result: '2.3x connect rate' },
  { channel: 'linkedin', text: 'Mutual connection notes', result: '+67% acceptance' },
];

export const mockRecommendations: Recommendation[] = [
  { id: 'rec-1', text: 'CTOs convert 2.1x better than VPs in this campaign. Consider narrowing ICP.' },
  { id: 'rec-2', text: 'Short emails under 100 words get +28% more replies. Your avg is 145 words.' },
  { id: 'rec-3', text: 'Avoid Friday afternoons — reply rate drops 40%. Shift sends to Tue-Thu AM.' },
];
