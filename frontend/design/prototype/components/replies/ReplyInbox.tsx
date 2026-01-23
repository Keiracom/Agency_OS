"use client";

import { useState, useMemo } from "react";
import { MessageSquare, Inbox } from "lucide-react";
import { DashboardShell } from "../layout";
import { ReplyCard, ReplyChannel, ReplyIntent, ALSTier } from "./ReplyCard";
import { ReplyDetail, Reply, ThreadMessage } from "./ReplyDetail";
import { ReplyFilters } from "./ReplyFilters";

/**
 * Static demo data - 10 sample replies covering all channels and intents
 */
const demoReplies: Reply[] = [
  {
    id: "reply-1",
    leadName: "Sarah Chen",
    leadCompany: "TechFlow Solutions",
    leadTitle: "VP of Marketing",
    leadEmail: "sarah.chen@techflow.io",
    leadLinkedIn: "https://linkedin.com/in/sarahchen",
    channel: "email",
    subject: "Re: Partnership Opportunity for Q2 Growth",
    content: `Hi there,

Thanks for reaching out! I've been looking at your proposal and I'm genuinely interested in learning more about how you've helped similar B2B SaaS companies.

Could we schedule a 30-minute call next week? I'm free Tuesday or Thursday afternoon.

Looking forward to connecting,
Sarah`,
    preview: "Thanks for reaching out! I've been looking at your proposal and I'm genuinely interested...",
    timestamp: "2 hours ago",
    intent: "positive",
    tierBadge: "hot",
    alsScore: 92,
    isUnread: true,
    campaignName: "SaaS Growth Q1",
    threadHistory: [
      {
        id: "thread-1-1",
        sender: "agency",
        content: "Hi Sarah, I noticed TechFlow just closed a Series B - congratulations! I'd love to discuss how we've helped similar companies scale their outbound...",
        timestamp: "Yesterday",
      },
    ],
    aiSuggestedResponse: `Hi Sarah,

Great to hear from you! I'm delighted you're interested.

Tuesday afternoon works perfectly for me. How about 2:00 PM AEST? I'll send over a calendar invite.

Looking forward to our conversation!`,
  },
  {
    id: "reply-2",
    leadName: "Marcus Johnson",
    leadCompany: "DataPipe Analytics",
    leadTitle: "Head of Operations",
    leadEmail: "m.johnson@datapipe.com",
    channel: "linkedin",
    subject: "Connection Request Accepted",
    content: `Hey! Thanks for connecting. I saw your message about demand generation services.

Quick question - what's your typical engagement look like in terms of timeline and minimum commitment?

We're evaluating a few agencies right now.`,
    preview: "Hey! Thanks for connecting. I saw your message about demand generation services...",
    timestamp: "4 hours ago",
    intent: "question",
    tierBadge: "warm",
    alsScore: 74,
    isUnread: true,
    campaignName: "LinkedIn Outreach Feb",
    aiSuggestedResponse: `Hi Marcus,

Great question! Our typical engagements run 3-6 months with a minimum 90-day commitment to see real results.

We focus on quality over quantity - most clients see their first qualified meetings within 2-3 weeks.

Would you like to hop on a quick call to discuss what makes sense for DataPipe?`,
  },
  {
    id: "reply-3",
    leadName: "Emily Rodriguez",
    leadCompany: "CloudSecure Inc",
    leadTitle: "CEO",
    leadEmail: "emily@cloudsecure.co",
    channel: "email",
    subject: "Re: Security Solutions for Growing Teams",
    content: `Hi,

We're not looking for any new vendors at this time. Please remove me from your list.

Thanks,
Emily`,
    preview: "We're not looking for any new vendors at this time. Please remove me from your list...",
    timestamp: "6 hours ago",
    intent: "negative",
    tierBadge: "cold",
    alsScore: 28,
    isUnread: false,
    campaignName: "Security Vertical",
    threadHistory: [
      {
        id: "thread-3-1",
        sender: "agency",
        content: "Hi Emily, I came across CloudSecure and was impressed by your recent product launch...",
        timestamp: "2 days ago",
      },
    ],
  },
  {
    id: "reply-4",
    leadName: "James Wu",
    leadCompany: "Velocity Ventures",
    leadTitle: "Partner",
    leadEmail: "james@velocityvc.com",
    channel: "sms",
    subject: "SMS Response",
    content: "Sounds interesting. Can you send more details via email? j.wu@velocityvc.com",
    preview: "Sounds interesting. Can you send more details via email?",
    timestamp: "1 day ago",
    intent: "positive",
    tierBadge: "warm",
    alsScore: 68,
    isUnread: false,
    campaignName: "VC Outreach",
  },
  {
    id: "reply-5",
    leadName: "Lisa Thompson",
    leadCompany: "GrowthStack",
    leadTitle: "CMO",
    leadEmail: "lisa.t@growthstack.io",
    leadLinkedIn: "https://linkedin.com/in/lisathompson",
    channel: "email",
    subject: "Re: Scaling Your Outbound",
    content: `Thanks for the outreach.

I've forwarded this to our RevOps team who handles vendor evaluations. They may reach out if there's a fit.

Best,
Lisa`,
    preview: "I've forwarded this to our RevOps team who handles vendor evaluations...",
    timestamp: "1 day ago",
    intent: "neutral",
    tierBadge: "cool",
    alsScore: 52,
    isUnread: false,
    campaignName: "SaaS Growth Q1",
    threadHistory: [
      {
        id: "thread-5-1",
        sender: "agency",
        content: "Hi Lisa, I noticed GrowthStack has been expanding rapidly...",
        timestamp: "3 days ago",
      },
    ],
  },
  {
    id: "reply-6",
    leadName: "Alex Patel",
    leadCompany: "Innovate Labs",
    leadTitle: "Director of Sales",
    leadEmail: "alex.patel@innovatelabs.com",
    channel: "linkedin",
    subject: "LinkedIn Message",
    content: `Really appreciate you sharing that case study. The results for Acme Corp were impressive.

How does your pricing model work? Is it performance-based or retainer?`,
    preview: "Really appreciate you sharing that case study. The results were impressive...",
    timestamp: "2 days ago",
    intent: "question",
    tierBadge: "hot",
    alsScore: 86,
    isUnread: true,
    campaignName: "LinkedIn Outreach Feb",
    aiSuggestedResponse: `Hi Alex,

Glad you found the case study valuable!

We offer both models actually:
- Performance-based: Pay per qualified meeting
- Retainer: Fixed monthly fee with guaranteed outputs

Most clients at your stage prefer the retainer model as it provides more predictable budgeting.

Shall we jump on a quick call to discuss which makes more sense for Innovate Labs?`,
  },
  {
    id: "reply-7",
    leadName: "Michelle Chang",
    leadCompany: "FinEdge Financial",
    leadTitle: "VP Business Development",
    leadEmail: "mchang@finedge.com",
    channel: "voice",
    subject: "Voicemail Response",
    content: "Voicemail transcription: 'Hi, I got your voicemail. I'm interested but timing isn't great right now. Can you follow up in about 6 weeks? We'll be through our audit by then. Thanks.'",
    preview: "Voicemail: Hi, I got your voicemail. I'm interested but timing isn't great...",
    timestamp: "2 days ago",
    intent: "neutral",
    tierBadge: "cool",
    alsScore: 48,
    isUnread: false,
    campaignName: "Financial Services Q1",
  },
  {
    id: "reply-8",
    leadName: "David Kim",
    leadCompany: "Nexus Software",
    leadTitle: "CEO",
    leadEmail: "david@nexussoftware.com",
    leadLinkedIn: "https://linkedin.com/in/davidkim-nexus",
    channel: "email",
    subject: "Re: Quick Question About Your GTM Strategy",
    content: `Hi there!

This is exactly what we've been looking for. We're struggling with our outbound motion and your approach sounds different from the typical agencies we've talked to.

Let's definitely set up a call. I'm available:
- Monday 10am-12pm
- Wednesday 2pm-4pm
- Friday anytime

Talk soon,
David`,
    preview: "This is exactly what we've been looking for. We're struggling with our outbound...",
    timestamp: "3 days ago",
    intent: "positive",
    tierBadge: "hot",
    alsScore: 95,
    isUnread: false,
    campaignName: "SaaS Growth Q1",
    threadHistory: [
      {
        id: "thread-8-1",
        sender: "agency",
        content: "Hi David, Congrats on the recent product launch! I noticed Nexus is moving into enterprise...",
        timestamp: "5 days ago",
      },
    ],
    aiSuggestedResponse: `Hi David,

Fantastic - I'm excited to connect!

Let's do Monday at 10am. I'll send over a calendar invite with a Zoom link.

In the meantime, I'll prepare a few examples specific to software companies at your stage.

Talk soon!`,
  },
  {
    id: "reply-9",
    leadName: "Rachel Foster",
    leadCompany: "Bright Media Group",
    leadTitle: "Marketing Director",
    channel: "sms",
    subject: "SMS Response",
    content: "Stop messaging me please",
    preview: "Stop messaging me please",
    timestamp: "3 days ago",
    intent: "negative",
    tierBadge: "dead",
    alsScore: 12,
    isUnread: false,
    campaignName: "Media & Entertainment",
  },
  {
    id: "reply-10",
    leadName: "Tom Bradley",
    leadCompany: "Quantum Dynamics",
    leadTitle: "COO",
    leadEmail: "tbradley@quantumdynamics.io",
    channel: "linkedin",
    subject: "LinkedIn Message",
    content: `Interesting timing - we were just discussing our need to ramp up pipeline generation in our leadership meeting.

What industries do you typically work with? And do you have experience with complex B2B sales cycles (6+ months)?`,
    preview: "Interesting timing - we were just discussing our need to ramp up pipeline...",
    timestamp: "4 days ago",
    intent: "question",
    tierBadge: "warm",
    alsScore: 72,
    isUnread: false,
    campaignName: "Enterprise Tech",
    aiSuggestedResponse: `Hi Tom,

Perfect timing indeed!

We specialize in complex B2B with longer sales cycles - in fact, that's our sweet spot. Our clients typically sell to enterprises with 3-12 month cycles.

Industries we've had great success with include:
- Enterprise SaaS
- Manufacturing tech
- Professional services
- FinTech

I'd love to share some specific case studies relevant to Quantum Dynamics. Would Thursday or Friday work for a quick call?`,
  },
];

