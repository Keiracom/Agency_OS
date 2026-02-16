/**
 * FILE: frontend/lib/mock/inbox-data.ts
 * PURPOSE: Mock data for Inbox Command Center and Reply Detail pages
 * SPRINT: Dashboard Sprint 3b - Inbox Command Center
 * CEO Directive #027 — Design System Overhaul: No emojis
 */

export type IntentType = 'meeting' | 'interested' | 'question' | 'objection' | 'later';
export type SentimentType = 'positive' | 'negative' | 'neutral';
export type ChannelType = 'email' | 'linkedin' | 'sms' | 'voice';
export type TierType = 'hot' | 'warm' | 'cool';

export interface InboxMessage {
  id: string;
  name: string;
  initials: string;
  company: string;
  title: string;
  email: string;
  phone?: string;
  score: number;
  tier: TierType;
  channel: ChannelType;
  intent: IntentType;
  sentiment: SentimentType;
  preview: string;
  unread: boolean;
  timestamp: string;
  campaignName: string;
}

export interface ThreadMessage {
  id: string;
  sender: 'you' | 'them';
  senderName: string;
  senderEmail: string;
  channel: ChannelType;
  subject?: string;
  body: string;
  timestamp: string;
  date: string;
  sentiment?: SentimentType;
  intent?: IntentType;
}

export interface AISuggestion {
  id: string;
  label: string;
  icon: string;
  text: string;
}

export interface ActivityItem {
  id: string;
  channel: ChannelType;
  text: string;
  timestamp: string;
}

export interface Note {
  id: string;
  text: string;
  timestamp: string;
}

export interface ScoreFactor {
  icon: string;
  label: string;
  value: number;
}

export const mockInboxMessages: InboxMessage[] = [
  {
    id: 'david-park',
    name: 'David Park',
    initials: 'DP',
    company: 'Momentum Media',
    title: 'CEO',
    email: 'david@momentummedia.com.au',
    phone: '+61 412 345 678',
    score: 92,
    tier: 'hot',
    channel: 'email',
    intent: 'meeting',
    sentiment: 'positive',
    preview: "Yes, I'd be interested in learning more. Can we schedule a call next week? We're currently doing about $40K MRR...",
    unread: true,
    timestamp: '2h ago',
    campaignName: 'Multi-Channel Q1',
  },
  {
    id: 'anna-smith',
    name: 'Anna Smith',
    initials: 'AS',
    company: 'Digital First',
    title: 'Marketing Director',
    email: 'anna@digitalfirst.com.au',
    score: 78,
    tier: 'warm',
    channel: 'email',
    intent: 'interested',
    sentiment: 'positive',
    preview: 'This looks relevant. Send me more information about pricing and how this works for agencies our size.',
    unread: true,
    timestamp: '5h ago',
    campaignName: 'Agency Outreach Feb',
  },
  {
    id: 'mike-ross',
    name: 'Mike Ross',
    initials: 'MR',
    company: 'Velocity Growth',
    title: 'Head of Sales',
    email: 'mike@velocitygrowth.com',
    phone: '+61 421 987 654',
    score: 85,
    tier: 'hot',
    channel: 'sms',
    intent: 'meeting',
    sentiment: 'positive',
    preview: "Sure, how about Thursday? I've got 30 mins around 2pm if that works for you.",
    unread: true,
    timestamp: '6h ago',
    campaignName: 'Multi-Channel Q1',
  },
  {
    id: 'lisa-wong',
    name: 'Lisa Wong',
    initials: 'LW',
    company: 'Pixel Perfect',
    title: 'Founder',
    email: 'lisa@pixelperfect.com.au',
    score: 74,
    tier: 'warm',
    channel: 'linkedin',
    intent: 'question',
    sentiment: 'positive',
    preview: 'Thanks for reaching out! Your approach is interesting. How does the AI calling work exactly?',
    unread: true,
    timestamp: '1d ago',
    campaignName: 'LinkedIn Campaign',
  },
  {
    id: 'chris-lee',
    name: 'Chris Lee',
    initials: 'CL',
    company: 'Visionary Studios',
    title: 'Operations',
    email: 'chris@visionarystudios.com',
    score: 42,
    tier: 'cool',
    channel: 'email',
    intent: 'objection',
    sentiment: 'negative',
    preview: 'Not interested at this time. Please remove me from your list.',
    unread: false,
    timestamp: '1d ago',
    campaignName: 'Cold Email Q1',
  },
  {
    id: 'rachel-green',
    name: 'Rachel Green',
    initials: 'RG',
    company: 'Marketing Plus',
    title: 'Director',
    email: 'rachel@marketingplus.com.au',
    score: 56,
    tier: 'cool',
    channel: 'email',
    intent: 'later',
    sentiment: 'neutral',
    preview: "Thanks for reaching out. We're evaluating solutions for Q2. Can you follow up in March?",
    unread: false,
    timestamp: '2d ago',
    campaignName: 'Agency Outreach Feb',
  },
  {
    id: 'tom-brown',
    name: 'Tom Brown',
    initials: 'TB',
    company: 'Scale Agency',
    title: 'Founder',
    email: 'tom@scaleagency.com',
    phone: '+61 433 222 111',
    score: 68,
    tier: 'warm',
    channel: 'sms',
    intent: 'interested',
    sentiment: 'positive',
    preview: "Hey! Yeah we've been looking for something like this. What's the typical cost?",
    unread: true,
    timestamp: '3d ago',
    campaignName: 'SMS Blitz',
  },
];

