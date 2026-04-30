/**
 * FILE: frontend/components/inbox/InboxListItem.tsx
 * PURPOSE: Single message item in inbox list
 */
import { InboxMessage, TierType } from '@/lib/mock/inbox-data';
import { IntentBadge } from './IntentBadge';
import { ChannelBadge } from './ChannelBadge';
import { SentimentBadge } from './SentimentBadge';
import { cn } from '@/lib/utils';

const tierColors: Record<TierType, string> = {
  hot: 'bg-gradient-to-br from-amber to-amber-light',
  warm: 'bg-gradient-to-br from-amber-500 to-yellow-400',
  cool: 'bg-gradient-to-br from-amber to-text-secondary',
};

const scoreColors: Record<TierType, string> = {
  hot: 'text-status-error',
  warm: 'text-status-warning',
  cool: 'text-ink-2',
};

const sentimentBorders: Record<string, string> = {
  positive: 'border-l-status-success',
  negative: 'border-l-status-error',
  neutral: 'border-l-text-muted',
};

interface InboxListItemProps {
  message: InboxMessage;
  isActive: boolean;
  onClick: () => void;
}

export function InboxListItem({ message, isActive, onClick }: InboxListItemProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'p-4 border-b border-rule border-l-[3px] cursor-pointer transition-colors',
        sentimentBorders[message.sentiment],
        isActive && 'bg-accent-primary/10 border-l-accent-primary',
        message.unread && !isActive && 'bg-accent-primary/5',
        !isActive && 'hover:bg-bg-panel/[0.03]'
      )}
    >
      <div className="flex gap-3 mb-2">
        <div className={cn('w-11 h-11 rounded-xl flex items-center justify-center text-ink font-semibold text-sm', tierColors[message.tier])}>
          {message.initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-0.5">
            <span className="font-semibold text-sm text-ink flex items-center gap-2">
              {message.name}
              {message.unread && <span className="w-2 h-2 rounded-full bg-accent-primary" />}
            </span>
            <div className="text-right">
              <div className={cn('text-xl font-bold font-mono', scoreColors[message.tier])}>{message.score}</div>
              <div className="text-[9px] text-ink-3 uppercase tracking-wide">Score</div>
            </div>
          </div>
          <div className="text-xs text-ink-3">{message.company} • {message.title}</div>
        </div>
      </div>
      <p className={cn('text-sm mb-2 line-clamp-2', message.unread ? 'text-ink' : 'text-ink-2')}>
        {message.preview}
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        <ChannelBadge channel={message.channel} />
        <IntentBadge intent={message.intent} />
        <SentimentBadge sentiment={message.sentiment} />
        <span className="text-xs text-ink-3 ml-auto">{message.timestamp}</span>
      </div>
    </div>
  );
}