/**
 * ReplyInbox props
 */
export interface ReplyInboxProps {
  /** Navigation handler */
  onNavigate?: (path: string) => void;
}

/**
 * ReplyInbox - Full replies page component
 *
 * Features:
 * - Uses DashboardShell for consistent layout
 * - Split view: reply list on left, detail panel on right
 * - ReplyFilters at top for channel/intent/search filtering
 * - List of ReplyCard items with selection state
 * - ReplyDetail panel showing full message
 * - Empty state when no reply is selected
 * - Static demo data with 10 sample replies
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Content background: #F8FAFC (content-bg)
 * - Card background: #FFFFFF (card-bg)
 * - Card border: #E2E8F0 (card-border)
 */
export function ReplyInbox({ onNavigate }: ReplyInboxProps) {
  const [selectedReplyId, setSelectedReplyId] = useState<string | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<ReplyChannel | "all">("all");
  const [selectedIntent, setSelectedIntent] = useState<ReplyIntent | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Filter replies based on current filters
  const filteredReplies = useMemo(() => {
    return demoReplies.filter((reply) => {
      // Channel filter
      if (selectedChannel !== "all" && reply.channel !== selectedChannel) {
        return false;
      }

      // Intent filter
      if (selectedIntent !== "all" && reply.intent !== selectedIntent) {
        return false;
      }

      // Search filter (searches name, company, subject, preview)
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const searchableText = [
          reply.leadName,
          reply.leadCompany,
          reply.subject,
          reply.preview,
        ]
          .join(" ")
          .toLowerCase();
        if (!searchableText.includes(query)) {
          return false;
        }
      }

      return true;
    });
  }, [selectedChannel, selectedIntent, searchQuery]);

  // Get selected reply object
  const selectedReply = useMemo(() => {
    return filteredReplies.find((r) => r.id === selectedReplyId) || null;
  }, [filteredReplies, selectedReplyId]);

  // Count stats
  const unreadCount = demoReplies.filter((r) => r.isUnread).length;
  const positiveCount = demoReplies.filter((r) => r.intent === "positive").length;

  return (
    <DashboardShell
      title="Replies"
      activePath="/replies"
      onNavigate={onNavigate}
      notificationCount={unreadCount}
      userName="Acme Agency"
    >
      {/* Stats Bar */}
      <div className="flex items-center gap-6 mb-4">
        <div className="flex items-center gap-2">
          <Inbox className="h-5 w-5 text-[#64748B]" />
          <span className="text-sm text-[#64748B]">
            <span className="font-semibold text-[#1E293B]">{filteredReplies.length}</span> replies
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-[#3B82F6] rounded-full" />
          <span className="text-sm text-[#64748B]">
            <span className="font-semibold text-[#1E293B]">{unreadCount}</span> unread
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-[#10B981] rounded-full" />
          <span className="text-sm text-[#64748B]">
            <span className="font-semibold text-[#1E293B]">{positiveCount}</span> positive
          </span>
        </div>
      </div>

      {/* Main Content - Split View */}
      <div className="flex bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden" style={{ height: "calc(100vh - 200px)" }}>
        {/* Left Panel - Reply List */}
        <div className="w-[400px] flex flex-col border-r border-[#E2E8F0]">
          {/* Filters */}
          <ReplyFilters
            selectedChannel={selectedChannel}
            selectedIntent={selectedIntent}
            searchQuery={searchQuery}
            onChannelChange={setSelectedChannel}
            onIntentChange={setSelectedIntent}
            onSearchChange={setSearchQuery}
          />

          {/* Reply List */}
          <div className="flex-1 overflow-auto">
            {filteredReplies.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-6">
                <MessageSquare className="h-12 w-12 text-[#E2E8F0] mb-4" />
                <p className="text-sm font-medium text-[#64748B]">No replies found</p>
                <p className="text-xs text-[#94A3B8] mt-1">
                  Try adjusting your filters
                </p>
              </div>
            ) : (
              filteredReplies.map((reply) => (
                <ReplyCard
                  key={reply.id}
                  id={reply.id}
                  leadName={reply.leadName}
                  leadCompany={reply.leadCompany}
                  channel={reply.channel}
                  subject={reply.subject}
                  preview={reply.preview}
                  timestamp={reply.timestamp}
                  intent={reply.intent}
                  tierBadge={reply.tierBadge}
                  isUnread={reply.isUnread}
                  isSelected={reply.id === selectedReplyId}
                  onClick={() => setSelectedReplyId(reply.id)}
                />
              ))
            )}
          </div>
        </div>

        {/* Right Panel - Reply Detail */}
        <div className="flex-1 flex flex-col">
          {selectedReply ? (
            <ReplyDetail
              reply={selectedReply}
              onReply={() => console.log("Reply clicked")}
              onForward={() => console.log("Forward clicked")}
              onArchive={() => console.log("Archive clicked")}
            />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center px-6 bg-[#F8FAFC]">
              <div className="p-4 bg-[#E2E8F0] rounded-full mb-4">
                <MessageSquare className="h-8 w-8 text-[#94A3B8]" />
              </div>
              <h3 className="text-lg font-semibold text-[#1E293B] mb-2">
                Select a reply to view
              </h3>
              <p className="text-sm text-[#64748B] max-w-md">
                Choose a reply from the list to view the full conversation, see AI-suggested responses, and take action.
              </p>
            </div>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}

export default ReplyInbox;