export const mockDavidParkThread: ThreadMessage[] = [
  {
    id: 'msg-1',
    sender: 'you',
    senderName: 'You',
    senderEmail: 'dave@agencyos.com',
    channel: 'email',
    subject: 'Quick question about Momentum Media',
    body: `Hi David,

I noticed Momentum Media has been doing some impressive work in the agency space. I'm curious — are you currently looking to scale your client acquisition, or is that on the backburner for now?

We've helped agencies like yours book 10-15 qualified meetings per month without adding headcount. Happy to share how if you're interested.

Best,
Dave`,
    timestamp: '9:00 AM',
    date: 'January 29, 2026',
  },
  {
    id: 'msg-2',
    sender: 'them',
    senderName: 'David Park',
    senderEmail: 'david@momentummedia.com.au',
    channel: 'email',
    subject: 'Re: Quick question about Momentum Media',
    body: `Hi there,

Yes, I'd be interested in learning more. Can we schedule a call next week? I'm particularly interested in understanding how your multi-channel approach works and what kind of results you've seen for agencies similar to ours.

We're currently doing about $40K MRR and looking to scale to $100K by end of year. Would love to see if Agency OS could help accelerate that.

Best,
David`,
    timestamp: '10:42 AM',
    date: 'Today',
    sentiment: 'positive',
    intent: 'meeting',
  },
];

export const mockDavidParkSMS: ThreadMessage[] = [
  {
    id: 'sms-1',
    sender: 'you',
    senderName: 'You',
    senderEmail: '',
    channel: 'sms',
    body: "Hi David, it's Dave from Agency OS. Just saw your email — glad you're interested. Want to lock in that meeting?",
    timestamp: '11:15 AM',
    date: 'Today',
  },
  {
    id: 'sms-2',
    sender: 'them',
    senderName: 'David Park',
    senderEmail: '',
    channel: 'sms',
    body: 'Absolutely! What times work?',
    timestamp: '11:22 AM',
    date: 'Today',
    sentiment: 'positive',
  },
  {
    id: 'sms-3',
    sender: 'you',
    senderName: 'You',
    senderEmail: '',
    channel: 'sms',
    body: "How about Tuesday 2pm AEST? I'll send you a calendar invite with a Zoom link.",
    timestamp: '11:24 AM',
    date: 'Today',
  },
  {
    id: 'sms-4',
    sender: 'them',
    senderName: 'David Park',
    senderEmail: '',
    channel: 'sms',
    body: 'Perfect, that works!',
    timestamp: '11:30 AM',
    date: 'Today',
    sentiment: 'positive',
    intent: 'meeting',
  },
];

