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

// Mock lead data by ID
const MOCK_LEADS: Record<string, {
  id: string;
  name: string;
  title: string;
  company: string;
  location: string;
  email: string;
  phone: string;
  linkedinUrl: string;
  alsScore: number;
  enrichmentDepth: number;
  companyDetails: {
    abn: string;
    industry: string;
    employees: string;
    revenue: string;
    website: string;
  };
  whyHot: { label: string; type: string }[];
  alsBreakdown: { label: string; score: number; max: number }[];
  timeline: TimelineEvent[];
}> = {
  "1": {
    id: "1",
    name: "Sarah Chen",
    title: "Marketing Director",
    company: "Bloom Digital",
    location: "Melbourne, VIC",
    email: "sarah@bloomdigital.com.au",
    phone: "+61 412 345 678",
    linkedinUrl: "linkedin.com/in/sarahchen",
    alsScore: 94,
    enrichmentDepth: 95,
    companyDetails: {
      abn: "12 345 678 901",
      industry: "Digital Marketing",
      employees: "15-25",
      revenue: "$2-5M",
      website: "bloomdigital.com.au",
    },
    whyHot: [
      { label: "Marketing Director", type: "executive" },
      { label: "5 email opens today", type: "active" },
      { label: "Known Agency Buyer", type: "buyer" },
      { label: "LinkedIn Active", type: "linkedin" },
      { label: "Engaged in last 2h", type: "timing" },
    ],
    alsBreakdown: [
      { label: "Data Quality", score: 18, max: 20 },
      { label: "Authority (Title)", score: 23, max: 25 },
      { label: "Company Fit", score: 23, max: 25 },
      { label: "Timing", score: 10, max: 10 },
      { label: "Engagement", score: 20, max: 20 },
    ],
    timeline: [
      {
        id: "evt-1",
        type: "meeting_booked",
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        title: "Discovery Call Booked",
        preview: "Thursday 10:00 AM AEDT — 30 min discovery call",
        fullContent: "Meeting Details:\n- Date: Thursday, Feb 13, 2026\n- Time: 10:00 AM AEDT\n- Duration: 30 minutes\n- Type: Discovery Call\n- Attendees: Sarah Chen, Your Team\n\nAgenda:\n1. Introduction and company overview\n2. Current marketing challenges\n3. Discuss potential solutions\n4. Next steps",
        metadata: { "Booked via": "Voice AI", "Duration": "30 min" }
      },
      {
        id: "evt-2",
        type: "email_replied",
        timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000), // 3 hours ago
        title: "Sarah replied to your email",
        preview: "\"Yes, I'd love to learn more. Can we schedule a call?\"",
        fullContent: "Hi there,\n\nYes, I'd love to learn more. Can we schedule a call?\n\nI'm particularly interested in how you've helped other digital agencies scale their lead generation. Our current process is quite manual and we're looking to automate.\n\nI'm available Thursday or Friday morning if that works?\n\nBest,\nSarah",
        metadata: { "Sentiment": "Positive", "Response time": "2h 15m" }
      },
      {
        id: "evt-3",
        type: "email_opened",
        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
        title: "Email opened (5th time)",
        preview: "Subject: \"Quick question about Bloom Digital\"",
      },
      {
        id: "evt-4",
        type: "call_made",
        timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // Yesterday
        title: "Voice AI Call Completed",
        preview: "3 min 24 sec call — AI detected buying interest",
        fullContent: "Call Summary:\n\nDuration: 3 minutes 24 seconds\nOutcome: Positive - expressed interest in demo\n\nKey Points Discussed:\n- Current lead gen process (manual, time-consuming)\n- Pain points with existing tools\n- Interest in AI-powered automation\n- Requested follow-up email with case studies\n\nSentiment: Highly engaged, asked multiple questions\nNext Action: Discovery call scheduled",
        metadata: { "Duration": "3:24", "Outcome": "Meeting Booked" }
      },
      {
        id: "evt-5",
        type: "linkedin_connected",
        timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
        title: "LinkedIn Connection Accepted",
        preview: "Sarah accepted your connection request",
      },
      {
        id: "evt-6",
        type: "email_sent",
        timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000 - 60 * 60 * 1000), // 2 days + 1 hour ago
        title: "Initial Outreach Email Sent",
        preview: "Personalized outreach: Case study + value proposition",
        fullContent: "Subject: Quick question about Bloom Digital\n\nHi Sarah,\n\nI noticed Bloom Digital has been growing rapidly in the Melbourne market — congrats on the recent wins!\n\nI'm reaching out because we've helped agencies similar to yours increase their qualified lead pipeline by 3x using AI-powered prospecting.\n\nWould you be open to a quick 15-minute chat to see if there's a fit?\n\nI've attached a case study from another digital agency that saw results within 30 days.\n\nBest,\n[Your name]",
        metadata: { "Template": "Agency_Intro_v2", "Personalization": "High" }
      },
    ],
  },
  "2": {
    id: "2",
    name: "Marcus Johnson",
    title: "Owner",
    company: "TradeFlow Plumbing",
    location: "Melbourne, VIC",
    email: "marcus@tradeflow.com.au",
    phone: "+61 432 111 222",
    linkedinUrl: "linkedin.com/in/marcusjohnson",
    alsScore: 91,
    enrichmentDepth: 88,
    companyDetails: {
      abn: "23 456 789 012",
      industry: "Trade Services",
      employees: "10-20",
      revenue: "$1-2M",
      website: "tradeflowplumbing.com.au",
    },
    whyHot: [
      { label: "Business Owner", type: "executive" },
      { label: "Hiring on SEEK", type: "buyer" },
      { label: "Recent website visit", type: "active" },
    ],
    alsBreakdown: [
      { label: "Data Quality", score: 17, max: 20 },
      { label: "Authority (Title)", score: 25, max: 25 },
      { label: "Company Fit", score: 22, max: 25 },
      { label: "Timing", score: 9, max: 10 },
      { label: "Engagement", score: 18, max: 20 },
    ],
    timeline: [
      {
        id: "evt-1",
        type: "sms_sent",
        timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000),
        title: "SMS Follow-up Sent",
        preview: "Quick follow-up about our call yesterday...",
      },
      {
        id: "evt-2",
        type: "email_opened",
        timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000),
        title: "Email opened (2nd time)",
        preview: "Subject: \"Growing TradeFlow? Here's how we can help\"",
      },
      {
        id: "evt-3",
        type: "email_sent",
        timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
        title: "Initial Outreach Email Sent",
        preview: "Personalized outreach for trade business owners",
      },
    ],
  },
};

