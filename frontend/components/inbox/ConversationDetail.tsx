'use client';

import { Conversation, Message, channelEmoji } from '@/data/mock-inbox';

interface ConversationDetailProps {
  conversation: Conversation | null;
}

function MessageBubble({ message }: { message: Message }) {
  const isSent = message.direction === 'sent';
  
  return (
    <div className={`max-w-[80%] ${isSent ? 'self-end' : 'self-start'}`}>
      <div
        className={`px-4 py-3.5 rounded-2xl text-sm leading-relaxed ${
          isSent
            ? 'bg-bg-elevated text-text-primary rounded-br-sm'
            : 'bg-bg-surface border border-slate-200 text-slate-700 rounded-bl-sm'
        }`}
      >
        {message.content}
      </div>
      <div className="flex items-center gap-2 mt-1.5 text-[11px] text-text-secondary">
        <span>{channelEmoji[message.channel]}</span>
        <span className="capitalize">{message.channel}</span>
        <span>│</span>
        <span>{message.timestamp}</span>
      </div>
    </div>
  );
}

function AISuggestedReply({ suggestedReply }: { suggestedReply: string }) {
  return (
    <div className="bg-bg-surface border border-slate-200 rounded-2xl p-5 mt-auto">
      <div className="flex items-center gap-2 mb-3">
        <span className="px-2.5 py-1 bg-violet-100 text-amber rounded-md text-[11px] font-semibold">
          AI
        </span>
        <span className="text-sm font-semibold text-text-muted">Suggested Reply</span>
      </div>
      
      <div className="text-sm leading-relaxed text-text-muted p-4 bg-slate-50 rounded-lg mb-4 whitespace-pre-wrap">
        {suggestedReply}
      </div>
      
      <div className="flex gap-2.5">
        <button className="flex items-center gap-2 px-5 py-2.5 bg-bg-elevated text-text-primary rounded-lg text-sm font-semibold hover:bg-bg-elevated transition-colors">
          Send
        </button>
        <button className="flex items-center gap-2 px-5 py-2.5 bg-bg-surface border border-slate-200 text-text-muted rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors">
          Edit
        </button>
        <button className="flex items-center gap-2 px-5 py-2.5 bg-bg-surface border border-slate-200 text-text-muted rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors">
          Different tone
        </button>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-slate-50">
      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
        <span className="text-2xl"></span>
      </div>
      <h3 className="text-lg font-semibold text-slate-800 mb-2">No Conversation Selected</h3>
      <p className="text-sm text-text-muted max-w-xs">
        Select a conversation from the list to view messages and AI-suggested replies.
      </p>
    </div>
  );
}

export function ConversationDetail({ conversation }: ConversationDetailProps) {
  if (!conversation) {
    return <EmptyState />;
  }

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="px-6 py-5 bg-bg-surface border-b border-slate-200">
        <h2 className="text-lg font-bold text-slate-800">{conversation.leadName}</h2>
        <p className="text-sm text-text-muted">
          {conversation.leadTitle}, {conversation.company}
          {conversation.leadCompanyInfo && ` │ ${conversation.leadCompanyInfo}`}
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-5">
        {conversation.messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {conversation.suggestedReply && (
          <AISuggestedReply suggestedReply={conversation.suggestedReply} />
        )}
      </div>
    </div>
  );
}
