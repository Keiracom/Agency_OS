/**
 * Mock data for Lead Detail page
 * Will be replaced with real API calls
 */

import { Lead, LeadTier, WhyHotReason, Channel } from './mock-leads';

export interface LeadRadarScores {
  dataQuality: number;    // How complete is their data
  authority: number;       // Decision-making power
  companyFit: number;      // Match with ICP
  timing: number;          // Buying signals, job changes
  risk: number;            // Bounce risk, competition
}

export interface TimelineEvent {
  id: string;
  type: 'email' | 'linkedin' | 'sms' | 'voice' | 'enrichment' | 'reply';
  title: string;
  detail?: string;
  time: string;
  date: string; // For grouping
  badge?: 'booked' | 'replied' | 'opened' | 'clicked';
}

export interface CompanyIntel {
  name: string;
  website: string;
  industry: string;
  size: string;
  revenue: string;
  location: string;
  insights: string[];
}

export interface SiegeWaterfallTier {
  tier: number;
  name: string;
  status: 'complete' | 'in-progress' | 'pending';
  source?: string;
  timestamp?: string;
}

export interface LeadDetail extends Lead {
  radarScores: LeadRadarScores;
  timeline: TimelineEvent[];
  company: CompanyIntel;
  siegeWaterfall: SiegeWaterfallTier[];
  notes: { id: string; text: string; author: string; date: string }[];
}

export const mockLeadDetail: LeadDetail = {
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
  
  radarScores: {
    dataQuality: 92,
    authority: 98,
    companyFit: 88,
    timing: 95,
    risk: 15, // Lower is better
  },
  
  timeline: [
    {
      id: 't1',
      type: 'email',
      title: 'Email opened',
      detail: 'Subject: "Quick question about TechFlow\'s growth plans"',
      time: '9:42 AM',
      date: 'Today',
      badge: 'opened',
    },
    {
      id: 't2',
      type: 'linkedin',
      title: 'Connection accepted',
      time: '8:15 AM',
      date: 'Today',
    },
    {
      id: 't3',
      type: 'email',
      title: 'Initial outreach sent',
      detail: 'Personalized email about scaling marketing operations',
      time: '2:30 PM',
      date: 'Yesterday',
    },
    {
      id: 't4',
      type: 'enrichment',
      title: 'Lead enriched via Siege Waterfall',
      detail: 'ABN → GMB → Hunter → LinkedIn',
      time: '11:00 AM',
      date: 'Yesterday',
    },
  ],
  
  company: {
    name: 'TechFlow Inc',
    website: 'techflow.io',
    industry: 'SaaS / Marketing Technology',
    size: '51-200 employees',
    revenue: '$10M-$50M',
    location: 'Sydney, Australia',
    insights: [
      'Recently raised Series B ($25M)',
      'Hiring 5 marketing roles',
      'Launched new product line Q4 2025',
      'Competitor of MarketStack (your client)',
    ],
  },
  
  siegeWaterfall: [
    { tier: 1, name: 'ABN Lookup', status: 'complete', source: 'ABR', timestamp: '2 days ago' },
    { tier: 2, name: 'GMB Enrichment', status: 'complete', source: 'Google', timestamp: '2 days ago' },
    { tier: 3, name: 'Email Discovery', status: 'complete', source: 'Hunter.io', timestamp: '2 days ago' },
    { tier: 4, name: 'LinkedIn Profile', status: 'complete', source: 'LinkedIn', timestamp: '1 day ago' },
    { tier: 5, name: 'Deep Intel', status: 'in-progress', source: 'DataForSEO', timestamp: 'Running...' },
  ],
  
  notes: [
    {
      id: 'n1',
      text: 'Very responsive on LinkedIn. Mentioned budget approval in Q1.',
      author: 'You',
      date: 'Today, 10:15 AM',
    },
  ],
};
