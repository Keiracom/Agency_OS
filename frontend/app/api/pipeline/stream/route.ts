/**
 * FILE: app/api/pipeline/stream/route.ts
 * PURPOSE: SSE endpoint streaming ProspectCards from business_universe table
 * Sends initial 50 cards then polls every 5s for new arrivals
 */

import { createClient } from "@supabase/supabase-js";
import type { ProspectCard, AffordabilityBand, IntentBand, VulnerabilityReport } from "@/lib/types/prospect-card";

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

/** Derive intent band from propensity score */
function toIntentBand(score: number | null): IntentBand {
  if (!score) return "UNKNOWN";
  if (score >= 70) return "STRUGGLING";
  if (score >= 50) return "TRYING";
  if (score >= 30) return "DABBLING";
  return "NOT_TRYING";
}

/** Derive affordability band from propensity score */
function toAffordabilityBand(score: number | null): AffordabilityBand {
  if (!score) return "UNKNOWN";
  if (score >= 70) return "HIGH";
  if (score >= 40) return "MEDIUM";
  return "LOW";
}

/** Extract subject + body from outreach_messages.email string */
function extractEmailDraft(outreachMessages: Record<string, unknown> | null): {
  subject: string | null;
  body: string | null;
} {
  if (!outreachMessages) return { subject: null, body: null };
  const email = outreachMessages.email;
  if (typeof email !== "string" || !email) return { subject: null, body: null };

  // If the email has "Subject:" prefix, split it
  const subjectMatch = email.match(/^Subject:\s*(.+?)(?:\n|$)/i);
  if (subjectMatch) {
    const subject = subjectMatch[1].trim();
    const body = email.replace(/^Subject:.*?\n/i, "").trim();
    return { subject, body };
  }

  // Otherwise first line becomes subject
  const lines = email.split("\n").filter((l) => l.trim());
  return {
    subject: lines[0]?.trim() ?? null,
    body: lines.slice(1).join("\n").trim() || email,
  };
}

/** Map a business_universe row to ProspectCard shape */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function rowToCard(row: Record<string, any>): ProspectCard {
  const suburb: string = row.suburb ?? row.gmb_city ?? "";
  const state: string = row.state ?? "";
  const locationDisplay =
    row.location_display ??
    (suburb && state ? `${suburb}, ${state}` : suburb || state || "Australia");

  const propensity: number | null = row.propensity_score ?? null;
  const intBand: IntentBand = row.intent_band ?? toIntentBand(propensity);
  const intScore: number = row.intent_score ?? propensity ?? 0;
  const affordBand: AffordabilityBand =
    row.affordability_band ?? toAffordabilityBand(propensity);

  const outreachMessages: Record<string, unknown> | null =
    row.outreach_messages ?? null;
  const { subject: draftSubject, body: draftBody } =
    extractEmailDraft(outreachMessages);

  // is_running_ads: explicit column or derived from paid keyword data
  const isRunningAds: boolean =
    row.is_running_ads ??
    Boolean(row.dfs_paid_keywords && row.dfs_paid_keywords > 0);

  // services: from tech_stack or best_match_service
  const services: string[] = Array.isArray(row.tech_stack)
    ? (row.tech_stack as string[]).slice(0, 5)
    : row.best_match_service
    ? [row.best_match_service]
    : [];

  // evidence: from score_reason
  const evidence: string[] = row.score_reason ? [row.score_reason] : [];

  // vulnerability_report
  const vulnReport: VulnerabilityReport | null =
    row.vulnerability_report ?? null;

  return {
    domain: row.domain ?? "",
    company_name: row.display_name ?? row.domain ?? "",
    location: locationDisplay,
    location_suburb: suburb,
    location_state: state,
    location_display: locationDisplay,

    affordability_band: affordBand,
    affordability_score: propensity ?? 0,
    intent_band: intBand,
    intent_score: intScore,

    services,
    evidence,

    headline_signal: row.score_reason ?? null,
    recommended_service: row.best_match_service ?? null,
    outreach_angle: outreachMessages?.outreach_angle
      ? String(outreachMessages.outreach_angle)
      : null,

    dm_name: row.dm_name ?? null,
    dm_title: row.dm_title ?? null,
    dm_email: row.dm_email ?? null,
    dm_email_verified: Boolean(row.dm_email_verified),
    dm_email_source: row.dm_source ?? row.dm_email_source ?? null,
    dm_email_confidence: row.dm_email_confidence ?? null,
    dm_mobile: row.dm_phone ?? null,
    dm_linkedin_url: row.dm_linkedin_url ?? null,
    dm_confidence: row.dm_confidence ?? null,

    draft_email_subject: draftSubject,
    draft_email_body: draftBody,

    gmb_rating: row.gmb_rating ?? null,
    gmb_review_count: row.gmb_review_count ?? 0,

    is_running_ads: isRunningAds,

    competitors_top3: Array.isArray(row.competitors_top3)
      ? row.competitors_top3
      : [],
    competitor_count: row.competitor_count ?? 0,

    referring_domains: row.backlinks_count ?? row.referring_domains ?? 0,
    domain_rank: row.domain_rank ?? 0,
    backlink_trend: row.backlink_trend ?? "unknown",

    brand_position: row.brand_position ?? null,
    brand_gmb_showing: Boolean(row.brand_gmb_showing),
    brand_competitors_bidding: Boolean(row.brand_competitors_bidding),

    indexed_pages: row.indexed_pages ?? 0,
    email_cost_usd: row.enrichment_cost_usd ?? 0,

    vulnerability_report: vulnReport,

    pipeline_stage: row.pipeline_stage ?? undefined,
    pipeline_updated_at: row.pipeline_updated_at ?? undefined,
  };
}

