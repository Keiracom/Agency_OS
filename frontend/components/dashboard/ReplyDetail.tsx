/**
 * ReplyDetail.tsx - Full Conversation View with Score Breakdown
 * Phase: Operation Modular Cockpit
 * 
 * Features:
 * - Chat bubble UI for conversation thread
 * - Score breakdown sidebar
 * - Quick actions panel
 * - Activity timeline
 * - Notes section
 * 
 * Ported from: agency-os-html/reply-detail-v2.html
 */

"use client";

import { useState } from "react";
import {
  ArrowLeft,
  Mail,
  MessageSquare,
  Linkedin,
  Calendar,
  Phone,
  User,
  Upload,
  Edit3,
  Zap,
  Send,
  Paperclip,
  Flame,
  Crown,
  BarChart3,
  Clock,
  Plus,
} from "lucide-react";
import type { ChannelType, ALSTier } from "@/lib/api/types";
import type { InboxConversation, IntentType, SentimentType } from "./RepliesInbox";

// ============================================
// Types
// ============================================

interface ScoreFactor {
  id: string;
  icon: string;
  label: string;
  value: number;
}

interface ActivityItem {
  id: string;
  channel: ChannelType | "linkedin-view";
  text: string;
  timestamp: string;
}

interface Note {
  id: string;
  text: string;
  timestamp: string;
}

interface SMSMessage {
  id: string;
  sender: "you" | "them";
  text: string;
  timestamp: string;
  intent?: IntentType;
}

export interface ConversationDetail extends InboxConversation {
  phone?: string;
  linkedinUrl?: string;
  mrr?: string;
  campaign?: string;
  scoreFactors: ScoreFactor[];
  activity: ActivityItem[];
  notes: Note[];
  smsMessages?: SMSMessage[];
}

// ============================================
// Mock Data
// ============================================

