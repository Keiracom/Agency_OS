'use client';

import { useState } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { InboxFilters } from '@/components/inbox/InboxFilters';
import { ConversationList } from '@/components/inbox/ConversationList';
import { ConversationDetail } from '@/components/inbox/ConversationDetail';
import { mockConversations, InboxFilter, Conversation } from '@/data/mock-inbox';

const FILTER_TABS = [
  { id: 'all', label: 'All' },
  { id: 'needs-reply', label: 'Needs Reply' },
  { id: 'meetings', label: 'Meetings' },
];

export default function RepliesPage() {
  const [filter, setFilter] = useState<InboxFilter>('all');
  const [selectedId, setSelectedId] = useState<string>(mockConversations[0]?.id || '');

  const handleFilterChange = (id: string) => {
    setFilter(id as InboxFilter);
  };

  // Filter conversations based on active filter
  const filteredConversations = mockConversations.filter((conv) => {
    if (filter === 'all') return true;
    if (filter === 'needs-reply') return conv.unread;
    if (filter === 'meetings') return conv.intent === 'meeting';
    return true;
  });

  const selectedConversation = mockConversations.find((c) => c.id === selectedId) || null;

  const handleSelectConversation = (conversation: Conversation) => {
    setSelectedId(conversation.id);
  };

  return (
    <AppShell>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Inbox</h1>
        <InboxFilters activeFilter={filter} onFilterChange={handleFilterChange} tabs={FILTER_TABS} />
      </div>

      {/* Inbox Container - Two Column Layout */}
      <div className="flex gap-0 bg-white rounded-2xl border border-slate-200 overflow-hidden h-[calc(100vh-180px)]">
        {/* Left: Conversation List */}
        <div className="w-[360px] overflow-y-auto">
          <ConversationList
            conversations={filteredConversations}
            selectedId={selectedId}
            onSelect={handleSelectConversation}
          />
        </div>

        {/* Right: Conversation Detail */}
        <div className="flex-1 flex flex-col bg-slate-50">
          <ConversationDetail conversation={selectedConversation} />
        </div>
      </div>
    </AppShell>
  );
}
