'use client';

import { cn } from '@/lib/utils';

export type TierType = 'hot' | 'warm' | 'cool' | 'cold';

interface LeadTierBadgeProps {
  tier: TierType;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeConfig = {
  sm: 'px-1.5 py-0.5 text-[9px]',
  md: 'px-2 py-1 text-[10px]',
  lg: 'px-3 py-1.5 text-xs',
};

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

export function LeadTierBadge({ tier, showLabel = true, size = 'md', className }: LeadTierBadgeProps) {
  const config = tierConfig[tier];

  return (
    <span
      className={cn(
        'inline-flex items-center rounded font-semibold uppercase tracking-wide border',
        sizeConfig[size],
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
