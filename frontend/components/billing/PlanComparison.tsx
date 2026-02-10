'use client';

import { TrendingUp, Check } from 'lucide-react';
import { AvailablePlan } from '@/data/mock-billing';

interface PlanComparisonProps {
  plans: AvailablePlan[];
}

export function PlanComparison({ plans }: PlanComparisonProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-text-primary font-semibold">
          <TrendingUp className="w-5 h-5 text-accent-primary" />
          Available Plans
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-3 gap-5 p-6">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`relative rounded-2xl p-7 text-center transition-all ${
              plan.isCurrent
                ? 'bg-bg-elevated border-2 border-accent-teal'
                : plan.isPopular
                ? 'bg-gradient-to-b from-[rgba(124,58,237,0.08)] to-bg-surface-hover border-2 border-accent-primary'
                : 'bg-bg-surface-hover border-2 border-border-subtle hover:border-border-default'
            }`}
          >
            {/* Top gradient for popular */}
            {plan.isPopular && (
              <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent-primary to-accent-blue rounded-t-2xl" />
            )}

            {/* Badge */}
            {(plan.isCurrent || plan.isPopular) && (
              <div
                className={`inline-block px-3.5 py-[5px] text-[11px] font-bold rounded-full uppercase tracking-wider mb-4 ${
                  plan.isCurrent
                    ? 'bg-[rgba(20,184,166,0.15)] text-accent-teal border border-accent-teal'
                    : 'bg-accent-primary text-white'
                }`}
              >
                {plan.isCurrent ? 'Current Plan' : 'Recommended'}
              </div>
            )}

            <div className="text-[22px] font-bold text-text-primary mb-2">{plan.name}</div>
            <div className="text-sm text-text-muted mb-4">{plan.tagline}</div>
            <div className="text-[40px] font-extrabold font-mono text-text-primary mb-1">
              ${plan.price.toLocaleString()}
              <span className="text-sm font-normal text-text-muted">/mo</span>
            </div>

            {/* Outcomes */}
            <div className="flex justify-center gap-6 my-5 py-4 bg-bg-surface rounded-[10px]">
              <div className="text-center">
                <div className="text-xl font-bold font-mono text-text-primary">
                  {plan.meetingsMin}-{plan.meetingsMax}
                </div>
                <div className="text-[11px] text-text-muted uppercase tracking-wide">Meetings/mo</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold font-mono text-text-primary">
                  {plan.clientsMin}-{plan.clientsMax}
                </div>
                <div className="text-[11px] text-text-muted uppercase tracking-wide">New Clients</div>
              </div>
            </div>

            {/* Features */}
            <ul className="list-none my-5 text-left">
              {plan.features.map((feature, idx) => (
                <li key={idx} className="flex items-start gap-2.5 text-sm text-text-secondary py-2">
                  <Check className="w-4 h-4 text-accent-teal flex-shrink-0 mt-0.5" />
                  {feature}
                </li>
              ))}
            </ul>

            {/* Button */}
            <button
              className={`w-full py-3.5 text-sm font-semibold rounded-[10px] border-none cursor-pointer transition-all ${
                plan.isCurrent
                  ? 'bg-[rgba(20,184,166,0.15)] text-accent-teal border border-accent-teal cursor-default'
                  : plan.isPopular
                  ? 'bg-accent-primary text-white hover:bg-accent-primary-hover hover:-translate-y-0.5 hover:shadow-[0_8px_20px_rgba(124,58,237,0.3)]'
                  : 'bg-bg-surface text-text-muted border border-border-default hover:bg-bg-elevated hover:text-text-secondary'
              }`}
              disabled={plan.isCurrent}
            >
              {plan.isCurrent
                ? 'Current Plan'
                : plan.isPopular
                ? `Upgrade to ${plan.name}`
                : 'Downgrade'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default PlanComparison;
