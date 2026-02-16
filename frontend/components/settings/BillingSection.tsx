'use client';

import { CreditCard, TrendingUp } from 'lucide-react';
import { BillingInfo } from '@/lib/mock/settings-data';

interface BillingSectionProps {
  billing: BillingInfo;
}

function UsageBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const pct = Math.round((used / limit) * 100);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between text-sm">
        <span className="text-text-secondary">{label}</span>
        <span className="text-text-muted">{used.toLocaleString()} / {limit.toLocaleString()}</span>
      </div>
      <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[#D4956A] to-[#E4A57A] rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function BillingSection({ billing }: BillingSectionProps) {
  return (
    <div className="glass-surface border border-border-subtle rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border-subtle flex items-center gap-2.5">
        <CreditCard className="w-5 h-5 text-[#D4956A]" />
        <span className="font-serif font-semibold text-text-primary">Billing & Usage</span>
      </div>

      <div className="p-6 space-y-6">
        {/* Current Plan */}
        <div className="flex items-center justify-between p-5 bg-bg-surface-hover rounded-xl border border-border-subtle">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#D4956A] to-[#C4854A] flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-text-primary" />
            </div>
            <div>
              <div className="text-lg font-semibold text-text-primary">{billing.plan} Plan</div>
              <div className="text-sm text-text-muted">
                {billing.price}/{billing.period} · Next billing: {billing.nextBilling}
              </div>
            </div>
          </div>
          <button className="px-5 py-2.5 text-sm font-medium rounded-lg bg-[rgba(212,149,106,0.15)] text-[#D4956A] hover:bg-[rgba(212,149,106,0.25)] transition-all">
            Upgrade Plan
          </button>
        </div>

        {/* Usage Stats */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-text-secondary">Current Usage</h4>
          <UsageBar used={billing.usage.leads.used} limit={billing.usage.leads.limit} label="Leads" />
          <UsageBar used={billing.usage.emails.used} limit={billing.usage.emails.limit} label="Emails Sent" />
          <UsageBar used={billing.usage.campaigns.used} limit={billing.usage.campaigns.limit} label="Active Campaigns" />
        </div>
      </div>
    </div>
  );
}

export default BillingSection;
