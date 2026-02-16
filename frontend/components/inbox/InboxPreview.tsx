/**
 * FILE: frontend/components/inbox/InboxPreview.tsx
 * PURPOSE: Preview panel for selected message
 */
import { InboxMessage } from '@/lib/mock/inbox-data';
import { Calendar, Phone, User, Archive, Send, Paperclip, Zap } from 'lucide-react';
import Link from 'next/link';

interface InboxPreviewProps {
  message: InboxMessage | null;
}

export function InboxPreview({ message }: InboxPreviewProps) {
  if (!message) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-10">
        <div className="w-20 h-20 glass-surface rounded-2xl flex items-center justify-center text-4xl mb-5">📬</div>
        <h3 className="text-lg font-semibold text-text-primary mb-2">Select a conversation</h3>
        <p className="text-sm text-text-muted max-w-xs">Choose a message from the list to see the full conversation and reply.</p>
      </div>
    );
  }

  const tierBg = message.tier === 'hot' ? 'from-amber to-amber-light' : message.tier === 'warm' ? 'from-amber-500 to-yellow-400' : 'from-amber to-text-secondary';

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <div className="glass-surface border-b border-border-subtle p-5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-13 h-13 rounded-xl bg-gradient-to-br ${tierBg} flex items-center justify-center text-text-primary font-bold text-lg`}>
            {message.initials}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">{message.name}</h2>
            <p className="text-sm text-text-muted">{message.title} at {message.company} • {message.email}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href={`/dashboard/inbox/${message.id}`} className="btn-primary flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold">
            <Calendar className="w-4 h-4" /> Schedule Meeting
          </Link>
          <button className="flex items-center gap-2 px-4 py-2.5 glass-surface border border-border-subtle rounded-lg text-sm text-text-primary hover:bg-bg-surface/5">
            <Phone className="w-4 h-4" /> Call
          </button>
          <button className="w-10 h-10 glass-surface border border-border-subtle rounded-lg flex items-center justify-center text-text-muted hover:text-text-primary">
            <User className="w-4 h-4" />
          </button>
          <button className="w-10 h-10 glass-surface border border-border-subtle rounded-lg flex items-center justify-center text-text-muted hover:text-text-primary">
            <Archive className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Thread Preview */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl">
          <div className="text-center text-xs text-text-muted py-4">Today</div>
          <div className="glass-surface border border-border-subtle rounded-xl p-5 border-l-[3px] border-l-status-success">
            <div className="flex items-center justify-between mb-3 pb-3 border-b border-border-subtle">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${tierBg} flex items-center justify-center text-text-primary font-semibold text-xs`}>{message.initials}</div>
                <span className="font-semibold text-sm">{message.name}</span>
              </div>
              <span className="text-xs text-text-muted">{message.timestamp}</span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">{message.preview}</p>
            <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 bg-status-success/10 rounded text-xs text-status-success">
              😊 Positive sentiment • Meeting intent detected
            </div>
          </div>
        </div>
      </div>
      
      {/* Composer */}
      <div className="glass-surface border-t border-border-subtle p-5">
        <div className="max-w-2xl">
          <textarea className="w-full p-4 bg-bg-base border border-border-subtle rounded-xl text-sm text-text-primary placeholder:text-text-muted resize-none h-24 focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20" placeholder="Write your reply..." />
          <div className="flex items-center justify-between mt-3">
            <div className="flex gap-2">
              <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-border-subtle rounded-md text-xs text-text-muted hover:text-text-secondary">
                <Paperclip className="w-3.5 h-3.5" /> Attach
              </button>
              <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-border-subtle rounded-md text-xs text-text-muted hover:text-text-secondary">
                <Calendar className="w-3.5 h-3.5" /> Schedule
              </button>
              <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-border-subtle rounded-md text-xs text-text-muted hover:text-text-secondary">
                <Zap className="w-3.5 h-3.5" /> AI Write
              </button>
            </div>
            <button className="btn-primary flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold">
              <Send className="w-4 h-4" /> Send Reply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
