'use client';

import { useState } from 'react';
import { Bell } from 'lucide-react';
import { NotificationPreference } from '@/lib/mock/settings-data';

interface NotificationsSectionProps {
  preferences: NotificationPreference[];
}

export function NotificationsSection({ preferences: initialPrefs }: NotificationsSectionProps) {
  const [preferences, setPreferences] = useState(initialPrefs);

  const toggle = (id: string) => {
    setPreferences(preferences.map((p) => p.id === id ? { ...p, enabled: !p.enabled } : p));
  };

  return (
    <div className="glass-surface border border-rule rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-rule flex items-center gap-2.5">
        <Bell className="w-5 h-5 text-[#D4956A]" />
        <span className="font-serif font-semibold text-ink">Notification Preferences</span>
      </div>

      <div className="p-6">
        <div className="flex flex-col gap-4">
          {preferences.map((pref) => (
            <div key={pref.id} className="flex items-center justify-between px-5 py-4 bg-bg-panel-hover rounded-xl">
              <div className="flex flex-col gap-1">
                <div className="text-sm font-medium text-ink">{pref.label}</div>
                <div className="text-sm text-ink-3">{pref.description}</div>
              </div>
              <button
                onClick={() => toggle(pref.id)}
                className={`relative w-12 h-[26px] rounded-[13px] cursor-pointer transition-all duration-200 border ${
                  pref.enabled
                    ? 'bg-[#D4956A] border-[#D4956A]'
                    : 'bg-bg-elevated border-rule-strong'
                }`}
              >
                <span className={`absolute top-[2px] w-5 h-5 bg-bg-panel rounded-full shadow-md transition-all duration-200 ${
                  pref.enabled ? 'left-6' : 'left-[2px]'
                }`} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default NotificationsSection;
