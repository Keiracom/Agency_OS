/**
 * FILE: frontend/components/inbox/detail/ReplyComposer.tsx
 * PURPOSE: Composer textarea + send button
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { useState } from 'react';
import { Paperclip, Calendar, Zap, Send } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ReplyComposerProps {
  recipientEmail: string;
  initialValue?: string;
  onSend?: (message: string) => void;
}

export function ReplyComposer({ recipientEmail, initialValue = '', onSend }: ReplyComposerProps) {
  const [message, setMessage] = useState(initialValue);
  
  const handleSend = () => {
    if (message.trim() && onSend) {
      onSend(message);
      setMessage('');
    }
  };
  
  return (
    <div className="bg-surface-dark border-t border-border-subtle px-8 py-5">
      <div className="max-w-[720px]">
        {/* To field */}
        <div className="flex items-center gap-2 mb-3 text-sm">
          <span className="text-text-muted">To:</span>
          <span className="text-text-primary font-medium">{recipientEmail}</span>
        </div>
        
        {/* Textarea */}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Write your reply..."
          className={cn(
            'w-full p-4 bg-bg-base border border-border-subtle rounded-xl',
            'text-sm text-text-primary placeholder:text-text-muted',
            'resize-none min-h-[120px]',
            'focus:outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20',
            'transition-colors'
          )}
        />
        
        {/* Footer */}
        <div className="flex items-center justify-between mt-3">
          {/* Tools */}
          <div className="flex gap-2">
            <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-border-subtle rounded-md text-xs text-text-muted hover:text-text-secondary hover:bg-white/[0.05] transition-colors">
              <Paperclip className="w-3.5 h-3.5" />
              Attach
            </button>
            <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-border-subtle rounded-md text-xs text-text-muted hover:text-text-secondary hover:bg-white/[0.05] transition-colors">
              <Calendar className="w-3.5 h-3.5" />
              Schedule
            </button>
            <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-border-subtle rounded-md text-xs text-text-muted hover:text-text-secondary hover:bg-white/[0.05] transition-colors">
              <Zap className="w-3.5 h-3.5" />
              AI Write
            </button>
          </div>
          
          {/* Send */}
          <button
            onClick={handleSend}
            disabled={!message.trim()}
            className={cn(
              'flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-semibold transition-all',
              message.trim()
                ? 'bg-amber-600 hover:bg-amber-500 text-white hover:-translate-y-0.5'
                : 'bg-amber-600/50 text-white/50 cursor-not-allowed'
            )}
          >
            <Send className="w-4 h-4" />
            Send Reply
          </button>
        </div>
      </div>
    </div>
  );
}
