"use client";

/**
 * FILE: components/pipeline/ProspectCardView.tsx
 * PURPOSE: Single ProspectCard display — GlassCard style with DM panel + vulnerability report
 */

import { Zap, Star } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { DMContactPanel } from "./DMContactPanel";
import { VulnerabilityReportPanel } from "./VulnerabilityReportPanel";
import type { ProspectCard, IntentBand } from "@/lib/types/prospect-card";

interface ProspectCardViewProps {
  card: ProspectCard;
}

const INTENT_BAND_CONFIG: Record<
  IntentBand,
  { label: string; className: string }
> = {
  STRUGGLING: {
    label: "HOT",
    className:
      "text-amber bg-amber-glow border-amber/40 font-extrabold",
  },
  TRYING: {
    label: "WARM",
    className:
      "text-[#F59E0B] bg-[#F59E0B]/10 border-[#F59E0B]/30 font-bold",
  },
  DABBLING: {
    label: "DABBLING",
    className:
      "text-ink-2 bg-panel border-rule font-medium",
  },
  NOT_TRYING: {
    label: "NOT TRYING",
    className:
      "text-ink-3 bg-bg-panel border-rule font-medium",
  },
  UNKNOWN: {
    label: "UNKNOWN",
    className:
      "text-ink-3 bg-bg-panel border-rule font-medium",
  },
};

function IntentBadge({
  band,
  score,
}: {
  band: IntentBand;
  score: number;
}) {
  const config = INTENT_BAND_CONFIG[band];
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded border uppercase tracking-wide ${config.className}`}
    >
      {config.label}
      <span className="text-[10px] opacity-80">{score}</span>
    </span>
  );
}

export function ProspectCardView({ card }: ProspectCardViewProps) {
  const gmbStars =
    card.gmb_rating != null
      ? `★ ${card.gmb_rating.toFixed(1)} (${card.gmb_review_count} reviews)`
      : null;

  const evidenceToShow = card.evidence.slice(0, 3);

  return (
    <GlassCard className="p-0 overflow-hidden" hover>
      {/* Card header */}
      <div className="px-5 py-4 border-b border-rule">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <IntentBadge band={card.intent_band} score={card.intent_score} />
              {card.is_running_ads && (
                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-[#F97316]/10 border border-[#F97316]/30 text-[#F97316] uppercase">
                  <Zap className="w-2.5 h-2.5" />
                  Ads
                </span>
              )}
            </div>
            <h3 className="text-base font-bold text-ink leading-tight">
              {card.company_name}
            </h3>
            <p className="text-xs text-ink-3 font-mono mt-0.5">
              {card.location_display || card.domain}
            </p>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-2xl font-extrabold font-mono text-amber leading-none">
              {card.intent_score || card.affordability_score}
            </div>
            <div className="text-[10px] text-ink-3 font-mono uppercase mt-0.5">Score</div>
          </div>
        </div>

        {/* DM name */}
        {card.dm_name && (
          <p className="text-xs text-ink-2 mt-2">
            <span className="text-ink-3">Owner </span>
            <span className="font-semibold text-ink">{card.dm_name}</span>
            {card.dm_title && (
              <span className="text-ink-3"> • {card.dm_title}</span>
            )}
          </p>
        )}
      </div>

      {/* Body */}
      <div className="px-5 py-4 space-y-4">
        {/* Headline signal */}
        {card.headline_signal && (
          <div>
            <p className="text-sm italic text-ink leading-relaxed">
              &ldquo;{card.headline_signal}&rdquo;
            </p>
          </div>
        )}

        {/* Recommended service */}
        {card.recommended_service && (
          <div className="flex items-start gap-2">
            <span className="text-[11px] font-mono font-semibold uppercase tracking-wide text-ink-3 flex-shrink-0 pt-0.5">
              Service
            </span>
            <span className="text-xs text-amber font-semibold">
              {card.recommended_service}
            </span>
          </div>
        )}

        {/* Evidence bullets */}
        {evidenceToShow.length > 0 && (
          <ul className="space-y-1">
            {evidenceToShow.map((item, i) => (
              <li key={i} className="flex gap-2 text-xs text-ink-2">
                <span className="text-amber font-mono flex-shrink-0 mt-0.5">•</span>
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
        )}

        {/* GMB rating + competitors */}
        {(gmbStars || card.brand_competitors_bidding) && (
          <div className="flex flex-wrap gap-3">
            {gmbStars && (
              <span className="flex items-center gap-1 text-xs text-ink-2 font-mono">
                <Star className="w-3 h-3 text-amber fill-amber" />
                {gmbStars}
              </span>
            )}
            {card.brand_competitors_bidding && (
              <span className="text-xs text-[#F97316] font-mono">
                {card.competitors_top3.length > 0
                  ? `${card.competitors_top3.length} competitors bidding on brand`
                  : "Competitors bidding on brand name"}
              </span>
            )}
          </div>
        )}

        <div className="space-y-3">
          {/* DM Contact Panel */}
          <DMContactPanel card={card} />

          {/* Vulnerability Report Panel */}
          <VulnerabilityReportPanel report={card.vulnerability_report} />
        </div>
      </div>
    </GlassCard>
  );
}
