/**
 * LeadDetailModal.tsx - Lead Detail Slide-Over Modal
 * Phase: Operation Modular Cockpit
 * 
 * Bloomberg-style dark mode design
 * Ported from ~/clawd/agency-os-html/lead-detail-v2.html
 * 
 * Features:
 * - Transcripts → scrolling message-style UI
 * - Call Logs → structured activity timeline
 * - "Why Hot?" badges
 * - Engagement Profile display
 */

"use client";

import { useState, useEffect } from "react";
import {
  X,
  Mail,
  Phone,
  Briefcase,
  Flame,
  Sparkles,
  BadgeCheck,
  Clock,
  Link2,
  DollarSign,
  BarChart3,
  Zap,
  Calendar,
  MessageSquare,
  Play,
  FileText,
  TrendingUp,
  Users,
  Trophy,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";
import type {
  Lead,
  LeadDetailModalProps,
  TimelineEvent,
  TimelineDay,
  TranscriptLine,
  ChannelType,
  WhyHotCategory,
} from "@/types/lead";

// ============================================
// Bloomberg Color Reference (Tailwind classes)
// ============================================
// Base: bg-bg-void
// Surface: bg-bg-base
// Surface Hover: bg-bg-elevated
// Elevated: bg-bg-elevated
// Border Subtle: border-default
// Border Default: border-default
// Text Primary: text-text-primary
// Text Secondary: text-text-secondary
// Text Muted: text-text-muted
// Accent Purple: text-amber / bg-amber
// Tier Hot: text-amber / bg-amber-glow

// ============================================
// Mock Data
// ============================================

const MOCK_LEAD: Lead = {
  id: "lead_001",
  firstName: "Sarah",
  lastName: "Chen",
  email: "sarah@bloomdigital.com.au",
  phone: "+61 412 345 678",
  linkedinUrl: "linkedin.com/in/sarahchen",
  title: "Marketing Director",
  company: {
    id: "company_001",
    name: "Bloom Digital",
    domain: "bloomdigital.com.au",
    logoEmoji: "🌸",
    employees: "15-30",
    industry: "Agency",
    estimatedRevenue: "$1-2M",
    location: "Sydney",
    recentIntelligence: [
      { icon: "", text: "Expanded to Queensland market (Jan 2026)" },
      { icon: "", text: "Hired 3 new BDRs in last 60 days" },
      { icon: "", text: 'Featured in "Top 50 Agencies to Watch"' },
    ],
  },
  score: 94,
  tier: "hot",
  whyHot: [
    { id: "1", category: "executive", label: "Marketing Director" },
    { id: "2", category: "active", label: "5 email opens today" },
    { id: "3", category: "buyer", label: "Known Agency Buyer" },
    { id: "4", category: "linkedin", label: "LinkedIn Active" },
    { id: "5", category: "timing", label: "Engaged in last 2h" },
  ],
  engagementProfile: {
    dataQuality: { label: "Data Quality", value: 18, maxValue: 20, level: "high" },
    authority: { label: "Authority (Title)", value: 21, maxValue: 25, level: "high" },
    companyFit: { label: "Company Fit", value: 22, maxValue: 25, level: "high" },
    timing: { label: "Timing", value: 15, maxValue: 15, level: "high" },
    engagement: { label: "Engagement", value: 18, maxValue: 20, level: "high" },
  },
  timeline: [
    {
      date: "Today",
      isToday: true,
      events: [
        {
          id: "e1",
          type: "reply",
          title: "Replied to Email",
          detail: '"Yes, I\'d love to learn more. Can we schedule a call?"',
          timestamp: new Date().toISOString(),
          displayTime: "10:42 AM",
          badge: { type: "positive", label: "Positive" },
          hasThread: true,
        },
        {
          id: "e2",
          type: "email",
          title: "Opened email (5th time)",
          detail: 'Subject: "Quick question about Bloom Digital"',
          timestamp: new Date().toISOString(),
          displayTime: "10:38 AM",
        },
      ],
    },
    {
      date: "Yesterday",
      events: [
        {
          id: "e3",
          type: "voice",
          title: "Voice AI Call",
          detail: "3 min 24 sec call — AI detected buying interest and booked demo for Thursday 10am",
          timestamp: new Date().toISOString(),
          displayTime: "4:30 PM",
          badge: { type: "booked", label: "Meeting Booked" },
          hasTranscript: true,
        },
        {
          id: "e4",
          type: "email",
          title: "Opened email (2nd time)",
          detail: 'Subject: "Quick question about Bloom Digital"',
          timestamp: new Date().toISOString(),
          displayTime: "3:15 PM",
        },
      ],
    },
    {
      date: "Jan 29, 2026",
      events: [
        {
          id: "e5",
          type: "linkedin",
          title: "LinkedIn Connection Accepted",
          detail: "Now connected — sent personalized intro message",
          timestamp: new Date().toISOString(),
          displayTime: "2:30 PM",
          hasThread: true,
        },
        {
          id: "e6",
          type: "email",
          title: "Email Sent",
          detail: 'Subject: "Quick question about Bloom Digital"',
          timestamp: new Date().toISOString(),
          displayTime: "9:00 AM",
        },
      ],
    },
  ],
  callLogs: [],
  emailThread: [
    {
      id: "em1",
      sender: "You",
      timestamp: "Jan 29, 2026 • 9:00 AM",
      subject: "Quick question about Bloom Digital",
      body: "Hi Sarah,\n\nI noticed Bloom Digital has been doing some impressive work in the agency space. I'm curious — are you currently looking to scale your client acquisition, or is that on the backburner for now?\n\nWe've helped agencies like yours book 10-15 qualified meetings per month without adding headcount. Happy to share how if you're interested.\n\nBest,\nDave",
      direction: "sent",
    },
    {
      id: "em2",
      sender: "Sarah Chen",
      timestamp: "Today • 10:42 AM",
      subject: "Re: Quick question about Bloom Digital",
      body: "Hi Dave,\n\nYes, I'd love to learn more. We're definitely looking to scale — our current approach is too manual and I know we're leaving opportunities on the table.\n\nCan we schedule a call next week? I'm free Tuesday or Wednesday afternoon.\n\nBest,\nSarah",
      direction: "received",
    },
  ],
  linkedinThread: [
    {
      id: "li1",
      sender: "You",
      timestamp: "Jan 29 • 9:00 AM",
      text: "Hi Sarah — I came across Bloom Digital and love what you're doing in the agency space. Would be great to connect!",
      direction: "sent",
    },
    {
      id: "li2",
      sender: "System",
      timestamp: "Jan 29 • 2:30 PM",
      text: "Sarah accepted your connection request",
      direction: "sent",
      isConnectionAccepted: true,
    },
    {
      id: "li3",
      sender: "You",
      timestamp: "Jan 29 • 2:35 PM",
      text: "Thanks for connecting, Sarah! I noticed you're scaling Bloom Digital — we help agencies like yours book 10-15 qualified meetings per month. Thought it might be relevant. Worth a quick chat?",
      direction: "sent",
    },
    {
      id: "li4",
      sender: "Sarah Chen",
      timestamp: "Jan 29 • 3:12 PM",
      text: "Hi! Thanks for reaching out. I actually just got your email too — good timing. Yes, definitely interested in learning more. I just replied to your email with my availability.",
      direction: "received",
    },
    {
      id: "li5",
      sender: "You",
      timestamp: "Jan 29 • 3:18 PM",
      text: "Perfect! Just saw it. Looking forward to chatting 🙌",
      direction: "sent",
    },
  ],
  notes: [
    {
      id: "n1",
      author: "You",
      timestamp: "Today at 10:45 AM",
      text: "Hot lead! She replied asking for a call. Schedule ASAP — she's actively evaluating solutions for scaling their agency's outreach.",
    },
  ],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const MOCK_TRANSCRIPT: TranscriptLine[] = [
  { speaker: "ai", speakerName: "Emma (Voice AI)", timestamp: "0:00", text: "Hi, is this Sarah?" },
  { speaker: "lead", speakerName: "Sarah Chen", timestamp: "0:03", text: "Yes, speaking. Who's this?" },
  { speaker: "ai", speakerName: "Emma (Voice AI)", timestamp: "0:05", text: "Hey Sarah, this is Emma calling from Agency OS. I'm following up on an email we sent over — you'd mentioned you were interested in learning more about scaling your client acquisition. Did I catch you at an okay time?" },
  { speaker: "lead", speakerName: "Sarah Chen", timestamp: "0:18", text: "Oh, yeah, I remember that email. I've got a few minutes. What exactly do you help with?" },
  { speaker: "ai", speakerName: "Emma (Voice AI)", timestamp: "0:25", text: "Perfect, I'll keep it quick. We work with agencies like Bloom Digital to help them book more qualified meetings without adding headcount. I saw you're doing some great work in the digital marketing space — are you currently looking to bring on more clients, or is the pipeline pretty full right now?" },
  { speaker: "lead", speakerName: "Sarah Chen", timestamp: "0:45", text: "Actually, we're definitely looking to grow. We just expanded into Queensland and our current outreach is way too manual. It's eating up so much of my team's time.", highlight: { type: "pain_point", label: "Pain Point: Manual outreach, team time drain" } },
  { speaker: "ai", speakerName: "Emma (Voice AI)", timestamp: "1:02", text: "That's exactly what we solve. We automate multi-channel outreach — email, LinkedIn, even AI calls like this one — and typically help agencies book 10-15 qualified meetings per month. Would it make sense to do a quick demo so you can see how it would work for Bloom specifically?" },
  { speaker: "lead", speakerName: "Sarah Chen", timestamp: "1:20", text: "Yeah, actually that would be great. I'd love to see how it works. When are you available?", highlight: { type: "meeting_intent", label: "Meeting Intent Detected" } },
  { speaker: "ai", speakerName: "Emma (Voice AI)", timestamp: "1:28", text: "I have Thursday at 10am or Friday at 2pm. Which works better for you?" },
  { speaker: "lead", speakerName: "Sarah Chen", timestamp: "1:35", text: "Thursday at 10 works perfectly.", highlight: { type: "meeting_booked", label: "Meeting Booked: Thursday 10:00 AM" } },
];

// ============================================
// Sub-Modal State Type
// ============================================
type SubModalType = "voice" | "email" | "linkedin" | null;

// ============================================
// Helper Functions
// ============================================

function getChannelColor(type: ChannelType | "reply") {
  switch (type) {
    case "email": return "bg-amber/15 text-amber";
    case "linkedin": return "bg-amber-glow text-amber";
    case "voice": return "bg-amber-500/15 text-amber-400";
    case "sms": return "bg-amber-glow text-amber";
    case "reply": return "bg-amber/15 text-amber";
    default: return "bg-amber/15 text-amber";
  }
}

function getWhyHotStyle(category: WhyHotCategory) {
  switch (category) {
    case "executive": return "bg-amber/15 text-amber border-amber/30";
    case "active": return "bg-amber/15 text-amber border-amber/30";
    case "buyer": return "bg-amber-500/15 text-amber-400 border-amber-500/30";
    case "linkedin": return "bg-amber-glow text-amber border-amber/30";
    case "timing": return "bg-amber-glow text-amber-light border-amber-light/30";
    default: return "bg-bg-surface text-text-secondary border-slate-500/30";
  }
}

function getWhyHotIcon(category: WhyHotCategory) {
  switch (category) {
    case "executive": return <Sparkles className="w-3 h-3" />;
    case "active": return <Sparkles className="w-3 h-3" />;
    case "buyer": return <DollarSign className="w-3 h-3" />;
    case "linkedin": return <Link2 className="w-3 h-3" />;
    case "timing": return <Clock className="w-3 h-3" />;
    default: return <Sparkles className="w-3 h-3" />;
  }
}

// ============================================
// Voice Transcript Sub-Modal
// ============================================

function VoiceTranscriptModal({
  isOpen,
  onClose,
  lead,
}: {
  isOpen: boolean;
  onClose: () => void;
  lead: Lead;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[60]">
      <div className="w-full max-w-2xl bg-bg-base border border-default rounded-2xl shadow-2xl overflow-hidden mx-4 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-default">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-text-primary">
            <Phone className="w-5 h-5" />
            Voice AI Transcript
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-bg-elevated text-text-muted hover:text-text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {/* Call Header */}
          <div className="flex items-center gap-4 p-5 bg-bg-elevated rounded-xl mb-5">
            <div className="w-13 h-13 bg-gradient-to-br from-amber to-amber-light rounded-xl flex items-center justify-center p-3">
              <Phone className="w-6 h-6 text-text-primary" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-text-primary">
                Call with {lead.firstName} {lead.lastName}
              </h4>
              <p className="text-sm text-text-muted">{lead.phone}</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold font-mono text-amber">3:24</div>
              <div className="text-xs text-text-muted">Yesterday • 4:30 PM</div>
            </div>
          </div>

          {/* Audio Player */}
          <div className="flex items-center gap-4 p-4 bg-bg-void rounded-xl mb-6">
            <button className="w-12 h-12 bg-amber hover:bg-violet-400 rounded-full flex items-center justify-center transition-colors">
              <Play className="w-5 h-5 text-text-primary ml-0.5" />
            </button>
            <div className="flex-1">
              <div className="flex justify-between text-xs font-mono text-text-muted mb-2">
                <span>0:00</span>
                <span>3:24</span>
              </div>
              <div className="h-1.5 bg-[#2A2A3D] rounded-full overflow-hidden">
                <div className="h-full w-[35%] bg-amber rounded-full" />
              </div>
            </div>
          </div>

          {/* Transcript */}
          <div>
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-muted mb-4">
              <FileText className="w-4 h-4" />
              AI Transcript with Highlights
            </h4>

            <div className="space-y-4">
              {MOCK_TRANSCRIPT.map((line, idx) => (
                <div key={idx} className="flex gap-3">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                      line.speaker === "ai"
                        ? "bg-amber/15 text-amber"
                        : "bg-bg-elevated text-text-muted"
                    }`}
                  >
                    {line.speaker === "ai" ? "AI" : "SC"}
                  </div>
                  <div className="flex-1">
                    <div className="text-xs text-text-secondary mb-1">
                      <span className="font-semibold">{line.speakerName}</span>
                      <span className="font-mono text-text-muted ml-2">{line.timestamp}</span>
                    </div>
                    <p className="text-sm text-text-primary leading-relaxed">{line.text}</p>
                    {line.highlight && (
                      <div
                        className={`inline-flex items-center gap-1.5 mt-2 px-3 py-1.5 rounded-md text-xs font-medium ${
                          line.highlight.type === "pain_point"
                            ? "bg-amber/10 text-amber border border-amber/30"
                            : "bg-amber/10 text-amber border border-amber/30"
                        }`}
                      >
                        {line.highlight.type === "pain_point" && ""}
                        {line.highlight.type === "meeting_intent" && ""}
                        {line.highlight.type === "meeting_booked" && "✓"}
                        {line.highlight.label}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Email Thread Sub-Modal
// ============================================

function EmailThreadModal({
  isOpen,
  onClose,
  lead,
}: {
  isOpen: boolean;
  onClose: () => void;
  lead: Lead;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[60]">
      <div className="w-full max-w-2xl bg-bg-base border border-default rounded-2xl shadow-2xl overflow-hidden mx-4 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-default">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-text-primary">
            <Mail className="w-5 h-5" />
            Email Conversation
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-bg-elevated text-text-muted hover:text-text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[70vh] overflow-y-auto space-y-4">
          {lead.emailThread.map((email) => (
            <div
              key={email.id}
              className={`p-5 rounded-xl ${
                email.direction === "sent"
                  ? "bg-amber/10 border border-amber/20 ml-6"
                  : "bg-bg-elevated border border-default mr-6"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold text-text-primary">{email.sender}</span>
                <span className="text-xs text-text-muted">{email.timestamp}</span>
              </div>
              <div className="text-sm font-medium text-text-secondary mb-3 pb-3 border-b border-default">
                Subject: {email.subject}
              </div>
              <div className="text-sm text-text-primary leading-relaxed whitespace-pre-line">
                {email.body}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================
// LinkedIn Thread Sub-Modal
// ============================================

function LinkedInThreadModal({
  isOpen,
  onClose,
  lead,
}: {
  isOpen: boolean;
  onClose: () => void;
  lead: Lead;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[60]">
      <div className="w-full max-w-2xl bg-bg-base border border-default rounded-2xl shadow-2xl overflow-hidden mx-4 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-default">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-text-primary">
            <Briefcase className="w-5 h-5" />
            LinkedIn Conversation
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-bg-elevated text-text-muted hover:text-text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {/* LinkedIn Header */}
          <div className="flex items-center gap-4 p-5 bg-amber-glow border border-amber/20 rounded-xl mb-5">
            <div className="w-13 h-13 bg-[#0077B5] rounded-xl flex items-center justify-center p-3">
              <Briefcase className="w-7 h-7 text-text-primary" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-text-primary">
                {lead.firstName} {lead.lastName}
              </h4>
              <p className="text-sm text-text-muted">{lead.title} at {lead.company.name}</p>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-amber font-medium">
              <CheckCircle2 className="w-4 h-4" />
              1st degree
            </div>
          </div>

          {/* Messages */}
          <div className="space-y-3">
            {lead.linkedinThread.map((msg) => {
              if (msg.isConnectionAccepted) {
                return (
                  <div key={msg.id} className="flex justify-center my-4">
                    <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber/10 border border-amber/30 text-amber rounded-full text-sm font-medium">
                      <CheckCircle2 className="w-4 h-4" />
                      {msg.text}
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={msg.id}
                  className={`max-w-[85%] p-4 rounded-2xl ${
                    msg.direction === "sent"
                      ? "bg-[#0077B5] text-text-primary ml-auto rounded-br-sm"
                      : "bg-bg-elevated text-text-primary mr-auto rounded-bl-sm"
                  }`}
                >
                  <p className="text-sm leading-relaxed">{msg.text}</p>
                  <div
                    className={`text-xs mt-1.5 ${
                      msg.direction === "sent" ? "text-text-primary/70" : "text-text-muted"
                    }`}
                  >
                    {msg.timestamp}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function LeadDetailModal({ isOpen, onClose, lead: propLead }: LeadDetailModalProps) {
  const [activeFilter, setActiveFilter] = useState<ChannelType | "all">("all");
  const [subModal, setSubModal] = useState<SubModalType>(null);
  const [noteInput, setNoteInput] = useState("");

  // Use mock data if no lead provided
  const lead = propLead ?? MOCK_LEAD;

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (subModal) {
          setSubModal(null);
        } else {
          onClose();
        }
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, subModal, onClose]);

  if (!isOpen) return null;

  // Filter timeline events
  const filteredTimeline = lead.timeline.map((day) => ({
    ...day,
    events:
      activeFilter === "all"
        ? day.events
        : day.events.filter((e) => e.type === activeFilter || (activeFilter === "email" && e.type === "reply")),
  })).filter((day) => day.events.length > 0);

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50" onClick={onClose} />

      {/* Slide-over Panel */}
      <div className="fixed inset-y-0 right-0 w-full max-w-4xl bg-bg-void shadow-xl z-50 overflow-hidden flex flex-col animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="bg-bg-base border-b border-default px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={onClose}
                className="flex items-center gap-2 text-sm text-text-muted hover:text-text-secondary transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Leads
              </button>
              <div className="w-px h-6 bg-[#2A2A3D]" />
              <span className="text-sm text-text-muted">Lead Details</span>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-bg-elevated text-text-muted hover:text-text-primary transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6">
            {/* Profile Header Card */}
            <div className="bg-bg-base border border-default rounded-2xl p-6 mb-6 relative overflow-hidden">
              {/* Top accent bar */}
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber to-amber" />

              <div className="flex gap-8">
                {/* Left: Avatar + Info */}
                <div className="flex gap-6 flex-1">
                  {/* Avatar */}
                  <div className="w-20 h-20 bg-gradient-to-br from-amber to-amber-light rounded-2xl flex items-center justify-center text-text-primary font-bold text-2xl flex-shrink-0">
                    {lead.firstName[0]}
                    {lead.lastName[0]}
                  </div>

                  {/* Info */}
                  <div>
                    <h1 className="text-2xl font-bold text-text-primary mb-1">
                      {lead.firstName} {lead.lastName}
                    </h1>
                    <p className="text-text-secondary mb-4">
                      {lead.title} at {lead.company.name}
                    </p>

                    {/* Meta */}
                    <div className="flex flex-wrap gap-5">
                      <div className="flex items-center gap-2 text-sm text-text-secondary">
                        <Mail className="w-4 h-4 text-text-muted" />
                        <a href={`mailto:${lead.email}`} className="text-amber hover:underline">
                          {lead.email}
                        </a>
                      </div>
                      {lead.phone && (
                        <div className="flex items-center gap-2 text-sm text-text-secondary">
                          <Phone className="w-4 h-4 text-text-muted" />
                          {lead.phone}
                        </div>
                      )}
                      {lead.linkedinUrl && (
                        <div className="flex items-center gap-2 text-sm text-text-secondary">
                          <Briefcase className="w-4 h-4 text-text-muted" />
                          <a href="#" className="text-amber hover:underline">
                            {lead.linkedinUrl}
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Score + Tier */}
                <div className="flex flex-col items-end gap-3">
                  <div className="text-center px-6 py-4 bg-amber-glow border border-amber/30 rounded-xl">
                    <div className="text-5xl font-extrabold font-mono text-amber leading-none">
                      {lead.score}
                    </div>
                    <div className="text-[10px] font-semibold text-text-muted uppercase tracking-widest mt-1">
                      Lead Score
                    </div>
                  </div>
                  <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-glow text-amber text-sm font-semibold rounded-lg border border-amber/30">
                    <Flame className="w-4 h-4" />
                    Very Hot
                  </div>
                </div>
              </div>

              {/* Why Hot Section */}
              <div className="mt-6 pt-6 border-t border-default">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-text-muted mb-3">
                  <BadgeCheck className="w-4 h-4" />
                  Why This Lead is Hot
                </div>
                <div className="flex flex-wrap gap-2.5">
                  {lead.whyHot.map((badge) => (
                    <span
                      key={badge.id}
                      className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium border transition-transform hover:-translate-y-0.5 ${getWhyHotStyle(
                        badge.category
                      )}`}
                    >
                      {getWhyHotIcon(badge.category)}
                      {badge.label}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Grid Layout */}
            <div className="grid grid-cols-3 gap-6">
              {/* Left Column (2/3) */}
              <div className="col-span-2 space-y-6">
                {/* Engagement Profile Card */}
                <div className="bg-bg-base border border-default rounded-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-default flex items-center justify-between">
                    <div className="flex items-center gap-2.5 text-[15px] font-semibold text-text-primary">
                      <BarChart3 className="w-4 h-4" />
                      Engagement Profile
                    </div>
                    <span className="text-xs text-text-muted">Score breakdown by signal</span>
                  </div>
                  <div className="p-6">
                    <div className="space-y-3">
                      {Object.values(lead.engagementProfile).map((score) => (
                        <div key={score.label} className="flex items-center gap-4">
                          <span className="flex-1 text-sm text-text-secondary">{score.label}</span>
                          <div className="w-32 h-2 bg-bg-elevated rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                score.level === "high"
                                  ? "bg-amber"
                                  : score.level === "medium"
                                  ? "bg-amber-500"
                                  : "bg-bg-elevated"
                              }`}
                              style={{ width: `${(score.value / score.maxValue) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-semibold font-mono text-text-primary min-w-[50px] text-right">
                            {score.value}/{score.maxValue}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Activity Timeline Card */}
                <div className="bg-bg-base border border-default rounded-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-default flex items-center justify-between">
                    <div className="flex items-center gap-2.5 text-[15px] font-semibold text-text-primary">
                      <Zap className="w-4 h-4" />
                      Activity Timeline
                    </div>
                    <span className="text-xs text-text-muted">Multi-channel engagement history</span>
                  </div>
                  <div className="p-6">
                    {/* Filters */}
                    <div className="flex gap-2 mb-5">
                      {(["all", "email", "linkedin", "voice", "sms"] as const).map((filter) => (
                        <button
                          key={filter}
                          onClick={() => setActiveFilter(filter)}
                          className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                            activeFilter === filter
                              ? filter === "all"
                                ? "bg-bg-elevated text-text-primary border-[#3A3A50]"
                                : filter === "email"
                                ? "border-amber text-amber"
                                : filter === "linkedin"
                                ? "border-amber text-amber"
                                : filter === "voice"
                                ? "border-amber-500 text-amber-400"
                                : "border-amber text-amber"
                              : "bg-bg-elevated text-text-muted border-default hover:text-text-primary hover:border-[#3A3A50]"
                          }`}
                        >
                          {filter.charAt(0).toUpperCase() + filter.slice(1)}
                        </button>
                      ))}
                    </div>

                    {/* Timeline */}
                    <div className="space-y-6">
                      {filteredTimeline.map((day) => (
                        <div key={day.date}>
                          <div
                            className={`flex items-center gap-3 text-[11px] font-semibold uppercase tracking-widest mb-3 ${
                              day.isToday ? "text-amber" : "text-text-muted"
                            }`}
                          >
                            {day.date}
                            <div className="flex-1 h-px bg-bg-surface" />
                          </div>

                          <div className="space-y-2 pl-5 border-l-2 border-default">
                            {day.events.map((event) => (
                              <div
                                key={event.id}
                                onClick={() => {
                                  if (event.hasTranscript) setSubModal("voice");
                                  else if (event.hasThread && event.type === "linkedin") setSubModal("linkedin");
                                  else if (event.hasThread) setSubModal("email");
                                }}
                                className="relative flex items-start gap-3.5 p-4 bg-bg-elevated hover:bg-bg-elevated rounded-xl cursor-pointer transition-all hover:translate-x-1"
                              >
                                {/* Timeline dot */}
                                <div
                                  className={`absolute -left-[26px] top-5 w-2.5 h-2.5 rounded-full border-2 ${
                                    event.type === "reply"
                                      ? "border-amber bg-amber/20"
                                      : event.type === "email"
                                      ? "border-amber bg-amber/20"
                                      : event.type === "linkedin"
                                      ? "border-amber bg-amber/20"
                                      : event.type === "voice"
                                      ? "border-amber-500 bg-amber-500/20"
                                      : "border-amber bg-amber/20"
                                  }`}
                                />

                                {/* Icon */}
                                <div
                                  className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${getChannelColor(
                                    event.type
                                  )}`}
                                >
                                  {event.type === "reply" && ""}
                                  {event.type === "email" && ""}
                                  {event.type === "linkedin" && ""}
                                  {event.type === "voice" && ""}
                                  {event.type === "sms" && ""}
                                </div>

                                {/* Content */}
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 text-sm text-text-primary">
                                    <span className="font-semibold">{event.title}</span>
                                    {event.badge && (
                                      <span
                                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${
                                          event.badge.type === "booked"
                                            ? "bg-amber/15 text-amber"
                                            : "bg-bg-elevated/15 text-text-secondary"
                                        }`}
                                      >
                                        {event.badge.label}
                                      </span>
                                    )}
                                  </div>
                                  {event.detail && (
                                    <p className="text-sm text-text-secondary mt-1 leading-relaxed">
                                      {event.detail}
                                    </p>
                                  )}
                                  <div className="flex items-center gap-3 mt-2">
                                    <span className="text-xs font-mono text-text-muted">
                                      {event.displayTime}
                                    </span>
                                    {(event.hasTranscript || event.hasThread) && (
                                      <span className="text-xs text-amber hover:underline">
                                        {event.hasTranscript ? "▶ Play & View Transcript →" : "View thread →"}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column (1/3) */}
              <div className="space-y-6">
                {/* Company Intel Card */}
                <div className="bg-bg-base border border-default rounded-xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-default">
                    <div className="flex items-center gap-2 text-[15px] font-semibold text-text-primary">
                      Company Intel
                    </div>
                  </div>
                  <div className="p-5">
                    {/* Company Header */}
                    <div className="flex items-center gap-4 mb-5">
                      <div className="w-13 h-13 bg-bg-elevated rounded-xl flex items-center justify-center text-2xl border border-default p-3">
                        {lead.company.logoEmoji}
                      </div>
                      <div>
                        <h3 className="font-semibold text-text-primary">{lead.company.name}</h3>
                        <a href={`https://${lead.company.domain}`} className="text-sm text-amber hover:underline">
                          {lead.company.domain}
                        </a>
                      </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 gap-3 mb-5">
                      {[
                        { label: "Employees", value: lead.company.employees },
                        { label: "Industry", value: lead.company.industry },
                        { label: "Est. Revenue", value: lead.company.estimatedRevenue },
                        { label: "Location", value: lead.company.location },
                      ].map((stat) => (
                        <div key={stat.label} className="p-4 bg-bg-elevated rounded-xl text-center">
                          <div className="text-lg font-bold font-mono text-text-primary">{stat.value}</div>
                          <div className="text-[11px] text-text-muted uppercase mt-1">{stat.label}</div>
                        </div>
                      ))}
                    </div>

                    {/* Recent Intelligence */}
                    <div className="pt-5 border-t border-default">
                      <div className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-3">
                        📰 Recent Intelligence
                      </div>
                      <div className="space-y-2.5">
                        {lead.company.recentIntelligence.map((intel, idx) => (
                          <div key={idx} className="flex items-start gap-2.5 py-2.5 border-b border-default last:border-0">
                            <span className="text-sm">{intel.icon}</span>
                            <span className="text-sm text-text-secondary leading-relaxed">{intel.text}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Quick Actions Card */}
                <div className="bg-bg-base border border-default rounded-xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-default">
                    <div className="flex items-center gap-2 text-[15px] font-semibold text-text-primary">
                      <Zap className="w-4 h-4" />
                      Quick Actions
                    </div>
                  </div>
                  <div className="p-5">
                    <div className="grid grid-cols-2 gap-2.5">
                      <button className="col-span-2 flex items-center justify-center gap-2 px-4 py-3.5 bg-gradient-to-r from-amber to-amber-light text-text-primary text-sm font-medium rounded-xl hover:opacity-90 hover:-translate-y-0.5 transition-all">
                        <Calendar className="w-5 h-5" />
                        Book Meeting
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-bg-elevated text-text-secondary text-sm font-medium rounded-xl border border-default hover:bg-bg-elevated hover:text-text-primary hover:border-[#3A3A50] transition-all">
                        <Mail className="w-4 h-4" />
                        Send Email
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-bg-elevated text-text-secondary text-sm font-medium rounded-xl border border-default hover:bg-bg-elevated hover:text-text-primary hover:border-[#3A3A50] transition-all">
                        <Briefcase className="w-4 h-4" />
                        LinkedIn DM
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-bg-elevated text-text-secondary text-sm font-medium rounded-xl border border-default hover:bg-bg-elevated hover:text-text-primary hover:border-[#3A3A50] transition-all">
                        <MessageSquare className="w-4 h-4" />
                        Send SMS
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-bg-elevated text-text-secondary text-sm font-medium rounded-xl border border-default hover:bg-bg-elevated hover:text-text-primary hover:border-[#3A3A50] transition-all">
                        <Phone className="w-4 h-4" />
                        AI Call
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-amber-glow text-amber text-sm font-medium rounded-xl border border-amber/30 hover:bg-amber/20 transition-all">
                        ⏸️ Pause
                      </button>
                    </div>
                  </div>
                </div>

                {/* Notes Card */}
                <div className="bg-bg-base border border-default rounded-xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-default">
                    <div className="flex items-center gap-2 text-[15px] font-semibold text-text-primary">
                      Notes
                    </div>
                  </div>
                  <div className="p-5">
                    <textarea
                      value={noteInput}
                      onChange={(e) => setNoteInput(e.target.value)}
                      placeholder="Add a note about this lead..."
                      rows={3}
                      className="w-full p-4 text-sm bg-bg-elevated border border-default rounded-xl resize-none text-text-primary placeholder-[#6E6E82] outline-none focus:border-amber focus:ring-2 focus:ring-amber/20 transition-all"
                    />
                    <div className="mt-4 space-y-3">
                      {lead.notes.map((note) => (
                        <div
                          key={note.id}
                          className="bg-amber-500/10 border-l-[3px] border-amber-500 rounded-r-xl p-4"
                        >
                          <div className="text-xs text-text-muted mb-1.5">
                            {note.author} • {note.timestamp}
                          </div>
                          <p className="text-sm text-text-secondary leading-relaxed">{note.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sub-modals */}
      <VoiceTranscriptModal isOpen={subModal === "voice"} onClose={() => setSubModal(null)} lead={lead} />
      <EmailThreadModal isOpen={subModal === "email"} onClose={() => setSubModal(null)} lead={lead} />
      <LinkedInThreadModal isOpen={subModal === "linkedin"} onClose={() => setSubModal(null)} lead={lead} />
    </>
  );
}

export default LeadDetailModal;
