"use client";

/**
 * FILE: frontend/app/dashboard/leads/[id]/page.tsx
 * PURPOSE: Lead detail view with chronological communication timeline
 * SPRINT: Dashboard Sprint 2 - Step 6/8 Animated Lead Scoreboard
 * SSOT: lead_scoreboard_vision (ffd41389-645a-47c8-91d6-017b6cebe7ae)
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { AppShell } from "@/components/layout/AppShell";
import { 
  CommunicationTimeline, 
  TimelineEmptyState,
  type TimelineEvent 
} from "@/components/leads/CommunicationTimeline";
import { getALSTier, getALSColour } from "@/components/leads/LeadScoreboardRow";
import { useLeadDetail } from "@/hooks/use-lead-detail";
import { useClient } from "@/hooks/use-client";
import type { Lead, SDKEnrichmentData } from "@/lib/api/types";
import {
  ArrowLeft,
  Mail,
  Phone,
  Linkedin,
  Building2,
  Flame,
  Send,
  Calendar,
  CheckCircle2,
  Zap,
  Moon,
  Snowflake,
} from "lucide-react";

// Why Hot badge colors
function getWhyHotStyle(type: string) {
  switch (type) {
    case "executive":
      return { bg: "rgba(124, 58, 237, 0.15)", color: "#7C3AED", border: "rgba(124, 58, 237, 0.3)" };
    case "active":
      return { bg: "rgba(16, 185, 129, 0.15)", color: "#10B981", border: "rgba(16, 185, 129, 0.3)" };
    case "buyer":
      return { bg: "rgba(245, 158, 11, 0.15)", color: "#F59E0B", border: "rgba(245, 158, 11, 0.3)" };
    case "linkedin":
      return { bg: "rgba(0, 119, 181, 0.15)", color: "#0077B5", border: "rgba(0, 119, 181, 0.3)" };
    case "timing":
      return { bg: "rgba(236, 72, 153, 0.15)", color: "#EC4899", border: "rgba(236, 72, 153, 0.3)" };
    default:
      return { bg: "rgba(255, 255, 255, 0.06)", color: "#A09890", border: "rgba(255, 255, 255, 0.1)" };
  }
}

// Get tier icon
function getTierIcon(tier: ReturnType<typeof getALSTier>) {
  switch (tier) {
    case "hot": return <Flame className="w-4 h-4" />;
    case "warm": return <Zap className="w-4 h-4" />;
    case "cool": return <Moon className="w-4 h-4" />;
    case "cold": return <Snowflake className="w-4 h-4" />;
  }
}

/**
 * Derive whyHot badges from real lead data
 */
function deriveWhyHot(lead: Lead): { label: string; type: string }[] {
  const badges: { label: string; type: string }[] = [];

  // Executive title signals
  const executiveTitles = ["ceo", "cto", "coo", "cmo", "founder", "owner", "director", "vp", "president", "managing"];
  if (lead.title && executiveTitles.some(t => lead.title!.toLowerCase().includes(t))) {
    badges.push({ label: lead.title, type: "executive" });
  }

  // SDK signals from enrichment
  if (lead.sdk_signals && lead.sdk_signals.length > 0) {
    lead.sdk_signals.slice(0, 3).forEach(signal => {
      badges.push({ label: signal, type: "active" });
    });
  }

  // LinkedIn presence
  if (lead.linkedin_url) {
    badges.push({ label: "LinkedIn Active", type: "linkedin" });
  }

  // Hot propensity tier
  if (lead.propensity_tier === "hot") {
    badges.push({ label: "High Propensity", type: "buyer" });
  }

  return badges;
}

/**
 * Derive ALS breakdown from als_* fields on the lead
 */
