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

// Australian mock data - Melbourne digital agency prospects (tradies + dentists)
const MOCK_LEADS = [
  {
    id: "1",
    name: "Sarah Chen",
    title: "Marketing Director",
    company: "Bloom Digital",
    email: "sarah@bloomdigital.com.au",
    alsScore: 94,
    enrichmentDepth: 95,
    isNew: false,
    meetingBooked: true,
  },
  {
    id: "2",
    name: "Marcus Johnson",
    title: "Owner",
    company: "TradeFlow Plumbing",
    email: "marcus@tradeflow.com.au",
    alsScore: 91,
    enrichmentDepth: 88,
    isNew: true,
    meetingBooked: false,
  },
  {
    id: "3",
    name: "David Park",
    title: "Founder & CEO",
    company: "Momentum Media",
    email: "david@momentummedia.co",
    alsScore: 88,
    enrichmentDepth: 92,
    isNew: false,
    meetingBooked: true,
  },
  {
    id: "4",
    name: "Lisa Wong",
    title: "Practice Manager",
    company: "Smile Dental Fitzroy",
    email: "lisa@smiledentalfitzroy.com.au",
    alsScore: 82,
    enrichmentDepth: 78,
    isNew: false,
    meetingBooked: false,
  },
  {
    id: "5",
    name: "James Cooper",
    title: "Managing Director",
    company: "Cooper Electrical",
    email: "james@cooperelectrical.com.au",
    alsScore: 76,
    enrichmentDepth: 65,
    isNew: false,
    meetingBooked: false,
  },
  {
    id: "6",
    name: "Emma Wilson",
    title: "Head of Marketing",
    company: "Coastal Electrical",
    email: "emma@coastalelectrical.com.au",
    alsScore: 71,
    enrichmentDepth: 72,
    isNew: true,
    meetingBooked: false,
  },
  {
    id: "7",
    name: "Rachel Nguyen",
    title: "Practice Owner",
    company: "Growth Dental Kew",
    email: "rachel@growthdentalkew.com.au",
    alsScore: 68,
    enrichmentDepth: 45,
    isNew: false,
    meetingBooked: false,
  },
  {
    id: "8",
    name: "Tom Brown",
    title: "Director",
    company: "Scale Trades",
    email: "tom@scaletrades.com.au",
    alsScore: 58,
    enrichmentDepth: 82,
    isNew: false,
    meetingBooked: false,
  },
  {
    id: "9",
    name: "Sophie Martinez",
    title: "Marketing Manager",
    company: "Digital Edge Agency",
    email: "sophie@digitaledge.com.au",
    alsScore: 45,
    enrichmentDepth: 35,
    isNew: false,
    meetingBooked: false,
  },
  {
    id: "10",
    name: "Michael Chen",
    title: "Operations Manager",
    company: "Elite Plumbing Services",
    email: "michael@eliteplumbing.com.au",
    alsScore: 52,
    enrichmentDepth: 28,
    isNew: false,
    meetingBooked: false,
  },
  {
    id: "11",
    name: "Amanda White",
    title: "Dental Hygienist",
    company: "Bright Smile Clinic",
    email: "amanda@brightsmileclinic.com.au",
    alsScore: 32,
    enrichmentDepth: 42,
    isNew: false,
    meetingBooked: false,
  },
  {
    id: "12",
    name: "Daniel Lee",
    title: "Junior Marketing",
    company: "Spark Creative",
    email: "daniel@sparkcreative.com.au",
    alsScore: 28,
    enrichmentDepth: 15,
    isNew: false,
    meetingBooked: false,
  },
];

// Calculate stats from leads
function calculateStats(leads: typeof MOCK_LEADS) {
  return {
    total: leads.length,
    enriched: leads.filter(l => l.enrichmentDepth >= 50).length,
    avgALS: Math.round(leads.reduce((acc, l) => acc + l.alsScore, 0) / leads.length),
    meetingsBooked: leads.filter(l => l.meetingBooked).length,
    hot: leads.filter(l => getALSTier(l.alsScore) === "hot").length,
    warm: leads.filter(l => getALSTier(l.alsScore) === "warm").length,
    cool: leads.filter(l => getALSTier(l.alsScore) === "cool").length,
    cold: leads.filter(l => getALSTier(l.alsScore) === "cold").length,
  };
}

export default function LeadsScoreboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<TierFilter>("all");
  const [sortAscending, setSortAscending] = useState(false);

  // Calculate stats
  const stats = useMemo(() => calculateStats(MOCK_LEADS), []);

  // Filter and sort leads
  const sortedLeads = useMemo(() => {
    let filtered = MOCK_LEADS.filter(lead => {
      const matchesSearch =
        lead.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.email.toLowerCase().includes(searchQuery.toLowerCase());
      
      const tier = getALSTier(lead.alsScore);
      const matchesTier = selectedTier === "all" || tier === selectedTier;
      
      return matchesSearch && matchesTier;
    });

    // Sort by ALS score (descending by default = leaderboard style)
    filtered.sort((a, b) => 
      sortAscending ? a.alsScore - b.alsScore : b.alsScore - a.alsScore
    );

    return filtered;
  }, [searchQuery, selectedTier, sortAscending]);

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

          {/* Leaderboard Rows */}
          <LayoutGroup>
            <AnimatePresence mode="popLayout">
              {sortedLeads.length > 0 ? (
                <div className="space-y-2">
                  {sortedLeads.map((lead, index) => (
                    <LeadScoreboardRow
                      key={lead.id}
                      id={lead.id}
                      rank={index + 1}
                      alsScore={lead.alsScore}
                      companyName={lead.company}
                      decisionMaker={lead.name}
                      title={lead.title}
                      enrichmentDepth={lead.enrichmentDepth}
                      isNew={lead.isNew}
                      index={index}
                    />
                  ))}
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
