/**
 * FILE: frontend/app/dashboard/inbox/page.tsx
 * PURPOSE: Inbox Command Center page
 * SPRINT: Dashboard Sprint 3b
 */
'use client';
import { useState } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { InboxHeader, InboxList, InboxPreview } from '@/components/inbox';
import { mockInboxMessages } from '@/lib/mock/inbox-data';

export default function InboxPage() {
  const [selectedId, setSelectedId] = useState<string | null>(mockInboxMessages[0]?.id || null);
  const selectedMessage = mockInboxMessages.find((m) => m.id === selectedId) || null;
  const unreadCount = mockInboxMessages.filter((m) => m.unread).length;

  return (
    <AppShell pageTitle="Inbox">
      <div className="-m-8 h-[calc(100vh-64px)] flex flex-col">
        <InboxHeader unreadCount={unreadCount} />
        <div className="flex-1 flex overflow-hidden">
          <InboxList 
            messages={mockInboxMessages} 
            selectedId={selectedId} 
            onSelectMessage={setSelectedId} 
          />
          <InboxPreview message={selectedMessage} />
        </div>
      </div>
    </AppShell>
  );
}
