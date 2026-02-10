'use client';

import { useState } from 'react';
import { Bell } from 'lucide-react';
import { NotificationPreference } from '@/data/mock-settings';

interface NotificationTogglesProps {
  preferences: NotificationPreference[];
}

export function NotificationToggles({ preferences: initialPreferences }: NotificationTogglesProps) {
  const [preferences, setPreferences] = useState(initialPreferences);

  const togglePreference = (id: string) => {
    setPreferences(
      preferences.map((pref) =>
        pref.id === id ? { ...pref, enabled: !pref.enabled } : pref
      )
    );
  };

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-text-primary font-semibold">
          <Bell className="w-5 h-5 text-accent-primary" />
          Notification Preferences
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="flex flex-col gap-4">
          {preferences.map((pref) => (
            <div
              key={pref.id}
              className="flex items-center justify-between px-5 py-4 bg-bg-surface-hover rounded-[10px]"
            >
              <div className="flex flex-col gap-1">
                <div className="text-sm font-medium text-text-primary">{pref.label}</div>
                <div className="text-sm text-text-muted">{pref.description}</div>
              </div>
              <button
                onClick={() => togglePreference(pref.id)}
                className={`relative w-12 h-[26px] rounded-[13px] cursor-pointer transition-all duration-200 border ${
                  pref.enabled
                    ? 'bg-accent-primary border-accent-primary'
                    : 'bg-bg-elevated border-border-default'
                }`}
              >
                <span
                  className={`absolute top-[2px] w-5 h-5 bg-white rounded-full shadow-md transition-all duration-200 ${
                    pref.enabled ? 'left-6' : 'left-[2px]'
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default NotificationToggles;
