'use client';

import { Settings, Save } from 'lucide-react';

interface SettingsHeaderProps {
  onSave?: () => void;
  isSaving?: boolean;
}

export function SettingsHeader({ onSave, isSaving }: SettingsHeaderProps) {
  return (
    <header className="flex items-center justify-between mb-8">
      <div>
        <h1 className="font-serif text-2xl font-bold text-text-primary flex items-center gap-3">
          <Settings className="w-6 h-6 text-[#D4956A]" />
          Settings
        </h1>
        <p className="text-sm text-text-muted mt-1">
          Manage your account, team, and integrations
        </p>
      </div>
      {onSave && (
        <button
          onClick={onSave}
          disabled={isSaving}
          className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg
            bg-gradient-to-r from-[#D4956A] to-[#C4854A] text-white
            hover:from-[#E4A57A] hover:to-[#D4956A] hover:-translate-y-px
            disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <Save className="w-4 h-4" />
          {isSaving ? 'Saving...' : 'Save Changes'}
        </button>
      )}
    </header>
  );
}

export default SettingsHeader;
