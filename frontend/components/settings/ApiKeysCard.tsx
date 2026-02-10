'use client';

import { Key, Plus, Copy, RefreshCw } from 'lucide-react';
import { ApiKey } from '@/data/mock-settings';

interface ApiKeysCardProps {
  apiKeys: ApiKey[];
}

export function ApiKeysCard({ apiKeys }: ApiKeysCardProps) {
  const handleCopy = (value: string) => {
    navigator.clipboard.writeText(value);
  };

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden mb-6">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-text-primary font-semibold">
          <Key className="w-5 h-5 text-accent-primary" />
          API Keys
        </div>
        <button className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-transparent text-text-secondary border border-border-default hover:bg-bg-surface-hover hover:text-text-primary transition-all">
          <Plus className="w-3.5 h-3.5" />
          Generate New Key
        </button>
      </div>

      {/* Body */}
      <div className="p-6">
        {apiKeys.map((apiKey) => (
          <div
            key={apiKey.id}
            className="flex items-center justify-between px-5 py-4 bg-bg-surface-hover rounded-[10px] mb-3 last:mb-0"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-[rgba(124,58,237,0.15)] rounded-[10px] flex items-center justify-center">
                <Key className="w-5 h-5 text-accent-primary" />
              </div>
              <div>
                <div className="text-sm font-semibold text-text-primary">{apiKey.name}</div>
                <div className="text-sm text-text-muted font-mono mt-0.5">{apiKey.value}</div>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleCopy(apiKey.value)}
                className="px-3 py-1.5 text-xs font-medium rounded-md bg-bg-elevated text-text-secondary border-none cursor-pointer transition-all hover:bg-border-default hover:text-text-primary"
              >
                <Copy className="w-3.5 h-3.5 inline-block mr-1" />
                Copy
              </button>
              <button className="px-3 py-1.5 text-xs font-medium rounded-md bg-bg-elevated text-text-secondary border-none cursor-pointer transition-all hover:bg-border-default hover:text-text-primary">
                <RefreshCw className="w-3.5 h-3.5 inline-block mr-1" />
                Regenerate
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ApiKeysCard;
