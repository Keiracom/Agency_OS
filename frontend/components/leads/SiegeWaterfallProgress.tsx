'use client';

import { SiegeWaterfallTier } from '@/data/mock-lead-detail';
import { CheckCircle2, Loader2, Circle, Database } from 'lucide-react';

interface SiegeWaterfallProgressProps {
  tiers: SiegeWaterfallTier[];
}

const statusIcons: Record<SiegeWaterfallTier['status'], React.ReactNode> = {
  complete: <CheckCircle2 className="w-5 h-5 text-status-success" />,
  'in-progress': <Loader2 className="w-5 h-5 text-accent-primary animate-spin" />,
  pending: <Circle className="w-5 h-5 text-muted" />,
};

const statusLineColors: Record<SiegeWaterfallTier['status'], string> = {
  complete: 'bg-status-success',
  'in-progress': 'bg-accent-primary',
  pending: 'bg-border-default',
};

const statusTextColors: Record<SiegeWaterfallTier['status'], string> = {
  complete: 'text-primary',
  'in-progress': 'text-primary',
  pending: 'text-muted',
};

export function SiegeWaterfallProgress({ tiers }: SiegeWaterfallProgressProps) {
  return (
    <div className="bg-surface border border-border-subtle rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Database className="w-4 h-4 text-accent-primary" />
          <span className="text-sm font-semibold text-primary">Siege Waterfall</span>
        </div>
        <span className="text-xs text-muted">Enrichment progress</span>
      </div>

      <div className="p-6">
        <div className="relative">
          {tiers.map((tier, index) => {
            const isLast = index === tiers.length - 1;

            return (
              <div key={tier.tier} className="relative flex gap-4">
                {/* Vertical line connector */}
                {!isLast && (
                  <div
                    className={`absolute left-[9px] top-6 w-0.5 h-[calc(100%-0.5rem)] ${statusLineColors[tier.status]}`}
                  />
                )}

                {/* Status icon */}
                <div className="relative z-10 shrink-0">{statusIcons[tier.status]}</div>

                {/* Content */}
                <div className={`flex-1 pb-6 ${isLast ? 'pb-0' : ''}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className={`text-sm font-medium ${statusTextColors[tier.status]}`}>
                        Tier {tier.tier}: {tier.name}
                      </div>
                      {tier.source && (
                        <div className="text-xs text-muted mt-0.5">
                          Source: <span className="text-secondary">{tier.source}</span>
                        </div>
                      )}
                    </div>
                    {tier.timestamp && (
                      <span
                        className={`text-xs font-mono ${
                          tier.status === 'in-progress' ? 'text-accent-primary' : 'text-muted'
                        }`}
                      >
                        {tier.timestamp}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Progress summary */}
        <div className="mt-4 pt-4 border-t border-border-subtle">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted">
              {tiers.filter((t) => t.status === 'complete').length} of {tiers.length} tiers complete
            </span>
            <div className="flex gap-1">
              {tiers.map((tier) => (
                <div
                  key={tier.tier}
                  className={`w-8 h-1.5 rounded-full ${
                    tier.status === 'complete'
                      ? 'bg-status-success'
                      : tier.status === 'in-progress'
                        ? 'bg-accent-primary'
                        : 'bg-border-default'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
