"use client";

/**
 * FILE: frontend/components/campaigns/TargetingFilters.tsx
 * PURPOSE: Campaign targeting filters - ALS tier, hiring, revenue, funding
 * SPRINT: Step 5/8 - Campaign Targeting Filters + ICP Auto-Populate
 * SSOT: campaign_targeting_gaps reference
 */

import { useState } from "react";
import {
  Flame,
  ThermometerSun,
  Snowflake,
  IceCreamCone,
  Briefcase,
  DollarSign,
  TrendingUp,
  Sparkles,
} from "lucide-react";

// ALS Tier options
const ALS_TIERS = [
  { id: "Hot", icon: Flame, color: "text-red-500", bg: "bg-red-500/20" },
  { id: "Warm", icon: ThermometerSun, color: "text-orange-400", bg: "bg-orange-400/20" },
  { id: "Cool", icon: Snowflake, color: "text-blue-400", bg: "bg-blue-400/20" },
  { id: "Cold", icon: IceCreamCone, color: "text-slate-400", bg: "bg-slate-400/20" },
] as const;

// Funding stage options
const FUNDING_STAGES = [
  { id: "Seed", label: "Seed" },
  { id: "Series A", label: "Series A" },
  { id: "Series B", label: "Series B" },
  { id: "Series C+", label: "Series C+" },
  { id: "Bootstrapped", label: "Bootstrapped" },
  { id: "Unknown", label: "Unknown" },
] as const;

export interface TargetingFiltersData {
  alsTiers: string[];
  hiringOnly: boolean;
  revenueMinAud: number | null;
  revenueMaxAud: number | null;
  fundingStages: string[];
}

interface TargetingFiltersProps {
  value: TargetingFiltersData;
  onChange: (value: TargetingFiltersData) => void;
  icpSuggested?: {
    alsTiers?: string[];
    hiringOnly?: boolean;
    revenueMinAud?: number | null;
    revenueMaxAud?: number | null;
    fundingStages?: string[];
  } | null;
}

export function TargetingFilters({
  value,
  onChange,
  icpSuggested,
}: TargetingFiltersProps) {
  const toggleAlsTier = (tier: string) => {
    const newTiers = value.alsTiers.includes(tier)
      ? value.alsTiers.filter((t) => t !== tier)
      : [...value.alsTiers, tier];
    onChange({ ...value, alsTiers: newTiers });
  };

  const toggleFundingStage = (stage: string) => {
    const newStages = value.fundingStages.includes(stage)
      ? value.fundingStages.filter((s) => s !== stage)
      : [...value.fundingStages, stage];
    onChange({ ...value, fundingStages: newStages });
  };

  const isSuggestedField = (field: keyof TargetingFiltersData) => {
    if (!icpSuggested) return false;
    return icpSuggested[field] !== undefined;
  };

  return (
    <div className="space-y-6">
      {/* ALS Tier Filter */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <label className="block text-sm font-medium text-text-primary">
            Lead Quality (ALS Tier)
          </label>
          {isSuggestedField("alsTiers") && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-primary/20 text-accent-primary">
              <Sparkles className="w-3 h-3" />
              Suggested by Maya
            </span>
          )}
        </div>
        <div className="grid grid-cols-4 gap-3">
          {ALS_TIERS.map((tier) => {
            const Icon = tier.icon;
            const isSelected = value.alsTiers.includes(tier.id);
            return (
              <button
                key={tier.id}
                onClick={() => toggleAlsTier(tier.id)}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                  isSelected
                    ? `${tier.bg} border-current ${tier.color}`
                    : "bg-bg-surface border-border-default hover:border-border-strong"
                }`}
              >
                <Icon
                  className={`w-6 h-6 ${isSelected ? tier.color : "text-text-muted"}`}
                />
                <span
                  className={`text-sm font-medium ${
                    isSelected ? tier.color : "text-text-secondary"
                  }`}
                >
                  {tier.id}
                </span>
              </button>
            );
          })}
        </div>
        <p className="text-xs text-text-muted mt-2">
          Hot = High intent | Warm = Good fit | Cool = Potential | Cold = Low priority
        </p>
      </div>

      {/* Hiring Signal Filter */}
      <div className="p-4 rounded-xl bg-bg-surface border border-border-default">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text-primary">
                  Only Companies Actively Hiring
                </span>
                {isSuggestedField("hiringOnly") && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-primary/20 text-accent-primary">
                    <Sparkles className="w-3 h-3" />
                    Suggested
                  </span>
                )}
              </div>
              <p className="text-xs text-text-muted">
                Filter to companies with active job postings (higher budget signal)
              </p>
            </div>
          </div>
          <button
            onClick={() => onChange({ ...value, hiringOnly: !value.hiringOnly })}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
              value.hiringOnly ? "bg-green-500" : "bg-border-strong"
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition ${
                value.hiringOnly ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
        </div>
      </div>

      {/* Revenue Range Filter */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
            <DollarSign className="w-4 h-4 text-emerald-500" />
          </div>
          <label className="block text-sm font-medium text-text-primary">
            Company Revenue Range (AUD)
          </label>
          {isSuggestedField("revenueMinAud") && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-primary/20 text-accent-primary">
              <Sparkles className="w-3 h-3" />
              Suggested by Maya
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-text-muted mb-1.5">Minimum</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
                $
              </span>
              <input
                type="number"
                value={value.revenueMinAud ?? ""}
                onChange={(e) =>
                  onChange({
                    ...value,
                    revenueMinAud: e.target.value ? Number(e.target.value) : null,
                  })
                }
                placeholder="0"
                className="w-full pl-7 pr-4 py-2.5 rounded-lg text-sm bg-bg-surface border border-border-default text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all font-mono"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1.5">Maximum</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
                $
              </span>
              <input
                type="number"
                value={value.revenueMaxAud ?? ""}
                onChange={(e) =>
                  onChange({
                    ...value,
                    revenueMaxAud: e.target.value ? Number(e.target.value) : null,
                  })
                }
                placeholder="No limit"
                className="w-full pl-7 pr-4 py-2.5 rounded-lg text-sm bg-bg-surface border border-border-default text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all font-mono"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Funding Stage Filter */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-purple-500" />
          </div>
          <label className="block text-sm font-medium text-text-primary">
            Funding Stage
          </label>
          {isSuggestedField("fundingStages") && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-primary/20 text-accent-primary">
              <Sparkles className="w-3 h-3" />
              Suggested by Maya
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {FUNDING_STAGES.map((stage) => {
            const isSelected = value.fundingStages.includes(stage.id);
            return (
              <button
                key={stage.id}
                onClick={() => toggleFundingStage(stage.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  isSelected
                    ? "bg-purple-500/20 text-purple-400 border border-purple-500/50"
                    : "bg-bg-surface text-text-secondary border border-border-default hover:border-border-strong"
                }`}
              >
                {stage.label}
              </button>
            );
          })}
        </div>
        <p className="text-xs text-text-muted mt-2">
          Select one or more funding stages, or leave empty for all
        </p>
      </div>
    </div>
  );
}

export default TargetingFilters;
