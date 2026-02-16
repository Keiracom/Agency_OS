'use client';

import { Zap, TrendingUp, CreditCard, Users, Calendar, User, Lightbulb, Check } from 'lucide-react';
import { CurrentPlan, PlanMetrics } from '@/data/mock-billing';

interface PlanHeroCardProps {
  plan: CurrentPlan;
  metrics: PlanMetrics;
}

export function PlanHeroCard({ plan, metrics }: PlanHeroCardProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-2xl p-8 mb-6 relative overflow-hidden">
      {/* Top gradient border */}
      <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent-primary to-accent-blue" />

      {/* Header Grid */}
      <div className="grid grid-cols-[1fr_auto] gap-8 items-start">
        <div>
          <h2 className="text-2xl font-bold text-text-primary mb-1 flex items-center gap-3">
            <Zap className="w-7 h-7 text-accent-primary" />
            {plan.name} Plan
          </h2>
          <p className="text-sm text-text-muted">
            Your subscription renews on{' '}
            <strong className="text-text-primary">{plan.renewalDate}</strong>
          </p>
          <div className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[rgba(34,197,94,0.15)] text-status-success text-xs font-semibold rounded-full mt-3">
            <Check className="w-3.5 h-3.5" />
            Active
          </div>
        </div>
        <div className="text-right">
          <div className="text-5xl font-extrabold font-mono text-text-primary leading-none">
            {plan.currency}{plan.price.toLocaleString()}
          </div>
          <div className="text-sm text-text-muted mt-1">per {plan.period}</div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4 my-7 py-6 border-t border-b border-border-subtle">
        <div className="flex items-center gap-3 px-[18px] py-3.5 bg-bg-surface-hover rounded-[10px]">
          <div className="w-10 h-10 bg-[rgba(124,58,237,0.15)] rounded-[10px] flex items-center justify-center">
            <Users className="w-5 h-5 text-accent-primary" />
          </div>
          <div className="text-sm text-text-secondary">
            <strong className="block font-bold text-text-primary font-mono text-lg">{metrics.leads.toLocaleString()}</strong>
            Leads per month
          </div>
        </div>
        <div className="flex items-center gap-3 px-[18px] py-3.5 bg-bg-surface-hover rounded-[10px]">
          <div className="w-10 h-10 bg-[rgba(20,184,166,0.15)] rounded-[10px] flex items-center justify-center">
            <Calendar className="w-5 h-5 text-accent-teal" />
          </div>
          <div className="text-sm text-text-secondary">
            <strong className="block font-bold text-text-primary font-mono text-lg">{metrics.meetingsMin}-{metrics.meetingsMax}</strong>
            Meetings per month
          </div>
        </div>
        <div className="flex items-center gap-3 px-[18px] py-3.5 bg-bg-surface-hover rounded-[10px]">
          <div className="w-10 h-10 bg-[rgba(59,130,246,0.15)] rounded-[10px] flex items-center justify-center">
            <User className="w-5 h-5 text-accent-blue" />
          </div>
          <div className="text-sm text-text-secondary">
            <strong className="block font-bold text-text-primary font-mono text-lg">{metrics.clientsMin}-{metrics.clientsMax}</strong>
            New clients per month
          </div>
        </div>
        <div className="flex items-center gap-3 px-[18px] py-3.5 bg-bg-surface-hover rounded-[10px]">
          <div className="w-10 h-10 bg-[rgba(245,158,11,0.15)] rounded-[10px] flex items-center justify-center">
            <Lightbulb className="w-5 h-5 text-status-warning" />
          </div>
          <div className="text-sm text-text-secondary">
            <strong className="block font-bold text-text-primary font-mono text-lg">{metrics.channels}-Channel</strong>
            Outreach system
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-accent-primary text-text-primary hover:bg-accent-primary-hover hover:-translate-y-px transition-all">
          <TrendingUp className="w-4 h-4" />
          Upgrade Plan
        </button>
        <button className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-transparent text-text-secondary border border-border-default hover:bg-bg-surface-hover hover:text-text-primary transition-all">
          <CreditCard className="w-4 h-4" />
          Update Payment
        </button>
        <button className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-transparent text-text-secondary border border-border-default hover:bg-bg-surface-hover hover:text-text-primary transition-all">
          Cancel Subscription
        </button>
      </div>
    </div>
  );
}

export default PlanHeroCard;
