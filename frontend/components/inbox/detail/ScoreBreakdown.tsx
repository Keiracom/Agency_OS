/**
 * FILE: frontend/components/inbox/detail/ScoreBreakdown.tsx
 * PURPOSE: Score factors breakdown
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { ScoreFactor } from '@/lib/mock/inbox-data';
import { BarChart2 } from 'lucide-react';

interface ScoreBreakdownProps {
  score: number;
  factors: ScoreFactor[];
}

export function ScoreBreakdown({ score, factors }: ScoreBreakdownProps) {
  return (
    <div className="bg-bg-surface rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-ink-3">
        <BarChart2 className="w-3.5 h-3.5" />
        Why {score} Score
      </div>
      <div className="space-y-2.5">
        {factors.map((factor, index) => (
          <div key={index} className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-panel-dark flex items-center justify-center text-xs flex-shrink-0">
              {factor.icon}
            </div>
            <span className="flex-1 text-xs text-ink-2">{factor.label}</span>
            <span className="text-xs font-semibold font-mono text-amber">+{factor.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
