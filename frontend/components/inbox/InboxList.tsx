/**
 * FILE: frontend/components/inbox/InboxList.tsx
 * PURPOSE: Scrollable list of inbox messages
 */
'use client';
import { useState } from 'react';
import { InboxMessage } from '@/lib/mock/inbox-data';
import { InboxFilters } from './InboxFilters';
import { InboxListItem } from './InboxListItem';

interface InboxListProps {
  messages: InboxMessage[];
  selectedId: string | null;
  onSelectMessage: (id: string) => void;
}

const filterTabs = [
  { id: 'all', label: 'All', count: 23 },
  { id: 'unread', label: 'Unread', count: 7 },
  { id: 'positive', label: 'Positive', count: 12 },
  { id: 'action', label: 'Action' },
];

export function InboxList({ messages, selectedId, onSelectMessage }: InboxListProps) {
  const [activeFilter, setActiveFilter] = useState('all');
  
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
