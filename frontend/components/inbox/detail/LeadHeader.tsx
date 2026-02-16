/**
 * FILE: frontend/components/inbox/detail/LeadHeader.tsx
 * PURPOSE: Lead avatar, name, badges, score ring, actions
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { InboxMessage, TierType, IntentType } from '@/lib/mock/inbox-data';
import { Calendar, Phone, Flame } from 'lucide-react';
import { cn } from '@/lib/utils';

const tierGradients: Record<TierType, string> = {
  hot: 'from-amber to-amber-light',
  warm: 'from-amber-500 to-yellow-400',
  cool: 'from-amber to-text-secondary',
};

const tierColors: Record<TierType, string> = {
  hot: '#EF4444',
  warm: '#F59E0B',
  cool: '#3B82F6',
};

const tierBgColors: Record<TierType, string> = {
  hot: 'bg-amber-glow',
  warm: 'bg-amber-500/15',
  cool: 'bg-bg-elevated/15',
};

interface LeadHeaderProps {
  message: InboxMessage;
}

export function LeadHeader({ message }: LeadHeaderProps) {
  const badges = [];
  
  // Tier badge
  if (message.tier === 'hot') {
    badges.push(
      <span key="tier" className={cn('flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide', tierBgColors[message.tier])} style={{ color: tierColors[message.tier] }}>
        <Flame className="w-3.5 h-3.5" />
        Hot
      </span>
    );
  }
  
  // Title badge (if CEO)
  if (message.title.toLowerCase().includes('ceo') || message.title.toLowerCase().includes('founder')) {
    badges.push(
      <span key="title" className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide bg-amber/15 text-amber">
         {message.title}
      </span>
    );
  }
  
  // Intent badge
  if (message.intent === 'meeting') {
    badges.push(
      <span key="intent" className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide bg-amber/15 text-amber">
        <Calendar className="w-3.5 h-3.5" />
        Meeting Requested
      </span>
    );
  }
  
  return (
    <div className="bg-surface-dark border-b border-border-subtle px-8 py-5 flex items-center gap-5">
      {/* Avatar */}
      <div className={cn(
        'w-14 h-14 rounded-2xl flex items-center justify-center text-text-primary font-bold text-xl bg-gradient-to-br flex-shrink-0',
        tierGradients[message.tier]
      )}>
        {message.initials}
      </div>
      
      {/* Info */}
      <div className="flex-1 min-w-0">
        <h1 className="font-serif text-xl font-bold text-text-primary mb-1">
          {message.name}
        </h1>
        <p className="text-sm text-text-muted">
          {message.title} at {message.company} • {message.email}
        </p>
        {badges.length > 0 && (
          <div className="flex gap-2 mt-2 flex-wrap">
            {badges}
          </div>
        )}
      </div>
      
      {/* Score Ring */}
      <div
        className="w-[72px] h-[72px] rounded-full flex flex-col items-center justify-center flex-shrink-0"
        style={{
          border: `4px solid ${tierColors[message.tier]}`,
          backgroundColor: `${tierColors[message.tier]}12`,
        }}
      >
        <span className="font-mono text-2xl font-extrabold leading-none" style={{ color: tierColors[message.tier] }}>
          {message.score}
        </span>
        <span className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Score</span>
      </div>
      
      {/* Actions */}
      <div className="flex gap-2.5">
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold bg-amber-600 hover:bg-amber-500 text-text-primary transition-colors">
          <Calendar className="w-4 h-4" />
          Schedule Call
        </button>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold glass-surface border border-border-subtle text-text-primary hover:bg-bg-surface/[0.05] transition-colors">
          <Phone className="w-4 h-4" />
          Call Now
        </button>
      </div>
    </div>
  );
}
