/**
 * FILE: app/api/replies/route.ts
 * PURPOSE: Reply inbox - all incoming replies needing attention
 * TODO: Replace mock data with Supabase + email provider integration
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface Reply {
  id: string;
  leadId: string;
  leadName: string;
  companyName: string;
  leadEmail: string;
  leadTitle: string;
  channel: "email" | "linkedin" | "sms";
  subject: string;
  snippet: string;
  fullBody: string;
  sentiment: "positive" | "neutral" | "negative" | "unsubscribe";
  status: "unread" | "read" | "replied" | "archived";
  suggestedReply?: string;
  receivedAt: string;
  threadId?: string;
  sequenceStep?: number;
}

export interface RepliesResponse {
  success: boolean;
  data: Reply[];
  total: number;
  unread: number;
}

// Mock data
const mockReplies: Reply[] = [
  {
    id: "rpl_001",
    leadId: "lead_201",
    leadName: "Sarah Chen",
    companyName: "TechFlow Digital",
    leadEmail: "sarah@techflow.com.au",
    leadTitle: "Marketing Director",
    channel: "email",
    subject: "Re: Quick question about your agency",
    snippet: "Hi, thanks for reaching out. I'd be interested in learning more about how you help agencies with...",
    fullBody: "Hi,\n\nThanks for reaching out. I'd be interested in learning more about how you help agencies with lead generation. We've been struggling to find quality leads lately.\n\nCould you share some case studies or examples of agencies you've worked with?\n\nBest,\nSarah",
    sentiment: "positive",
    status: "unread",
    suggestedReply: "Hi Sarah, great to hear from you! I'd be happy to share some case studies. We recently helped a Melbourne-based agency increase their qualified meetings by 340%. Would you have 15 minutes this week for a quick call?",
    receivedAt: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    sequenceStep: 1,
  },
  {
    id: "rpl_002",
    leadId: "lead_202",
    leadName: "Michael Brown",
    companyName: "Creative Pulse",
    leadEmail: "michael@creativepulse.com.au",
    leadTitle: "CEO",
    channel: "email",
    subject: "Re: Partnership opportunity",
    snippet: "Not interested right now, but maybe reach out again in a few months...",
    fullBody: "Hi,\n\nNot interested right now, but maybe reach out again in a few months when we've sorted out our current projects.\n\nCheers,\nMichael",
    sentiment: "neutral",
    status: "unread",
    suggestedReply: "Hi Michael, completely understand - timing is everything. I'll set a reminder to follow up in Q3. In the meantime, feel free to reach out if anything changes. Best of luck with your current projects!",
    receivedAt: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    sequenceStep: 2,
  },
  {
    id: "rpl_003",
    leadId: "lead_203",
    leadName: "Emma Johnson",
    companyName: "Bright Marketing Co",
    leadEmail: "emma@brightmarketing.com.au",
    leadTitle: "Founder",
    channel: "linkedin",
    subject: "LinkedIn Message",
    snippet: "This sounds interesting! I've been looking for something like this. When can we chat?",
    fullBody: "This sounds interesting! I've been looking for something like this. When can we chat?",
    sentiment: "positive",
    status: "read",
    suggestedReply: "Fantastic, Emma! I have availability tomorrow at 10am or Thursday at 2pm AEST. Which works better for you? Here's my calendar link: [CALENDAR_LINK]",
    receivedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    sequenceStep: 1,
  },
  {
    id: "rpl_004",
    leadId: "lead_204",
    leadName: "David Wilson",
    companyName: "Digital Dynamics",
    leadEmail: "david@digitaldynamics.com.au",
    leadTitle: "Managing Director",
    channel: "email",
    subject: "Re: Helping agencies like yours",
    snippet: "Please remove me from your list",
    fullBody: "Please remove me from your list.\n\nDavid",
    sentiment: "unsubscribe",
    status: "unread",
    receivedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    sequenceStep: 3,
  },
];

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status"); // unread, read, replied, archived
    const sentiment = searchParams.get("sentiment"); // positive, neutral, negative, unsubscribe
    const channel = searchParams.get("channel"); // email, linkedin, sms
    const limit = parseInt(searchParams.get("limit") || "50");

    // TODO: Supabase integration
    // const supabase = createClient(...)
    // let query = supabase.from('replies').select('*, leads(name, company_name, email, title)')
    // if (status) query = query.eq('status', status)
    // if (sentiment) query = query.eq('sentiment', sentiment)
    // if (channel) query = query.eq('channel', channel)
    // const { data } = await query.order('received_at', { ascending: false }).limit(limit)

    let filtered = [...mockReplies];
    
    if (status) {
      filtered = filtered.filter((r) => r.status === status);
    }
    if (sentiment) {
      filtered = filtered.filter((r) => r.sentiment === sentiment);
    }
    if (channel) {
      filtered = filtered.filter((r) => r.channel === channel);
    }

    const unreadCount = mockReplies.filter((r) => r.status === "unread").length;

    return NextResponse.json({
      success: true,
      data: filtered.slice(0, limit),
      total: filtered.length,
      unread: unreadCount,
    } as RepliesResponse);
  } catch (error) {
    console.error("Replies error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch replies" },
      { status: 500 }
    );
  }
}
