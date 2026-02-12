"use client";

/**
 * FILE: frontend/app/dashboard/leads/page.tsx
 * PURPOSE: Prospects list - lead management view
 * SPRINT: Dashboard Sprint 2 - Prospects List
 * SSOT: frontend/design/html-prototypes/leads-v2.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  Search,
  Filter,
  Plus,
  Download,
  Upload,
  Flame,
  Zap,
  Moon,
  Mail,
  Linkedin,
  Phone,
  MessageSquare,
  Send,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

// Tier type
type Tier = "hot" | "warm" | "cool" | "cold";
type Status = "sourced" | "enriching" | "enriched" | "active";

// Australian mock data - Melbourne digital agency prospects (tradies + dentists)
const MOCK_PROSPECTS = [
  {
    id: "1",
    name: "Sarah Chen",
    title: "Marketing Director",
    company: "Bloom Digital",
    email: "sarah@bloomdigital.com.au",
    score: 94,
    tier: "hot" as Tier,
    whyHot: ["5 opens today", "Buyer signal"],
    channels: { email: true, linkedin: true, sms: false, voice: true, mail: false },
    status: "active" as Status,
    lastActivity: "2 minutes ago",
    recent: true,
  },
  {
    id: "2",
    name: "Marcus Johnson",
    title: "Owner",
    company: "TradeFlow Plumbing",
    email: "marcus@tradeflow.com.au",
    score: 91,
    tier: "hot" as Tier,
    whyHot: ["Business Owner", "Hiring"],
    channels: { email: true, linkedin: true, sms: true, voice: false, mail: false },
    status: "active" as Status,
    lastActivity: "15 minutes ago",
    recent: true,
  },
  {
    id: "3",
    name: "David Park",
    title: "Founder & CEO",
    company: "Momentum Media",
    email: "david@momentummedia.co",
    score: 88,
    tier: "hot" as Tier,
    whyHot: ["Founder", "New Role", "LinkedIn Active"],
    channels: { email: true, linkedin: true, sms: false, voice: true, mail: false },
    status: "active" as Status,
    lastActivity: "1 hour ago",
    recent: true,
  },
  {
    id: "4",
    name: "Lisa Wong",
    title: "Practice Manager",
    company: "Smile Dental Fitzroy",
    email: "lisa@smiledentalfitzroy.com.au",
    score: 82,
    tier: "warm" as Tier,
    whyHot: ["Decision Maker"],
    channels: { email: true, linkedin: false, sms: true, voice: false, mail: false },
    status: "enriched" as Status,
    lastActivity: "3 hours ago",
    recent: false,
  },
  {
    id: "5",
    name: "James Cooper",
    title: "Managing Director",
    company: "Cooper Electrical",
    email: "james@cooperelectrical.com.au",
    score: 76,
    tier: "warm" as Tier,
    whyHot: ["Executive", "Agency Buyer"],
    channels: { email: true, linkedin: false, sms: true, voice: false, mail: false },
    status: "active" as Status,
    lastActivity: "1 day ago",
    recent: false,
  },
  {
    id: "6",
    name: "Emma Wilson",
    title: "Head of Marketing",
    company: "Coastal Electrical",
    email: "emma@coastalelectrical.com.au",
    score: 71,
    tier: "warm" as Tier,
    whyHot: ["Recently active"],
    channels: { email: true, linkedin: true, sms: true, voice: false, mail: false },
    status: "enriched" as Status,
    lastActivity: "2 days ago",
    recent: false,
  },
  {
    id: "7",
    name: "Rachel Nguyen",
    title: "Practice Owner",
    company: "Growth Dental Kew",
    email: "rachel@growthdentalkew.com.au",
    score: 68,
    tier: "warm" as Tier,
    whyHot: ["Owner"],
    channels: { email: true, linkedin: true, sms: false, voice: false, mail: false },
    status: "enriching" as Status,
    lastActivity: "2 days ago",
    recent: false,
  },
  {
    id: "8",
    name: "Tom Brown",
    title: "Director",
    company: "Scale Trades",
    email: "tom@scaletrades.com.au",
    score: 58,
    tier: "cool" as Tier,
    whyHot: ["Good fit"],
    channels: { email: true, linkedin: false, sms: false, voice: false, mail: false },
    status: "enriched" as Status,
    lastActivity: "5 days ago",
    recent: false,
  },
  {
    id: "9",
    name: "Sophie Martinez",
    title: "Marketing Manager",
    company: "Digital Edge Agency",
    email: "sophie@digitaledge.com.au",
    score: 45,
    tier: "cool" as Tier,
    whyHot: ["Mid-level"],
    channels: { email: true, linkedin: true, sms: false, voice: false, mail: false },
    status: "sourced" as Status,
    lastActivity: "1 week ago",
    recent: false,
  },
  {
    id: "10",
    name: "Michael Chen",
    title: "Operations Manager",
    company: "Elite Plumbing Services",
    email: "michael@eliteplumbing.com.au",
    score: 52,
    tier: "cool" as Tier,
    whyHot: ["ICP match"],
    channels: { email: true, linkedin: false, sms: false, voice: false, mail: false },
    status: "enriching" as Status,
    lastActivity: "4 days ago",
    recent: false,
  },
  {
    id: "11",
    name: "Amanda White",
    title: "Dental Hygienist",
    company: "Bright Smile Clinic",
    email: "amanda@brightsmileclinic.com.au",
    score: 32,
    tier: "cool" as Tier,
    whyHot: ["Engaged"],
    channels: { email: true, linkedin: false, sms: false, voice: false, mail: false },
    status: "sourced" as Status,
    lastActivity: "2 weeks ago",
    recent: false,
  },
  {
    id: "12",
    name: "Daniel Lee",
    title: "Junior Marketing",
    company: "Spark Creative",
    email: "daniel@sparkcreative.com.au",
    score: 28,
    tier: "cold" as Tier,
    whyHot: [],
    channels: { email: true, linkedin: false, sms: false, voice: false, mail: false },
    status: "sourced" as Status,
    lastActivity: "3 weeks ago",
    recent: false,
  },
];

// Stats computed from prospects
const MOCK_STATS = {
  total: MOCK_PROSPECTS.length,
  enriched: MOCK_PROSPECTS.filter(p => p.status === "enriched" || p.status === "active").length,
  avgALS: Math.round(MOCK_PROSPECTS.reduce((acc, p) => acc + p.score, 0) / MOCK_PROSPECTS.length),
  channelsUnlocked: MOCK_PROSPECTS.filter(p => 
    Object.values(p.channels).filter(Boolean).length >= 2
  ).length,
  hot: MOCK_PROSPECTS.filter(p => p.tier === "hot").length,
  warm: MOCK_PROSPECTS.filter(p => p.tier === "warm").length,
  cool: MOCK_PROSPECTS.filter(p => p.tier === "cool").length,
};

// Tier colors
function getTierColors(tier: Tier) {
  switch (tier) {
    case "hot":
      return { bg: "rgba(239, 68, 68, 0.1)", border: "rgba(239, 68, 68, 0.3)", text: "#EF4444", gradient: "linear-gradient(135deg, #EF4444, #F97316)" };
    case "warm":
      return { bg: "rgba(245, 158, 11, 0.1)", border: "rgba(245, 158, 11, 0.3)", text: "#F59E0B", gradient: "linear-gradient(135deg, #F59E0B, #FBBF24)" };
    case "cool":
      return { bg: "rgba(59, 130, 246, 0.1)", border: "rgba(59, 130, 246, 0.3)", text: "#3B82F6", gradient: "linear-gradient(135deg, #3B82F6, #60A5FA)" };
    default:
      return { bg: "rgba(107, 114, 128, 0.1)", border: "rgba(107, 114, 128, 0.3)", text: "#6B7280", gradient: "linear-gradient(135deg, #6B7280, #9CA3AF)" };
  }
}

// Status badge colors
function getStatusColors(status: Status) {
  switch (status) {
    case "active":
      return { bg: "rgba(16, 185, 129, 0.1)", text: "#10B981" };
    case "enriched":
      return { bg: "rgba(124, 58, 237, 0.1)", text: "#7C3AED" };
    case "enriching":
      return { bg: "rgba(245, 158, 11, 0.1)", text: "#F59E0B" };
    default:
      return { bg: "rgba(107, 114, 128, 0.1)", text: "#6B7280" };
  }
}

// Get initials
function getInitials(name: string): string {
  return name.split(" ").map(n => n[0]).join("").toUpperCase();
}

export default function ProspectsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<"all" | Tier>("all");

  // Filter prospects
  const filteredProspects = MOCK_PROSPECTS.filter(p => {
    const matchesSearch = 
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTier = selectedTier === "all" || p.tier === selectedTier;
    return matchesSearch && matchesTier;
  });

  return (
    <AppShell pageTitle="Prospects">
      <div className="space-y-6">
        {/* Header Bar */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-serif text-text-primary">Prospects</h1>
              <span className="px-3 py-1 rounded-md font-mono text-sm font-semibold"
                style={{ backgroundColor: "rgba(212, 149, 106, 0.15)", color: "#D4956A" }}
              >
                {MOCK_STATS.total}
              </span>
            </div>
            <p className="text-sm text-text-muted mt-1">
              Track and engage your leads across all channels
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
            <button className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium gradient-premium text-white hover:opacity-90 transition-opacity">
              <Plus className="w-4 h-4" />
              Add Prospect
            </button>
          </div>
        </div>

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
          <button className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium glass-surface hover:bg-bg-surface-hover transition-colors">
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <div className="flex rounded-lg overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            {(["all", "hot", "warm", "cool"] as const).map((tier) => (
              <button
                key={tier}
                onClick={() => setSelectedTier(tier)}
                className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2 ${
                  selectedTier === tier
                    ? "bg-bg-surface text-text-primary"
                    : "text-text-muted hover:text-text-secondary"
                }`}
                style={selectedTier === tier && tier !== "all" ? { color: getTierColors(tier as Tier).text } : {}}
              >
                {tier === "hot" && <Flame className="w-4 h-4" />}
                {tier === "warm" && <Zap className="w-4 h-4" />}
                {tier === "cool" && <Moon className="w-4 h-4" />}
                {tier === "all" ? "All" : tier.charAt(0).toUpperCase() + tier.slice(1)}
                <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ backgroundColor: "rgba(255,255,255,0.06)" }}>
                  {tier === "all" ? MOCK_STATS.total : MOCK_STATS[tier]}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-4 gap-4">
          <div className="glass-surface rounded-xl p-4 flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ backgroundColor: "rgba(239, 68, 68, 0.1)" }}>
              <Flame className="w-5 h-5 text-tier-hot" />
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-text-primary">{MOCK_STATS.hot}</p>
              <p className="text-xs text-text-muted">Hot Leads (85-100)</p>
            </div>
          </div>
          <div className="glass-surface rounded-xl p-4 flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ backgroundColor: "rgba(245, 158, 11, 0.1)" }}>
              <Zap className="w-5 h-5 text-tier-warm" />
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-text-primary">{MOCK_STATS.warm}</p>
              <p className="text-xs text-text-muted">Warm Leads (60-84)</p>
            </div>
          </div>
          <div className="glass-surface rounded-xl p-4 flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ backgroundColor: "rgba(59, 130, 246, 0.1)" }}>
              <Moon className="w-5 h-5 text-tier-cool" />
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-text-primary">{MOCK_STATS.cool}</p>
              <p className="text-xs text-text-muted">Cool Leads (20-59)</p>
            </div>
          </div>
          <div className="glass-surface rounded-xl p-4 flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ backgroundColor: "rgba(212, 149, 106, 0.15)" }}>
              <span className="text-accent-primary font-bold">Ø</span>
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-text-primary">{MOCK_STATS.avgALS}</p>
              <p className="text-xs text-text-muted">Avg. ALS Score</p>
            </div>
          </div>
        </div>

        {/* Prospects Table */}
        <div className="glass-surface rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                <th className="w-10 p-4">
                  <input type="checkbox" className="w-4 h-4 rounded" />
                </th>
                <th className="text-left p-4 text-xs font-semibold text-text-muted uppercase tracking-wider">Prospect</th>
                <th className="text-left p-4 text-xs font-semibold text-text-muted uppercase tracking-wider">Company</th>
                <th className="text-left p-4 text-xs font-semibold text-text-muted uppercase tracking-wider">Score</th>
                <th className="text-left p-4 text-xs font-semibold text-text-muted uppercase tracking-wider">Why Hot?</th>
                <th className="text-left p-4 text-xs font-semibold text-text-muted uppercase tracking-wider">Channels</th>
                <th className="text-left p-4 text-xs font-semibold text-text-muted uppercase tracking-wider">Last Activity</th>
                <th className="w-24 p-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {filteredProspects.map((prospect) => {
                const tierColors = getTierColors(prospect.tier);
                const statusColors = getStatusColors(prospect.status);
                return (
                  <tr
                    key={prospect.id}
                    className="hover:bg-bg-surface-hover transition-colors cursor-pointer group"
                    onClick={() => window.location.href = `/dashboard/leads/${prospect.id}`}
                    style={{
                      boxShadow: `inset 4px 0 0 transparent`,
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.boxShadow = `inset 4px 0 0 ${tierColors.text}`;
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.boxShadow = `inset 4px 0 0 transparent`;
                    }}
                  >
                    <td className="p-4" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" className="w-4 h-4 rounded" />
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-11 h-11 rounded-xl flex items-center justify-center text-white font-semibold text-sm"
                          style={{ background: tierColors.gradient }}
                        >
                          {getInitials(prospect.name)}
                        </div>
                        <div>
                          <p className="font-medium text-text-primary text-sm">{prospect.name}</p>
                          <p className="text-xs text-text-secondary">{prospect.title}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <p className="font-medium text-text-primary text-sm">{prospect.company}</p>
                      <p className="text-xs text-text-muted">{prospect.email}</p>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <span className="text-xl font-bold font-mono" style={{ color: tierColors.text }}>
                          {prospect.score}
                        </span>
                        <span
                          className="text-[10px] font-semibold uppercase px-2 py-1 rounded"
                          style={{
                            backgroundColor: tierColors.bg,
                            color: tierColors.text,
                            border: `1px solid ${tierColors.border}`,
                          }}
                        >
                          {prospect.tier}
                        </span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex flex-wrap gap-1.5">
                        {prospect.whyHot.length > 0 ? (
                          prospect.whyHot.slice(0, 2).map((reason, idx) => (
                            <span
                              key={idx}
                              className="text-[11px] font-medium px-2 py-1 rounded"
                              style={{ backgroundColor: "rgba(255,255,255,0.06)", color: "#A09890" }}
                            >
                              {reason}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-text-muted">—</span>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex gap-1.5">
                        <ChannelIcon active={prospect.channels.email} icon={<Mail className="w-3.5 h-3.5" />} color="#7C3AED" />
                        <ChannelIcon active={prospect.channels.linkedin} icon={<Linkedin className="w-3.5 h-3.5" />} color="#0077B5" />
                        <ChannelIcon active={prospect.channels.sms} icon={<MessageSquare className="w-3.5 h-3.5" />} color="#14B8A6" />
                        <ChannelIcon active={prospect.channels.voice} icon={<Phone className="w-3.5 h-3.5" />} color="#F59E0B" />
                        <ChannelIcon active={prospect.channels.mail} icon={<Send className="w-3.5 h-3.5" />} color="#EC4899" />
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`text-sm ${prospect.recent ? "text-status-success" : "text-text-muted"}`}>
                        {prospect.lastActivity}
                      </span>
                    </td>
                    <td className="p-4" onClick={(e) => e.stopPropagation()}>
                      <Link
                        href={`/dashboard/leads/${prospect.id}`}
                        className="text-sm font-medium px-3 py-1.5 rounded-md transition-colors"
                        style={{ backgroundColor: "rgba(212, 149, 106, 0.1)", color: "#D4956A" }}
                      >
                        Details →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-text-muted">
            Showing <span className="font-mono font-medium text-text-secondary">1-{filteredProspects.length}</span> of{" "}
            <span className="font-mono font-medium text-text-secondary">{MOCK_STATS.total}</span> prospects
          </p>
          <div className="flex items-center gap-2">
            <button className="px-3 py-2 rounded-lg text-sm glass-surface hover:bg-bg-surface-hover transition-colors flex items-center gap-1">
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>
            <button className="px-3 py-2 rounded-lg text-sm font-medium" style={{ backgroundColor: "#D4956A", color: "#0C0A08" }}>
              1
            </button>
            <button className="px-3 py-2 rounded-lg text-sm glass-surface hover:bg-bg-surface-hover transition-colors">2</button>
            <button className="px-3 py-2 rounded-lg text-sm glass-surface hover:bg-bg-surface-hover transition-colors">3</button>
            <button className="px-3 py-2 rounded-lg text-sm glass-surface hover:bg-bg-surface-hover transition-colors flex items-center gap-1">
              Next <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

// Channel icon component
function ChannelIcon({ active, icon, color }: { active: boolean; icon: React.ReactNode; color: string }) {
  return (
    <div
      className="w-7 h-7 rounded-md flex items-center justify-center relative"
      style={{
        backgroundColor: active ? `${color}20` : "rgba(255,255,255,0.03)",
        color: active ? color : "rgba(255,255,255,0.2)",
      }}
    >
      {icon}
      {active && (
        <span
          className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full"
          style={{ backgroundColor: "#10B981", border: "2px solid #0C0A08" }}
        />
      )}
    </div>
  );
}
