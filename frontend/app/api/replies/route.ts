/**
 * FILE: app/api/replies/route.ts
 * PURPOSE: Reply inbox — incoming replies needing attention.
 *          Queries activities filtered to reply-shaped actions, joined
 *          with leads for sender display. Honest empty state when no rows.
 */

import { type NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export interface Reply {
  id: string;
  leadId: string;
  leadName: string;
  companyName: string;
  leadEmail: string;
  leadTitle: string;
  channel: string;
  subject: string;
  snippet: string;
  sentiment: string;
  status: string;
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

type ActivityRow = {
  id: string;
  lead_id: string | null;
  channel: string | null;
  subject: string | null;
  content_preview: string | null;
  thread_id: string | null;
  sequence_step: number | null;
  intent: string | null;
  created_at: string;
  metadata: Record<string, unknown> | null;
  leads: {
    first_name: string | null;
    last_name: string | null;
    company: string | null;
    email: string | null;
    title: string | null;
  } | null;
};

const REPLY_ACTIONS = ["reply.received", "reply_received", "received_reply"];

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const sentiment = searchParams.get("sentiment");
    const channel = searchParams.get("channel");
    const limit = Math.min(parseInt(searchParams.get("limit") || "50"), 200);

    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json(
        { success: false, error: "Unauthorized" },
        { status: 401 }
      );
    }

    let query = supabase
      .from("activities")
      .select(
        "id, lead_id, channel, subject, content_preview, thread_id, sequence_step, intent, created_at, metadata, leads(first_name, last_name, company, email, title)"
      )
      .in("action", REPLY_ACTIONS)
      .order("created_at", { ascending: false })
      .limit(limit);
    if (channel) query = query.eq("channel", channel);
    if (sentiment) query = query.eq("intent", sentiment);

    const { data, error } = await query;
    if (error) {
      console.error("Replies query error:", error);
      return NextResponse.json(
        { success: false, error: "Failed to fetch replies" },
        { status: 500 }
      );
    }

    const rows = (data ?? []) as unknown as ActivityRow[];

    const replies: Reply[] = rows.map((row) => {
      const meta = (row.metadata ?? {}) as Record<string, unknown>;
      // status is not yet a first-class column — until a writer populates
      // metadata.status (read/replied/archived), every row reads "unread".
      // metadata.status is the forward-compat hook for that writer.
      const status = typeof meta.status === "string" ? meta.status : "unread";
      return {
        id: row.id,
        leadId: row.lead_id ?? "",
        // "Unknown" surfaces in the UI when leads JOIN returns no name —
        // happens for activities recorded against deleted/anonymised leads.
        leadName:
          [row.leads?.first_name, row.leads?.last_name].filter(Boolean).join(" ") ||
          "Unknown",
        companyName: row.leads?.company ?? "",
        leadEmail: row.leads?.email ?? "",
        leadTitle: row.leads?.title ?? "",
        channel: row.channel ?? "email",
        subject: row.subject ?? "",
        snippet: row.content_preview ?? "",
        sentiment: row.intent ?? "neutral",
        status,
        receivedAt: row.created_at,
        threadId: row.thread_id ?? undefined,
        sequenceStep: row.sequence_step ?? undefined,
      };
    });

    const unread = replies.filter((r) => r.status === "unread").length;

    return NextResponse.json({
      success: true,
      data: replies,
      total: replies.length,
      unread,
    } as RepliesResponse);
  } catch (error) {
    console.error("Replies error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch replies" },
      { status: 500 }
    );
  }
}