const mockDetail: ConversationDetail = {
  id: "1",
  leadId: "lead-1",
  name: "David Park",
  initials: "DP",
  email: "david@momentummedia.com.au",
  company: "Momentum Media",
  title: "CEO",
  channel: "email",
  tier: "hot",
  score: 92,
  intent: "meeting",
  sentiment: "positive",
  preview: "",
  unread: false,
  timestamp: "",
  phone: "+61 412 345 678",
  linkedinUrl: "https://linkedin.com/in/davidpark",
  mrr: "$40K (→ $100K goal)",
  campaign: "Multi-Channel Q1",
  messages: [
    {
      id: "m1",
      sender: "you",
      content: `Hi David,\n\nI noticed Momentum Media has been doing some impressive work in the agency space. I'm curious — are you currently looking to scale your client acquisition, or is that on the backburner for now?\n\nWe've helped agencies like yours book 10-15 qualified meetings per month without adding headcount. Happy to share how if you're interested.\n\nBest,\nDave`,
      timestamp: "Jan 29, 9:00 AM",
      channel: "email",
      subject: "Quick question about Momentum Media",
    },
    {
      id: "m2",
      sender: "them",
      content: `Hi there,\n\nYes, I'd be interested in learning more. Can we schedule a call next week? I'm particularly interested in understanding how your multi-channel approach works and what kind of results you've seen for agencies similar to ours.\n\nWe're currently doing about $40K MRR and looking to scale to $100K by end of year. Would love to see if Agency OS could help accelerate that.\n\nBest,\nDavid`,
      timestamp: "Today, 10:42 AM",
      channel: "email",
      subject: "Re: Quick question about Momentum Media",
    },
  ],
  smsMessages: [
    {
      id: "sms1",
      sender: "you",
      text: "Hi David, it's Dave from Agency OS. Just saw your email — glad you're interested. Want to lock in that meeting?",
      timestamp: "11:15 AM • Delivered",
    },
    {
      id: "sms2",
      sender: "them",
      text: "Absolutely! What times work?",
      timestamp: "11:22 AM",
      intent: "interested",
    },
    {
      id: "sms3",
      sender: "you",
      text: "How about Tuesday 2pm AEST? I'll send you a calendar invite with a Zoom link.",
      timestamp: "11:24 AM • Delivered",
    },
    {
      id: "sms4",
      sender: "them",
      text: "Perfect, that works! 👍",
      timestamp: "11:30 AM",
      intent: "meeting",
    },
  ],
  aiSuggestions: [
    {
      id: "s1",
      label: "✨ Confirm Meeting",
      text: "Perfect, David! Just sent you a calendar invite for Tuesday 2pm AEST. Looking forward to learning more about your $40K → $100K goals and showing you how we can help accelerate that. See you then!",
      icon: "sparkles",
    },
    {
      id: "s2",
      label: "Add Social Proof",
      text: "Great! Calendar invite coming your way. Quick note — we recently helped an agency at similar scale go from $35K to $87K MRR in 6 months. Will share their playbook on the call. Tuesday at 2pm AEST works!",
      icon: "chart",
    },
    {
      id: "s3",
      label: "Pre-qualify",
      text: "Awesome! Before I send the invite — to make our time super valuable, what's your biggest bottleneck right now: lead quality, follow-up consistency, or bandwidth to handle more meetings? That way I can tailor the demo.",
      icon: "target",
    },
  ],
  scoreFactors: [
    { id: "sf1", icon: "👑", label: "CEO-Level Title", value: 25 },
    { id: "sf2", icon: "📅", label: "Meeting Request", value: 20 },
    { id: "sf3", icon: "💰", label: "Budget Revealed ($40K MRR)", value: 15 },
    { id: "sf4", icon: "📈", label: "Growth Intent", value: 12 },
    { id: "sf5", icon: "✉️", label: "Email Opened (3x)", value: 10 },
    { id: "sf6", icon: "💬", label: "SMS Engaged", value: 10 },
  ],
  activity: [
    { id: "a1", channel: "sms", text: "Replied to SMS — confirmed Tuesday call", timestamp: "Today, 11:30 AM" },
    { id: "a2", channel: "email", text: "Replied to email — meeting request", timestamp: "Today, 10:42 AM" },
    { id: "a3", channel: "email", text: "Opened email (3rd time)", timestamp: "Today, 10:38 AM" },
    { id: "a4", channel: "linkedin-view", text: "Viewed your LinkedIn profile", timestamp: "Yesterday, 4:15 PM" },
    { id: "a5", channel: "email", text: "Initial email sent", timestamp: "Jan 29, 9:00 AM" },
  ],
  notes: [
    {
      id: "n1",
      text: "High-priority lead! CEO wants to 2.5x his MRR. Confirmed Tuesday 2pm AEST call via SMS. Prepare case study about similar agency scale-up.",
      timestamp: "Today at 10:45 AM",
    },
    {
      id: "n2",
      text: "Initial outreach sent. Momentum Media doing good work — featured in Top 50 Agencies. Worth pursuing.",
      timestamp: "Jan 29 at 9:15 AM",
    },
  ],
};

// ============================================
// Configuration
// ============================================

const tierScoreConfig: Record<ALSTier, { text: string; bg: string; border: string }> = {
  hot: { text: "text-red-400", bg: "bg-gradient-to-br from-red-500 to-orange-500", border: "border-red-500" },
  warm: { text: "text-amber-400", bg: "bg-gradient-to-br from-amber-500 to-yellow-500", border: "border-amber-500" },
  cool: { text: "text-blue-400", bg: "bg-gradient-to-br from-blue-500 to-cyan-500", border: "border-blue-500" },
  cold: { text: "text-slate-400", bg: "bg-gradient-to-br from-slate-500 to-slate-600", border: "border-slate-500" },
  dead: { text: "text-slate-500", bg: "bg-slate-600", border: "border-slate-600" },
};

const intentConfig: Record<IntentType, { bg: string; text: string }> = {
  meeting: { bg: "bg-green-500/15", text: "text-green-400" },
  interested: { bg: "bg-violet-500/15", text: "text-violet-400" },
  objection: { bg: "bg-red-500/15", text: "text-red-400" },
  later: { bg: "bg-amber-500/15", text: "text-amber-400" },
  question: { bg: "bg-blue-500/15", text: "text-blue-400" },
};

