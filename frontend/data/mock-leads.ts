/**
 * Mock data for Leads page
 * Will be replaced with real API calls
 */

export type LeadTier = 'hot' | 'warm' | 'cool' | 'cold';
export type WhyHotReason = 'ceo' | 'founder' | 'active' | 'new-role' | 'hiring' | 'buyer';
export type Channel = 'email' | 'linkedin' | 'sms' | 'voice' | 'mail';

export interface Lead {
  id: string;
  name: string;
  title: string;
  company: string;
  email: string;
  alsScore: number;
  tier: LeadTier;
  whyHot: WhyHotReason[];
  channels: { type: Channel; active: boolean }[];
  lastActivity: string;
}

export const mockLeads: Lead[] = [
  {
    id: '1',
    name: 'Sarah Chen',
    title: 'CEO',
    company: 'TechFlow Inc',
    email: 'sarah@techflow.io',
    alsScore: 94,
    tier: 'hot',
    whyHot: ['ceo', 'active', 'hiring'],
    channels: [
      { type: 'email', active: true },
      { type: 'linkedin', active: true },
    ],
    lastActivity: '2 min ago',
  },
  {
    id: '2',
    name: 'Marcus Webb',
    title: 'Founder',
    company: 'GrowthLabs',
    email: 'marcus@growthlabs.com',
    alsScore: 89,
    tier: 'hot',
    whyHot: ['founder', 'buyer'],
    channels: [
      { type: 'email', active: true },
      { type: 'linkedin', active: false },
      { type: 'sms', active: true },
    ],
    lastActivity: '15 min ago',
  },
  {
    id: '3',
    name: 'Jennifer Wu',
    title: 'VP Marketing',
    company: 'ScaleUp Co',
    email: 'jwu@scaleup.co',
    alsScore: 76,
    tier: 'warm',
    whyHot: ['new-role'],
    channels: [
      { type: 'email', active: true },
    ],
    lastActivity: '1 hour ago',
  },
  {
    id: '4',
    name: 'David Park',
    title: 'Head of Growth',
    company: 'Innovate AI',
    email: 'dpark@innovateai.com',
    alsScore: 71,
    tier: 'warm',
    whyHot: ['active'],
    channels: [
      { type: 'email', active: false },
      { type: 'linkedin', active: true },
    ],
    lastActivity: '3 hours ago',
  },
  {
    id: '5',
    name: 'Emily Rodriguez',
    title: 'Director of Ops',
    company: 'FastTrack',
    email: 'emily@fasttrack.io',
    alsScore: 58,
    tier: 'cool',
    whyHot: [],
    channels: [
      { type: 'email', active: true },
    ],
    lastActivity: '1 day ago',
  },
  {
    id: '6',
    name: 'James Wilson',
    title: 'Marketing Manager',
    company: 'LocalBiz',
    email: 'james@localbiz.net',
    alsScore: 42,
    tier: 'cold',
    whyHot: [],
    channels: [
      { type: 'email', active: false },
    ],
    lastActivity: '5 days ago',
  },
];

export const mockLeadStats = {
  hot: 12,
  warm: 18,
  cool: 24,
  total: 67,
};
