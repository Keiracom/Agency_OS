"use client";

/**
 * FILE: frontend/app/dashboard/leads/[id]/page.tsx
 * PURPOSE: Prospect detail - individual lead view
 * SPRINT: Dashboard Sprint 2 - Prospect Detail
 * SSOT: frontend/design/html-prototypes/lead-detail-v2.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  ArrowLeft,
  Mail,
  Phone,
  Linkedin,
  MapPin,
  Building2,
  Flame,
  Send,
  MessageSquare,
  Play,
  Calendar,
  ExternalLink,
  Clock,
  CheckCircle2,
  Eye,
  MousePointer,
  Reply,
} from "lucide-react";

// Mock prospect data
const MOCK_PROSPECT = {
  id: "1",
  name: "Sarah Chen",
  title: "Marketing Director",
  company: "Bloom Digital",
  location: "Melbourne, VIC",
  email: "sarah@bloomdigital.com.au",
  phone: "+61 412 345 678",
  linkedinUrl: "linkedin.com/in/sarahchen",
  score: 94,
  tier: "hot" as const,
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
      date: "Today",
      events: [
        {
          type: "reply",
          icon: "reply",
          title: "Replied to Email",
          badge: "Positive",
          detail: '"Yes, I\'d love to learn more. Can we schedule a call?"',
          time: "10:42 AM",
        },
        {
          type: "email",
          icon: "email",
          title: "Opened email (5th time)",
          detail: 'Subject: "Quick question about Bloom Digital"',
          time: "10:38 AM",
        },
      ],
    },
    {
      date: "Yesterday",
      events: [
        {
          type: "voice",
          icon: "voice",
          title: "Voice AI Call",
          badge: "Meeting Booked",
          detail: "3 min 24 sec call — AI detected buying interest and booked demo for Thursday 10am",
          time: "4:30 PM",
        },
        {
          type: "email",
          icon: "email",
          title: "Opened email (2nd time)",
          detail: 'Subject: "Quick question about Bloom Digital"',
          time: "3:15 PM",
        },
      ],
    },
    {
      date: "Feb 10, 2026",
      events: [
        {
          type: "linkedin",
          icon: "linkedin",
          title: "LinkedIn Connection Accepted",
          detail: "Sarah accepted your connection request",
          time: "11:20 AM",
        },
        {
          type: "email",
          icon: "email",
          title: "Email Sent",
          detail: "Personalized outreach: Case study + value prop",
          time: "9:00 AM",
        },
      ],
    },
  ],
  sequence: [
    { step: 1, channel: "email", status: "sent", label: "Initial Outreach", date: "Feb 10" },
    { step: 2, channel: "linkedin", status: "connected", label: "LinkedIn Connect", date: "Feb 10" },
    { step: 3, channel: "email", status: "opened", label: "Follow-up Email", date: "Feb 11" },
    { step: 4, channel: "voice", status: "completed", label: "Voice AI Call", date: "Feb 11" },
    { step: 5, channel: "email", status: "replied", label: "Meeting Confirm", date: "Today" },
    { step: 6, channel: "meeting", status: "pending", label: "Discovery Call", date: "Feb 13" },
  ],
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

// Event icon colors
function getEventStyle(type: string) {
  switch (type) {
    case "email":
      return { bg: "rgba(124, 58, 237, 0.15)", border: "#7C3AED" };
    case "linkedin":
      return { bg: "rgba(0, 119, 181, 0.15)", border: "#0077B5" };
    case "voice":
      return { bg: "rgba(245, 158, 11, 0.15)", border: "#F59E0B" };
    case "reply":
      return { bg: "rgba(16, 185, 129, 0.15)", border: "#10B981" };
    case "sms":
      return { bg: "rgba(20, 184, 166, 0.15)", border: "#14B8A6" };
    default:
      return { bg: "rgba(255, 255, 255, 0.06)", border: "#6B7280" };
  }
}

// Sequence status colors
function getSequenceStatus(status: string) {
  switch (status) {
    case "sent":
      return { bg: "rgba(124, 58, 237, 0.15)", text: "#7C3AED", icon: <Send className="w-3 h-3" /> };
    case "opened":
      return { bg: "rgba(59, 130, 246, 0.15)", text: "#3B82F6", icon: <Eye className="w-3 h-3" /> };
    case "clicked":
      return { bg: "rgba(20, 184, 166, 0.15)", text: "#14B8A6", icon: <MousePointer className="w-3 h-3" /> };
    case "replied":
      return { bg: "rgba(16, 185, 129, 0.15)", text: "#10B981", icon: <Reply className="w-3 h-3" /> };
    case "connected":
      return { bg: "rgba(0, 119, 181, 0.15)", text: "#0077B5", icon: <Linkedin className="w-3 h-3" /> };
    case "completed":
      return { bg: "rgba(16, 185, 129, 0.15)", text: "#10B981", icon: <CheckCircle2 className="w-3 h-3" /> };
    case "pending":
      return { bg: "rgba(245, 158, 11, 0.15)", text: "#F59E0B", icon: <Clock className="w-3 h-3" /> };
    default:
      return { bg: "rgba(107, 114, 128, 0.15)", text: "#6B7280", icon: null };
  }
}

export default function ProspectDetailPage() {
  const params = useParams();
  const prospect = MOCK_PROSPECT; // In production, fetch by params.id

  return (
    <AppShell pageTitle={prospect.name}>
      <div className="space-y-6">
        {/* Back Navigation */}
        <Link
          href="/dashboard/leads"
          className="inline-flex items-center gap-2 text-sm text-text-muted hover:text-text-secondary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Prospects
        </Link>

        {/* Profile Header */}
        <div className="glass-surface rounded-2xl p-8 relative overflow-hidden">
          {/* Top accent bar */}
          <div
            className="absolute top-0 left-0 right-0 h-1"
            style={{ background: "linear-gradient(90deg, #EF4444, #D4956A)" }}
          />

          <div className="flex gap-8">
            {/* Left: Profile info */}
            <div className="flex gap-6 flex-1">
              {/* Avatar */}
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center text-text-primary font-bold text-2xl flex-shrink-0"
                style={{ background: "linear-gradient(135deg, #EF4444, #F97316)" }}
              >
                {prospect.name.split(" ").map(n => n[0]).join("")}
              </div>

              {/* Info */}
              <div>
                <h1 className="text-2xl font-serif font-semibold text-text-primary">{prospect.name}</h1>
                <p className="text-base text-text-secondary mt-1">
                  {prospect.title} at {prospect.company}
                </p>

                {/* Meta items */}
                <div className="flex flex-wrap items-center gap-5 mt-4">
                  <a href={`mailto:${prospect.email}`} className="flex items-center gap-2 text-sm text-text-secondary hover:text-accent-primary transition-colors">
                    <Mail className="w-4 h-4 text-text-muted" />
                    {prospect.email}
                  </a>
                  <span className="flex items-center gap-2 text-sm text-text-secondary">
                    <Phone className="w-4 h-4 text-text-muted" />
                    {prospect.phone}
                  </span>
                  <a href={`https://${prospect.linkedinUrl}`} target="_blank" className="flex items-center gap-2 text-sm text-accent-primary hover:underline">
                    <Linkedin className="w-4 h-4" />
                    {prospect.linkedinUrl}
                  </a>
                </div>
              </div>
            </div>

            {/* Right: Score */}
            <div className="flex flex-col items-end gap-3">
              <div
                className="text-center px-6 py-4 rounded-xl"
                style={{
                  backgroundColor: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                }}
              >
                <p className="text-5xl font-bold font-mono text-tier-hot leading-none">{prospect.score}</p>
                <p className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mt-1">Lead Score</p>
              </div>
              <span
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold"
                style={{
                  backgroundColor: "rgba(239, 68, 68, 0.1)",
                  color: "#EF4444",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                }}
              >
                <Flame className="w-4 h-4" />
                Very Hot
              </span>
            </div>
          </div>

          {/* Why Hot Section */}
          <div className="mt-6 pt-6 border-t border-border-subtle">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              Why This Lead is Hot
            </p>
            <div className="flex flex-wrap gap-2">
              {prospect.whyHot.map((item, idx) => {
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
        </div>

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
          {/* Left Column - Timeline (2/3 width) */}
          <div className="col-span-2 space-y-6">
            {/* Activity Timeline */}
            <div className="glass-surface rounded-xl overflow-hidden">
              <div className="flex items-center justify-between p-5 border-b border-border-subtle">
                <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                  <Clock className="w-5 h-5 text-accent-primary" />
                  Activity Timeline
                </h3>
                <p className="text-xs text-text-muted">Multi-channel engagement history</p>
              </div>
              <div className="p-5 space-y-6">
                {prospect.timeline.map((day, dayIdx) => (
                  <div key={dayIdx}>
                    <p className={`text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-3 ${
                      day.date === "Today" ? "text-status-success" : "text-text-muted"
                    }`}>
                      {day.date}
                      <span className="flex-1 h-px bg-border-subtle" />
                    </p>
                    <div className="space-y-2 pl-5 border-l-2 border-border-subtle">
                      {day.events.map((event, eventIdx) => {
                        const style = getEventStyle(event.type);
                        return (
                          <div
                            key={eventIdx}
                            className="relative flex items-start gap-4 p-4 rounded-xl cursor-pointer transition-all hover:translate-x-1"
                            style={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                          >
                            {/* Timeline dot */}
                            <span
                              className="absolute -left-[26px] top-5 w-2.5 h-2.5 rounded-full"
                              style={{ backgroundColor: style.bg, border: `2px solid ${style.border}` }}
                            />

                            {/* Event icon */}
                            <div
                              className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                              style={{ backgroundColor: style.bg }}
                            >
                              {event.icon === "email" && <Mail className="w-4 h-4" style={{ color: style.border }} />}
                              {event.icon === "linkedin" && <Linkedin className="w-4 h-4" style={{ color: style.border }} />}
                              {event.icon === "voice" && <Phone className="w-4 h-4" style={{ color: style.border }} />}
                              {event.icon === "reply" && <Reply className="w-4 h-4" style={{ color: style.border }} />}
                            </div>

                            {/* Content */}
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium text-text-primary">{event.title}</p>
                                {event.badge && (
                                  <span
                                    className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded"
                                    style={{
                                      backgroundColor: event.badge === "Meeting Booked" || event.badge === "Positive"
                                        ? "rgba(16, 185, 129, 0.15)"
                                        : "rgba(59, 130, 246, 0.15)",
                                      color: event.badge === "Meeting Booked" || event.badge === "Positive"
                                        ? "#10B981"
                                        : "#3B82F6",
                                    }}
                                  >
                                    {event.badge}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-text-secondary mt-1">{event.detail}</p>
                              <p className="text-xs text-text-muted font-mono mt-2">{event.time}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Outreach Sequence */}
            <div className="glass-surface rounded-xl overflow-hidden">
              <div className="flex items-center justify-between p-5 border-b border-border-subtle">
                <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                  <Send className="w-5 h-5 text-accent-primary" />
                  Outreach Sequence
                </h3>
              </div>
              <div className="p-5">
                <div className="flex items-center gap-2">
                  {prospect.sequence.map((step, idx) => {
                    const statusStyle = getSequenceStatus(step.status);
                    const isLast = idx === prospect.sequence.length - 1;
                    return (
                      <div key={idx} className="flex items-center gap-2">
                        <div className="text-center">
                          <div
                            className="w-10 h-10 rounded-full flex items-center justify-center mb-1"
                            style={{ backgroundColor: statusStyle.bg, color: statusStyle.text }}
                          >
                            {statusStyle.icon}
                          </div>
                          <p className="text-[10px] text-text-muted font-medium">{step.label}</p>
                          <p className="text-[9px] text-text-muted font-mono">{step.date}</p>
                        </div>
                        {!isLast && (
                          <div className="w-8 h-0.5 mb-6" style={{ backgroundColor: "rgba(255,255,255,0.1)" }} />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Company & ALS (1/3 width) */}
          <div className="space-y-6">
            {/* Company Intel */}
            <div className="glass-surface rounded-xl overflow-hidden">
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
                    <p className="font-semibold text-text-primary">{prospect.company}</p>
                    <a href={`https://${prospect.companyDetails.website}`} target="_blank" className="text-sm text-accent-primary hover:underline">
                      {prospect.companyDetails.website}
                    </a>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-5">
                  <div className="p-3 rounded-xl bg-bg-elevated text-center">
                    <p className="text-lg font-bold font-mono text-text-primary">{prospect.companyDetails.employees}</p>
                    <p className="text-[10px] text-text-muted uppercase">Employees</p>
                  </div>
                  <div className="p-3 rounded-xl bg-bg-elevated text-center">
                    <p className="text-lg font-bold font-mono text-text-primary">{prospect.companyDetails.revenue}</p>
                    <p className="text-[10px] text-text-muted uppercase">Revenue</p>
                  </div>
                </div>

                <div className="pt-5 border-t border-border-subtle space-y-3">
                  <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">Details</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Industry</span>
                      <span className="text-text-primary">{prospect.companyDetails.industry}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">ABN</span>
                      <span className="text-text-primary font-mono">{prospect.companyDetails.abn}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Location</span>
                      <span className="text-text-primary">{prospect.location}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ALS Breakdown */}
            <div className="glass-surface rounded-xl overflow-hidden">
              <div className="p-5 border-b border-border-subtle">
                <h3 className="font-serif font-semibold text-text-primary">ALS Score Breakdown</h3>
                <p className="text-xs text-text-muted mt-1">Adaptive Lead Scoring components</p>
              </div>
              <div className="p-5 space-y-4">
                {prospect.alsBreakdown.map((item, idx) => {
                  const percent = (item.score / item.max) * 100;
                  return (
                    <div key={idx}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-text-secondary">{item.label}</span>
                        <span className="font-mono font-medium text-text-primary">{item.score}/{item.max}</span>
                      </div>
                      <div className="h-2 rounded-full bg-bg-elevated overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${percent}%`,
                            backgroundColor: percent >= 80 ? "#10B981" : percent >= 60 ? "#F59E0B" : "#3B82F6",
                          }}
                        />
                      </div>
                    </div>
                  );
                })}

                <div className="pt-4 border-t border-border-subtle">
                  <div className="flex justify-between">
                    <span className="font-semibold text-text-primary">Total Score</span>
                    <span className="text-2xl font-bold font-mono text-tier-hot">{prospect.score}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
