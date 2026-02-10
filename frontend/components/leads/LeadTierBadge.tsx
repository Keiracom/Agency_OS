'use client';

import { cn } from '@/lib/utils';

export type TierType = 'hot' | 'warm' | 'cool' | 'cold';

interface LeadTierBadgeProps {
  tier: TierType;
  showLabel?: boolean;
  className?: string;
}

const tierConfig = {
  hot: {
    bg: 'bg-[rgba(239,68,68,0.1)]',
    text: 'text-[#EF4444]',
    border: 'border-[rgba(239,68,68,0.3)]',
    label: 'HOT',
  },
  warm: {
    bg: 'bg-[rgba(245,158,11,0.1)]',
    text: 'text-[#F59E0B]',
    border: 'border-[rgba(245,158,11,0.3)]',
    label: 'WARM',
  },
  cool: {
    bg: 'bg-[rgba(59,130,246,0.1)]',
    text: 'text-[#3B82F6]',
    border: 'border-[rgba(59,130,246,0.3)]',
    label: 'COOL',
  },
  cold: {
    bg: 'bg-[rgba(107,114,128,0.1)]',
    text: 'text-[#6B7280]',
    border: 'border-[rgba(107,114,128,0.3)]',
    label: 'COLD',
  },
};

export function LeadTierBadge({ tier, showLabel = true, className }: LeadTierBadgeProps) {
  const config = tierConfig[tier];

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wide border',
        config.bg,
        config.text,
        config.border,
        className
      )}
    >
      {showLabel && config.label}
    </span>
  );
}

export default LeadTierBadge;
