/**
 * FILE: frontend/components/inbox/detail/ReplyDetailHeader.tsx
 * PURPOSE: Back button + breadcrumb header for reply detail page
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import Link from 'next/link';
import { ChevronLeft } from 'lucide-react';

interface ReplyDetailHeaderProps {
  leadName: string;
}

export function ReplyDetailHeader({ leadName }: ReplyDetailHeaderProps) {
  return (
    <header className="bg-surface-dark border-b border-border-subtle px-6 py-3 flex items-center gap-4">
      <Link
        href="/dashboard/inbox"
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-text-muted hover:bg-white/[0.05] hover:text-text-secondary transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        Back to Inbox
      </Link>
      <div className="w-px h-6 bg-border-subtle" />
      <span className="text-sm text-text-secondary">
        Conversation with <span className="font-medium text-text-primary">{leadName}</span>
      </span>
    </header>
  );
}
