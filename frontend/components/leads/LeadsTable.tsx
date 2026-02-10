'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Lead, Channel } from '@/data/mock-leads';
import { LeadTierBadge } from './LeadTierBadge';
import { WhyHotBadge } from './WhyHotBadge';

interface LeadsTableProps {
  leads: Lead[];
  onLeadClick: (lead: Lead) => void;
  className?: string;
}

// Channel Icons
const ChannelIcons: Record<Channel, React.ReactNode> = {
  email: (
    <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13" height="13">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  linkedin: (
    <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13" height="13">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  sms: (
    <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13" height="13">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  ),
  voice: (
    <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13" height="13">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    </svg>
  ),
  mail: (
    <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13" height="13">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
};

const channelBgColors: Record<Channel, string> = {
  email: 'bg-[rgba(124,58,237,0.15)]',
  linkedin: 'bg-[rgba(0,119,181,0.15)]',
  sms: 'bg-[rgba(20,184,166,0.15)]',
  voice: 'bg-[rgba(245,158,11,0.15)]',
  mail: 'bg-[rgba(236,72,153,0.15)]',
};

const avatarGradients: Record<string, string> = {
  hot: 'bg-gradient-to-br from-[#EF4444] to-[#F97316]',
  warm: 'bg-gradient-to-br from-[#F59E0B] to-[#FBBF24]',
  cool: 'bg-gradient-to-br from-[#3B82F6] to-[#60A5FA]',
  cold: 'bg-gradient-to-br from-[#6B7280] to-[#9CA3AF]',
};

const scoreColors: Record<string, string> = {
  hot: 'text-[#EF4444]',
  warm: 'text-[#F59E0B]',
  cool: 'text-[#3B82F6]',
  cold: 'text-[#6B7280]',
};

const rowHoverBorders: Record<string, string> = {
  hot: 'hover:shadow-[inset_4px_0_0_#EF4444]',
  warm: 'hover:shadow-[inset_4px_0_0_#F59E0B]',
  cool: 'hover:shadow-[inset_4px_0_0_#3B82F6]',
  cold: '',
};

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function SortIcon() {
  return (
    <svg className="w-3 h-3 opacity-0 group-hover:opacity-50" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
    </svg>
  );
}

export function LeadsTable({ leads, onLeadClick, className }: LeadsTableProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const toggleAll = () => {
    if (selectedIds.size === leads.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(leads.map((l) => l.id)));
    }
  };

  const toggleOne = (id: string) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  return (
    <div className={cn('bg-surface rounded-xl border border-subtle overflow-hidden', className)}>
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="w-10 bg-surface-hover px-5 py-3.5 text-left border-b border-subtle">
              <input
                type="checkbox"
                checked={selectedIds.size === leads.length && leads.length > 0}
                onChange={toggleAll}
                className="w-[18px] h-[18px] rounded border-2 border-default bg-base cursor-pointer appearance-none checked:bg-[#7C3AED] checked:border-[#7C3AED] transition-all"
              />
            </th>
            <th className="group bg-surface-hover px-5 py-3.5 text-left text-[11px] font-semibold text-muted uppercase tracking-wider border-b border-subtle cursor-pointer">
              <span className="flex items-center gap-1">Lead <SortIcon /></span>
            </th>
            <th className="group bg-surface-hover px-5 py-3.5 text-left text-[11px] font-semibold text-muted uppercase tracking-wider border-b border-subtle cursor-pointer">
              <span className="flex items-center gap-1">Company <SortIcon /></span>
            </th>
            <th className="group bg-surface-hover px-5 py-3.5 text-left text-[11px] font-semibold text-muted uppercase tracking-wider border-b border-subtle cursor-pointer">
              <span className="flex items-center gap-1">Score <SortIcon /></span>
            </th>
            <th className="bg-surface-hover px-5 py-3.5 text-left text-[11px] font-semibold text-muted uppercase tracking-wider border-b border-subtle">
              Why Hot?
            </th>
            <th className="bg-surface-hover px-5 py-3.5 text-left text-[11px] font-semibold text-muted uppercase tracking-wider border-b border-subtle">
              Channels
            </th>
            <th className="group bg-surface-hover px-5 py-3.5 text-left text-[11px] font-semibold text-muted uppercase tracking-wider border-b border-subtle cursor-pointer">
              <span className="flex items-center gap-1">Last Activity <SortIcon /></span>
            </th>
            <th className="w-[100px] bg-surface-hover px-5 py-3.5 text-left text-[11px] font-semibold text-muted uppercase tracking-wider border-b border-subtle">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => {
            const isRecent = lead.lastActivity.includes('min') || lead.lastActivity.includes('hour');
            
            return (
              <tr
                key={lead.id}
                onClick={() => onLeadClick(lead)}
                className={cn(
                  'cursor-pointer transition-all hover:bg-surface-hover',
                  rowHoverBorders[lead.tier]
                )}
              >
                {/* Checkbox */}
                <td className="px-5 py-4 border-b border-subtle align-middle">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(lead.id)}
                    onChange={() => toggleOne(lead.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-[18px] h-[18px] rounded border-2 border-default bg-base cursor-pointer appearance-none checked:bg-[#7C3AED] checked:border-[#7C3AED] transition-all"
                  />
                </td>

                {/* Lead Cell */}
                <td className="px-5 py-4 border-b border-subtle align-middle">
                  <div className="flex items-center gap-3.5">
                    <div
                      className={cn(
                        'w-11 h-11 rounded-[10px] flex items-center justify-center text-white font-semibold text-sm flex-shrink-0',
                        avatarGradients[lead.tier]
                      )}
                    >
                      {getInitials(lead.name)}
                    </div>
                    <div>
                      <div className="font-semibold text-sm text-primary">{lead.name}</div>
                      <div className="text-[13px] text-secondary">{lead.title}</div>
                    </div>
                  </div>
                </td>

                {/* Company Cell */}
                <td className="px-5 py-4 border-b border-subtle align-middle">
                  <div className="font-medium text-sm text-primary">{lead.company}</div>
                  <div className="text-xs text-muted">{lead.email}</div>
                </td>

                {/* Score Cell */}
                <td className="px-5 py-4 border-b border-subtle align-middle">
                  <div className="flex items-center gap-3">
                    <span className={cn('text-[22px] font-bold font-mono min-w-[36px]', scoreColors[lead.tier])}>
                      {lead.alsScore}
                    </span>
                    <LeadTierBadge tier={lead.tier} />
                  </div>
                </td>

                {/* Why Hot Cell */}
                <td className="px-5 py-4 border-b border-subtle align-middle">
                  <WhyHotBadge reasons={lead.whyHot} />
                </td>

                {/* Channels Cell */}
                <td className="px-5 py-4 border-b border-subtle align-middle">
                  <div className="flex gap-1.5">
                    {lead.channels.map((channel, idx) => (
                      <div
                        key={idx}
                        className={cn(
                          'w-7 h-7 rounded-md flex items-center justify-center relative',
                          channelBgColors[channel.type]
                        )}
                        title={channel.type}
                      >
                        {ChannelIcons[channel.type]}
                        {channel.active && (
                          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-[#22C55E] rounded-full border-2 border-surface" />
                        )}
                      </div>
                    ))}
                  </div>
                </td>

                {/* Activity Cell */}
                <td className="px-5 py-4 border-b border-subtle align-middle">
                  <span className={cn('text-[13px]', isRecent ? 'text-[#22C55E]' : 'text-muted')}>
                    {lead.lastActivity}
                  </span>
                </td>

                {/* Action Cell */}
                <td className="px-5 py-4 border-b border-subtle align-middle">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onLeadClick(lead);
                    }}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 text-[13px] font-medium text-[#7C3AED] bg-[rgba(124,58,237,0.1)] rounded-md hover:bg-[rgba(124,58,237,0.2)] transition-all"
                  >
                    Details →
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default LeadsTable;
