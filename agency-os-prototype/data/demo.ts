// Demo data for Agency OS Prototype

export const dashboardData = {
  greeting: "Good morning, Dave 👋",
  subtext: "Here's how your pipeline is performing this month.",
  
  celebration: {
    show: true,
    title: "Target hit 3 days early!",
    subtitle: "You've booked 12 meetings this month. Keep the momentum going!",
  },
  
  meetingsGoal: {
    current: 12,
    target: 10,
    percentComplete: 120,
    targetHit: true,
    daysEarly: 3,
  },
  
  momentum: {
    direction: "up" as const,
    percentChange: 25,
    label: "Strong momentum",
  },
  
  quickStats: [
    { value: "68%", label: "Show Rate", change: "↑ 5% vs avg", changeDirection: "up" as const },
    { value: "4", label: "Deals Started", change: "↑ 2 this week", changeDirection: "up" as const },
    { value: "$47K", label: "Pipeline Value", change: "↑ $12K added", changeDirection: "up" as const },
    { value: "8.2x", label: "ROI", change: "Lifetime", changeDirection: "neutral" as const },
  ],
  
  hotProspects: [
    {
      id: "1",
      name: "Sarah Chen",
      company: "Bloom Digital",
      title: "Marketing Director",
      initials: "SC",
      score: 94,
      signal: "Opened 5 emails in 2 hours",
      isVeryHot: true,
    },
    {
      id: "2",
      name: "Michael Jones",
      company: "Growth Labs",
      title: "CEO",
      initials: "MJ",
      score: 87,
      signal: "Visited pricing page twice",
      isVeryHot: false,
    },
    {
      id: "3",
      name: "Lisa Wong",
      company: "Pixel Perfect",
      title: "Founder",
      initials: "LW",
      score: 82,
      signal: "Replied to LinkedIn message",
      isVeryHot: false,
    },
  ],
  
  weekAhead: [
    {
      id: "1",
      title: "Discovery Call",
      contact: "James Cooper",
      company: "Creative Co",
      time: "Today • 2:00 PM",
      dealValue: "$8K",
      isToday: true,
    },
    {
      id: "2",
      title: "Proposal Review",
      contact: "Emma Wilson",
      company: "Brand Forward",
      time: "Monday • 10:00 AM",
      dealValue: "$15K",
      isToday: false,
    },
    {
      id: "3",
      title: "Intro Call",
      contact: "Tom Brown",
      company: "Scale Agency",
      time: "Wednesday • 3:30 PM",
      dealValue: null,
      isToday: false,
    },
  ],
  
  insight: {
    icon: "💡",
    headline: "Tuesday emails are crushing it",
    detail: "Your Tuesday morning sends have a 42% open rate — double your average. Consider shifting more volume to Tuesdays.",
    highlightText: "42% open rate",
  },
  
  warmReplies: [
    {
      id: "1",
      name: "David Park",
      company: "Momentum Media",
      initials: "DP",
      preview: "Yes, I'd be interested in learning more. Can we schedule a call next week?",
      time: "2h ago",
    },
    {
      id: "2",
      name: "Anna Smith",
      company: "Digital First",
      initials: "AS",
      preview: "This looks relevant. Send me more information about pricing.",
      time: "5h ago",
    },
  ],
}

