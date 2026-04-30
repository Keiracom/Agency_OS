'use client';

import { Users, Calendar, CheckCircle, BarChart3 } from 'lucide-react';
import { UsageData } from '@/data/mock-billing';

interface UsageMetersProps {
  usage: UsageData;
  resetDate: string;
}

export function UsageMeters({ usage, resetDate }: UsageMetersProps) {
  const leadsPercent = (usage.leads.current / usage.leads.max) * 100;
  const meetingsPercent = (usage.meetings.current / usage.meetings.targetMax) * 100;
  const clientsPercent = (usage.clients.current / usage.clients.targetMax) * 100;

  return (
    <div className="bg-bg-panel border border-rule rounded-2xl mb-6 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-ink font-semibold">
          <BarChart3 className="w-5 h-5 text-accent-primary" />
          Usage This Month
        </div>
        <span className="text-sm text-ink-3">Resets {resetDate}</span>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="grid grid-cols-3 gap-6">
          {/* Leads */}
          <div className="bg-bg-panel-hover rounded-xl p-5">
            <div className="flex justify-between items-start mb-4">
              <div className="text-sm font-semibold text-ink">Leads Contacted</div>
              <div className="w-9 h-9 rounded-lg bg-[rgba(124,58,237,0.15)] flex items-center justify-center">
                <Users className="w-[18px] h-[18px] text-accent-primary" />
              </div>
            </div>
            <div className="flex items-baseline gap-1 mb-3">
              <span className="text-[28px] font-extrabold font-mono text-ink">{usage.leads.current.toLocaleString()}</span>
              <span className="text-base text-ink-3 font-mono">/ {usage.leads.max.toLocaleString()}</span>
            </div>
            <div className="h-2 bg-panel rounded overflow-hidden mb-2">
              <div
                className="h-full rounded bg-gradient-to-r from-accent-primary to-accent-blue transition-all duration-500"
                style={{ width: `${leadsPercent}%` }}
              />
            </div>
            <div className="text-sm text-ink-3">
              <strong className="text-status-success">{(usage.leads.max - usage.leads.current).toLocaleString()}</strong> leads remaining
            </div>
          </div>

          {/* Meetings */}
          <div className="bg-bg-panel-hover rounded-xl p-5">
            <div className="flex justify-between items-start mb-4">
              <div className="text-sm font-semibold text-ink">Meetings Booked</div>
              <div className="w-9 h-9 rounded-lg bg-[rgba(20,184,166,0.15)] flex items-center justify-center">
                <Calendar className="w-[18px] h-[18px] text-accent-teal" />
              </div>
            </div>
            <div className="flex items-baseline gap-1 mb-3">
              <span className="text-[28px] font-extrabold font-mono text-ink">{usage.meetings.current}</span>
              <span className="text-base text-ink-3 font-mono">/ {usage.meetings.targetMin}-{usage.meetings.targetMax}</span>
            </div>
            <div className="h-2 bg-panel rounded overflow-hidden mb-2">
              <div
                className="h-full rounded bg-gradient-to-r from-accent-teal to-status-success transition-all duration-500"
                style={{ width: `${meetingsPercent}%` }}
              />
            </div>
            <div className="text-sm text-ink-3">
              <strong className="text-status-success">On track</strong> for target
            </div>
          </div>

          {/* Clients */}
          <div className="bg-bg-panel-hover rounded-xl p-5">
            <div className="flex justify-between items-start mb-4">
              <div className="text-sm font-semibold text-ink">New Clients Won</div>
              <div className="w-9 h-9 rounded-lg bg-[rgba(34,197,94,0.15)] flex items-center justify-center">
                <CheckCircle className="w-[18px] h-[18px] text-status-success" />
              </div>
            </div>
            <div className="flex items-baseline gap-1 mb-3">
              <span className="text-[28px] font-extrabold font-mono text-ink">{usage.clients.current}</span>
              <span className="text-base text-ink-3 font-mono">/ {usage.clients.targetMin}-{usage.clients.targetMax}</span>
            </div>
            <div className="h-2 bg-panel rounded overflow-hidden mb-2">
              <div
                className="h-full rounded bg-gradient-to-r from-accent-teal to-status-success transition-all duration-500"
                style={{ width: `${clientsPercent}%` }}
              />
            </div>
            <div className="text-sm text-ink-3">
              <strong className="text-status-success">Exceeding</strong> expectations
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UsageMeters;
