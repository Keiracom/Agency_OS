/**
 * UI-side types for the campaigns components — extracted from
 * frontend/data/mock-campaigns.ts during Tier 2 stranded-route cleanup
 * (2026-05-09). Different from the API contract types in
 * @/lib/api/types.ts: these describe the display shape consumed by
 * CampaignCard / CampaignSequence / CampaignMetrics / etc.
 *
 * Re-exports ChannelType + channelEmoji from the shared types module
 * so component callsites can import one path.
 */

export type { ChannelType } from "@/data/types";
export { channelEmoji } from "@/data/types";

import type { ChannelType } from "@/data/types";

export type CampaignStatus = "active" | "paused" | "draft" | "complete";

export type SequenceStepStatus = "completed" | "active" | "upcoming";

export interface MetricData {
  value: number | string;
  label: string;
  change: number;
  isPercentage?: boolean;
}

export interface SequenceStep {
  day: number;
  channel: ChannelType;
  label: string;
  status: SequenceStepStatus;
  stats: string;
}

export interface Campaign {
  id: string;
  name: string;
  isAI: boolean;
  channels: ChannelType[];
  status: CampaignStatus;
  priority: number;
  metrics: MetricData[];
  sequence: SequenceStep[];
  aiInsight?: string;
}

export const statusStyles: Record<
  CampaignStatus,
  { bg: string; text: string; dot: string }
> = {
  active: { bg: "bg-emerald-50", text: "text-emerald-600", dot: "●" },
  paused: { bg: "bg-amber-50", text: "text-amber-600", dot: "◐" },
  draft: { bg: "bg-slate-100", text: "text-ink-3", dot: "○" },
  complete: { bg: "bg-panel", text: "text-ink-2", dot: "✓" },
};
