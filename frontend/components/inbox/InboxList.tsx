/**
 * FILE: frontend/components/inbox/InboxList.tsx
 * PURPOSE: Scrollable list of inbox messages
 */
'use client';
import { useState, useMemo } from 'react';
import { InboxMessage } from '@/lib/mock/inbox-data';
import { InboxFilters } from './InboxFilters';
import { InboxListItem } from './InboxListItem';

interface InboxListProps {
  messages: InboxMessage[];
  selectedId: string | null;
  onSelectMessage: (id: string) => void;
}

export function InboxList({ messages, selectedId, onSelectMessage }: InboxListProps) {
  const [activeFilter, setActiveFilter] = useState('all');
  
  // Derive counts from actual data
  const filterTabs = useMemo(() => [
    { id: 'all', label: 'All', count: messages.length },
    { id: 'unread', label: 'Unread', count: messages.filter((m) => m.unread).length },
    { id: 'positive', label: 'Positive', count: messages.filter((m) => m.sentiment === 'positive').length },
    { id: 'action', label: 'Action', count: messages.filter((m) => m.intent === 'meeting' || m.intent === 'interested').length },
  ], [messages]);
  
  const filteredMessages = messages.filter((m) => {
    if (activeFilter === 'unread') return m.unread;
    if (activeFilter === 'positive') return m.sentiment === 'positive';
    if (activeFilter === 'action') return m.intent === 'meeting' || m.intent === 'interested';
    return true;
  });

  return (
    <div className="w-[420px] glass-surface border-r border-border-subtle flex flex-col h-full">
      <InboxFilters activeFilter={activeFilter} onFilterChange={setActiveFilter} tabs={filterTabs} />
      <div className="flex-1 overflow-y-auto">
        {filteredMessages.map((message) => (
          <InboxListItem
            key={message.id}
            message={message}
            isActive={selectedId === message.id}
            onClick={() => onSelectMessage(message.id)}
          />
        ))}
      </div>
    </div>
  );
}
