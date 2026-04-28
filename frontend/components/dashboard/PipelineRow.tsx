/**
 * FILE: frontend/components/dashboard/PipelineRow.tsx
 * PURPOSE: Single pipeline row — left intent bar, rank, business name,
 *          DM info, status badge. PR3 dashboard rebuild.
 * REFERENCE: dashboard-master-agency-desk.html — `.k-card`,
 *            `.col-*` left-border colours, `.pipe-table` row styling.
 */

"use client";

import type { PipelineProspect, PipelineStage } from "@/lib/hooks/usePipelineData";

export type IntentTier = "struggling" | "trying" | "dabbling";

const INTENT_COLOR: Record<IntentTier, string> = {
  struggling: "var(--red)",     // immediate pain → highest urgency
  trying:     "var(--amber)",   // active but underperforming
  dabbling:   "#C9A88C",        // soft tan — light/exploratory
};

const STATUS_LABEL: Record<PipelineStage, { label: string; bg: string; fg: string }> = {
  discovered: { label: "Discovered",     bg: "rgba(12,10,8,0.06)",    fg: "var(--ink-3)" },
  enriched:   { label: "Enriched",       bg: "rgba(74,111,165,0.10)", fg: "var(--blue)" },
  contacted:  { label: "Contacted",      bg: "rgba(74,111,165,0.14)", fg: "var(--blue)" },
  replied:    { label: "Replied",        bg: "var(--amber-soft)",     fg: "var(--copper)" },
  meeting:    { label: "Meeting Booked", bg: "rgba(107,142,90,0.16)", fg: "var(--green)" },
  converted:  { label: "Won",            bg: "rgba(107,142,90,0.16)", fg: "var(--green)" },
};

/**
 * Map a propensity score into the prototype's intent tier.
 * TODO(api): replace with a server-side `intent_tier` once the BU
 * detector exposes it directly. Today we infer from `score`.
 */
export function inferIntent(score: number | null | undefined): IntentTier {
  if (score == null) return "dabbling";
  if (score >= 70) return "struggling";   // hot — most pain
  if (score >= 45) return "trying";        // mid
  return "dabbling";
}

interface Props {
  rank: number;
  prospect: PipelineProspect & { suppressed?: boolean };
  onClick?: (id: string) => void;
}

export function PipelineRow({ rank, prospect, onClick }: Props) {
  const intent = inferIntent(prospect.score);
  const status = prospect.suppressed
    ? { label: "Suppressed", bg: "rgba(181,90,76,0.10)", fg: "var(--red)" }
    : STATUS_LABEL[prospect.stage];

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onClick?.(prospect.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.(prospect.id);
        }
      }}
      className="group grid items-center gap-4 rounded-[8px] border border-rule bg-panel hover:border-amber hover:shadow-[0_2px_10px_rgba(212,149,106,0.08)] transition-all px-4 py-3 cursor-pointer"
      style={{
        gridTemplateColumns: "4px 36px 1fr auto auto",
        borderLeft: `4px solid ${INTENT_COLOR[intent]}`,
        paddingLeft: 0,
      }}
    >
      {/* Spacer for the inset border */}
      <span aria-hidden className="block h-full" />

      {/* Rank */}
      <div className="font-mono text-[12px] tracking-[0.06em] text-ink-3 text-right">
        {String(rank).padStart(2, "0")}
      </div>

      {/* Name + DM */}
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-display font-bold text-[15px] text-ink truncate">
            {prospect.company || prospect.name}
          </span>
          {prospect.vrGrade && <Badge text={prospect.vrGrade} />}
          {intent === "struggling" && (
            <Badge text="HOT" tone="hot" title="High propensity — most pain signals" />
          )}
        </div>
        <div className="font-mono text-[11px] text-ink-3 mt-0.5 truncate">
          {prospect.name || "—"}
          {prospect.lastChannel && (
            <span className="text-ink-3"> · last via {prospect.lastChannel}</span>
          )}
        </div>
      </div>

      {/* Score */}
      <div className="font-mono text-[13px] font-semibold text-copper tabular-nums px-2 hidden sm:block">
        {prospect.score ?? "—"}
      </div>

      {/* Status badge */}
      <span
        className="font-mono text-[10px] tracking-[0.1em] uppercase font-semibold px-2.5 py-[3px] rounded-full whitespace-nowrap"
        style={{ backgroundColor: status.bg, color: status.fg }}
      >
        {status.label}
      </span>
    </div>
  );
}

function Badge({
  text, tone = "neutral", title,
}: { text: string; tone?: "neutral" | "hot"; title?: string }) {
  if (tone === "hot") {
    return (
      <span
        title={title}
        className="font-mono text-[9px] tracking-[0.14em] uppercase font-bold px-1.5 py-[1px] rounded"
        style={{
          color: "var(--red)",
          backgroundColor: "rgba(181,90,76,0.10)",
          border: "1px solid rgba(181,90,76,0.30)",
        }}
      >
        {text}
      </span>
    );
  }
  return (
    <span
      className="font-display font-bold text-[10px] grid place-items-center w-5 h-5 rounded-[4px] text-white"
      style={{
        backgroundColor:
          text === "A" || text === "B" ? "var(--green)" :
          text === "C" ? "var(--amber)" :
          text === "D" ? "var(--copper)" :
          "var(--red)",
        color: text === "C" ? "var(--on-amber)" : "white",
      }}
    >
      {text}
    </span>
  );
}
