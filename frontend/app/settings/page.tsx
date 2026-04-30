'use client';

import { useState } from 'react';
import { User, Users, Link2, Bell } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import {
  ProfileSection,
  TeamSection,
  IntegrationsSection,
  NotificationsSection,
} from '@/components/settings';
import {
  mockUserProfile,
  mockTeamMembers,
  mockIntegrations,
  mockNotifications,
} from '@/lib/mock/settings-data';

type SettingsTab = 'profile' | 'team' | 'integrations' | 'notifications';

const tabs: { id: SettingsTab; label: string; icon: typeof User }[] = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'integrations', label: 'Integrations', icon: Link2 },
  { id: 'notifications', label: 'Notifications', icon: Bell },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');

  return (
    <AppShell pageTitle="Settings">
      <div className="px-6 pt-2 pb-0">
        <p className="text-sm text-ink-3">Manage your account, team, and integrations</p>
      </div>

      <div className="p-6 max-w-[1000px]">
        {/* Tabs */}
        <div className="flex gap-1 mb-8 p-1.5 bg-bg-panel rounded-xl w-fit">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg transition-all ${
                  isActive
                    ? 'bg-[rgba(212,149,106,0.15)] text-[#D4956A]'
                    : 'text-ink-3 hover:text-ink-2 hover:bg-bg-panel-hover'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeTab === 'profile' && <ProfileSection profile={mockUserProfile} />}
        {activeTab === 'team' && <TeamSection members={mockTeamMembers} />}
        {activeTab === 'integrations' && <IntegrationsSection integrations={mockIntegrations} />}
        {activeTab === 'notifications' && <NotificationsSection preferences={mockNotifications} />}
      </div>
    </AppShell>
  );
}
