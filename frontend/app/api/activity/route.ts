/**
 * FILE: app/api/activity/route.ts
 * PURPOSE: Live activity feed for dashboard, scoped to the authenticated user's client via RLS.
 *          Returns activities table rows joined with leads for name/company display.
 *          Honest empty state when no rows (Phase 1 pre-revenue: 0 sent → 0 activity).
 */

import { type NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export interface ActivityItem {
  id: string;
  type: string; // raw activities.action — UI maps display name
  leadName: string;
  companyName: string;
  channel: string;
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface ActivityResponse {
  success: boolean;
  data: ActivityItem[];
  hasMore: boolean;
  cursor?: string;
}

type ActivityRow = {
  id: string;
  action: string | null;
  channel: string | null;
  content_preview: string | null;
  subject: string | null;
  created_at: string;
  metadata: Record<string, unknown> | null;
  leads: {
    first_name: string | null;
    last_name: string | null;
    company: string | null;
  } | null;
};

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = Math.min(parseInt(searchParams.get("limit") || "10"), 200);
    const cursor = searchParams.get("cursor");
    const action = searchParams.get("type"); // legacy param name

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
        "id, action, channel, content_preview, subject, created_at, metadata, leads(first_name, last_name, company)"
      )
      .order("created_at", { ascending: false })
      .limit(limit + 1);
    if (cursor) query = query.lt("created_at", cursor);
    if (action) query = query.eq("action", action);

    const { data, error } = await query;
    if (error) {
      console.error("Activity feed query error:", error);
      return NextResponse.json(
        { success: false, error: "Failed to fetch activity feed" },
        { status: 500 }
      );
    }

    const rows = (data ?? []) as unknown as ActivityRow[];
    const hasMore = rows.length > limit;
    const page = rows.slice(0, limit);

    const items: ActivityItem[] = page.map((row) => ({
      id: row.id,
      type: row.action ?? "unknown",
      leadName:
        [row.leads?.first_name, row.leads?.last_name].filter(Boolean).join(" ") ||
        "Unknown",
      companyName: row.leads?.company ?? "",
      channel: row.channel ?? "email",
      message: row.content_preview ?? row.subject ?? "",
      timestamp: row.created_at,
      metadata: row.metadata ?? undefined,
    }));

    return NextResponse.json({
      success: true,
      data: items,
      hasMore,
      cursor: items.length > 0 ? items[items.length - 1].timestamp : undefined,
    } as ActivityResponse);
  } catch (error) {
    console.error("Activity feed error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch activity feed" },
      { status: 500 }
    );
  }
}