// Default lead for unknown IDs (empty timeline)
const DEFAULT_LEAD = {
  id: "unknown",
  name: "New Lead",
  title: "Contact",
  company: "Unknown Company",
  location: "Australia",
  email: "contact@example.com",
  phone: "+61 400 000 000",
  linkedinUrl: "",
  alsScore: 50,
  enrichmentDepth: 10,
  companyDetails: {
    abn: "00 000 000 000",
    industry: "Unknown",
    employees: "Unknown",
    revenue: "Unknown",
    website: "",
  },
  whyHot: [],
  alsBreakdown: [
    { label: "Data Quality", score: 5, max: 20 },
    { label: "Authority (Title)", score: 10, max: 25 },
    { label: "Company Fit", score: 15, max: 25 },
    { label: "Timing", score: 5, max: 10 },
    { label: "Engagement", score: 15, max: 20 },
  ],
  timeline: [], // Empty timeline triggers the empty state
};

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

export default function LeadDetailPage() {
  const params = useParams();
  const leadId = params.id as string;
  
  // Get lead data or fall back to default (empty timeline)
  const lead = MOCK_LEADS[leadId] || { ...DEFAULT_LEAD, id: leadId };
  const tier = getALSTier(lead.alsScore);
  const tierColours = getALSColour(tier);

  return (
    <AppShell pageTitle={lead.name}>
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
                {lead.name.split(" ").map(n => n[0]).join("")}
              </div>

              {/* Info */}
              <div>
                <h1 className="text-2xl font-serif font-semibold text-text-primary">{lead.name}</h1>
                <p className="text-base text-text-secondary mt-1">
                  {lead.title} at {lead.company}
                </p>

                {/* Meta items */}
                <div className="flex flex-wrap items-center gap-5 mt-4">
                  <a href={`mailto:${lead.email}`} className="flex items-center gap-2 text-sm text-text-secondary hover:text-accent-primary transition-colors">
                    <Mail className="w-4 h-4 text-text-muted" />
                    {lead.email}
                  </a>
                  <span className="flex items-center gap-2 text-sm text-text-secondary">
                    <Phone className="w-4 h-4 text-text-muted" />
                    {lead.phone}
                  </span>
                  {lead.linkedinUrl && (
                    <a href={`https://${lead.linkedinUrl}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-accent-primary hover:underline">
                      <Linkedin className="w-4 h-4" />
                      {lead.linkedinUrl}
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
                  {lead.alsScore}
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
          {lead.whyHot.length > 0 && (
            <div className="mt-6 pt-6 border-t border-border-subtle">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Why This Lead is {tier === "hot" ? "Hot" : tier === "warm" ? "Warm" : "Ranked"}
              </p>
              <div className="flex flex-wrap gap-2">
                {lead.whyHot.map((item, idx) => {
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
                <CommunicationTimeline events={lead.timeline} showEmptyState={true} />
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
                    <p className="font-semibold text-text-primary">{lead.company}</p>
                    {lead.companyDetails.website && (
                      <a href={`https://${lead.companyDetails.website}`} target="_blank" rel="noopener noreferrer" className="text-sm text-accent-primary hover:underline">
                        {lead.companyDetails.website}
                      </a>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-5">
                  <div className="p-3 rounded-xl bg-bg-elevated text-center">
                    <p className="text-lg font-bold font-mono text-text-primary">{lead.companyDetails.employees}</p>
                    <p className="text-[10px] text-text-muted uppercase">Employees</p>
                  </div>
                  <div className="p-3 rounded-xl bg-bg-elevated text-center">
                    <p className="text-lg font-bold font-mono text-text-primary">{lead.companyDetails.revenue}</p>
                    <p className="text-[10px] text-text-muted uppercase">Revenue</p>
                  </div>
                </div>

                <div className="pt-5 border-t border-border-subtle space-y-3">
                  <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">Details</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Industry</span>
                      <span className="text-text-primary">{lead.companyDetails.industry}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">ABN</span>
                      <span className="text-text-primary font-mono">{lead.companyDetails.abn}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Location</span>
                      <span className="text-text-primary">{lead.location}</span>
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
                {lead.alsBreakdown.map((item, idx) => {
                  const percent = (item.score / item.max) * 100;
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
                      {lead.alsScore}
                    </span>
                  </div>
                </div>
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
                  style={{ color: lead.enrichmentDepth >= 80 ? "#D4956A" : lead.enrichmentDepth >= 50 ? "#EAB308" : "#6B7280" }}
                >
                  {lead.enrichmentDepth}%
                </span>
              </div>
              <div className="h-3 rounded-full bg-bg-elevated overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${lead.enrichmentDepth}%` }}
                  transition={{ duration: 1, delay: 0.7 }}
                  className="h-full rounded-full"
                  style={{ 
                    backgroundColor: lead.enrichmentDepth >= 80 ? "#D4956A" : lead.enrichmentDepth >= 50 ? "#EAB308" : "#6B7280"
                  }}
                />
              </div>
              <p className="text-xs text-text-muted mt-2">
                {lead.enrichmentDepth >= 80 
                  ? "Fully enriched — all data points captured" 
                  : lead.enrichmentDepth >= 50 
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
