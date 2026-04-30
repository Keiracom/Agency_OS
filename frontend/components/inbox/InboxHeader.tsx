/**
 * FILE: frontend/components/inbox/InboxHeader.tsx
 * PURPOSE: Inbox header with title, unread count, action buttons
 */
import { Inbox, Filter, RefreshCw } from 'lucide-react';

interface InboxHeaderProps {
  unreadCount: number;
}

export function InboxHeader({ unreadCount }: InboxHeaderProps) {
  return (
    <header className="glass-surface border-b border-rule px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-ink font-serif flex items-center gap-3">
          <Inbox className="w-5 h-5 text-accent-primary" />
          Inbox Command Center
          <span className="bg-accent-primary/15 text-accent-primary px-2.5 py-1 rounded-full text-xs font-semibold">
            {unreadCount} unread
          </span>
        </h1>
      </div>
      <div className="flex gap-3">
        <button className="flex items-center gap-2 px-4 py-2 glass-surface border border-rule rounded-lg text-sm text-ink-2 hover:text-ink transition-colors">
          <Filter className="w-4 h-4" /> Filters
        </button>
        <button className="flex items-center gap-2 px-4 py-2 glass-surface border border-rule rounded-lg text-sm text-ink-2 hover:text-ink transition-colors">
          <RefreshCw className="w-4 h-4" /> Sync
        </button>
      </div>
    </header>
  );
}
