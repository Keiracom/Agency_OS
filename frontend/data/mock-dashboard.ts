/**
 * Mock data for Dashboard (Command Center)
 * Will be replaced with real API calls
 */

export const mockDashboardStats = {
  leadsThisMonth: 47,
  emailsSent: 1284,
  meetingsBooked: 12,
  responseRate: 18.5,
};

export const mockActivityFeed = [
  {
    id: '1',
    type: 'email' as const,
    text: 'Sarah Chen opened your email',
    time: '2 minutes ago',
  },
  {
    id: '2',
    type: 'linkedin' as const,
    text: 'Marcus Webb accepted connection request',
    time: '15 minutes ago',
  },
  {
    id: '3',
    type: 'meeting' as const,
    text: 'Meeting booked with TechFlow Inc',
    time: '1 hour ago',
  },
  {
    id: '4',
    type: 'email' as const,
    text: 'Reply received from David Park',
    time: '2 hours ago',
  },
  {
    id: '5',
    type: 'linkedin' as const,
    text: 'New lead enriched: Jennifer Wu',
    time: '3 hours ago',
  },
];

export const mockQuickActions = [
  { id: '1', label: 'Create Campaign', icon: 'zap' as const, href: '/campaigns' },
  { id: '2', label: 'View Leads', icon: 'users' as const, href: '/leads' },
  { id: '3', label: 'Settings', icon: 'settings' as const, href: '/settings' },
];
