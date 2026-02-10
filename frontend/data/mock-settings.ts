/**
 * Mock data for Settings page
 * Will be replaced with real API calls
 */

export interface UserProfile {
  name: string;
  email: string;
  phone: string;
  company: string;
  timezone: string;
  initials: string;
  plan: string;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'owner' | 'admin' | 'member';
  initials: string;
}

export type IntegrationStatus = 'connected' | 'pending' | 'disconnected';

export interface Integration {
  id: string;
  name: string;
  icon: 'email' | 'linkedin' | 'sms' | 'voice' | 'calendar' | 'crm';
  status: IntegrationStatus;
}

export interface NotificationPreference {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
}

export interface ApiKey {
  id: string;
  name: string;
  value: string;
  type: 'production' | 'test';
}

export const mockUserProfile: UserProfile = {
  name: 'Dave K.',
  email: 'dave@example.com',
  phone: '+61 4XX XXX XXX',
  company: 'Growth Agency',
  timezone: 'Australia/Sydney (AEST)',
  initials: 'DK',
  plan: 'Velocity Plan',
};

export const mockTeamMembers: TeamMember[] = [
  {
    id: '1',
    name: 'Dave K.',
    email: 'dave@example.com',
    role: 'owner',
    initials: 'DK',
  },
  {
    id: '2',
    name: 'Jane Miller',
    email: 'jane@example.com',
    role: 'admin',
    initials: 'JM',
  },
  {
    id: '3',
    name: 'Tom Smith',
    email: 'tom@example.com',
    role: 'member',
    initials: 'TS',
  },
];

export const mockIntegrations: Integration[] = [
  { id: '1', name: 'Email', icon: 'email', status: 'connected' },
  { id: '2', name: 'LinkedIn', icon: 'linkedin', status: 'connected' },
  { id: '3', name: 'SMS', icon: 'sms', status: 'connected' },
  { id: '4', name: 'Voice', icon: 'voice', status: 'pending' },
  { id: '5', name: 'Calendar', icon: 'calendar', status: 'connected' },
  { id: '6', name: 'CRM', icon: 'crm', status: 'disconnected' },
];

export const mockNotificationPreferences: NotificationPreference[] = [
  {
    id: '1',
    label: 'Email Notifications',
    description: 'Receive email alerts for important activity',
    enabled: true,
  },
  {
    id: '2',
    label: 'New Reply Alerts',
    description: 'Get notified when leads respond',
    enabled: true,
  },
  {
    id: '3',
    label: 'Meeting Booked',
    description: 'Get notified when a meeting is scheduled',
    enabled: true,
  },
  {
    id: '4',
    label: 'Hot Lead Alerts',
    description: 'Instant notification when a lead becomes hot',
    enabled: true,
  },
  {
    id: '5',
    label: 'Weekly Digest',
    description: "Summary of your week's performance",
    enabled: false,
  },
  {
    id: '6',
    label: 'Marketing Updates',
    description: 'News about new features and updates',
    enabled: false,
  },
];

export const mockApiKeys: ApiKey[] = [
  {
    id: '1',
    name: 'Production API Key',
    value: 'aos_live_••••••••••••••••',
    type: 'production',
  },
  {
    id: '2',
    name: 'Test API Key',
    value: 'aos_test_••••••••••••••••',
    type: 'test',
  },
];

export const mockTimezones = [
  'Australia/Sydney (AEST)',
  'Australia/Melbourne',
  'Australia/Brisbane',
  'America/New_York',
  'America/Los_Angeles',
];
