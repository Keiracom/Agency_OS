'use client';

import { useState } from 'react';
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
    <div className="min-h-screen bg-bg-void">
      {/* Header */}
      <header className="bg-bg-surface border-b border-border-subtle px-8 py-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Settings</h1>
          <p className="text-sm text-text-muted mt-1">Manage your account, team, and integrations</p>
        </div>
      </header>

      {/* Content */}
      <div className="p-8 max-w-[1000px]">
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
    </div>
  );
}
