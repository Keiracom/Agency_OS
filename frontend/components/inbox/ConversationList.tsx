'use client';

import { cn } from '@/lib/utils';
import { Conversation, channelEmoji, intentStyles } from '@/data/mock-inbox';
import { Inbox } from 'lucide-react';

interface ConversationListProps {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (conversation: Conversation) => void;
  className?: string;
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  className,
}: ConversationListProps) {
  return (
    <div className={cn('bg-bg-panel overflow-y-auto', className)}>
      {conversations.map((conversation) => {
        const isActive = conversation.id === selectedId;
        const isUnread = conversation.unread;
        const intent = intentStyles[conversation.intent];

        return (
          <div
            key={conversation.id}
            onClick={() => onSelect(conversation)}
            className={cn(
              'px-5 py-4 border-b border-slate-100 cursor-pointer transition-colors',
              'hover:bg-slate-50',
              isActive && 'bg-bg-panel border-l-[3px] border-l-amber',
              isUnread && !isActive && 'bg-amber-50',
              isUnread && isActive && 'bg-bg-panel'
            )}
          >
            {/* Header: Name + Time */}
            <div className="flex justify-between items-start mb-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-sm text-slate-800">
                {isUnread && (
                  <span className="w-2 h-2 rounded-full bg-bg-elevated flex-shrink-0" />
                )}
                <span>{conversation.leadName}</span>
              </div>
              <span className="text-xs text-ink-2 flex-shrink-0">
                {conversation.lastMessageTime}
              </span>
            </div>

            {/* Company */}
            <div className="text-xs text-ink-3 mb-1.5">
              {conversation.company}
            </div>

            {/* Preview: Channel emoji + Message + Intent badge */}
            <div className="flex items-center gap-2 text-[13px] text-ink-3">
              <span className="flex-shrink-0">
                {channelEmoji[conversation.channel]}
              </span>
              <span className="truncate flex-1 min-w-0">
                {conversation.lastMessage}
              </span>
              <span
                className={cn(
                  'px-2 py-0.5 rounded text-[10px] font-semibold uppercase flex-shrink-0',
                  intent.bg,
                  intent.text
                )}
              >
                {intent.label}
              </span>
            </div>
          </div>
        );
      })}

      {conversations.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
          <Inbox className="w-10 h-10 text-ink-3 mb-3" />
          <div className="text-sm font-medium text-slate-800 mb-1">No conversations</div>
          <div className="text-xs text-ink-2">
            Conversations will appear here when leads reply
          </div>
        </div>
      )}
    </div>
  );
}

export default ConversationList;
