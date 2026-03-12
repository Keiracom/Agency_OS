"use client";

/**
 * FILE: frontend/app/dashboard/leads/page.tsx
 * PURPOSE: Animated Lead Scoreboard - live leaderboard sorted by ALS score
 * SPRINT: Dashboard Sprint 2 - Step 6/8 Animated Lead Scoreboard
 * SSOT: lead_scoreboard_vision (ffd41389-645a-47c8-91d6-017b6cebe7ae)
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useState, useMemo } from "react";
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
} from "lucide-react";

// Tier filter type
type TierFilter = "all" | "hot" | "warm" | "cool" | "cold";

/**
 * Derive a 0–100 enrichment depth from available Lead fields.
 * - Basic fields (10 total) contribute up to 70 points.
 * - sdk_enrichment presence adds 30 points.
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
  // Fall back to score-based tier
  const score = lead.propensity_score ?? 0;
  return getALSTier(score) as TierFilter;
}

export default function LeadsScoreboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<TierFilter>("all");
  const [sortAscending, setSortAscending] = useState(false);

  // Fetch real leads data
  const { leads, total, isLoading, error } = useLeads({ page_size: 100 });

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
      // TODO: wire meetingsBooked per lead when available
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
      const name = [lead.first_name, lead.last_name]
        .filter(Boolean)
        .join(" ");
      const matchesSearch =
        name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (lead.company ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.email.toLowerCase().includes(searchQuery.toLowerCase());

      const tier = getLeadTierFilter(lead);
      const matchesTier = selectedTier === "all" || tier === selectedTier;

      return matchesSearch && matchesTier;
    });

    // Sort by ALS score (descending by default = leaderboard style)
    filtered.sort((a, b) => {
      const aScore = a.propensity_score ?? 0;
      const bScore = b.propensity_score ?? 0;
      return sortAscending ? aScore - bScore : bScore - aScore;
    });

    return filtered;
  }, [leads, searchQuery, selectedTier, sortAscending]);

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
                style={{ backgroundColor: "rgba(212, 149, 106, 0.15)", color: "#D4956A" }}
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
            style={{ backgroundColor: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            {([
              { key: "all" as const, label: "All", icon: null, count: stats.total, color: undefined },
              { key: "hot" as const, label: "Hot", icon: <Flame className="w-4 h-4" />, count: stats.hot, color: "#D4956A" },
              { key: "warm" as const, label: "Warm", icon: <Zap className="w-4 h-4" />, count: stats.warm, color: "#EAB308" },
              { key: "cool" as const, label: "Cool", icon: <Moon className="w-4 h-4" />, count: stats.cool, color: "#6B7280" },
              { key: "cold" as const, label: "Cold", icon: <Snowflake className="w-4 h-4" />, count: stats.cold, color: "#374151" },
            ]).map(({ key, label, icon, count, color }) => (
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
            <span className="w-8 text-xs font-semibold text-text-muted uppercase tracking-wider">#</span>
            <span className="w-16 text-xs font-semibold text-text-muted uppercase tracking-wider">Score</span>
            <span className="flex-1 text-xs font-semibold text-text-muted uppercase tracking-wider">Lead</span>
            <span className="w-24 text-xs font-semibold text-text-muted uppercase tracking-wider">Enrichment</span>
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
                      const name = [lead.first_name, lead.last_name]
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
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center py-12"
                  >
                    <p className="text-text-muted">No leads match your filters</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </LayoutGroup>
          )}
        </motion.div>

        {/* Footer Stats */}
        <div className="flex items-center justify-between text-sm text-text-muted">
          <p>
            Showing <span className="font-mono font-medium text-text-secondary">{sortedLeads.length}</span> of{" "}
            <span className="font-mono font-medium text-text-secondary">{stats.total}</span> leads
          </p>
          <p className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-success animate-pulse" />
            Live updates enabled
          </p>
        </div>
      </div>
    </AppShell>
  );
}