export const mockAISuggestions: AISuggestion[] = [
  {
    id: 'ai-1',
    label: 'Confirm Meeting',
    icon: 'sparkles',
    text: "Perfect, David! Just sent you a calendar invite for Tuesday 2pm AEST. Looking forward to learning more about your $40K → $100K goals and showing you how we can help accelerate that. See you then!",
  },
  {
    id: 'ai-2',
    label: 'Add Social Proof',
    icon: 'chart',
    text: "Great! Calendar invite coming your way. Quick note — we recently helped an agency at similar scale go from $35K to $87K MRR in 6 months. Will share their playbook on the call. Tuesday at 2pm AEST works!",
  },
  {
    id: 'ai-3',
    label: 'Pre-qualify',
    icon: 'target',
    text: "Awesome! Before I send the invite — to make our time super valuable, what's your biggest bottleneck right now: lead quality, follow-up consistency, or bandwidth to handle more meetings? That way I can tailor the demo.",
  },
];

export const mockDavidParkActivity: ActivityItem[] = [
  { id: 'act-1', channel: 'sms', text: 'Replied to SMS — confirmed Tuesday call', timestamp: 'Today, 11:30 AM' },
  { id: 'act-2', channel: 'email', text: 'Replied to email — meeting request', timestamp: 'Today, 10:42 AM' },
  { id: 'act-3', channel: 'email', text: 'Opened email (3rd time)', timestamp: 'Today, 10:38 AM' },
  { id: 'act-4', channel: 'linkedin', text: 'Viewed your LinkedIn profile', timestamp: 'Yesterday, 4:15 PM' },
  { id: 'act-5', channel: 'email', text: 'Initial email sent', timestamp: 'Jan 29, 9:00 AM' },
];

export const mockDavidParkNotes: Note[] = [
  {
    id: 'note-1',
    text: 'High-priority lead! CEO wants to 2.5x his MRR. Confirmed Tuesday 2pm AEST call via SMS. Prepare case study about similar agency scale-up.',
    timestamp: 'Today at 10:45 AM',
  },
  {
    id: 'note-2',
    text: 'Initial outreach sent. Momentum Media doing good work — featured in Top 50 Agencies. Worth pursuing.',
    timestamp: 'Jan 29 at 9:15 AM',
  },
];

// Lucide icon names for score factors
export const mockDavidParkScoreFactors: ScoreFactor[] = [
  { icon: 'Crown', label: 'CEO-Level Title', value: 25 },
  { icon: 'Calendar', label: 'Meeting Request', value: 20 },
  { icon: 'DollarSign', label: 'Budget Revealed ($40K MRR)', value: 15 },
  { icon: 'TrendingUp', label: 'Growth Intent', value: 12 },
  { icon: 'Mail', label: 'Email Opened (3x)', value: 10 },
  { icon: 'MessageSquare', label: 'SMS Engaged', value: 10 },
];

export const intentLabels: Record<IntentType, string> = {
  meeting: 'Meeting Request',
  interested: 'Interested',
  question: 'Question',
  objection: 'Objection',
  later: 'Not Now',
};

// Lucide icon names for sentiment
export const sentimentIcon: Record<SentimentType, string> = {
  positive: 'ThumbsUp',
  negative: 'ThumbsDown',
  neutral: 'Minus',
};

// DEPRECATED: Use sentimentIcon instead
export const sentimentEmoji: Record<SentimentType, string> = {
  positive: 'ThumbsUp',
  negative: 'ThumbsDown',
  neutral: 'Minus',
};

export const channelLabels: Record<ChannelType, string> = {
  email: 'Email',
  linkedin: 'LinkedIn',
  sms: 'SMS',
  voice: 'Voice',
};
