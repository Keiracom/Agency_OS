'use client';

import { useState } from 'react';
import { User, Users, Link2, Bell, CreditCard, Key, AlertTriangle, Upload, Trash2 } from 'lucide-react';
import {
  SettingsHeader,
  ProfileSection,
  IntegrationsSection,
  NotificationsSection,
  BillingSection,
  TeamSection,
} from '@/components/settings';
import {
  mockUserProfile,
  mockIntegrations,
  mockNotifications,
  mockBillingInfo,
  mockTeamMembers,
  mockApiKeys,
} from '@/lib/mock/settings-data';

type TabId = 'profile' | 'team' | 'integrations' | 'notifications' | 'billing';

const tabs: { id: TabId; label: string; icon: typeof User }[] = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'integrations', label: 'Integrations', icon: Link2 },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'billing', label: 'Billing', icon: CreditCard },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('profile');

  return (
    <div className="max-w-4xl mx-auto">
      <SettingsHeader />

      {/* Tabs — wrap on small screens so labels stay readable */}
      <div className="flex flex-wrap gap-1 mb-6 md:mb-8 p-1.5 bg-bg-panel rounded-xl w-full sm:w-fit overflow-x-auto">
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

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'profile' && (
          <>
            <ProfileSection profile={mockUserProfile} />
            <ApiKeysSection />
            <DangerZone />
          </>
        )}
        {activeTab === 'team' && <TeamSection members={mockTeamMembers} />}
        {activeTab === 'integrations' && <IntegrationsSection integrations={mockIntegrations} />}
        {activeTab === 'notifications' && <NotificationsSection preferences={mockNotifications} />}
        {activeTab === 'billing' && <BillingSection billing={mockBillingInfo} />}
      </div>
    </div>
  );
}

function ApiKeysSection() {
  return (
    <div className="glass-surface border border-rule rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Key className="w-5 h-5 text-[#D4956A]" />
          <span className="font-serif font-semibold text-ink">API Keys</span>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-rule-strong text-ink-2 hover:bg-bg-panel-hover hover:text-ink transition-all">
          + Generate New Key
        </button>
      </div>
      <div className="p-6 space-y-3">
        {mockApiKeys.map((key) => (
          <div key={key.id} className="flex items-center justify-between p-4 bg-bg-panel-hover rounded-xl">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-[rgba(212,149,106,0.15)] rounded-xl flex items-center justify-center">
                <Key className="w-5 h-5 text-[#D4956A]" />
              </div>
              <div>
                <div className="text-sm font-semibold text-ink">{key.name}</div>
                <div className="text-sm text-ink-3 font-mono">{key.value}</div>
              </div>
            </div>
            <div className="flex gap-2">
              <button className="px-3 py-1.5 text-xs font-medium rounded-md bg-panel text-ink-2 hover:bg-border-default hover:text-ink transition-all">Copy</button>
              <button className="px-3 py-1.5 text-xs font-medium rounded-md bg-panel text-ink-2 hover:bg-border-default hover:text-ink transition-all">Regenerate</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DangerZone() {
  return (
    <div className="rounded-xl border border-[rgba(239,68,68,0.3)] bg-[rgba(239,68,68,0.05)] p-6">
      <h3 className="flex items-center gap-2.5 text-base font-semibold text-status-error mb-4">
        <AlertTriangle className="w-5 h-5" />
        Danger Zone
      </h3>
      <div className="flex gap-3">
        <button className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-[rgba(239,68,68,0.1)] text-status-error border border-[rgba(239,68,68,0.3)] hover:bg-[rgba(239,68,68,0.2)] transition-all">
          <Upload className="w-4 h-4" />
          Export All Data
        </button>
        <button className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-[rgba(239,68,68,0.1)] text-status-error border border-[rgba(239,68,68,0.3)] hover:bg-[rgba(239,68,68,0.2)] transition-all">
          <Trash2 className="w-4 h-4" />
          Delete Account
        </button>
      </div>
    </div>
  );
}
