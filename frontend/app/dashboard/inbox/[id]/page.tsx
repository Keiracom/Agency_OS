/**
 * FILE: frontend/app/dashboard/inbox/[id]/page.tsx
 * PURPOSE: Reply Detail page - Full conversation view with lead context
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 * ROUTE: /dashboard/inbox/[id]
 */
'use client';

import { useParams } from 'next/navigation';
import { useState, useMemo } from 'react';
import {
  ReplyDetailHeader,
  LeadHeader,
  EmailMessage,
  SMSThread,
  AISuggestions,
  ReplyComposer,
  QuickActions,
  LeadDetails,
  ScoreBreakdown,
  ActivityTimeline,
  NotesSection,
} from '@/components/inbox/detail';
import {
  mockInboxMessages,
  mockDavidParkThread,
  mockDavidParkSMS,
  mockAISuggestions,
  mockDavidParkActivity,
  mockDavidParkNotes,
  mockDavidParkScoreFactors,
  ThreadMessage,
} from '@/lib/mock/inbox-data';

export default function ReplyDetailPage() {
  const params = useParams();
  const id = params.id as string;
  
  // Find the message from mock data
  const message = useMemo(() => {
    return mockInboxMessages.find((m) => m.id === id);
  }, [id]);
  
  // State for composer
  const [composerValue, setComposerValue] = useState('');
  
  // Handle AI suggestion click
  const handleUseSuggestion = (text: string) => {
    setComposerValue(text);
  };
  
  // Handle send
  const handleSend = (text: string) => {
    console.log('Sending message:', text);
    // In a real app, this would send the message via API
  };
  
  // Get thread data based on message ID
  // For now, we use David Park data for his ID, or empty for others
  const emailThread = id === 'david-park' ? mockDavidParkThread : [];
  const smsThread = id === 'david-park' ? mockDavidParkSMS : [];
  const activities = id === 'david-park' ? mockDavidParkActivity : [];
  const notes = id === 'david-park' ? mockDavidParkNotes : [];
  const scoreFactors = id === 'david-park' ? mockDavidParkScoreFactors : [];
  
  if (!message) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#0C0A08]">
        <div className="w-20 h-20 glass-surface rounded-2xl flex items-center justify-center text-4xl mb-5">❓</div>
        <h3 className="text-lg font-semibold text-text-primary mb-2">Conversation not found</h3>
        <p className="text-sm text-text-muted">The message you&apos;re looking for doesn&apos;t exist.</p>
      </div>
    );
  }
  
  // Group messages by date for display
  const groupedEmails = useMemo(() => {
    const groups: { date: string; messages: ThreadMessage[] }[] = [];
    let currentDate = '';
    
    emailThread.forEach((msg) => {
      if (msg.date !== currentDate) {
        currentDate = msg.date;
        groups.push({ date: currentDate, messages: [msg] });
      } else {
        groups[groups.length - 1].messages.push(msg);
      }
    });
    
    return groups;
  }, [emailThread]);

  return (
    <div className="flex-1 flex flex-col h-screen bg-[#0C0A08]">
      {/* Header with back button */}
      <ReplyDetailHeader leadName={message.name} />
      
      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Conversation Panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Lead Header */}
          <LeadHeader message={message} />
          
          {/* Thread */}
          <div className="flex-1 overflow-y-auto px-8 py-6">
            {/* Email messages */}
            {groupedEmails.map((group) => (
              <div key={group.date}>
                {/* Date divider */}
                <div className="flex items-center gap-4 py-4">
                  <div className="flex-1 h-px bg-border-subtle" />
                  <span className="text-xs text-text-muted">{group.date}</span>
                  <div className="flex-1 h-px bg-border-subtle" />
                </div>
                
                {/* Messages */}
                {group.messages.map((msg) => (
                  <EmailMessage key={msg.id} message={msg} />
                ))}
              </div>
            ))}
            
            {/* SMS Thread (if any) */}
            {smsThread.length > 0 && (
              <SMSThread messages={smsThread} />
            )}
            
            {/* AI Suggestions */}
            <AISuggestions
              suggestions={mockAISuggestions}
              onUseSuggestion={handleUseSuggestion}
            />
          </div>
          
          {/* Composer */}
          <ReplyComposer
            recipientEmail={message.email}
            initialValue={composerValue}
            onSend={handleSend}
          />
        </div>
        
        {/* Right Panel / Sidebar */}
        <div className="w-[340px] bg-surface-dark border-l border-border-subtle overflow-y-auto p-6 space-y-5 flex-shrink-0">
          <QuickActions />
          <LeadDetails message={message} />
          <ScoreBreakdown score={message.score} factors={scoreFactors} />
          <ActivityTimeline activities={activities} />
          <NotesSection notes={notes} />
        </div>
      </div>
    </div>
  );
}