const channelIcons: Record<string, { icon: typeof Mail; bg: string }> = {
  email: { icon: Mail, bg: "bg-violet-500/15" },
  sms: { icon: MessageSquare, bg: "bg-emerald-500/15" },
  linkedin: { icon: Linkedin, bg: "bg-sky-500/15" },
  "linkedin-view": { icon: Linkedin, bg: "bg-sky-500/15" },
  voice: { icon: Phone, bg: "bg-amber-500/15" },
};

// ============================================
// Sub-Components
// ============================================

function ScoreRing({ score, tier }: { score: number; tier: ALSTier }) {
  const config = tierScoreConfig[tier];
  return (
    <div className={`w-[72px] h-[72px] rounded-full border-4 ${config.border} flex flex-col items-center justify-center bg-red-500/8`}>
      <span className={`text-2xl font-extrabold font-mono leading-none ${config.text}`}>{score}</span>
      <span className="text-[9px] text-slate-500 uppercase tracking-wide">Score</span>
    </div>
  );
}

function LeadBadge({ type, children }: { type: "hot" | "ceo" | "meeting"; children: React.ReactNode }) {
  const styles = {
    hot: "bg-red-500/15 text-red-400",
    ceo: "bg-violet-500/15 text-violet-400",
    meeting: "bg-green-500/15 text-green-400",
  };
  return (
    <span className={`px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide flex items-center gap-1.5 ${styles[type]}`}>
      {children}
    </span>
  );
}

function ActivityIcon({ channel }: { channel: string }) {
  const config = channelIcons[channel] ?? channelIcons.email;
  const Icon = config.icon;
  return (
    <div className={`w-7 h-7 rounded-md flex items-center justify-center ${config.bg}`}>
      <Icon className="w-3.5 h-3.5" />
    </div>
  );
}

// ============================================
// Main Component
// ============================================

interface ReplyDetailProps {
  conversation?: ConversationDetail;
  onBack?: () => void;
}

