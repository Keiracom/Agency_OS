/**
 * FILE: frontend/components/inbox/detail/EmailMessage.tsx
 * PURPOSE: Email card (sent/received variants)
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { ThreadMessage, SentimentType, IntentType, sentimentEmoji, intentLabels } from '@/lib/mock/inbox-data';
import { Mail, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EmailMessageProps {
  message: ThreadMessage;
}

export function EmailMessage({ message }: EmailMessageProps) {
  const isSent = message.sender === 'you';
  
  return (
    <div
      className={cn(
        'max-w-[720px] rounded-2xl p-6 mb-5',
        isSent
          ? 'ml-auto bg-amber-500/8 border border-amber-500/20'
          : 'bg-surface-dark border border-border-subtle border-l-[3px] border-l-green-500'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-border-subtle">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center font-semibold text-sm text-white',
              isSent
                ? 'bg-gradient-to-br from-amber-500 to-orange-400'
                : 'bg-gradient-to-br from-red-500 to-orange-500'
            )}
          >
            {isSent ? 'Y' : message.senderName.split(' ').map(n => n[0]).join('')}
          </div>
          <div>
            <div className="font-semibold text-sm text-text-primary">{message.senderName}</div>
            <div className="text-xs text-text-muted">{message.senderEmail}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-text-muted">{message.timestamp}</div>
          <div className="flex items-center gap-1 text-[11px] text-amber-500 justify-end mt-1">
            <Mail className="w-3.5 h-3.5" />
            Email
          </div>
        </div>
      </div>
      
      {/* Subject */}
      {message.subject && (
        <h3 className="font-semibold text-[15px] text-text-primary mb-4">{message.subject}</h3>
      )}
      
      {/* Body */}
      <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
        {message.body}
      </div>
      
      {/* Sentiment Tag (for received messages) */}
      {!isSent && message.sentiment && (
        <div className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 bg-green-500/10 rounded-md text-xs font-medium text-green-400">
          {sentimentEmoji[message.sentiment]} {message.sentiment.charAt(0).toUpperCase() + message.sentiment.slice(1)}
          {message.intent === 'meeting' && (
            <>
              <span className="text-text-muted">•</span>
              <Calendar className="w-3.5 h-3.5" />
              Meeting Intent Detected
            </>
          )}
        </div>
      )}
    </div>
  );
}
