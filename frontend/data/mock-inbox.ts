// Mock data for Inbox/Replies page
// Source: frontend/design/html-prototypes/dashboard-inbox.html

import { ChannelType, channelEmoji } from './types';
export { ChannelType, channelEmoji };

export type IntentType = 'interested' | 'meeting' | 'future' | 'not-interested';
export type MessageDirection = 'sent' | 'received';

export interface Message {
  id: string;
  direction: MessageDirection;
  content: string;
  channel: ChannelType;
  timestamp: string;
}

export interface Conversation {
  id: string;
  leadName: string;
  company: string;
  channel: ChannelType;
  lastMessage: string;
  lastMessageTime: string;
  unread: boolean;
  intent: IntentType;
  leadTitle?: string;
  leadCompanyInfo?: string;
  messages: Message[];
  suggestedReply?: string;
}

// Intent badge styles
export const intentStyles: Record<IntentType, { bg: string; text: string; label: string }> = {
  interested: { bg: 'bg-emerald-50', text: 'text-emerald-600', label: 'Interested' },
  meeting: { bg: 'bg-violet-100', text: 'text-violet-600', label: 'Meeting Booked' },
  future: { bg: 'bg-amber-100', text: 'text-amber-600', label: 'Future Interest' },
  'not-interested': { bg: 'bg-slate-100', text: 'text-slate-500', label: 'Not Interested' },
};

