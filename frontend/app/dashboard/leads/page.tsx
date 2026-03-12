"use client";

/**
 * FILE: frontend/app/dashboard/leads/page.tsx
 * PURPOSE: Animated Lead Scoreboard - live leaderboard sorted by ALS score
 * SPRINT: Dashboard Sprint 2 - Step 6/8 Animated Lead Scoreboard
 * SSOT: lead_scoreboard_vision (ffd41389-645a-47c8-91d6-017b6cebe7ae)
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 *
 * DIRECTIVE #183 — Added onboarding progress states + auto-poll
 */

import { useState, useMemo, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence, LayoutGroup } from "framer-motion";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { SplitFlapCounterBar } from "@/components/leads/SplitFlapCounter";
import { LeadScoreboardRow, getALSTier } from "@/components/leads/LeadScoreboardRow";
import { useLeads } from "@/hooks/use-leads";
import type { Lead } from "@/lib/api/types";
import {
  Search,
  Filter,
  Plus,
  Download,
  Upload,
  Flame,
  Zap,
  Moon,
  Snowflake,
  ArrowUpDown,
  Loader2,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

// Tier filter type
type TierFilter = "all" | "hot" | "warm" | "cool" | "cold";

// Onboarding progress stages
const ONBOARDING_STAGES = [
  { label: "Discovering prospects in your market...", minSec: 0, maxSec: 30 },
  { label: "Enriching company data...", minSec: 30, maxSec: 90 },
  { label: "Scoring leads with AI...", minSec: 90, maxSec: 150 },
];

/**
 * Derive a 0–100 enrichment depth from available Lead fields.
 */
function getEnrichmentDepth(lead: Lead): number {
  const fields = [
    lead.first_name,
    lead.last_name,
    lead.title,
    lead.company,
    lead.phone,
    lead.linkedin_url,
    lead.domain,
    lead.organization_industry,
    lead.organization_employee_count,
    lead.organization_country,
  ];
  const filled = fields.filter((f) => f !== null && f !== undefined).length;
  const base = Math.round((filled / fields.length) * 70);
  const sdkBonus = lead.sdk_enrichment ? 30 : 0;
  return Math.min(100, base + sdkBonus);
}

/** Map propensity_tier (or derive from score) to the TierFilter type */
function getLeadTierFilter(lead: Lead): TierFilter {
  if (lead.propensity_tier === "dead") return "cold";
  if (lead.propensity_tier) return lead.propensity_tier as TierFilter;
  const score = lead.propensity_score ?? 0;
  return getALSTier(score) as TierFilter;
}

export default function LeadsScoreboardPage() {
  const searchParams = useSearchParams();
  const isOnboarding = searchParams.get("onboarding") === "true";

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<TierFilter>("all");
  const [sortAscending, setSortAscending] = useState(false);

  // Onboarding progress state
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [pipelineReady, setPipelineReady] = useState(false);
  const elapsedRef = useRef<NodeJS.Timeout | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch real leads data
  const { leads, total, isLoading, error, refresh } = useLeads({
    page_size: 100,
  });

  // When onboarding mode: tick elapsed seconds + poll every 10s for leads
  useEffect(() => {
    if (!isOnboarding) return;

    // Start elapsed timer
    elapsedRef.current = setInterval(() => {
      setElapsedSeconds((s) => s + 1);
    }, 1000);

    // Poll for leads every 10s
    pollRef.current = setInterval(() => {
      refresh();
    }, 10_000);

    return () => {
      if (elapsedRef.current) clearInterval(elapsedRef.current);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isOnboarding, refresh]);

  // When leads appear in onboarding mode, mark pipeline ready + stop timers
  useEffect(() => {
    if (isOnboarding && leads.length > 0 && !pipelineReady) {
      setPipelineReady(true);
      if (elapsedRef.current) clearInterval(elapsedRef.current);
      if (pollRef.current) clearInterval(pollRef.current);
    }
  }, [isOnboarding, leads.length, pipelineReady]);

  // Determine current onboarding stage
  const currentStageIndex = useMemo(() => {
    if (pipelineReady) return -1; // done
    for (let i = ONBOARDING_STAGES.length - 1; i >= 0; i--) {
      if (elapsedSeconds >= ONBOARDING_STAGES[i].minSec) return i;
    }
    return 0;
  }, [elapsedSeconds, pipelineReady]);

  // Progress percentage within current stage (for animated bar)
  const stageProgress = useMemo(() => {
    if (pipelineReady) return 100;
    const stage = ONBOARDING_STAGES[currentStageIndex];
    if (!stage) return 0;
    const range = stage.maxSec - stage.minSec;
    const within = elapsedSeconds - stage.minSec;
    // Stage fills to 90% max (leaves room until real data arrives)
    return Math.min(90, Math.round((within / range) * 100));
  }, [elapsedSeconds, currentStageIndex, pipelineReady]);

  // Overall progress (0-100) across all stages
  const overallProgress = useMemo(() => {
    if (pipelineReady) return 100;
    const totalDuration =
      ONBOARDING_STAGES[ONBOARDING_STAGES.length - 1].maxSec;
    return Math.min(95, Math.round((elapsedSeconds / totalDuration) * 100));
  }, [elapsedSeconds, pipelineReady]);

  // Calculate stats from real data
  const stats = useMemo(() => {
    return {
      total,
      enriched: leads.filter(
        (l) =>
          l.status === "enriched" ||
          l.status === "scored" ||
          l.sdk_enrichment !== null
      ).length,
      avgALS:
        leads.length > 0
          ? Math.round(
              leads.reduce((acc, l) => acc + (l.propensity_score ?? 0), 0) /
                leads.length
            )
          : 0,
      meetingsBooked: 0,
      hot: leads.filter((l) => getLeadTierFilter(l) === "hot").length,
      warm: leads.filter((l) => getLeadTierFilter(l) === "warm").length,
      cool: leads.filter((l) => getLeadTierFilter(l) === "cool").length,
      cold: leads.filter((l) => getLeadTierFilter(l) === "cold").length,
    };
  }, [leads, total]);

  // Filter and sort leads
  const sortedLeads = useMemo(() => {
    const filtered = leads.filter((lead) => {
      const name = [lead.first_name, lead.last_name].filter(Boolean).join(" ");
      const matchesSearch =
        name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (lead.company ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.email.toLowerCase().includes(searchQuery.toLowerCase());
      const tier = getLeadTierFilter(lead);
      const matchesTier = selectedTier === "all" || tier === selectedTier;
      return matchesSearch && matchesTier;
    });
    filtered.sort((a, b) => {
      const aScore = a.propensity_score ?? 0;
      const bScore = b.propensity_score ?? 0;
      return sortAscending ? aScore - bScore : bScore - aScore;
    });
    return filtered;
  }, [leads, searchQuery, selectedTier, sortAscending]);

  // ── Show onboarding progress when ?onboarding=true and no leads yet ──
  const showOnboardingProgress = isOnboarding && leads.length === 0 && !pipelineReady;

  return (
    <AppShell pageTitle="Lead Scoreboard">
      <div className="space-y-6">
        {/* Header Bar */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-serif text-text-primary flex items-center gap-3">
              Lead Scoreboard
              <motion.span
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="px-3 py-1 rounded-md font-mono text-sm font-semibold"
                style={{
                  backgroundColor: "rgba(212, 149, 106, 0.15)",
                  color: "#D4956A",
                }}
              >
                LIVE
              </motion.span>
            </h1>
            <p className="text-sm text-text-muted mt-1">
              Real-time lead rankings by Adaptive Lead Score
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium glass-surface hover:bg-bg-surface-hover transition-colors">
              <Download className="w-4 h-4" />
              Export
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium glass-surface hover:bg-bg-surface-hover transition-colors">
              <Upload className="w-4 h-4" />
              Import
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium gradient-premium text-text-primary hover:opacity-90 transition-opacity">
              <Plus className="w-4 h-4" />
              Add Lead
            </button>
          </div>
        </div>

        {/* ── ONBOARDING PROGRESS BANNER ── */}
        <AnimatePresence>
          {showOnboardingProgress && (
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.4 }}
              className="rounded-2xl p-6 space-y-5"
              style={{
                background:
                  "linear-gradient(135deg, rgba(212, 149, 106, 0.08) 0%, rgba(16, 185, 129, 0.05) 100%)",
                border: "1px solid rgba(212, 149, 106, 0.25)",
              }}
            >
              {/* Top row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-xl flex items-center justify-center"
                    style={{
                      backgroundColor: "rgba(212, 149, 106, 0.15)",
                    }}
                  >
                    <Sparkles className="w-5 h-5 text-accent-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text-primary">
                      Building your pipeline
                    </p>
                    <p className="text-xs text-text-muted">
                      Maya is sourcing leads based on your ICP
                    </p>
                  </div>
                </div>
                <span className="font-mono text-sm text-accent-primary font-semibold">
                  {overallProgress}%
                </span>
              </div>

              {/* Overall progress bar */}
              <div
                className="w-full h-2 rounded-full overflow-hidden"
                style={{ backgroundColor: "rgba(255,255,255,0.06)" }}
              >
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    background:
                      "linear-gradient(90deg, #D4956A 0%, #10B981 100%)",
                  }}
                  initial={{ width: "5%" }}
                  animate={{ width: `${overallProgress}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
              </div>

              {/* Stage steps */}
              <div className="space-y-3">
                {ONBOARDING_STAGES.map((stage, i) => {
                  const isDone = i < currentStageIndex;
                  const isActive = i === currentStageIndex;
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
                        style={{
                          backgroundColor: isDone
                            ? "rgba(16, 185, 129, 0.2)"
                            : isActive
                            ? "rgba(212, 149, 106, 0.2)"
                            : "rgba(255,255,255,0.05)",
                        }}
                      >
                        {isDone ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-status-success" />
                        ) : isActive ? (
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{
                              repeat: Infinity,
                              duration: 1,
                              ease: "linear",
                            }}
                          >
                            <Loader2 className="w-3.5 h-3.5 text-accent-primary" />
                          </motion.div>
                        ) : (
                          <div className="w-2 h-2 rounded-full bg-text-muted" />
                        )}
                      </div>
                      <span
                        className="text-sm transition-colors duration-300"
                        style={{
                          color: isDone
                            ? "#10B981"
                            : isActive
                            ? "#D4956A"
                            : "#6B6560",
                        }}
                      >
                        {stage.label}
                      </span>
                      {isActive && (
                        <motion.span
                          className="ml-auto text-xs text-text-muted font-mono"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                        >
                          {stageProgress}%
                        </motion.span>
                      )}
                    </div>
                  );
                })}
              </div>

              <p className="text-xs text-text-muted text-center">
                Auto-refreshing every 10 seconds · this usually takes 2–3 minutes
              </p>
            </motion.div>
          )}

          {/* Pipeline ready celebration */}
          {isOnboarding && pipelineReady && leads.length > 0 && (
            <motion.div
              key="ready"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
              className="rounded-2xl p-5 flex items-center gap-4"
              style={{
                background:
                  "linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
              }}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: "rgba(16, 185, 129, 0.15)" }}
              >
                <CheckCircle2 className="w-6 h-6 text-status-success" />
              </div>
              <div>
                <p className="text-sm font-semibold text-status-success">
                  Your pipeline is ready!
                </p>
                <p className="text-xs text-text-muted mt-0.5">
                  {leads.length} leads discovered and scored for you
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Split-Flap Counter Bar */}
        <SplitFlapCounterBar
          totalLeads={stats.total}
          enrichedCount={stats.enriched}
          averageALS={stats.avgALS}
          meetingsBooked={stats.meetingsBooked}
        />

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
            <input
              type="text"
              placeholder="Search by name, company, or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm text-text-primary placeholder-text-muted transition-all"
              style={{
                backgroundColor: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            />
          </div>

          {/* Sort Toggle */}
          <button
            onClick={() => setSortAscending(!sortAscending)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium glass-surface hover:bg-bg-surface-hover transition-colors"
          >
            <ArrowUpDown className="w-4 h-4" />
            {sortAscending ? "Low → High" : "High → Low"}
          </button>

          {/* Tier Filter Tabs */}
          <div
            className="flex rounded-lg overflow-hidden"
            style={{
              backgroundColor: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            {(
              [
                { key: "all" as const, label: "All", icon: null, count: stats.total, color: undefined },
                { key: "hot" as const, label: "Hot", icon: <Flame className="w-4 h-4" />, count: stats.hot, color: "#D4956A" },
                { key: "warm" as const, label: "Warm", icon: <Zap className="w-4 h-4" />, count: stats.warm, color: "#EAB308" },
                { key: "cool" as const, label: "Cool", icon: <Moon className="w-4 h-4" />, count: stats.cool, color: "#6B7280" },
                { key: "cold" as const, label: "Cold", icon: <Snowflake className="w-4 h-4" />, count: stats.cold, color: "#374151" },
              ] as Array<{
                key: TierFilter;
                label: string;
                icon: React.ReactNode | null;
                count: number;
                color: string | undefined;
              }>
            ).map(({ key, label, icon, count, color }) => (
              <button
                key={key}
                onClick={() => setSelectedTier(key)}
                className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2 ${
                  selectedTier === key
                    ? "bg-bg-surface text-text-primary"
                    : "text-text-muted hover:text-text-secondary"
                }`}
                style={selectedTier === key && color ? { color } : {}}
              >
                {icon}
                {label}
                <span
                  className="text-xs font-mono px-1.5 py-0.5 rounded"
                  style={{ backgroundColor: "rgba(255,255,255,0.06)" }}
                >
                  {count}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Animated Leaderboard */}
        <motion.div
          className="glass-surface rounded-2xl p-5"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Leaderboard Header */}
          <div
            className="flex items-center gap-4 px-5 py-3 mb-4 rounded-xl"
            style={{ backgroundColor: "rgba(255,255,255,0.02)" }}
          >
            <span className="w-8 text-xs font-semibold text-text-muted uppercase tracking-wider">
              #
            </span>
            <span className="w-16 text-xs font-semibold text-text-muted uppercase tracking-wider">
              Score
            </span>
            <span className="flex-1 text-xs font-semibold text-text-muted uppercase tracking-wider">
              Lead
            </span>
            <span className="w-24 text-xs font-semibold text-text-muted uppercase tracking-wider">
              Enrichment
            </span>
            <span className="w-12"></span>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12">
              <motion.div
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ repeat: Infinity, duration: 1.5 }}
                className="text-text-muted font-mono text-sm"
              >
                Loading leads...
              </motion.div>
            </div>
          )}

          {/* Error State */}
          {error && !isLoading && (
            <div className="text-center py-12">
              <p className="text-text-muted text-sm">
                Failed to load leads. Please try refreshing.
              </p>
            </div>
          )}

          {/* Leaderboard Rows */}
          {!isLoading && !error && (
            <LayoutGroup>
              <AnimatePresence mode="popLayout">
                {sortedLeads.length > 0 ? (
                  <div className="space-y-2">
                    {sortedLeads.map((lead, index) => {
                      const name =
                        [lead.first_name, lead.last_name]
                          .filter(Boolean)
                          .join(" ") || lead.email;
                      return (
                        <LeadScoreboardRow
                          key={lead.id}
                          id={lead.id}
                          rank={index + 1}
                          alsScore={lead.propensity_score ?? 0}
                          companyName={lead.company ?? ""}
                          decisionMaker={name}
                          title={lead.title ?? ""}
                          enrichmentDepth={getEnrichmentDepth(lead)}
                          isNew={lead.status === "new"}
                          index={index}
                        />
                      );
                    })}
                  </div>
                ) : !showOnboardingProgress ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center py-12"
                  >
                    <p className="text-text-muted">
                      {searchQuery || selectedTier !== "all"
                        ? "No leads match your filters"
                        : "No leads yet"}
                    </p>
                  </motion.div>
                ) : (
                  // Skeleton rows while onboarding is in progress
                  <div className="space-y-3">
                    {[...Array(5)].map((_, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: [0.3, 0.6, 0.3] }}
                        transition={{
                          repeat: Infinity,
                          duration: 1.5,
                          delay: i * 0.15,
                        }}
                        className="flex items-center gap-4 px-5 py-4 rounded-xl"
                        style={{
                          backgroundColor: "rgba(255,255,255,0.02)",
                        }}
                      >
                        <div
                          className="w-8 h-4 rounded"
                          style={{
                            backgroundColor: "rgba(255,255,255,0.06)",
                          }}
                        />
                        <div
                          className="w-16 h-4 rounded"
                          style={{
                            backgroundColor: "rgba(255,255,255,0.06)",
                          }}
                        />
                        <div className="flex-1 flex items-center gap-3">
                          <div
                            className="w-8 h-8 rounded-full"
                            style={{
                              backgroundColor: "rgba(255,255,255,0.06)",
                            }}
                          />
                          <div className="space-y-1.5">
                            <div
                              className="h-3 rounded"
                              style={{
                                width: `${100 + i * 30}px`,
                                backgroundColor: "rgba(255,255,255,0.06)",
                              }}
                            />
                            <div
                              className="h-2.5 rounded"
                              style={{
                                width: `${70 + i * 20}px`,
                                backgroundColor: "rgba(255,255,255,0.04)",
                              }}
                            />
                          </div>
                        </div>
                        <div
                          className="w-24 h-2 rounded-full"
                          style={{
                            backgroundColor: "rgba(255,255,255,0.06)",
                          }}
                        />
                      </motion.div>
                    ))}
                  </div>
                )}
              </AnimatePresence>
            </LayoutGroup>
          )}
        </motion.div>

        {/* Footer Stats */}
        <div className="flex items-center justify-between text-sm text-text-muted">
          <p>
            Showing{" "}
            <span className="font-mono font-medium text-text-secondary">
              {sortedLeads.length}
            </span>{" "}
            of{" "}
            <span className="font-mono font-medium text-text-secondary">
              {stats.total}
            </span>{" "}
            leads
          </p>
          <p className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-success animate-pulse" />
            {isOnboarding && !pipelineReady
              ? "Sourcing in progress..."
              : "Live updates enabled"}
          </p>
        </div>
      </div>
    </AppShell>
  );
}
