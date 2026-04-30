/**
 * FILE: frontend/components/inbox/detail/SMSThread.tsx
 * PURPOSE: SMS bubbles conversation
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { ThreadMessage, SentimentType, IntentType } from '@/lib/mock/inbox-data';
import { MessageCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SMSThreadProps {
  messages: ThreadMessage[];
}

function SMSBubble({ message }: { message: ThreadMessage }) {
  const isSent = message.sender === 'you';
  
  const intentLabel = message.intent === 'meeting' ? 'Meeting Request' : message.sentiment === 'positive' ? 'Positive' : null;
  
  return (
    <div className={cn('max-w-[85%] mb-2', isSent && 'ml-auto')}>
      <div
        className={cn(
          'px-4 py-3 text-sm leading-relaxed',
          isSent
            ? 'bg-amber-600 text-ink rounded-2xl rounded-br-sm'
            : 'bg-panel-dark border border-rule text-ink rounded-2xl rounded-bl-sm'
        )}
      >
        {message.body}
      </div>
      <div className={cn(
        'flex items-center gap-2 mt-1.5 text-[11px]',
        isSent ? 'justify-end text-amber-400/70' : 'text-ink-3'
      )}>
        {!isSent && intentLabel && (
          <span className="px-1.5 py-0.5 bg-amber/15 text-amber rounded text-[10px] font-semibold uppercase">
            {intentLabel}
          </span>
        )}
        {message.timestamp}
        {isSent && <span>• Delivered</span>}
      </div>
    </div>
  );
}

export function SMSThread({ messages }: SMSThreadProps) {
  return (
    <div className="max-w-[500px] mb-6">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-rule">
        <div className="w-8 h-8 rounded-lg bg-amber-glow flex items-center justify-center">
          <MessageCircle className="w-4 h-4 text-amber" />
        </div>
        <span className="text-sm font-semibold text-amber">SMS Conversation</span>
      </div>
      
      {/* Bubbles */}
      <div className="space-y-0">
        {messages.map((msg) => (
          <SMSBubble key={msg.id} message={msg} />
        ))}
      </div>
    </div>
  );
}
