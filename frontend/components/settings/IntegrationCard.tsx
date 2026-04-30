'use client';

import { Mail, Briefcase, MessageSquare, Phone, Calendar, Cloud, LucideIcon } from 'lucide-react';
import { Integration, IntegrationStatus } from '@/lib/mock/settings-data';

interface IntegrationCardProps {
  integration: Integration;
  onAction?: (id: string, status: IntegrationStatus) => void;
}

const iconMap: Record<string, LucideIcon> = {
  email: Mail, linkedin: Briefcase, sms: MessageSquare,
  voice: Phone, calendar: Calendar, crm: Cloud,
};

const iconBgMap: Record<string, string> = {
  email: 'bg-[rgba(212,149,106,0.15)]',
  linkedin: 'bg-[rgba(59,130,246,0.15)]',
  sms: 'bg-[rgba(20,184,166,0.15)]',
  voice: 'bg-[rgba(245,158,11,0.15)]',
  calendar: 'bg-[rgba(236,72,153,0.15)]',
  crm: 'bg-[rgba(99,102,241,0.15)]',
};

const statusStyles: Record<IntegrationStatus, { dot: string; text: string; label: string }> = {
  connected: { dot: 'bg-status-success', text: 'text-status-success', label: 'Connected' },
  pending: { dot: 'bg-status-warning', text: 'text-status-warning', label: 'Pending Setup' },
  disconnected: { dot: 'bg-text-muted', text: 'text-ink-3', label: 'Not Connected' },
};

const buttonStyles: Record<IntegrationStatus, { bg: string; text: string; label: string }> = {
  connected: { bg: 'bg-[rgba(239,68,68,0.1)] hover:bg-[rgba(239,68,68,0.2)]', text: 'text-status-error', label: 'Disconnect' },
  pending: { bg: 'bg-[rgba(245,158,11,0.15)] hover:bg-[rgba(245,158,11,0.25)]', text: 'text-status-warning', label: 'Complete Setup' },
  disconnected: { bg: 'bg-[rgba(212,149,106,0.15)] hover:bg-[rgba(212,149,106,0.25)]', text: 'text-[#D4956A]', label: 'Connect' },
};

export function IntegrationCard({ integration, onAction }: IntegrationCardProps) {
  const Icon = iconMap[integration.icon];
  const status = statusStyles[integration.status];
  const button = buttonStyles[integration.status];

  return (
    <div className="flex items-center justify-between p-5 bg-bg-panel-hover border border-rule rounded-xl transition-all hover:border-rule-strong">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${iconBgMap[integration.icon]}`}>
          <Icon className="w-6 h-6 text-ink-2" />
        </div>
        <div>
          <div className="text-[15px] font-semibold text-ink">{integration.name}</div>
          <div className={`flex items-center gap-1.5 text-sm mt-1 ${status.text}`}>
            <span className={`w-2 h-2 rounded-full ${status.dot}`} />
            {status.label}
          </div>
        </div>
      </div>
      <button
        onClick={() => onAction?.(integration.id, integration.status)}
        className={`px-4 py-2 text-sm font-medium rounded-md border-none cursor-pointer transition-all ${button.bg} ${button.text}`}
      >
        {button.label}
      </button>
    </div>
  );
}

export default IntegrationCard;
