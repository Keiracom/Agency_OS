'use client';

import { Mail, Briefcase, MessageSquare, Phone, Calendar, Cloud } from 'lucide-react';
import { Integration, IntegrationStatus } from '@/data/mock-settings';

interface IntegrationsGridProps {
  integrations: Integration[];
}

const iconMap = {
  email: Mail,
  linkedin: Briefcase,
  sms: MessageSquare,
  voice: Phone,
  calendar: Calendar,
  crm: Cloud,
};

const iconBgMap = {
  email: 'bg-[rgba(124,58,237,0.15)]',
  linkedin: 'bg-[rgba(59,130,246,0.15)]',
  sms: 'bg-[rgba(20,184,166,0.15)]',
  voice: 'bg-[rgba(245,158,11,0.15)]',
  calendar: 'bg-[rgba(236,72,153,0.15)]',
  crm: 'bg-[rgba(99,102,241,0.15)]',
};

const statusConfig: Record<IntegrationStatus, { dot: string; text: string; label: string }> = {
  connected: {
    dot: 'bg-status-success',
    text: 'text-status-success',
    label: 'Connected',
  },
  pending: {
    dot: 'bg-status-warning',
    text: 'text-status-warning',
    label: 'Pending Setup',
  },
  disconnected: {
    dot: 'bg-text-muted',
    text: 'text-text-muted',
    label: 'Not Connected',
  },
};

const buttonConfig: Record<IntegrationStatus, { bg: string; text: string; label: string }> = {
  connected: {
    bg: 'bg-[rgba(239,68,68,0.1)] hover:bg-[rgba(239,68,68,0.2)]',
    text: 'text-status-error',
    label: 'Disconnect',
  },
  pending: {
    bg: 'bg-[rgba(245,158,11,0.15)] hover:bg-[rgba(245,158,11,0.25)]',
    text: 'text-status-warning',
    label: 'Complete Setup',
  },
  disconnected: {
    bg: 'bg-[rgba(124,58,237,0.15)] hover:bg-[rgba(124,58,237,0.25)]',
    text: 'text-accent-primary',
    label: 'Connect',
  },
};

export function IntegrationsGrid({ integrations }: IntegrationsGridProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-text-primary font-semibold">
          <svg className="w-5 h-5 text-accent-primary" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          Connected Services
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="grid grid-cols-2 gap-4">
          {integrations.map((integration) => {
            const Icon = iconMap[integration.icon];
            const status = statusConfig[integration.status];
            const button = buttonConfig[integration.status];

            return (
              <div
                key={integration.id}
                className="flex items-center justify-between p-5 bg-bg-surface-hover border border-border-subtle rounded-xl transition-all hover:border-border-default"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${iconBgMap[integration.icon]}`}>
                    <Icon className="w-6 h-6 text-text-secondary" />
                  </div>
                  <div>
                    <div className="text-[15px] font-semibold text-text-primary">{integration.name}</div>
                    <div className={`flex items-center gap-1.5 text-sm mt-1 ${status.text}`}>
                      <span className={`w-2 h-2 rounded-full ${status.dot}`} />
                      {status.label}
                    </div>
                  </div>
                </div>
                <button
                  className={`px-4 py-2 text-sm font-medium rounded-md border-none cursor-pointer transition-all ${button.bg} ${button.text}`}
                >
                  {button.label}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default IntegrationsGrid;
