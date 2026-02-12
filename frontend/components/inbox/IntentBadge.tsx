/**
 * FILE: frontend/components/inbox/IntentBadge.tsx
 * PURPOSE: Intent classification badge component
 */
import { IntentType, intentLabels } from '@/lib/mock/inbox-data';
import { cn } from '@/lib/utils';

const intentStyles: Record<IntentType, string> = {
  meeting: 'bg-status-success/15 text-status-success',
  interested: 'bg-accent-primary/15 text-accent-primary',
  question: 'bg-blue-500/15 text-blue-400',
  objection: 'bg-status-error/15 text-status-error',
  later: 'bg-status-warning/15 text-status-warning',
};

export function IntentBadge({ intent }: { intent: IntentType }) {
  return (
    <span className={cn(
      'px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide',
      intentStyles[intent]
    )}>
      {intentLabels[intent]}
    </span>
  );
}
