"use client";

import { ALSTierBadge, type ALSTier } from "./ALSTierBadge";

/**
 * ALS breakdown scores
 */
export interface ALSBreakdown {
  /** Data quality score (0-20) */
  dataQuality: number;
  /** Authority score (0-25) */
  authority: number;
  /** Company fit score (0-25) */
  companyFit: number;
  /** Timing score (0-15) */
  timing: number;
  /** Risk score (0-15) */
  risk: number;
}

/**
 * ALSScorecard props
 */
export interface ALSScorecardProps {
  /** Overall ALS score (0-100) */
  score: number;
  /** Score breakdown components */
  breakdown: ALSBreakdown;
}

/**
 * Max values for each breakdown component
 */
const breakdownConfig = {
  dataQuality: { label: "Data Quality", max: 20 },
  authority: { label: "Authority", max: 25 },
  companyFit: { label: "Company Fit", max: 25 },
  timing: { label: "Timing", max: 15 },
  risk: { label: "Risk", max: 15 },
};

/**
 * Get tier from score
 */
function getTierFromScore(score: number): ALSTier {
  if (score >= 85) return "hot";
  if (score >= 60) return "warm";
  if (score >= 35) return "cool";
  if (score >= 20) return "cold";
  return "dead";
}

/**
 * Get tier color for progress bar
 */
function getTierColor(score: number, max: number): string {
  const percentage = (score / max) * 100;
  if (percentage >= 85) return "bg-[#EF4444]";
  if (percentage >= 60) return "bg-[#F97316]";
  if (percentage >= 35) return "bg-[#3B82F6]";
  if (percentage >= 20) return "bg-[#6B7280]";
  return "bg-[#D1D5DB]";
}

/**
 * ALSScorecard - ALS score breakdown component
 *
 * Features:
 * - Large score number with tier badge
 * - 5 progress bars for score components
 * - Score/max display for each component
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Card background: #FFFFFF (card-bg)
 * - Card border: #E2E8F0 (card-border)
 * - Text primary: #1E293B (text-primary)
 * - Text secondary: #64748B (text-secondary)
 *
 * Usage:
 * ```tsx
 * <ALSScorecard
 *   score={87}
 *   breakdown={{
 *     dataQuality: 18,
 *     authority: 22,
 *     companyFit: 25,
 *     timing: 10,
 *     risk: 12,
 *   }}
 * />
 * ```
 */
export function ALSScorecard({ score, breakdown }: ALSScorecardProps) {
  const tier = getTierFromScore(score);

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
          ALS Score Breakdown
        </h2>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Score Display */}
        <div className="flex items-center gap-4 mb-6">
          <div className="text-5xl font-bold text-[#1E293B]">{score}</div>
          <ALSTierBadge tier={tier} size="lg" />
        </div>

        {/* Breakdown Bars */}
        <div className="space-y-4">
          {(Object.keys(breakdownConfig) as (keyof ALSBreakdown)[]).map(
            (key) => {
              const config = breakdownConfig[key];
              const value = breakdown[key];
              const percentage = (value / config.max) * 100;
              const barColor = getTierColor(value, config.max);

              return (
                <div key={key}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-[#64748B]">
                      {config.label}
                    </span>
                    <span className="text-sm text-[#94A3B8]">
                      {value}/{config.max}
                    </span>
                  </div>
                  <div className="h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            }
          )}
        </div>
      </div>
    </div>
  );
}

export default ALSScorecard;