// Mock conversations (from HTML prototype)
export const mockConversations: Conversation[] = [
  {
    id: 'conv-1',
    leadName: 'Mike Johnson',
    company: 'StartupXYZ',
    channel: 'linkedin',
    lastMessage: 'Thanks for the connection!...',
    lastMessageTime: '15m ago',
    unread: true,
    intent: 'interested',
    leadTitle: 'VP Sales',
    leadCompanyInfo: 'Series A │ 45 employees',
    messages: [
      {
        id: 'msg-1a',
        direction: 'sent',
        content: "Hi Mike, I noticed StartupXYZ just closed your Series A — congratulations! I work with similar stage companies to help them build predictable pipeline. Would love to connect and share some ideas.",
        channel: 'linkedin',
        timestamp: 'Jan 27, 3:00 PM',
      },
      {
        id: 'msg-1b',
        direction: 'received',
        content: "Thanks for the connection! We're actually looking at this space. We've been struggling to get consistent meetings booked — our SDRs are maxed out and we need to scale without adding headcount.",
        channel: 'linkedin',
        timestamp: 'Jan 28, 10:15 AM',
      },
    ],
    suggestedReply: "Thanks Mike! That's exactly the challenge we solve — we've helped similar Series A companies book 15-20 qualified meetings per month without adding headcount.\n\nWould a 15-minute call this week work to show you how? I have availability Thursday 2pm or Friday 10am AEST.",
  },
  {
    id: 'conv-2',
    leadName: 'David Lee',
    company: 'Growth Co',
    channel: 'sms',
    lastMessage: 'Interested in learning more...',
    lastMessageTime: '2h ago',
    unread: true,
    intent: 'interested',
    leadTitle: 'CEO',
    leadCompanyInfo: 'Seed Stage │ 12 employees',
    messages: [
      {
        id: 'msg-2a',
        direction: 'sent',
        content: 'Hi David, saw Growth Co is scaling fast. Happy to share how we help similar companies automate outreach. Quick call?',
        channel: 'sms',
        timestamp: 'Jan 28, 9:00 AM',
      },
      {
        id: 'msg-2b',
        direction: 'received',
        content: 'Interested in learning more about what you offer. Send me some details?',
        channel: 'sms',
        timestamp: 'Jan 28, 11:30 AM',
      },
    ],
    suggestedReply: "Great to hear, David! We help companies like yours book 20+ qualified meetings per month using AI-powered multi-channel outreach.\n\nI'll send over a quick 2-min video walkthrough. Would love to hear your thoughts after!",
  },
  {
    id: 'conv-3',
    leadName: 'Sarah Chen',
    company: 'TechCorp',
    channel: 'email',
    lastMessage: 'Re: Question about...',
    lastMessageTime: '1h ago',
    unread: false,
    intent: 'meeting',
    leadTitle: 'CTO',
    leadCompanyInfo: 'Series B │ 120 employees',
    messages: [
      {
        id: 'msg-3a',
        direction: 'sent',
        content: "Hi Sarah, I noticed TechCorp's engineering team has grown 3x this year. As you scale, outbound typically becomes harder to manage. Would love to show you how we help CTOs like yourself systematize pipeline generation.",
        channel: 'email',
        timestamp: 'Jan 25, 2:00 PM',
      },
      {
        id: 'msg-3b',
        direction: 'received',
        content: "Thanks for reaching out. We're actually evaluating options in this space. Let's set up a call — I have 30 mins free Thursday at 3pm AEST.",
        channel: 'email',
        timestamp: 'Jan 26, 10:45 AM',
      },
      {
        id: 'msg-3c',
        direction: 'sent',
        content: "Perfect! I've sent over a calendar invite for Thursday 3pm AEST. Looking forward to chatting!",
        channel: 'email',
        timestamp: 'Jan 26, 11:00 AM',
      },
    ],
  },
  {
    id: 'conv-4',
    leadName: 'Emma Wilson',
    company: 'Scale Labs',
    channel: 'email',
    lastMessage: 'Not right now, but maybe...',
    lastMessageTime: '3h ago',
    unread: false,
    intent: 'future',
    leadTitle: 'Head of Growth',
    leadCompanyInfo: 'Series A │ 35 employees',
    messages: [
      {
        id: 'msg-4a',
        direction: 'sent',
        content: 'Hi Emma, congrats on the recent funding round! Would love to connect about how we can help Scale Labs accelerate growth.',
        channel: 'email',
        timestamp: 'Jan 27, 1:00 PM',
      },
      {
        id: 'msg-4b',
        direction: 'received',
        content: "Thanks for reaching out! We're focused on product right now and not actively looking at outbound solutions. Maybe circle back in Q2?",
        channel: 'email',
        timestamp: 'Jan 28, 9:30 AM',
      },
    ],
    suggestedReply: "Totally understand, Emma — timing is everything. I'll set a reminder to reconnect in April.\n\nIn the meantime, here's a case study from a similar Series A company that might be useful when you're ready: [link]\n\nBest of luck with the product push!",
  },
  {
    id: 'conv-5',
    leadName: 'James Park',
    company: 'Velocity Inc',
    channel: 'voice',
    lastMessage: 'Left voicemail, called back...',
    lastMessageTime: 'Yesterday',
    unread: false,
    intent: 'interested',
    leadTitle: 'VP Revenue',
    leadCompanyInfo: 'Series B │ 80 employees',
    messages: [
      {
        id: 'msg-5a',
        direction: 'sent',
        content: '[Voicemail] Hi James, this is calling about Velocity Inc — noticed your team is scaling. Would love to chat about how we help similar companies book more meetings. Call me back at your convenience.',
        channel: 'voice',
        timestamp: 'Jan 27, 10:00 AM',
      },
      {
        id: 'msg-5b',
        direction: 'received',
        content: '[Callback] Interested in learning more. Currently have 2 SDRs but struggling with reply rates. What do you offer?',
        channel: 'voice',
        timestamp: 'Jan 27, 2:30 PM',
      },
    ],
    suggestedReply: "Great chatting with you, James! As discussed, here's a quick summary:\n\n• We handle multi-channel outreach (email, LinkedIn, calls, SMS)\n• Typical clients see 3-4x improvement in reply rates\n• No additional headcount needed\n\nI'll send a calendar link for a deeper dive. Looking forward to it!",
  },
];

// Filter options
export const inboxFilters = [
  { id: 'all', label: 'All' },
  { id: 'needs-reply', label: 'Needs Reply' },
  { id: 'meetings', label: 'Meetings' },
] as const;

export type InboxFilter = typeof inboxFilters[number]['id'];