export const leadsData = [
  { id: "1", name: "Sarah Chen", company: "Bloom Digital", title: "Marketing Director", email: "sarah@bloomdigital.com.au", score: 94, tier: "hot", lastActivity: "2 hours ago", channel: "email" },
  { id: "2", name: "Michael Jones", company: "Growth Labs", title: "CEO", email: "michael@growthlabs.com.au", score: 87, tier: "hot", lastActivity: "1 day ago", channel: "linkedin" },
  { id: "3", name: "Lisa Wong", company: "Pixel Perfect", title: "Founder", email: "lisa@pixelperfect.com.au", score: 82, tier: "warm", lastActivity: "3 hours ago", channel: "linkedin" },
  { id: "4", name: "James Cooper", company: "Creative Co", title: "Managing Director", email: "james@creativeco.com.au", score: 76, tier: "warm", lastActivity: "1 day ago", channel: "email" },
  { id: "5", name: "Emma Wilson", company: "Brand Forward", title: "Head of Marketing", email: "emma@brandforward.com.au", score: 71, tier: "warm", lastActivity: "2 days ago", channel: "sms" },
  { id: "6", name: "Tom Brown", company: "Scale Agency", title: "Director", email: "tom@scaleagency.com.au", score: 58, tier: "cool", lastActivity: "5 days ago", channel: "email" },
  { id: "7", name: "Sophie Martinez", company: "Digital Edge", title: "Marketing Manager", email: "sophie@digitaledge.com.au", score: 45, tier: "cool", lastActivity: "1 week ago", channel: "linkedin" },
  { id: "8", name: "Ryan Taylor", company: "Apex Media", title: "CEO", email: "ryan@apexmedia.com.au", score: 32, tier: "cold", lastActivity: "2 weeks ago", channel: "email" },
]

export const campaignsData = [
  {
    id: "1",
    name: "Q1 Agency Outreach",
    status: "active",
    channels: ["email", "linkedin"],
    sent: 1245,
    opened: 412,
    replied: 47,
    meetings: 8,
    startDate: "Jan 15, 2026",
  },
  {
    id: "2",
    name: "SaaS Founders Campaign",
    status: "active",
    channels: ["email", "sms", "voice"],
    sent: 856,
    opened: 298,
    replied: 34,
    meetings: 5,
    startDate: "Jan 20, 2026",
  },
  {
    id: "3",
    name: "December Warm-Up",
    status: "completed",
    channels: ["email"],
    sent: 2100,
    opened: 672,
    replied: 89,
    meetings: 12,
    startDate: "Dec 1, 2025",
  },
  {
    id: "4",
    name: "LinkedIn Only Test",
    status: "paused",
    channels: ["linkedin"],
    sent: 320,
    opened: 145,
    replied: 12,
    meetings: 2,
    startDate: "Jan 10, 2026",
  },
]

export const repliesData = [
  {
    id: "1",
    name: "David Park",
    company: "Momentum Media",
    initials: "DP",
    subject: "Re: Quick question about your agency",
    preview: "Yes, I'd be interested in learning more. Can we schedule a call next week?",
    time: "2h ago",
    channel: "email",
    isUnread: true,
    sentiment: "positive",
  },
  {
    id: "2",
    name: "Anna Smith",
    company: "Digital First",
    initials: "AS",
    subject: "Re: Helping agencies scale",
    preview: "This looks relevant. Send me more information about pricing.",
    time: "5h ago",
    channel: "email",
    isUnread: true,
    sentiment: "positive",
  },
  {
    id: "3",
    name: "Chris Lee",
    company: "Visionary Studios",
    initials: "CL",
    subject: "Re: Introduction",
    preview: "Not interested at this time. Please remove me from your list.",
    time: "1d ago",
    channel: "email",
    isUnread: false,
    sentiment: "negative",
  },
  {
    id: "4",
    name: "Rachel Green",
    company: "Marketing Plus",
    initials: "RG",
    subject: "Re: Following up",
    preview: "Thanks for reaching out. We're currently evaluating solutions. Can you send a deck?",
    time: "1d ago",
    channel: "linkedin",
    isUnread: false,
    sentiment: "neutral",
  },
]

export const settingsData = {
  user: {
    name: "Dave K.",
    email: "dave@example.com",
    company: "Growth Agency",
    plan: "Velocity",
  },
  integrations: [
    { id: "1", name: "Gmail", status: "connected", icon: "📧" },
    { id: "2", name: "LinkedIn", status: "connected", icon: "💼" },
    { id: "3", name: "Twilio SMS", status: "connected", icon: "📱" },
    { id: "4", name: "Vapi Voice", status: "pending", icon: "📞" },
    { id: "5", name: "Salesforce", status: "disconnected", icon: "☁️" },
  ],
}