export function ReplyDetail({ conversation = mockDetail, onBack }: ReplyDetailProps) {
  const [replyText, setReplyText] = useState("");
  const config = tierScoreConfig[conversation.tier];

  const handleSuggestionClick = (text: string) => {
    setReplyText(text);
  };

  return (
    <div className="flex flex-col h-full bg-[#05050A]">
      {/* Header */}
      <header className="bg-[#12121D] border-b border-[#1E1E2E] px-6 py-3 flex items-center gap-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-500 hover:bg-[#1A1A28] hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Inbox
        </button>
        <div className="w-px h-6 bg-[#1E1E2E]" />
        <span className="text-sm text-slate-400">Conversation with {conversation.name}</span>
      </header>

      {/* Content */}
      <div className="flex-1 grid grid-cols-[1fr_340px] overflow-hidden">
        {/* Conversation Panel */}
        <div className="flex flex-col overflow-hidden">
          {/* Lead Header */}
          <div className="bg-[#12121D] border-b border-[#1E1E2E] px-8 py-5 flex items-center gap-5">
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center text-white font-bold text-xl ${config.bg}`}>
              {conversation.initials}
            </div>
            <div className="flex-1">
              <h1 className="text-xl font-bold text-white mb-1">{conversation.name}</h1>
              <p className="text-sm text-slate-500">{conversation.title} at {conversation.company} • {conversation.email}</p>
              <div className="flex gap-2 mt-2">
                <LeadBadge type="hot">
                  <Flame className="w-3 h-3" /> Hot
                </LeadBadge>
                <LeadBadge type="ceo">
                  <Crown className="w-3 h-3" /> CEO
                </LeadBadge>
                <LeadBadge type="meeting">
                  <Calendar className="w-3 h-3" /> Meeting Requested
                </LeadBadge>
              </div>
            </div>
            <ScoreRing score={conversation.score} tier={conversation.tier} />
            <div className="flex gap-2.5">
              <button className="flex items-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 rounded-lg text-white text-sm font-semibold transition-colors">
                <Calendar className="w-4 h-4" />
                Schedule Call
              </button>
              <button className="flex items-center gap-2 px-4 py-2.5 bg-[#1A1A28] border border-[#1E1E2E] rounded-lg text-white text-sm font-semibold hover:bg-[#222233] transition-colors">
                <Phone className="w-4 h-4" />
                Call Now
              </button>
            </div>
          </div>

          {/* Thread */}
          <div className="flex-1 overflow-y-auto px-8 py-6">
            {/* Email Messages */}
            {conversation.messages.map((msg, idx) => {
              const isFirst = idx === 0;
              const prevDate = idx > 0 ? conversation.messages[idx - 1].timestamp.split(",")[0] : null;
              const currDate = msg.timestamp.split(",")[0];
              const showDate = isFirst || prevDate !== currDate;

              return (
                <div key={msg.id}>
                  {showDate && (
                    <div className="flex items-center gap-4 py-4 text-xs text-slate-500">
                      <div className="flex-1 h-px bg-[#1E1E2E]" />
                      <span>{currDate}</span>
                      <div className="flex-1 h-px bg-[#1E1E2E]" />
                    </div>
                  )}
                  <div className={`max-w-[720px] bg-[#12121D] border rounded-2xl p-6 mb-5 ${
                    msg.sender === "you"
                      ? "ml-auto bg-violet-500/8 border-violet-500/20"
                      : "border-[#1E1E2E] border-l-[3px] border-l-green-500"
                  }`}>
                    <div className="flex items-center justify-between mb-4 pb-4 border-b border-[#1E1E2E]">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white font-semibold text-sm ${
                          msg.sender === "you" ? "bg-gradient-to-br from-violet-500 to-blue-500" : config.bg
                        }`}>
                          {msg.sender === "you" ? "Y" : conversation.initials}
                        </div>
                        <div>
                          <div className="font-semibold text-sm text-white">
                            {msg.sender === "you" ? "You" : conversation.name}
                          </div>
                          <div className="text-xs text-slate-500">
                            {msg.sender === "you" ? "dave@agencyos.com" : conversation.email}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-slate-500">{msg.timestamp.split(",")[1]?.trim() || msg.timestamp}</div>
                        <div className="text-[11px] text-violet-400 flex items-center gap-1 justify-end mt-1">
                          <Mail className="w-3 h-3" /> Email
                        </div>
                      </div>
                    </div>
                    {msg.subject && (
                      <div className="text-[15px] font-semibold text-white mb-4">{msg.subject}</div>
                    )}
                    <div className="text-sm text-slate-400 leading-relaxed whitespace-pre-line">
                      {msg.content}
                    </div>
                    {msg.sender === "them" && (
                      <div className="inline-flex items-center gap-2 mt-4 px-3 py-1.5 bg-green-500/10 rounded-md text-xs font-medium text-green-400">
                        😊 Positive • <Calendar className="w-3 h-3" /> Meeting Intent Detected
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* SMS Thread */}
            {conversation.smsMessages && conversation.smsMessages.length > 0 && (
              <div className="max-w-[500px] mb-6">
                <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[#1E1E2E]">
                  <div className="w-8 h-8 bg-emerald-500/15 rounded-lg flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-emerald-400" />
                  </div>
                  <span className="text-sm font-semibold text-emerald-400">SMS Conversation</span>
                </div>
                {conversation.smsMessages.map((sms) => (
                  <div
                    key={sms.id}
                    className={`max-w-[85%] p-3 px-4 rounded-2xl mb-2 text-sm leading-relaxed ${
                      sms.sender === "you"
                        ? "ml-auto bg-violet-600 text-white rounded-br-sm"
                        : "bg-[#12121D] border border-[#1E1E2E] text-white rounded-bl-sm"
                    }`}
                  >
                    {sms.text}
                    <div className={`flex items-center gap-2 mt-1.5 text-[11px] ${
                      sms.sender === "you" ? "justify-end text-white/70" : "text-slate-500"
                    }`}>
                      {sms.intent && (
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${intentConfig[sms.intent].bg} ${intentConfig[sms.intent].text}`}>
                          {sms.intent === "meeting" ? "Meeting Request" : "Positive"}
                        </span>
                      )}
                      {sms.timestamp}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* AI Suggestions */}
            {conversation.aiSuggestions.length > 0 && (
              <div className="max-w-[720px] bg-[#12121D] border border-[#1E1E2E] rounded-2xl p-6 mt-6">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-blue-500 rounded-lg flex items-center justify-center">
                    <Zap className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="text-base font-bold text-white">Suggested Responses</div>
                    <div className="text-sm text-slate-500">Click to use • Based on conversation context</div>
                  </div>
                </div>
                <div className="space-y-3">
                  {conversation.aiSuggestions.map((sug) => (
                    <div
                      key={sug.id}
                      onClick={() => handleSuggestionClick(sug.text)}
                      className="group p-4 bg-violet-500/5 border border-violet-500/15 rounded-xl cursor-pointer hover:bg-violet-500/10 hover:border-violet-500/30 hover:-translate-y-0.5 transition-all"
                    >
                      <div className="flex items-center justify-between mb-2.5">
                        <span className="text-[11px] font-bold uppercase tracking-wide text-violet-400 flex items-center gap-1.5">
                          {sug.icon === "chart" && <BarChart3 className="w-3 h-3" />}
                          {sug.label}
                        </span>
                        <button className="px-3 py-1.5 bg-violet-600 rounded-md text-[11px] font-semibold text-white opacity-0 group-hover:opacity-100 transition-opacity">
                          Use This
                        </button>
                      </div>
                      <p className="text-sm text-slate-400 leading-relaxed">{sug.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Composer */}
          <div className="bg-[#12121D] border-t border-[#1E1E2E] px-8 py-5">
            <div className="max-w-[720px]">
              <div className="flex items-center gap-2 mb-3 text-sm">
                <span className="text-slate-500">To:</span>
                <span className="text-white font-medium">{conversation.email}</span>
              </div>
              <textarea
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder="Write your reply..."
                className="w-full p-4 bg-[#0A0A12] border border-[#1E1E2E] rounded-xl text-white text-sm placeholder:text-slate-500 resize-none min-h-[120px] focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20"
              />
              <div className="flex items-center justify-between mt-3">
                <div className="flex gap-2">
                  <button className="flex items-center gap-2 px-3 py-2 bg-[#1A1A28] border border-[#1E1E2E] rounded-md text-xs text-slate-400 hover:bg-[#222233] hover:text-slate-200 transition-colors">
                    <Paperclip className="w-3.5 h-3.5" />
                    Attach
                  </button>
                  <button className="flex items-center gap-2 px-3 py-2 bg-[#1A1A28] border border-[#1E1E2E] rounded-md text-xs text-slate-400 hover:bg-[#222233] hover:text-slate-200 transition-colors">
                    <Calendar className="w-3.5 h-3.5" />
                    Schedule
                  </button>
                  <button className="flex items-center gap-2 px-3 py-2 bg-[#1A1A28] border border-[#1E1E2E] rounded-md text-xs text-slate-400 hover:bg-[#222233] hover:text-slate-200 transition-colors">
                    <Zap className="w-3.5 h-3.5" />
                    AI Write
                  </button>
                </div>
                <button className="flex items-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-500 rounded-lg text-white text-sm font-semibold transition-colors">
                  <Send className="w-4 h-4" />
                  Send Reply
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Score Breakdown & Details */}
        <div className="bg-[#12121D] border-l border-[#1E1E2E] overflow-y-auto p-6 space-y-6">
          {/* Quick Actions */}
          <div className="bg-[#0A0A12] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Zap className="w-3.5 h-3.5" />
              Quick Actions
            </div>
            <div className="space-y-2">
              <button className="w-full flex items-center gap-3 px-3.5 py-3 bg-violet-600 hover:bg-violet-500 rounded-lg text-white text-sm font-medium transition-colors">
                <Calendar className="w-4 h-4 opacity-80" />
                Schedule Call
              </button>
              <button className="w-full flex items-center gap-3 px-3.5 py-3 bg-[#1A1A28] border border-[#1E1E2E] rounded-lg text-white text-sm font-medium hover:bg-[#222233] hover:translate-x-0.5 transition-all">
                <Edit3 className="w-4 h-4 text-slate-400" />
                Add Note
              </button>
              <button className="w-full flex items-center gap-3 px-3.5 py-3 bg-[#1A1A28] border border-[#1E1E2E] rounded-lg text-white text-sm font-medium hover:bg-[#222233] hover:translate-x-0.5 transition-all">
                <Upload className="w-4 h-4 text-slate-400" />
                Send to CRM
              </button>
              <button className="w-full flex items-center gap-3 px-3.5 py-3 bg-[#1A1A28] border border-[#1E1E2E] rounded-lg text-white text-sm font-medium hover:bg-[#222233] hover:translate-x-0.5 transition-all">
                <User className="w-4 h-4 text-slate-400" />
                View Full Profile
              </button>
            </div>
          </div>

          {/* Lead Details */}
          <div className="bg-[#0A0A12] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <User className="w-3.5 h-3.5" />
              Lead Details
            </div>
            <div className="space-y-3">
              {[
                { label: "Company", value: conversation.company },
                { label: "Title", value: conversation.title },
                { label: "Phone", value: conversation.phone },
                { label: "LinkedIn", value: "View Profile →", isLink: true },
                { label: "MRR", value: conversation.mrr },
                { label: "Campaign", value: conversation.campaign },
              ].map((item) => (
                <div key={item.label} className="flex justify-between items-start text-sm">
                  <span className="text-slate-500">{item.label}</span>
                  {item.isLink ? (
                    <a href={conversation.linkedinUrl} className="text-violet-400 font-medium hover:underline">
                      {item.value}
                    </a>
                  ) : (
                    <span className="text-white font-medium text-right">{item.value}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Score Breakdown */}
          <div className="bg-[#0A0A12] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <BarChart3 className="w-3.5 h-3.5" />
              Why {conversation.score} Score
            </div>
            <div className="space-y-2.5">
              {conversation.scoreFactors.map((factor) => (
                <div key={factor.id} className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-md bg-[#1A1A28] flex items-center justify-center text-xs">
                    {factor.icon}
                  </div>
                  <span className="flex-1 text-xs text-slate-400">{factor.label}</span>
                  <span className="text-xs font-semibold font-mono text-green-400">+{factor.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Related Activity */}
          <div className="bg-[#0A0A12] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Clock className="w-3.5 h-3.5" />
              Related Activity
            </div>
            <div className="space-y-3">
              {conversation.activity.map((act) => (
                <div key={act.id} className="flex items-start gap-2.5">
                  <ActivityIcon channel={act.channel} />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-slate-400 leading-relaxed">{act.text}</div>
                    <div className="text-[11px] text-slate-600 mt-0.5">{act.timestamp}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div className="bg-[#0A0A12] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Edit3 className="w-3.5 h-3.5" />
              Notes
            </div>
            <div className="space-y-2.5">
              {conversation.notes.map((note) => (
                <div
                  key={note.id}
                  className="bg-amber-500/8 border-l-[3px] border-l-amber-500 p-3 rounded-r-lg"
                >
                  <div className="text-[10px] text-slate-500 mb-1.5">{note.timestamp}</div>
                  <div className="text-sm text-slate-400 leading-relaxed">{note.text}</div>
                </div>
              ))}
              <button className="w-full flex items-center justify-center gap-2 p-2.5 border border-dashed border-[#2A2A3D] rounded-lg text-xs text-slate-500 hover:bg-[#1A1A28] hover:text-slate-300 hover:border-[#3A3A50] transition-colors">
                <Plus className="w-3.5 h-3.5" />
                Add Note
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ReplyDetail;