function deriveALSBreakdown(lead: Lead): { label: string; score: number; max: number }[] {
  // Only show breakdown if at least some ALS fields are populated
  if (
    lead.als_data_quality === null &&
    lead.als_authority === null &&
    lead.als_company_fit === null &&
    lead.als_timing === null &&
    lead.als_risk === null
  ) {
    return [];
  }

  return [
    { label: "Data Quality", score: lead.als_data_quality ?? 0, max: 20 },
    { label: "Authority (Title)", score: lead.als_authority ?? 0, max: 25 },
    { label: "Company Fit", score: lead.als_company_fit ?? 0, max: 25 },
    { label: "Timing", score: lead.als_timing ?? 0, max: 10 },
    { label: "Engagement", score: lead.als_risk ?? 0, max: 20 },
  ];
}

/**
 * Compute enrichment depth 0–100 from field population + sdk_enrichment presence
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

export default function LeadDetailPage() {
  const params = useParams();
  const leadId = params.id as string;
  const { clientId } = useClient();

  const { lead, isLoading, error } = useLeadDetail(clientId, leadId);

  // Loading state
  if (isLoading) {
    return (
      <AppShell pageTitle="Loading...">
        <div className="space-y-6">
          <Link
            href="/dashboard/leads"
            className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-accent-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Scoreboard
          </Link>
          <div className="glass-surface rounded-2xl p-8 text-center">
            <motion.div
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="text-text-muted font-mono"
            >
              Loading lead data...
            </motion.div>
          </div>
        </div>
      </AppShell>
    );
  }

  // Error / not found state
  if (error || !lead) {
    return (
      <AppShell pageTitle="Lead Not Found">
        <div className="space-y-6">
          <Link
            href="/dashboard/leads"
            className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-accent-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Scoreboard
          </Link>
          <div className="glass-surface rounded-2xl p-8 text-center">
            <p className="text-text-muted">Lead not found or failed to load.</p>
          </div>
        </div>
      </AppShell>
    );
  }

  // Derived display values
  const name = [lead.first_name, lead.last_name].filter(Boolean).join(" ") || lead.email;
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();

  const alsScore = lead.propensity_score ?? 0;
  const tier = getALSTier(alsScore);
  const tierColours = getALSColour(tier);
  const enrichmentDepth = getEnrichmentDepth(lead);
  const whyHot = deriveWhyHot(lead);
  const alsBreakdown = deriveALSBreakdown(lead);

  const sdk = lead.sdk_enrichment as SDKEnrichmentData | null;

  // Company details from real data
  const companyDetails = {
    industry: lead.organization_industry ?? "—",
    employees: lead.organization_employee_count
      ? lead.organization_employee_count.toLocaleString()
      : "—",
    revenue: sdk?.company_revenue ?? "—",
    website: sdk?.company_website ?? lead.domain ?? "",
  };

  // Location from real data
  const location = lead.organization_country ?? "—";

  // Timeline: empty until activities endpoint is wired
  // TODO: wire timeline when getLeadActivities() is integrated into this page
  const timeline: TimelineEvent[] = [];

  return (
    <AppShell pageTitle={name}>
      <div className="space-y-6">
        {/* Back Navigation */}
        <Link
          href="/dashboard/leads"
          className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-accent-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Scoreboard
        </Link>

        {/* Profile Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-surface rounded-2xl p-8 relative overflow-hidden"
        >
          {/* Top accent bar - colour based on tier */}
          <div
            className="absolute top-0 left-0 right-0 h-1"
            style={{ backgroundColor: tierColours.text }}
          />

          <div className="flex gap-8">
            {/* Left: Profile info */}
            <div className="flex gap-6 flex-1">
              {/* Avatar */}
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center text-text-primary font-bold text-2xl flex-shrink-0"
                style={{ 
                  backgroundColor: tierColours.bg,
                  border: `2px solid ${tierColours.border}`,
                  boxShadow: tierColours.glow
                }}
              >
                {initials}
              </div>

              {/* Info */}
              <div>
                <h1 className="text-2xl font-serif font-semibold text-text-primary">{name}</h1>
                <p className="text-base text-text-secondary mt-1">
                  {lead.title ? `${lead.title}${lead.company ? ` at ${lead.company}` : ""}` : lead.company ?? ""}
                </p>

                {/* Meta items */}
                <div className="flex flex-wrap items-center gap-5 mt-4">
                  <a href={`mailto:${lead.email}`} className="flex items-center gap-2 text-sm text-text-secondary hover:text-accent-primary transition-colors">
                    <Mail className="w-4 h-4 text-text-muted" />
                    {lead.email}
                  </a>
                  {lead.phone && (
                    <span className="flex items-center gap-2 text-sm text-text-secondary">
                      <Phone className="w-4 h-4 text-text-muted" />
                      {lead.phone}
                    </span>
                  )}
                  {lead.linkedin_url && (
                    <a href={`https://${lead.linkedin_url.replace(/^https?:\/\//, "")}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-accent-primary hover:underline">
                      <Linkedin className="w-4 h-4" />
                      LinkedIn
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Right: Score */}
            <div className="flex flex-col items-end gap-3">
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-center px-6 py-4 rounded-xl"
                style={{
                  backgroundColor: tierColours.bg,
                  border: `1px solid ${tierColours.border}`,
                  boxShadow: tierColours.glow
                }}
              >
                <p 
                  className="text-5xl font-bold font-mono leading-none"
                  style={{ color: tierColours.text }}
                >
                  {alsScore}
                </p>
                <p className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mt-1">ALS Score</p>
              </motion.div>
              <span
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold"
                style={{
                  backgroundColor: tierColours.bg,
                  color: tierColours.text,
                  border: `1px solid ${tierColours.border}`,
                }}
              >
                {getTierIcon(tier)}
                {tier.charAt(0).toUpperCase() + tier.slice(1)} Lead
              </span>
            </div>
          </div>

          {/* Why Hot Section */}
          {whyHot.length > 0 && (
            <div className="mt-6 pt-6 border-t border-border-subtle">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Why This Lead is {tier === "hot" ? "Hot" : tier === "warm" ? "Warm" : "Ranked"}
              </p>
              <div className="flex flex-wrap gap-2">
                {whyHot.map((item, idx) => {
                  const style = getWhyHotStyle(item.type);
                  return (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium"
                      style={{
                        backgroundColor: style.bg,
                        color: style.color,
                        border: `1px solid ${style.border}`,
                      }}
                    >
                      {item.label}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </motion.div>

        {/* Quick Actions */}
        <div className="glass-surface rounded-xl p-4">
          <div className="grid grid-cols-4 gap-3">
            <button className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium gradient-premium text-text-primary hover:opacity-90 transition-opacity">
              <Mail className="w-4 h-4" />
              Send Email
            </button>
            <button className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium glass-surface hover:bg-bg-surface-hover transition-colors">
              <Linkedin className="w-4 h-4" />
              Connect LinkedIn
            </button>
            <button className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium glass-surface hover:bg-bg-surface-hover transition-colors">
              <Phone className="w-4 h-4" />
              Call
            </button>
            <button className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium glass-surface hover:bg-bg-surface-hover transition-colors">
              <Calendar className="w-4 h-4" />
              Schedule
            </button>
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left Column - Communication Timeline (2/3 width) */}
          <div className="col-span-2 space-y-6">
            {/* Communication Timeline */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="glass-surface rounded-xl overflow-hidden"
            >
              <div className="flex items-center justify-between p-5 border-b border-border-subtle">
                <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                  <Send className="w-5 h-5 text-accent-primary" />
                  Communication Timeline
                </h3>
                <p className="text-xs text-text-muted">Chronological activity history</p>
              </div>
              <div className="p-5">
                {/* TODO: wire timeline with getLeadActivities() when integrated */}
                <CommunicationTimeline events={timeline} showEmptyState={true} />
              </div>
            </motion.div>
          </div>

          {/* Right Column - Company & ALS (1/3 width) */}
          <div className="space-y-6">
            {/* Company Intel */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="glass-surface rounded-xl overflow-hidden"
            >
              <div className="p-5 border-b border-border-subtle">
                <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-accent-primary" />
                  Company Intel
                </h3>
              </div>
              <div className="p-5">
                <div className="flex items-center gap-4 mb-5">
                  <div className="w-12 h-12 rounded-xl bg-bg-elevated flex items-center justify-center text-xl border border-border-default">
                    <Building2 className="w-6 h-6 text-text-muted" />
                  </div>
                  <div>
                    <p className="font-semibold text-text-primary">{lead.company ?? "Unknown Company"}</p>
                    {companyDetails.website && (
                      <a href={`https://${companyDetails.website.replace(/^https?:\/\//, "")}`} target="_blank" rel="noopener noreferrer" className="text-sm text-accent-primary hover:underline">
                        {companyDetails.website}
                      </a>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-5">
                  <div className="p-3 rounded-xl bg-bg-elevated text-center">
                    <p className="text-lg font-bold font-mono text-text-primary">{companyDetails.employees}</p>
                    <p className="text-[10px] text-text-muted uppercase">Employees</p>
                  </div>
                  <div className="p-3 rounded-xl bg-bg-elevated text-center">
                    <p className="text-lg font-bold font-mono text-text-primary">{companyDetails.revenue}</p>
                    <p className="text-[10px] text-text-muted uppercase">Revenue</p>
                  </div>
                </div>

                <div className="pt-5 border-t border-border-subtle space-y-3">
                  <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">Details</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Industry</span>
                      <span className="text-text-primary">{companyDetails.industry}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Location</span>
                      <span className="text-text-primary">{location}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Status</span>
                      <span className="text-text-primary capitalize">{lead.status.replace(/_/g, " ")}</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* ALS Breakdown */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
              className="glass-surface rounded-xl overflow-hidden"
            >
              <div className="p-5 border-b border-border-subtle">
                <h3 className="font-serif font-semibold text-text-primary">ALS Score Breakdown</h3>
                <p className="text-xs text-text-muted mt-1">Adaptive Lead Scoring components</p>
              </div>
              <div className="p-5 space-y-4">
                {alsBreakdown.length > 0 ? (
                  <>
                    {alsBreakdown.map((item, idx) => {
                      const percent = item.max > 0 ? (item.score / item.max) * 100 : 0;
                      return (
                        <div key={idx}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-text-secondary">{item.label}</span>
                            <span className="font-mono font-medium text-text-primary">{item.score}/{item.max}</span>
                          </div>
                          <div className="h-2 rounded-full bg-bg-elevated overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${percent}%` }}
                              transition={{ duration: 0.8, delay: 0.6 + idx * 0.1 }}
                              className="h-full rounded-full"
                              style={{
                                backgroundColor: percent >= 80 ? "#10B981" : percent >= 60 ? "#F59E0B" : "#3B82F6",
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                    <div className="pt-4 border-t border-border-subtle">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-text-primary">Total Score</span>
                        <span 
                          className="text-2xl font-bold font-mono"
                          style={{ color: tierColours.text }}
                        >
                          {alsScore}
                        </span>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="py-4 text-center text-text-muted text-sm">
                    <p>Score breakdown unavailable</p>
                    <p className="text-xs mt-1 font-mono">Run lead scoring to see details</p>
                  </div>
                )}
              </div>
            </motion.div>

            {/* Enrichment Depth */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 }}
              className="glass-surface rounded-xl p-5"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-text-secondary">Enrichment Depth</span>
                <span 
                  className="font-mono font-bold"
                  style={{ color: enrichmentDepth >= 80 ? "#D4956A" : enrichmentDepth >= 50 ? "#EAB308" : "#6B7280" }}
                >
                  {enrichmentDepth}%
                </span>
              </div>
              <div className="h-3 rounded-full bg-bg-elevated overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${enrichmentDepth}%` }}
                  transition={{ duration: 1, delay: 0.7 }}
                  className="h-full rounded-full"
                  style={{ 
                    backgroundColor: enrichmentDepth >= 80 ? "#D4956A" : enrichmentDepth >= 50 ? "#EAB308" : "#6B7280"
                  }}
                />
              </div>
              <p className="text-xs text-text-muted mt-2">
                {enrichmentDepth >= 80 
                  ? "Fully enriched — all data points captured" 
                  : enrichmentDepth >= 50 
                  ? "Partially enriched — gathering more intel" 
                  : "Enrichment in progress..."}
              </p>
            </motion.div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
