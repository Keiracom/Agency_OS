/**
 * FILE: app/api/replies/[id]/send/route.ts
 * PURPOSE: Send reply to a specific lead/thread
 * TODO: Integrate with email providers (Salesforge/Resend) and update Supabase
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface SendReplyRequest {
  message: string;
  channel?: "email" | "linkedin" | "sms";
  scheduleFor?: string; // ISO datetime for scheduled send
}

export interface SendReplyResponse {
  success: boolean;
  messageId?: string;
  sentAt?: string;
  scheduledFor?: string;
  error?: string;
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: replyId } = await params;
    const body: SendReplyRequest = await request.json();
    const { message, channel = "email", scheduleFor } = body;

    // Validate
    if (!message || message.trim().length === 0) {
      return NextResponse.json(
        { success: false, error: "Message content is required" },
        { status: 400 }
      );
    }

    if (message.length > 10000) {
      return NextResponse.json(
        { success: false, error: "Message exceeds maximum length (10,000 chars)" },
        { status: 400 }
      );
    }

    // TODO: Supabase integration
    // 1. Fetch the original reply to get thread context
    // const supabase = createClient(...)
    // const { data: originalReply } = await supabase
    //   .from('replies')
    //   .select('*, leads(email, linkedin_url, phone)')
    //   .eq('id', replyId)
    //   .single()

    // 2. Send via appropriate channel
    // if (channel === 'email') {
    //   await salesforge.sendReply({ threadId: originalReply.thread_id, message })
    // } else if (channel === 'linkedin') {
    //   await unipile.sendMessage({ profileUrl: originalReply.leads.linkedin_url, message })
    // }

    // 3. Update reply status
    // await supabase.from('replies').update({ status: 'replied' }).eq('id', replyId)

    // 4. Log activity
    // await supabase.from('activity_feed').insert({ type: 'reply_sent', ... })

    // Mock response
    const mockResponse: SendReplyResponse = {
      success: true,
      messageId: `msg_${Date.now()}`,
      sentAt: scheduleFor ? undefined : new Date().toISOString(),
      scheduledFor: scheduleFor || undefined,
    };

    console.log(`✅ Reply sent for ${replyId} via ${channel}`);

    return NextResponse.json(mockResponse);
  } catch (error) {
    console.error("Send reply error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to send reply" },
      { status: 500 }
    );
  }
}
