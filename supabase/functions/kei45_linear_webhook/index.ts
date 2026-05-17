// KEI-45 Phase A Component 4 — Linear outbound webhook → Supabase edge function
// → public.tasks UPSERT → Realtime fanout (triggered by tasks table publication).
//
// Per Round-3-ratified architecture (Dave + Aiden + Max + Elliot consensus
// ts ~1778733900): Supabase is single canonical state-of-record; Linear acts
// as a display adapter. This edge function is the WRITE path from Linear
// into Supabase — Linear's outbound webhook fires on issue create/update;
// this handler upserts to public.tasks; the Postgres publication on tasks
// fans the change to subscribed agents via Realtime.
//
// Linear payload schema reference: https://developers.linear.app/docs/graphql/webhooks
// We handle Issue type webhooks (create/update) and map to tasks columns:
//   identifier      -> id            (e.g. KEI-67)
//   title           -> title
//   state.name      -> status (mapped)
//   priority        -> priority (Linear uses 0-4; 0=None, 1=Urgent, 2=High,
//                                3=Medium, 4=Low. Our table uses 1=urgent..3=low
//                                ish so we map.)
//   labels[]        -> tags
//   url             -> linear_url
//
// Auth: validate webhook signature via LINEAR_WEBHOOK_SIGNATURE secret.
// Operator step post-deploy: register this function's HTTPS URL as Linear
// outbound webhook (Linear Settings → Webhooks → New Webhook → URL = function
// URL + paste the signing secret).
//
// Deploy: `supabase functions deploy kei45_linear_webhook --project-ref jatzvazlbusedwsnqxzr`

// @ts-expect-error -- Deno globals available at runtime in Supabase Edge Functions.
import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
// @ts-expect-error -- supabase-js esm import at runtime.
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

interface LinearIssue {
  identifier: string;
  title: string;
  url: string;
  priority: number; // 0 None, 1 Urgent, 2 High, 3 Medium, 4 Low
  state?: { name: string };
  labels?: { nodes: Array<{ name: string }> };
}

interface LinearWebhookPayload {
  action: string; // "create" | "update" | "remove"
  type: string;   // "Issue"
  data: LinearIssue;
}

// Map Linear state name -> tasks.status value. Conservative: only known names
// transition; unknown names default to 'available' (safe — agents can pick up).
const STATE_MAP: Record<string, string> = {
  "Backlog": "available",
  "Todo": "available",
  "In Progress": "active",
  "In Review": "active",
  "Done": "done",
  "Canceled": "done",
  "Duplicate": "done",
};

// Map Linear priority (0..4) -> tasks.priority (1=urgent, 2=high, 3=med default).
// Linear 0 (None) maps to 3 default. 1 (Urgent) -> 1. 2 (High) -> 1. 3 (Medium)
// -> 2. 4 (Low) -> 3.
const PRIORITY_MAP: Record<number, number> = {
  0: 3, 1: 1, 2: 1, 3: 2, 4: 3,
};

serve(async (req: Request): Promise<Response> => {
  if (req.method !== "POST") {
    return new Response("method not allowed", { status: 405 });
  }

  // Optional signature validation (skip if LINEAR_WEBHOOK_SIGNATURE not set —
  // allows local testing without secret).
  const secret = Deno.env.get("LINEAR_WEBHOOK_SIGNATURE") ?? "";
  if (secret) {
    const signature = req.headers.get("linear-signature") ?? "";
    if (signature !== secret) {
      return new Response("invalid signature", { status: 401 });
    }
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  if (!supabaseUrl || !supabaseKey) {
    return new Response("server misconfig: env missing", { status: 500 });
  }
  const supabase = createClient(supabaseUrl, supabaseKey);

  let payload: LinearWebhookPayload;
  try {
    payload = await req.json();
  } catch (e) {
    console.error("[kei45_linear_webhook] failed to parse request body as JSON:", e);
    return new Response("invalid JSON", { status: 400 });
  }

  if (payload.type !== "Issue") {
    return new Response(JSON.stringify({ skipped: "non-issue payload" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }

  const issue = payload.data;
  if (!issue?.identifier || !issue?.title) {
    return new Response("missing identifier/title", { status: 400 });
  }

  const status = STATE_MAP[issue.state?.name ?? ""] ?? "available";
  const priority = PRIORITY_MAP[issue.priority ?? 0] ?? 3;
  const tags = issue.labels?.nodes?.map((n) => n.name) ?? [];

  const { error } = await supabase
    .from("tasks")
    .upsert({
      id: issue.identifier,
      title: issue.title,
      status,
      priority,
      tags,
      linear_url: issue.url,
      updated_at: new Date().toISOString(),
    }, { onConflict: "id" });

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { "content-type": "application/json" },
    });
  }

  return new Response(JSON.stringify({
    upserted: issue.identifier,
    status,
    priority,
    action: payload.action,
  }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
});
