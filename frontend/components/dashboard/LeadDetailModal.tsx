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
// Base: bg-[#0A0A12]
// Surface: bg-[#12121D]
// Surface Hover: bg-[#1A1A28]
// Elevated: bg-[#222233]
// Border Subtle: border-[#1E1E2E]
// Border Default: border-[#2A2A3D]
// Text Primary: text-[#F8F8FC]
// Text Secondary: text-[#B4B4C4]
// Text Muted: text-[#6E6E82]
// Accent Purple: text-violet-500 / bg-violet-500
// Tier Hot: text-red-500 / bg-red-500/10

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
      { icon: "📈", text: "Expanded to Queensland market (Jan 2026)" },
      { icon: "👥", text: "Hired 3 new BDRs in last 60 days" },
      { icon: "🏆", text: 'Featured in "Top 50 Agencies to Watch"' },
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
    case "email": return "bg-violet-500/15 text-violet-400";
    case "linkedin": return "bg-sky-500/15 text-sky-400";
    case "voice": return "bg-amber-500/15 text-amber-400";
    case "sms": return "bg-teal-500/15 text-teal-400";
    case "reply": return "bg-green-500/15 text-green-400";
    default: return "bg-violet-500/15 text-violet-400";
  }
}

function getWhyHotStyle(category: WhyHotCategory) {
  switch (category) {
    case "executive": return "bg-violet-500/15 text-violet-400 border-violet-500/30";
    case "active": return "bg-green-500/15 text-green-400 border-green-500/30";
    case "buyer": return "bg-amber-500/15 text-amber-400 border-amber-500/30";
    case "linkedin": return "bg-sky-500/15 text-sky-400 border-sky-500/30";
    case "timing": return "bg-pink-500/15 text-pink-400 border-pink-500/30";
    default: return "bg-slate-500/15 text-slate-400 border-slate-500/30";
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
      <div className="w-full max-w-2xl bg-[#12121D] border border-[#1E1E2E] rounded-2xl shadow-2xl overflow-hidden mx-4 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#1E1E2E]">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-[#F8F8FC]">
            <Phone className="w-5 h-5" />
            Voice AI Transcript
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-[#222233] text-[#6E6E82] hover:text-[#F8F8FC] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {/* Call Header */}
          <div className="flex items-center gap-4 p-5 bg-[#222233] rounded-xl mb-5">
            <div className="w-13 h-13 bg-gradient-to-br from-violet-500 to-blue-500 rounded-xl flex items-center justify-center p-3">
              <Phone className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-[#F8F8FC]">
                Call with {lead.firstName} {lead.lastName}
              </h4>
              <p className="text-sm text-[#6E6E82]">{lead.phone}</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold font-mono text-green-400">3:24</div>
              <div className="text-xs text-[#6E6E82]">Yesterday • 4:30 PM</div>
            </div>
          </div>

          {/* Audio Player */}
          <div className="flex items-center gap-4 p-4 bg-[#05050A] rounded-xl mb-6">
            <button className="w-12 h-12 bg-violet-500 hover:bg-violet-400 rounded-full flex items-center justify-center transition-colors">
              <Play className="w-5 h-5 text-white ml-0.5" />
            </button>
            <div className="flex-1">
              <div className="flex justify-between text-xs font-mono text-[#6E6E82] mb-2">
                <span>0:00</span>
                <span>3:24</span>
              </div>
              <div className="h-1.5 bg-[#2A2A3D] rounded-full overflow-hidden">
                <div className="h-full w-[35%] bg-violet-500 rounded-full" />
              </div>
            </div>
          </div>

          {/* Transcript */}
          <div>
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#6E6E82] mb-4">
              <FileText className="w-4 h-4" />
              AI Transcript with Highlights
            </h4>

            <div className="space-y-4">
              {MOCK_TRANSCRIPT.map((line, idx) => (
                <div key={idx} className="flex gap-3">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                      line.speaker === "ai"
                        ? "bg-violet-500/15 text-violet-400"
                        : "bg-[#222233] text-[#6E6E82]"
                    }`}
                  >
                    {line.speaker === "ai" ? "AI" : "SC"}
                  </div>
                  <div className="flex-1">
                    <div className="text-xs text-[#B4B4C4] mb-1">
                      <span className="font-semibold">{line.speakerName}</span>
                      <span className="font-mono text-[#6E6E82] ml-2">{line.timestamp}</span>
                    </div>
                    <p className="text-sm text-[#F8F8FC] leading-relaxed">{line.text}</p>
                    {line.highlight && (
                      <div
                        className={`inline-flex items-center gap-1.5 mt-2 px-3 py-1.5 rounded-md text-xs font-medium ${
                          line.highlight.type === "pain_point"
                            ? "bg-green-500/10 text-green-400 border border-green-500/30"
                            : "bg-violet-500/10 text-violet-400 border border-violet-500/30"
                        }`}
                      >
                        {line.highlight.type === "pain_point" && "🎯"}
                        {line.highlight.type === "meeting_intent" && "📅"}
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
      <div className="w-full max-w-2xl bg-[#12121D] border border-[#1E1E2E] rounded-2xl shadow-2xl overflow-hidden mx-4 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#1E1E2E]">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-[#F8F8FC]">
            <Mail className="w-5 h-5" />
            Email Conversation
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-[#222233] text-[#6E6E82] hover:text-[#F8F8FC] transition-colors"
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
                  ? "bg-violet-500/10 border border-violet-500/20 ml-6"
                  : "bg-[#222233] border border-[#1E1E2E] mr-6"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold text-[#F8F8FC]">{email.sender}</span>
                <span className="text-xs text-[#6E6E82]">{email.timestamp}</span>
              </div>
              <div className="text-sm font-medium text-[#B4B4C4] mb-3 pb-3 border-b border-[#1E1E2E]">
                Subject: {email.subject}
              </div>
              <div className="text-sm text-[#F8F8FC] leading-relaxed whitespace-pre-line">
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
      <div className="w-full max-w-2xl bg-[#12121D] border border-[#1E1E2E] rounded-2xl shadow-2xl overflow-hidden mx-4 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#1E1E2E]">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-[#F8F8FC]">
            <Briefcase className="w-5 h-5" />
            LinkedIn Conversation
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-[#222233] text-[#6E6E82] hover:text-[#F8F8FC] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {/* LinkedIn Header */}
          <div className="flex items-center gap-4 p-5 bg-sky-500/10 border border-sky-500/20 rounded-xl mb-5">
            <div className="w-13 h-13 bg-[#0077B5] rounded-xl flex items-center justify-center p-3">
              <Briefcase className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-[#F8F8FC]">
                {lead.firstName} {lead.lastName}
              </h4>
              <p className="text-sm text-[#6E6E82]">{lead.title} at {lead.company.name}</p>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-sky-400 font-medium">
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
                    <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-500/10 border border-green-500/30 text-green-400 rounded-full text-sm font-medium">
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
                      ? "bg-[#0077B5] text-white ml-auto rounded-br-sm"
                      : "bg-[#222233] text-[#F8F8FC] mr-auto rounded-bl-sm"
                  }`}
                >
                  <p className="text-sm leading-relaxed">{msg.text}</p>
                  <div
                    className={`text-xs mt-1.5 ${
                      msg.direction === "sent" ? "text-white/70" : "text-[#6E6E82]"
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
      <div className="fixed inset-y-0 right-0 w-full max-w-4xl bg-[#0A0A12] shadow-xl z-50 overflow-hidden flex flex-col animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="bg-[#12121D] border-b border-[#1E1E2E] px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={onClose}
                className="flex items-center gap-2 text-sm text-[#6E6E82] hover:text-[#B4B4C4] transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Leads
              </button>
              <div className="w-px h-6 bg-[#2A2A3D]" />
              <span className="text-sm text-[#6E6E82]">Lead Details</span>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-[#222233] text-[#6E6E82] hover:text-[#F8F8FC] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6">
            {/* Profile Header Card */}
            <div className="bg-[#12121D] border border-[#1E1E2E] rounded-2xl p-6 mb-6 relative overflow-hidden">
              {/* Top accent bar */}
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-500 to-violet-500" />

              <div className="flex gap-8">
                {/* Left: Avatar + Info */}
                <div className="flex gap-6 flex-1">
                  {/* Avatar */}
                  <div className="w-20 h-20 bg-gradient-to-br from-red-500 to-orange-500 rounded-2xl flex items-center justify-center text-white font-bold text-2xl flex-shrink-0">
                    {lead.firstName[0]}
                    {lead.lastName[0]}
                  </div>

                  {/* Info */}
                  <div>
                    <h1 className="text-2xl font-bold text-[#F8F8FC] mb-1">
                      {lead.firstName} {lead.lastName}
                    </h1>
                    <p className="text-[#B4B4C4] mb-4">
                      {lead.title} at {lead.company.name}
                    </p>

                    {/* Meta */}
                    <div className="flex flex-wrap gap-5">
                      <div className="flex items-center gap-2 text-sm text-[#B4B4C4]">
                        <Mail className="w-4 h-4 text-[#6E6E82]" />
                        <a href={`mailto:${lead.email}`} className="text-violet-400 hover:underline">
                          {lead.email}
                        </a>
                      </div>
                      {lead.phone && (
                        <div className="flex items-center gap-2 text-sm text-[#B4B4C4]">
                          <Phone className="w-4 h-4 text-[#6E6E82]" />
                          {lead.phone}
                        </div>
                      )}
                      {lead.linkedinUrl && (
                        <div className="flex items-center gap-2 text-sm text-[#B4B4C4]">
                          <Briefcase className="w-4 h-4 text-[#6E6E82]" />
                          <a href="#" className="text-violet-400 hover:underline">
                            {lead.linkedinUrl}
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Score + Tier */}
                <div className="flex flex-col items-end gap-3">
                  <div className="text-center px-6 py-4 bg-red-500/10 border border-red-500/30 rounded-xl">
                    <div className="text-5xl font-extrabold font-mono text-red-500 leading-none">
                      {lead.score}
                    </div>
                    <div className="text-[10px] font-semibold text-[#6E6E82] uppercase tracking-widest mt-1">
                      Lead Score
                    </div>
                  </div>
                  <div className="inline-flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-500 text-sm font-semibold rounded-lg border border-red-500/30">
                    <Flame className="w-4 h-4" />
                    Very Hot
                  </div>
                </div>
              </div>

              {/* Why Hot Section */}
              <div className="mt-6 pt-6 border-t border-[#1E1E2E]">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#6E6E82] mb-3">
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
                <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-[#1E1E2E] flex items-center justify-between">
                    <div className="flex items-center gap-2.5 text-[15px] font-semibold text-[#F8F8FC]">
                      <BarChart3 className="w-4 h-4" />
                      Engagement Profile
                    </div>
                    <span className="text-xs text-[#6E6E82]">Score breakdown by signal</span>
                  </div>
                  <div className="p-6">
                    <div className="space-y-3">
                      {Object.values(lead.engagementProfile).map((score) => (
                        <div key={score.label} className="flex items-center gap-4">
                          <span className="flex-1 text-sm text-[#B4B4C4]">{score.label}</span>
                          <div className="w-32 h-2 bg-[#222233] rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                score.level === "high"
                                  ? "bg-green-500"
                                  : score.level === "medium"
                                  ? "bg-amber-500"
                                  : "bg-blue-500"
                              }`}
                              style={{ width: `${(score.value / score.maxValue) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-semibold font-mono text-[#F8F8FC] min-w-[50px] text-right">
                            {score.value}/{score.maxValue}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Activity Timeline Card */}
                <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-[#1E1E2E] flex items-center justify-between">
                    <div className="flex items-center gap-2.5 text-[15px] font-semibold text-[#F8F8FC]">
                      <Zap className="w-4 h-4" />
                      Activity Timeline
                    </div>
                    <span className="text-xs text-[#6E6E82]">Multi-channel engagement history</span>
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
                                ? "bg-[#1A1A28] text-[#F8F8FC] border-[#3A3A50]"
                                : filter === "email"
                                ? "border-violet-500 text-violet-400"
                                : filter === "linkedin"
                                ? "border-sky-500 text-sky-400"
                                : filter === "voice"
                                ? "border-amber-500 text-amber-400"
                                : "border-teal-500 text-teal-400"
                              : "bg-[#222233] text-[#6E6E82] border-[#2A2A3D] hover:text-[#F8F8FC] hover:border-[#3A3A50]"
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
                              day.isToday ? "text-green-400" : "text-[#6E6E82]"
                            }`}
                          >
                            {day.date}
                            <div className="flex-1 h-px bg-[#1E1E2E]" />
                          </div>

                          <div className="space-y-2 pl-5 border-l-2 border-[#1E1E2E]">
                            {day.events.map((event) => (
                              <div
                                key={event.id}
                                onClick={() => {
                                  if (event.hasTranscript) setSubModal("voice");
                                  else if (event.hasThread && event.type === "linkedin") setSubModal("linkedin");
                                  else if (event.hasThread) setSubModal("email");
                                }}
                                className="relative flex items-start gap-3.5 p-4 bg-[#1A1A28] hover:bg-[#222233] rounded-xl cursor-pointer transition-all hover:translate-x-1"
                              >
                                {/* Timeline dot */}
                                <div
                                  className={`absolute -left-[26px] top-5 w-2.5 h-2.5 rounded-full border-2 ${
                                    event.type === "reply"
                                      ? "border-green-500 bg-green-500/20"
                                      : event.type === "email"
                                      ? "border-violet-500 bg-violet-500/20"
                                      : event.type === "linkedin"
                                      ? "border-sky-500 bg-sky-500/20"
                                      : event.type === "voice"
                                      ? "border-amber-500 bg-amber-500/20"
                                      : "border-teal-500 bg-teal-500/20"
                                  }`}
                                />

                                {/* Icon */}
                                <div
                                  className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${getChannelColor(
                                    event.type
                                  )}`}
                                >
                                  {event.type === "reply" && "✉️"}
                                  {event.type === "email" && "📧"}
                                  {event.type === "linkedin" && "💼"}
                                  {event.type === "voice" && "📞"}
                                  {event.type === "sms" && "💬"}
                                </div>

                                {/* Content */}
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 text-sm text-[#F8F8FC]">
                                    <span className="font-semibold">{event.title}</span>
                                    {event.badge && (
                                      <span
                                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${
                                          event.badge.type === "booked"
                                            ? "bg-green-500/15 text-green-400"
                                            : "bg-blue-500/15 text-blue-400"
                                        }`}
                                      >
                                        {event.badge.label}
                                      </span>
                                    )}
                                  </div>
                                  {event.detail && (
                                    <p className="text-sm text-[#B4B4C4] mt-1 leading-relaxed">
                                      {event.detail}
                                    </p>
                                  )}
                                  <div className="flex items-center gap-3 mt-2">
                                    <span className="text-xs font-mono text-[#6E6E82]">
                                      {event.displayTime}
                                    </span>
                                    {(event.hasTranscript || event.hasThread) && (
                                      <span className="text-xs text-violet-400 hover:underline">
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
                <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-[#1E1E2E]">
                    <div className="flex items-center gap-2 text-[15px] font-semibold text-[#F8F8FC]">
                      🏢 Company Intel
                    </div>
                  </div>
                  <div className="p-5">
                    {/* Company Header */}
                    <div className="flex items-center gap-4 mb-5">
                      <div className="w-13 h-13 bg-[#222233] rounded-xl flex items-center justify-center text-2xl border border-[#2A2A3D] p-3">
                        {lead.company.logoEmoji}
                      </div>
                      <div>
                        <h3 className="font-semibold text-[#F8F8FC]">{lead.company.name}</h3>
                        <a href={`https://${lead.company.domain}`} className="text-sm text-violet-400 hover:underline">
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
                        <div key={stat.label} className="p-4 bg-[#222233] rounded-xl text-center">
                          <div className="text-lg font-bold font-mono text-[#F8F8FC]">{stat.value}</div>
                          <div className="text-[11px] text-[#6E6E82] uppercase mt-1">{stat.label}</div>
                        </div>
                      ))}
                    </div>

                    {/* Recent Intelligence */}
                    <div className="pt-5 border-t border-[#1E1E2E]">
                      <div className="text-xs font-semibold uppercase tracking-widest text-[#6E6E82] mb-3">
                        📰 Recent Intelligence
                      </div>
                      <div className="space-y-2.5">
                        {lead.company.recentIntelligence.map((intel, idx) => (
                          <div key={idx} className="flex items-start gap-2.5 py-2.5 border-b border-[#1E1E2E] last:border-0">
                            <span className="text-sm">{intel.icon}</span>
                            <span className="text-sm text-[#B4B4C4] leading-relaxed">{intel.text}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Quick Actions Card */}
                <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-[#1E1E2E]">
                    <div className="flex items-center gap-2 text-[15px] font-semibold text-[#F8F8FC]">
                      <Zap className="w-4 h-4" />
                      Quick Actions
                    </div>
                  </div>
                  <div className="p-5">
                    <div className="grid grid-cols-2 gap-2.5">
                      <button className="col-span-2 flex items-center justify-center gap-2 px-4 py-3.5 bg-gradient-to-r from-violet-500 to-blue-500 text-white text-sm font-medium rounded-xl hover:opacity-90 hover:-translate-y-0.5 transition-all">
                        <Calendar className="w-5 h-5" />
                        Book Meeting
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-[#222233] text-[#B4B4C4] text-sm font-medium rounded-xl border border-[#2A2A3D] hover:bg-[#1A1A28] hover:text-[#F8F8FC] hover:border-[#3A3A50] transition-all">
                        <Mail className="w-4 h-4" />
                        Send Email
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-[#222233] text-[#B4B4C4] text-sm font-medium rounded-xl border border-[#2A2A3D] hover:bg-[#1A1A28] hover:text-[#F8F8FC] hover:border-[#3A3A50] transition-all">
                        <Briefcase className="w-4 h-4" />
                        LinkedIn DM
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-[#222233] text-[#B4B4C4] text-sm font-medium rounded-xl border border-[#2A2A3D] hover:bg-[#1A1A28] hover:text-[#F8F8FC] hover:border-[#3A3A50] transition-all">
                        <MessageSquare className="w-4 h-4" />
                        Send SMS
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-[#222233] text-[#B4B4C4] text-sm font-medium rounded-xl border border-[#2A2A3D] hover:bg-[#1A1A28] hover:text-[#F8F8FC] hover:border-[#3A3A50] transition-all">
                        <Phone className="w-4 h-4" />
                        AI Call
                      </button>
                      <button className="flex items-center justify-center gap-2 px-4 py-3 bg-red-500/10 text-red-500 text-sm font-medium rounded-xl border border-red-500/30 hover:bg-red-500/20 transition-all">
                        ⏸️ Pause
                      </button>
                    </div>
                  </div>
                </div>

                {/* Notes Card */}
                <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-[#1E1E2E]">
                    <div className="flex items-center gap-2 text-[15px] font-semibold text-[#F8F8FC]">
                      📝 Notes
                    </div>
                  </div>
                  <div className="p-5">
                    <textarea
                      value={noteInput}
                      onChange={(e) => setNoteInput(e.target.value)}
                      placeholder="Add a note about this lead..."
                      rows={3}
                      className="w-full p-4 text-sm bg-[#222233] border border-[#2A2A3D] rounded-xl resize-none text-[#F8F8FC] placeholder-[#6E6E82] outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
                    />
                    <div className="mt-4 space-y-3">
                      {lead.notes.map((note) => (
                        <div
                          key={note.id}
                          className="bg-amber-500/10 border-l-[3px] border-amber-500 rounded-r-xl p-4"
                        >
                          <div className="text-xs text-[#6E6E82] mb-1.5">
                            {note.author} • {note.timestamp}
                          </div>
                          <p className="text-sm text-[#B4B4C4] leading-relaxed">{note.text}</p>
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
