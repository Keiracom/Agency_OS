'use client';

import { cn } from '@/lib/utils';
import { Conversation, channelEmoji, intentStyles } from '@/data/mock-inbox';

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
    <div className={cn('bg-white overflow-y-auto', className)}>
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
              isActive && 'bg-blue-50 border-l-[3px] border-l-blue-500',
              isUnread && !isActive && 'bg-amber-50',
              isUnread && isActive && 'bg-blue-50'
            )}
          >
            {/* Header: Name + Time */}
            <div className="flex justify-between items-start mb-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-sm text-slate-800">
                {isUnread && (
                  <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                )}
                <span>{conversation.leadName}</span>
              </div>
              <span className="text-xs text-slate-400 flex-shrink-0">
                {conversation.lastMessageTime}
              </span>
            </div>

            {/* Company */}
            <div className="text-xs text-slate-500 mb-1.5">
              {conversation.company}
            </div>

            {/* Preview: Channel emoji + Message + Intent badge */}
            <div className="flex items-center gap-2 text-[13px] text-slate-500">
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
          <div className="text-4xl mb-3">📭</div>
          <div className="text-sm font-medium text-slate-800 mb-1">No conversations</div>
          <div className="text-xs text-slate-400">
            Conversations will appear here when leads reply
          </div>
        </div>
      )}
    </div>
  );
}

export default ConversationList;