const SELECT_COLS = [
  "id",
  "domain",
  "display_name",
  "suburb",
  "state",
  "location_display",
  "propensity_score",
  "reachability_score",
  "intent_band",
  "intent_score",
  "affordability_band",
  "best_match_service",
  "score_reason",
  "dm_name",
  "dm_title",
  "dm_email",
  "dm_email_verified",
  "dm_source",
  "dm_phone",
  "dm_linkedin_url",
  "dm_confidence",
  "gmb_rating",
  "gmb_review_count",
  "gmb_city",
  "dfs_paid_keywords",
  "dfs_paid_etv",
  "tech_stack",
  "domain_rank",
  "backlinks_count",
  "brand_competitors_bidding",
  "brand_position",
  "brand_gmb_showing",
  "vulnerability_report",
  "outreach_messages",
  "is_running_ads",
  "competitors_top3",
  "indexed_pages",
  "enrichment_cost_usd",
  "pipeline_stage",
  "pipeline_updated_at",
].join(",");

export async function GET(request: Request) {
  const supabase = getSupabase();
  const encoder = new TextEncoder();

  const transform = new TransformStream<Uint8Array, Uint8Array>();
  const writer = transform.writable.getWriter();

  const send = async (card: ProspectCard) => {
    const line = `event: prospect_card\ndata: ${JSON.stringify(card)}\n\n`;
    await writer.write(encoder.encode(line));
  };

  let lastSeenAt: string = new Date(0).toISOString();

  // ── Initial load ─────────────────────────────────────────────────────────
  (async () => {
    try {
      const { data: initialRows, error } = await supabase
        .from("business_universe")
        .select(SELECT_COLS)
        .gte("pipeline_stage", 4)
        .order("pipeline_updated_at", { ascending: false })
        .limit(50);

      if (error) {
        console.error("[pipeline/stream] initial load error:", error.message);
      } else if (initialRows && initialRows.length > 0) {
        const rows = initialRows as unknown as Record<string, unknown>[];
        for (const row of rows) {
          await send(rowToCard(row));
        }
        // Track newest timestamp for polling
        const newest = (rows[0] as Record<string, unknown>).pipeline_updated_at;
        if (newest && typeof newest === "string") lastSeenAt = newest;
      }

      // ── Polling loop ────────────────────────────────────────────────────
      const poll = setInterval(async () => {
        try {
          const { data: newRows } = await supabase
            .from("business_universe")
            .select(SELECT_COLS)
            .gte("pipeline_stage", 4)
            .gt("pipeline_updated_at", lastSeenAt)
            .order("pipeline_updated_at", { ascending: true })
            .limit(20);

          if (newRows && newRows.length > 0) {
            const rows = newRows as unknown as Record<string, unknown>[];
            for (const row of rows) {
              await send(rowToCard(row));
            }
            const ts = (rows[rows.length - 1] as Record<string, unknown>).pipeline_updated_at;
            if (ts && typeof ts === "string") lastSeenAt = ts;
          }
        } catch (pollErr) {
          console.error("[pipeline/stream] poll error:", pollErr);
        }
      }, 5000);

      // Cleanup when client disconnects
      request.signal.addEventListener("abort", () => {
        clearInterval(poll);
        writer.close().catch(() => {});
      });
    } catch (err) {
      console.error("[pipeline/stream] setup error:", err);
      writer.close().catch(() => {});
    }
  })();

  return new Response(transform.readable, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
