/**
 * FILE: frontend/components/inbox/detail/LeadDetails.tsx
 * PURPOSE: Lead info pairs in sidebar
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { InboxMessage } from '@/lib/mock/inbox-data';
import { User, ExternalLink } from 'lucide-react';

interface DetailRow {
  label: string;
  value: string;
  isLink?: boolean;
  href?: string;
}

interface LeadDetailsProps {
  message: InboxMessage;
  additionalDetails?: DetailRow[];
}

export function LeadDetails({ message, additionalDetails = [] }: LeadDetailsProps) {
  const defaultDetails: DetailRow[] = [
    { label: 'Company', value: message.company },
    { label: 'Title', value: message.title },
    { label: 'Phone', value: message.phone || 'Not available' },
    { label: 'LinkedIn', value: 'View Profile →', isLink: true, href: '#' },
    { label: 'Campaign', value: message.campaignName },
  ];
  
  const details = [...defaultDetails, ...additionalDetails];
  
  return (
    <div className="bg-bg-surface rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-ink-3">
        <User className="w-3.5 h-3.5" />
        Lead Details
      </div>
      <div className="space-y-3">
        {details.map((detail) => (
          <div key={detail.label} className="flex justify-between items-start text-sm">
            <span className="text-ink-3">{detail.label}</span>
            {detail.isLink ? (
              <a
                href={detail.href}
                className="text-amber-500 hover:text-amber-400 font-medium flex items-center gap-1 transition-colors"
              >
                {detail.value}
              </a>
            ) : (
              <span className="text-ink font-medium text-right max-w-[60%]">{detail.value}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
