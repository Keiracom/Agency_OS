'use client';

import { SequenceStep as StepType, channelEmoji } from '@/data/mock-campaigns';

interface Props {
  step: StepType;
}

const stepStyles = {
  completed: 'bg-emerald-50',
  active: 'bg-violet-100',
  upcoming: 'bg-slate-50 border border-dashed border-slate-300',
};

export function SequenceStep({ step }: Props) {
  return (
    <div className={`flex-1 p-3 rounded-lg text-center ${stepStyles[step.status]}`}>
      <div className="text-[10px] text-text-muted uppercase">Day {step.day}</div>
      <div className="text-base my-1">{channelEmoji[step.channel]}</div>
      <div className="text-[11px] font-semibold text-text-muted">{step.label}</div>
      <div className="text-[10px] text-text-muted mt-1">{step.stats}</div>
    </div>
  );
}
