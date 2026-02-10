'use client';

import { inboxFilters, InboxFilter } from '@/data/mock-inbox';

interface Props {
  activeFilter: InboxFilter;
  onFilterChange: (filter: InboxFilter) => void;
}

export function InboxFilters({ activeFilter, onFilterChange }: Props) {
  return (
    <div className="flex gap-2">
      {inboxFilters.map((filter) => (
        <button
          key={filter.id}
          onClick={() => onFilterChange(filter.id)}
          className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
            activeFilter === filter.id
              ? 'bg-slate-800 text-white border-slate-800'
              : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
          }`}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}
