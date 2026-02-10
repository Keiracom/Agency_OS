'use client';

export type SettingsTab = 'profile' | 'team' | 'integrations' | 'notifications';

interface SettingsTabsProps {
  activeTab: SettingsTab;
  onTabChange: (tab: SettingsTab) => void;
}

const tabs: { id: SettingsTab; label: string }[] = [
  { id: 'profile', label: 'Profile' },
  { id: 'team', label: 'Team' },
  { id: 'integrations', label: 'Integrations' },
  { id: 'notifications', label: 'Notifications' },
];

export function SettingsTabs({ activeTab, onTabChange }: SettingsTabsProps) {
  return (
    <div className="flex gap-1 mb-8 bg-bg-surface p-1.5 rounded-xl w-fit">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-5 py-2.5 text-sm font-medium rounded-lg border-none cursor-pointer transition-all ${
            activeTab === tab.id
              ? 'bg-[rgba(124,58,237,0.15)] text-accent-primary'
              : 'bg-transparent text-text-muted hover:text-text-secondary hover:bg-bg-surface-hover'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export default SettingsTabs;
