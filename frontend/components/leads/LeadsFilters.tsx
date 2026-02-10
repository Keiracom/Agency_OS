'use client';

import { cn } from '@/lib/utils';

interface TierCounts {
  hot: number;
  warm: number;
  cool: number;
  total: number;
}

interface LeadsFiltersProps {
  activeTier: string;
  onTierChange: (tier: string) => void;
  searchQuery: string;
  onSearch: (query: string) => void;
  counts: TierCounts;
  className?: string;
}

const SearchIcon = () => (
  <svg
    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted w-[18px] h-[18px]"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    viewBox="0 0 24 24"
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const HotIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="14" height="14">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
  </svg>
);

const WarmIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="14" height="14">
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

const CoolIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="14" height="14">
    <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
  </svg>
);

const tierTabs = [
  { id: 'all', label: 'All', icon: null, countKey: 'total' as keyof TierCounts },
  { id: 'hot', label: 'Hot', icon: <HotIcon />, countKey: 'hot' as keyof TierCounts },
  { id: 'warm', label: 'Warm', icon: <WarmIcon />, countKey: 'warm' as keyof TierCounts },
  { id: 'cool', label: 'Cool', icon: <CoolIcon />, countKey: 'cool' as keyof TierCounts },
];

const tierColors: Record<string, string> = {
  hot: 'text-[#EF4444]',
  warm: 'text-[#F59E0B]',
  cool: 'text-[#3B82F6]',
};

export function LeadsFilters({
  activeTier,
  onTierChange,
  searchQuery,
  onSearch,
  counts,
  className,
}: LeadsFiltersProps) {
  return (
    <div className={cn('flex items-center gap-4', className)}>
      {/* Search Input */}
      <div className="flex-1 max-w-[400px] relative">
        <SearchIcon />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Search by name, company, or email..."
          className="w-full py-2.5 px-4 pl-[42px] text-sm bg-base border border-default rounded-lg text-primary outline-none transition-all placeholder:text-muted focus:border-[#7C3AED] focus:ring-[3px] focus:ring-[rgba(124,58,237,0.15)]"
        />
      </div>

      {/* Tier Tabs */}
      <div className="flex bg-base border border-default rounded-lg p-1 gap-1">
        {tierTabs.map((tab) => {
          const isActive = activeTier === tab.id;
          const tierColor = tierColors[tab.id];

          return (
            <button
              key={tab.id}
              onClick={() => onTierChange(tab.id)}
              className={cn(
                'flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium rounded-md transition-all',
                isActive
                  ? cn('bg-surface', tierColor || 'text-primary')
                  : 'text-muted hover:text-secondary hover:bg-surface-hover'
              )}
            >
              {tab.icon}
              {tab.label}
              <span
                className={cn(
                  'font-mono text-[11px] px-1.5 py-0.5 rounded bg-surface-hover',
                  isActive && 'bg-base'
                )}
              >
                {counts[tab.countKey]}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default LeadsFilters;
