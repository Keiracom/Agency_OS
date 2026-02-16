'use client';

import { LeadDetail } from '@/data/mock-lead-detail';
import { LeadTierBadge } from './LeadTierBadge';
import { WhyHotBadge } from './WhyHotBadge';
import { Mail, Phone, Linkedin, Flame, Calendar, MessageSquare, MoreHorizontal } from 'lucide-react';

interface LeadHeaderProps {
  lead: LeadDetail;
}

const tierGradients = {
  hot: 'from-tier-hot to-amber-light',
  warm: 'from-tier-warm to-yellow-400',
  cool: 'from-tier-cool to-amber',
  cold: 'from-tier-cold to-slate-500',
};

const tierBgClasses = {
  hot: 'bg-tier-hot/10 border-tier-hot/30',
  warm: 'bg-tier-warm/10 border-tier-warm/30',
  cool: 'bg-tier-cool/10 border-tier-cool/30',
  cold: 'bg-tier-cold/10 border-tier-cold/30',
};

const tierTextClasses = {
  hot: 'text-tier-hot',
  warm: 'text-tier-warm',
  cool: 'text-tier-cool',
  cold: 'text-tier-cold',
};

export function LeadHeader({ lead }: LeadHeaderProps) {
  const initials = lead.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase();

  return (
    <div className="bg-surface border border-border-subtle rounded-2xl p-8 relative overflow-hidden">
      {/* Top gradient accent bar */}
      <div
        className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${tierGradients[lead.tier]}`}
      />

      <div className="flex gap-8">
        {/* Left: Avatar + Info */}
        <div className="flex gap-6 flex-1">
          {/* Avatar with tier gradient */}
          <div
            className={`w-20 h-20 rounded-2xl flex items-center justify-center text-text-primary font-bold text-2xl bg-gradient-to-br ${tierGradients[lead.tier]} shrink-0 shadow-lg`}
          >
            {initials}
          </div>

          <div className="flex flex-col">
            <h1 className="text-2xl font-bold text-primary mb-1">{lead.name}</h1>
            <p className="text-base text-secondary mb-4">
              {lead.title} at {lead.company.name}
            </p>

            {/* Meta links */}
            <div className="flex flex-wrap gap-5">
              <a
                href={`mailto:${lead.email}`}
                className="flex items-center gap-2 text-sm text-secondary hover:text-accent-primary transition-colors"
              >
                <Mail className="w-4 h-4 text-muted" />
                {lead.email}
              </a>
              {lead.company.website && (
                <a
                  href={`https://${lead.company.website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-accent-primary hover:underline"
                >
                  <Linkedin className="w-4 h-4 text-muted" />
                  linkedin.com/in/{lead.name.toLowerCase().replace(' ', '')}
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Right: Score + Tier */}
        <div className="flex flex-col items-end gap-3">
          {/* ALS Score Display */}
          <div
            className={`text-center px-6 py-4 rounded-xl border ${tierBgClasses[lead.tier]}`}
          >
            <div
              className={`text-5xl font-extrabold font-mono leading-none ${tierTextClasses[lead.tier]}`}
            >
              {lead.alsScore}
            </div>
            <div className="text-xs font-semibold text-muted uppercase tracking-wider mt-1">
              Lead Score
            </div>
          </div>

          {/* Tier Badge */}
          <LeadTierBadge tier={lead.tier} size="lg" />
        </div>
      </div>

      {/* Why Hot Section */}
      {lead.whyHot && lead.whyHot.length > 0 && (
        <div className="mt-6 pt-6 border-t border-border-subtle">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted uppercase tracking-wider mb-3">
            <Flame className="w-3.5 h-3.5" />
            Why This Lead is Hot
          </div>
          <div className="flex flex-wrap gap-2">
            <WhyHotBadge reasons={lead.whyHot} />
          </div>
        </div>
      )}

      {/* Action Buttons Row */}
      <div className="mt-6 pt-6 border-t border-border-subtle flex gap-3">
        <button className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-accent-primary to-accent-blue text-text-primary font-medium rounded-lg hover:opacity-90 transition-opacity">
          <Calendar className="w-4 h-4" />
          Book Meeting
        </button>
        <button className="flex items-center gap-2 px-4 py-2.5 bg-elevated border border-border-default text-secondary font-medium rounded-lg hover:bg-surface-hover hover:text-primary transition-colors">
          <Mail className="w-4 h-4" />
          Send Email
        </button>
        <button className="flex items-center gap-2 px-4 py-2.5 bg-elevated border border-border-default text-secondary font-medium rounded-lg hover:bg-surface-hover hover:text-primary transition-colors">
          <MessageSquare className="w-4 h-4" />
          Send SMS
        </button>
        <button className="flex items-center gap-2 px-4 py-2.5 bg-elevated border border-border-default text-secondary font-medium rounded-lg hover:bg-surface-hover hover:text-primary transition-colors">
          <Phone className="w-4 h-4" />
          Call
        </button>
        <button className="flex items-center justify-center w-10 h-10 bg-elevated border border-border-default text-muted rounded-lg hover:bg-surface-hover hover:text-secondary transition-colors ml-auto">
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
