'use client';

import { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import {
  ProfileCard,
  TeamList,
  IntegrationsGrid,
  NotificationToggles,
  ApiKeysCard,
  DangerZone,
  SettingsTabs,
  SettingsTab,
} from '@/components/settings';
import {
  mockUserProfile,
  mockTeamMembers,
  mockIntegrations,
  mockNotificationPreferences,
  mockApiKeys,
} from '@/data/mock-settings';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');

  return (
    <AppShell pageTitle="Settings">
      {/* Subtitle */}
      <div className="px-6 pt-2 pb-0">
        <p className="text-sm text-text-muted">Manage your account, team, and integrations</p>
      </div>

      {/* Content */}
      <div className="p-6 max-w-[1000px]">
        {/* Tabs */}
        <SettingsTabs activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div>
            <ProfileCard profile={mockUserProfile} />
            <ApiKeysCard apiKeys={mockApiKeys} />
            <DangerZone />
          </div>
        )}

        {/* Team Tab */}
        {activeTab === 'team' && <TeamList members={mockTeamMembers} />}

        {/* Integrations Tab */}
        {activeTab === 'integrations' && <IntegrationsGrid integrations={mockIntegrations} />}

        {/* Notifications Tab */}
        {activeTab === 'notifications' && (
          <NotificationToggles preferences={mockNotificationPreferences} />
        )}
      </div>
    </AppShell>
  );
}
