/**
 * Mock data for Dashboard (Command Center) v2
 * Will be replaced with real API calls
 */

// Hero Section - Meetings Booked
export const mockMeetingsHero = {
  current: 12,
  target: 10,
  goalText: 'Target exceeded — 3 days early',
  trendPercent: 25,
  trendLabel: 'vs last month',
};

// Hero Section - Channel Orchestration
export const mockChannelOrchestration = {
  totalTouches: 1800,
  channels: [
    { id: 'email', label: 'Email', value: 847, color: 'accent-primary' },
    { id: 'linkedin', label: 'LinkedIn', value: 423, color: 'accent-blue' },
    { id: 'sms', label: 'SMS', value: 127, color: 'accent-teal' },
    { id: 'voice', label: 'Calls', value: 47, color: 'status-warning' },
    { id: 'mail', label: 'Mail', value: 23, color: 'pink-500' },
  ],
};

// Stats Row
export const mockDashboardStats = {
  leadsThisMonth: 47,
  emailsSent: 1284,
  meetingsBooked: 12,
  responseRate: 18.5,
};

export const mockStatsGrid = [
  { id: 'show-rate', value: '68%', label: 'Show Rate', change: '↑ 5% vs avg', positive: true },
  { id: 'deals', value: '4', label: 'Deals Started', change: '↑ 2 this week', positive: true },
  { id: 'pipeline', value: '$47K', label: 'Pipeline Value', change: '↑ $12K added', positive: true },
  { id: 'roi', value: '8.2x', label: 'ROI', change: 'Lifetime', positive: null },
];

// Hot Prospects
export const mockHotProspects = [
  {
    id: '1',
    initials: 'SC',
    name: 'Sarah Chen',
    company: 'Bloom Digital',
    title: 'Marketing Director',
    score: 94,
    tier: 'hot' as const,
    badges: [
      { label: 'HOT', variant: 'hot' as const },
      { label: '5 opens today', variant: 'active' as const },
    ],
  },
  {
    id: '2',
    initials: 'MJ',
    name: 'Michael Jones',
    company: 'Growth Labs',
    title: 'CEO',
    score: 87,
    tier: 'hot' as const,
    badges: [
      { label: 'CEO', variant: 'ceo' as const },
      { label: 'Pricing page', variant: 'active' as const },
    ],
  },
  {
    id: '3',
    initials: 'LW',
    name: 'Lisa Wong',
    company: 'Pixel Perfect',
    title: 'Founder',
    score: 82,
    tier: 'warm' as const,
    badges: [
      { label: 'Founder', variant: 'ceo' as const },
    ],
  },
];

// Smart Calling (Voice AI)
export const mockVoiceStats = {
  calls: 47,
  connected: 31,
  booked: 8,
  rate: '26%',
};

export const mockRecentCalls = [
  {
    id: '1',
    name: 'Sarah Chen',
    outcome: 'BOOKED' as const,
    summary: '"Interested in learning more"',
    duration: '3:12',
  },
  {
    id: '2',
    name: 'Mike Ross',
    outcome: 'FOLLOW-UP' as const,
    summary: '"Call back in Q2"',
    duration: '1:45',
    followUpDate: 'Feb 10',
  },
];

// What's Working (Insights)
export const mockInsights = {
  whoConverts: [
    { label: 'CEO/Founder', value: '2.3x ↑' },
    { label: 'Marketing Dir', value: '1.8x ↑' },
  ],
  bestChannelMix: [
    { label: 'Email → LinkedIn', value: '68%' },
    { label: '+Voice', value: '+41%' },
  ],
  discovery: 'Prospects are most responsive on Tuesdays. Pipeline momentum is strongest mid-week.',
};

// Activity Feed
export const mockActivityFeed = [
  {
    id: '1',
    type: 'email' as const,
    text: 'Sarah Chen opened your email',
    subtext: '(5th time)',
    time: '2 minutes ago',
    status: 'success' as const,
  },
  {
    id: '2',
    type: 'linkedin' as const,
    text: 'Michael Jones visited pricing page',
    time: '15 minutes ago',
    status: 'info' as const,
  },
  {
    id: '3',
    type: 'linkedin' as const,
    text: 'Lisa Wong replied on LinkedIn',
    time: '1 hour ago',
    status: 'warning' as const,
  },
  {
    id: '4',
    type: 'meeting' as const,
    text: 'Meeting booked with Sarah via call',
    time: '2 hours ago',
    status: 'success' as const,
  },
];

// Week Ahead (Meetings)
export const mockWeekAhead = [
  {
    id: '1',
    datetime: 'Today 2:00 PM',
    type: 'Discovery Call',
    contact: 'James Cooper',
    company: 'Creative Co',
    dealValue: '$8K',
    status: 'success' as const,
  },
  {
    id: '2',
    datetime: 'Monday 10:00 AM',
    type: 'Proposal Review',
    contact: 'Emma Wilson',
    company: 'Brand Forward',
    dealValue: '$15K',
    status: 'info' as const,
  },
  {
    id: '3',
    datetime: 'Wednesday 3:30 PM',
    type: 'Intro Call',
    contact: 'Tom Brown',
    company: 'Scale Agency',
    status: 'info' as const,
  },
];

// Warm Replies
export const mockWarmReplies = [
  {
    id: '1',
    quote: '"Yes, I\'d be interested in learning more."',
    contact: 'David Park',
    company: 'Momentum Media',
    time: '2h ago',
  },
  {
    id: '2',
    quote: '"Send me more information about pricing."',
    contact: 'Anna Smith',
    company: 'Digital First',
    time: '5h ago',
  },
];

// Quick Actions (legacy)
export const mockQuickActions = [
  { id: '1', label: 'Create Campaign', icon: 'zap' as const, href: '/campaigns' },
  { id: '2', label: 'View Leads', icon: 'users' as const, href: '/leads' },
  { id: '3', label: 'Settings', icon: 'settings' as const, href: '/settings' },
];
