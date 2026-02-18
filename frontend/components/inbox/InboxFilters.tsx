/**
 * FILE: frontend/components/inbox/InboxFilters.tsx
 * PURPOSE: Search and filter tabs for inbox
 */
'use client';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FilterTab {
  id: string;
  label: string;
  count?: number;
}

interface InboxFiltersProps {
  activeFilter: string;
  onFilterChange: (id: string) => void;
  tabs: FilterTab[];
}

export function InboxFilters({ activeFilter, onFilterChange, tabs }: InboxFiltersProps) {
  return (
    <div className="p-4 border-b border-border-subtle">
      <div className="relative mb-3">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        <input
          type="text"
          placeholder="Search conversations..."
          className="w-full pl-10 pr-4 py-2.5 bg-bg-base border border-border-subtle rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20"
        />
      </div>
      <div className="flex gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onFilterChange(tab.id)}
            className={cn(
              'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
              activeFilter === tab.id
                ? 'bg-accent-primary/15 text-accent-primary'
                : 'text-text-muted hover:text-text-secondary hover:bg-bg-surface/5'
            )}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-1.5 text-xs opacity-70">{tab.count}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
