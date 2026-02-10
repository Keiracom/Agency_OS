'use client';

import { cn } from '@/lib/utils';

export type WhyHotReason = 'ceo' | 'founder' | 'active' | 'new-role' | 'hiring' | 'buyer';

interface WhyHotBadgeProps {
  reasons: WhyHotReason[];
  className?: string;
}

const reasonConfig: Record<WhyHotReason, { bg: string; text: string; label: string; icon: React.ReactNode }> = {
  ceo: {
    bg: 'bg-[rgba(124,58,237,0.15)]',
    text: 'text-[#7C3AED]',
    label: 'CEO',
    icon: (
      <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="12" height="12">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
      </svg>
    ),
  },
  founder: {
    bg: 'bg-[rgba(236,72,153,0.15)]',
    text: 'text-[#EC4899]',
    label: 'Founder',
    icon: (
      <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="12" height="12">
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
      </svg>
    ),
  },
  active: {
    bg: 'bg-[rgba(34,197,94,0.15)]',
    text: 'text-[#22C55E]',
    label: 'Active',
    icon: (
      <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="12" height="12">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
      </svg>
    ),
  },
  'new-role': {
    bg: 'bg-[rgba(59,130,246,0.15)]',
    text: 'text-[#3B82F6]',
    label: 'New Role',
    icon: (
      <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="12" height="12">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
      </svg>
    ),
  },
  hiring: {
    bg: 'bg-[rgba(20,184,166,0.15)]',
    text: 'text-[#14B8A6]',
    label: 'Hiring',
    icon: (
      <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="12" height="12">
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
      </svg>
    ),
  },
  buyer: {
    bg: 'bg-[rgba(245,158,11,0.15)]',
    text: 'text-[#F59E0B]',
    label: 'Buyer',
    icon: (
      <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="12" height="12">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
    ),
  },
};

export function WhyHotBadge({ reasons, className }: WhyHotBadgeProps) {
  if (reasons.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap gap-1.5', className)}>
      {reasons.map((reason) => {
        const config = reasonConfig[reason];
        return (
          <span
            key={reason}
            className={cn(
              'inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium whitespace-nowrap',
              config.bg,
              config.text
            )}
          >
            {config.icon}
            {config.label}
          </span>
        );
      })}
    </div>
  );
}

export default WhyHotBadge;
