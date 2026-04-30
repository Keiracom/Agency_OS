/**
 * FILE: frontend/components/inbox/InboxPreview.tsx
 * PURPOSE: Preview panel for selected message
 */
import { InboxMessage } from '@/lib/mock/inbox-data';
import { Calendar, Phone, User, Archive, Send, Paperclip, Zap, Mail } from 'lucide-react';
import Link from 'next/link';

interface InboxPreviewProps {
  message: InboxMessage | null;
}

export function InboxPreview({ message }: InboxPreviewProps) {
  if (!message) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-10">
        <div className="w-20 h-20 glass-surface rounded-2xl flex items-center justify-center text-4xl mb-5"><Mail className="w-10 h-10 text-ink-3" /></div>
        <h3 className="text-lg font-semibold text-ink mb-2">Select a conversation</h3>
        <p className="text-sm text-ink-3 max-w-xs">Choose a message from the list to see the full conversation and reply.</p>
      </div>
    );
  }

  const tierBg = message.tier === 'hot' ? 'from-amber to-amber-light' : message.tier === 'warm' ? 'from-amber-500 to-yellow-400' : 'from-amber to-text-secondary';

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <div className="glass-surface border-b border-rule p-5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-13 h-13 rounded-xl bg-gradient-to-br ${tierBg} flex items-center justify-center text-ink font-bold text-lg`}>
            {message.initials}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-ink">{message.name}</h2>
            <p className="text-sm text-ink-3">{message.title} at {message.company} • {message.email}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href={`/dashboard/inbox/${message.id}`} className="btn-primary flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold">
            <Calendar className="w-4 h-4" /> Schedule Meeting
          </Link>
          <button className="flex items-center gap-2 px-4 py-2.5 glass-surface border border-rule rounded-lg text-sm text-ink hover:bg-bg-panel/5">
            <Phone className="w-4 h-4" /> Call
          </button>
          <button className="w-10 h-10 glass-surface border border-rule rounded-lg flex items-center justify-center text-ink-3 hover:text-ink">
            <User className="w-4 h-4" />
          </button>
          <button className="w-10 h-10 glass-surface border border-rule rounded-lg flex items-center justify-center text-ink-3 hover:text-ink">
            <Archive className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Thread Preview */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl">
          <div className="text-center text-xs text-ink-3 py-4">Today</div>
          <div className="glass-surface border border-rule rounded-xl p-5 border-l-[3px] border-l-status-success">
            <div className="flex items-center justify-between mb-3 pb-3 border-b border-rule">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${tierBg} flex items-center justify-center text-ink font-semibold text-xs`}>{message.initials}</div>
                <span className="font-semibold text-sm">{message.name}</span>
              </div>
              <span className="text-xs text-ink-3">{message.timestamp}</span>
            </div>
            <p className="text-sm text-ink-2 leading-relaxed">{message.preview}</p>
            <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 bg-status-success/10 rounded text-xs text-status-success">
              Positive sentiment • Meeting intent detected
            </div>
          </div>
        </div>
      </div>
      
      {/* Composer */}
      <div className="glass-surface border-t border-rule p-5">
        <div className="max-w-2xl">
          <textarea className="w-full p-4 bg-panel border border-rule rounded-xl text-sm text-ink placeholder:text-ink-3 resize-none h-24 focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20" placeholder="Write your reply..." />
          <div className="flex items-center justify-between mt-3">
            <div className="flex gap-2">
              <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-rule rounded-md text-xs text-ink-3 hover:text-ink-2">
                <Paperclip className="w-3.5 h-3.5" /> Attach
              </button>
              <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-rule rounded-md text-xs text-ink-3 hover:text-ink-2">
                <Calendar className="w-3.5 h-3.5" /> Schedule
              </button>
              <button className="flex items-center gap-1.5 px-3 py-2 glass-surface border border-rule rounded-md text-xs text-ink-3 hover:text-ink-2">
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
