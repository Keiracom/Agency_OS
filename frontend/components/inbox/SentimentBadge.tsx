/**
 * FILE: frontend/components/inbox/SentimentBadge.tsx
 * PURPOSE: Sentiment indicator badge component
 */
import { SentimentType, sentimentEmoji } from '@/lib/mock/inbox-data';
import { cn } from '@/lib/utils';

const sentimentStyles: Record<SentimentType, string> = {
  positive: 'text-status-success',
  negative: 'text-status-error',
  neutral: 'text-text-muted',
};

const sentimentLabels: Record<SentimentType, string> = {
  positive: 'Positive',
  negative: 'Negative',
  neutral: 'Neutral',
};

export function SentimentBadge({ sentiment }: { sentiment: SentimentType }) {
  return (
    <span className={cn('flex items-center gap-1 text-[11px]', sentimentStyles[sentiment])}>
      {sentimentEmoji[sentiment]} {sentimentLabels[sentiment]}
    </span>
  );
}
