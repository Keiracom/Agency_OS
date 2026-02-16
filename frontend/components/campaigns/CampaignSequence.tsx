'use client';

import { SequenceStep as StepType } from '@/data/mock-campaigns';
import { SequenceStep } from './SequenceStep';

interface Props {
  sequence: StepType[];
}

export function CampaignSequence({ sequence }: Props) {
  return (
    <div className="mb-5">
      <div className="text-[13px] text-text-muted uppercase tracking-wide font-semibold mb-3">
        Sequence Progress
      </div>
      <div className="flex items-center gap-2">
        {sequence.map((step, idx) => (
          <div key={idx} className="contents">
            <SequenceStep step={step} />
            {idx < sequence.length - 1 && (
              <span className="text-slate-300 text-lg">→</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
