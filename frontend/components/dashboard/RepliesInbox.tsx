/**
 * RepliesInbox.tsx - Two-Pane Inbox Command Center
 * Phase: Operation Modular Cockpit
 * 
 * Features:
 * - Two-pane layout: message list + preview panel
 * - Intent classification badges
 * - Sentiment color borders
 * - AI suggested responses
 * - Reply composer
 * 
 * Ported from: agency-os-html/replies-v2.html
 */

"use client";

import { useState } from "react";
import {
  Search,
  Filter,
  RefreshCw,
  Mail,
  MessageSquare,
  Linkedin,
  Calendar,
  Phone,
  User,
  Archive,
  Paperclip,
  Zap,
  Send,
  Lightbulb,
  BarChart3,
  Target,
} from "lucide-react";
import type { ChannelType, ALSTier } from "@/lib/api/types";
import { ChannelIcon } from "./ChannelIcon";

// ============================================
// Types
// ============================================

export type IntentType = "meeting" | "interested" | "objection" | "later" | "question";
export type SentimentType = "positive" | "negative" | "neutral";

export interface ConversationMessage {
  id: string;
  sender: "you" | "them";
  content: string;
  timestamp: string;
  channel: ChannelType;
  subject?: string;
}

export interface AISuggestion {
  id: string;
  label: string;
  text: string;
  icon?: "sparkles" | "chart" | "target";
}

export interface InboxConversation {
  id: string;
  leadId: string;
  name: string;
  initials: string;
  email: string;
  company: string;
  title: string;
  channel: ChannelType;
  tier: ALSTier;
  score: number;
  intent: IntentType;
  sentiment: SentimentType;
  preview: string;
  unread: boolean;
  timestamp: string;
  messages: ConversationMessage[];
  aiSuggestions: AISuggestion[];
}

// ============================================
// Mock Data
// ============================================

const mockConversations: InboxConversation[] = [
  {
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
    preview: "Yes, I'd be interested in learning more. Can we schedule a call next week? We're currently doing about $40K MRR...",
    unread: true,
    timestamp: "2h ago",
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
    aiSuggestions: [
      {
        id: "s1",
        label: "Sparkles Quick Accept",
        text: "Hi David, great to hear! I'd love to learn more about your $40K → $100K goals. Tuesday at 2pm AEST work for a 30-min call? I'll send a calendar invite.",
        icon: "sparkles",
      },
      {
        id: "s2",
        label: "Show Results",
        text: "Hi David! Love the ambition. We recently helped an agency go from $35K to $85K MRR in 6 months. Happy to share their playbook. Which day works — Tuesday or Wednesday?",
        icon: "chart",
      },
      {
        id: "s3",
        label: "Discovery First",
        text: "Thanks David! Before we chat, quick question — what's your current biggest challenge: lead quality, follow-up consistency, or capacity to take calls? Want to make our time super relevant.",
        icon: "target",
      },
    ],
  },
  {
    id: "2",
    leadId: "lead-2",
    name: "Anna Smith",
    initials: "AS",
    email: "anna@digitalfirst.io",
    company: "Digital First",
    title: "Marketing Director",
    channel: "email",
    tier: "warm",
    score: 78,
    intent: "interested",
    sentiment: "positive",
    preview: "This looks relevant. Send me more information about pricing and how this works for agencies our size.",
    unread: true,
    timestamp: "5h ago",
    messages: [],
    aiSuggestions: [],
  },
  {
    id: "3",
    leadId: "lead-3",
    name: "Mike Ross",
    initials: "MR",
    email: "mike@velocitygrowth.com",
    company: "Velocity Growth",
    title: "Head of Sales",
    channel: "sms",
    tier: "hot",
    score: 85,
    intent: "meeting",
    sentiment: "positive",
    preview: "Sure, how about Thursday? I've got 30 mins around 2pm if that works for you.",
    unread: true,
    timestamp: "6h ago",
    messages: [],
    aiSuggestions: [],
  },
  {
    id: "4",
    leadId: "lead-4",
    name: "Lisa Wong",
    initials: "LW",
    email: "lisa@pixelperfect.co",
    company: "Pixel Perfect",
    title: "Founder",
    channel: "linkedin",
    tier: "warm",
    score: 74,
    intent: "question",
    sentiment: "positive",
    preview: "Thanks for reaching out! Your approach is interesting. How does the AI calling work exactly?",
    unread: true,
    timestamp: "1d ago",
    messages: [],
    aiSuggestions: [],
  },
  {
    id: "5",
    leadId: "lead-5",
    name: "Chris Lee",
    initials: "CL",
    email: "chris@visionarystudios.com",
    company: "Visionary Studios",
    title: "Operations",
    channel: "email",
    tier: "cool",
    score: 42,
    intent: "objection",
    sentiment: "negative",
    preview: "Not interested at this time. Please remove me from your list.",
    unread: false,
    timestamp: "1d ago",
    messages: [],
    aiSuggestions: [],
  },
  {
    id: "6",
    leadId: "lead-6",
    name: "Rachel Green",
    initials: "RG",
    email: "rachel@marketingplus.com",
    company: "Marketing Plus",
    title: "Director",
    channel: "email",
    tier: "cool",
    score: 56,
    intent: "later",
    sentiment: "neutral",
    preview: "Thanks for reaching out. We're evaluating solutions for Q2. Can you follow up in March?",
    unread: false,
    timestamp: "2d ago",
    messages: [],
    aiSuggestions: [],
  },
  {
    id: "7",
    leadId: "lead-7",
    name: "Tom Brown",
    initials: "TB",
    email: "tom@scaleagency.com",
    company: "Scale Agency",
    title: "Founder",
    channel: "sms",
    tier: "warm",
    score: 68,
    intent: "interested",
    sentiment: "positive",
    preview: "Hey! Yeah we've been looking for something like this. What's the typical cost?",
    unread: true,
    timestamp: "3d ago",
    messages: [],
    aiSuggestions: [],
  },
];

// ============================================
// Configuration
// ============================================

const intentConfig: Record<IntentType, { bg: string; text: string; label: string }> = {
  meeting: { bg: "bg-amber/15", text: "text-amber", label: "Meeting Request" },
  interested: { bg: "bg-amber/15", text: "text-amber", label: "Interested" },
  objection: { bg: "bg-amber-glow", text: "text-amber", label: "Objection" },
  later: { bg: "bg-amber-500/15", text: "text-amber-400", label: "Not Now" },
  question: { bg: "bg-bg-elevated/15", text: "text-text-secondary", label: "Question" },
};

const sentimentConfig: Record<SentimentType, { color: string; label: string; border: string }> = {
  positive: { color: "text-amber", label: "Positive", border: "border-l-amber" },
  negative: { color: "text-amber", label: "Negative", border: "border-l-amber" },
  neutral: { color: "text-text-secondary", label: "Neutral", border: "border-l-slate-500" },
};

const tierScoreConfig: Record<ALSTier, { text: string; bg: string }> = {
  hot: { text: "text-amber", bg: "bg-gradient-to-br from-amber to-amber-light" },
  warm: { text: "text-amber-400", bg: "bg-gradient-to-br from-amber-500 to-yellow-500" },
  cool: { text: "text-text-secondary", bg: "bg-gradient-to-br from-amber to-amber" },
  cold: { text: "text-text-secondary", bg: "bg-gradient-to-br from-slate-500 to-slate-600" },
  dead: { text: "text-text-muted", bg: "bg-bg-elevated" },
};

// ============================================
// Sub-Components
// ============================================

function IntentBadge({ intent }: { intent: IntentType }) {
  const config = intentConfig[intent];
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
}

function SentimentBadge({ sentiment }: { sentiment: SentimentType }) {
  const config = sentimentConfig[sentiment];
  return (
    <span className={`flex items-center gap-1 text-xs ${config.color}`}>
      <span className="capitalize">{config.label}</span>
    </span>
  );
}

function ScoreDisplay({ score, tier }: { score: number; tier: ALSTier }) {
  const config = tierScoreConfig[tier];
  return (
    <div className="text-right">
      <div className={`text-xl font-extrabold font-mono ${config.text}`}>{score}</div>
      <div className="text-[9px] text-text-muted uppercase tracking-wide">Score</div>
    </div>
  );
}

function MessageAvatar({ initials, tier }: { initials: string; tier: ALSTier }) {
  const config = tierScoreConfig[tier];
  return (
    <div className={`w-11 h-11 rounded-lg flex items-center justify-center text-text-primary font-semibold text-sm ${config.bg}`}>
      {initials}
    </div>
  );
}

// ============================================
// Main Component
// ============================================

interface RepliesInboxProps {
  /** Callback when a conversation is selected for detail view */
  onViewDetail?: (conversation: InboxConversation) => void;
}

export function RepliesInbox({ onViewDetail }: RepliesInboxProps) {
  const [selectedId, setSelectedId] = useState<string>(mockConversations[0]?.id ?? "");
  const [filter, setFilter] = useState<"all" | "unread" | "positive" | "action">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [replyText, setReplyText] = useState("");

  const selected = mockConversations.find((c) => c.id === selectedId) ?? mockConversations[0];

  // Filter conversations
  const filtered = mockConversations.filter((c) => {
    if (filter === "unread" && !c.unread) return false;
    if (filter === "positive" && c.sentiment !== "positive") return false;
    if (filter === "action" && !["meeting", "interested"].includes(c.intent)) return false;
    if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const unreadCount = mockConversations.filter((c) => c.unread).length;
  const positiveCount = mockConversations.filter((c) => c.sentiment === "positive").length;

  const handleSuggestionClick = (suggestion: AISuggestion) => {
    setReplyText(suggestion.text);
  };

  return (
    <div className="flex flex-col h-full bg-bg-void">
      {/* Header */}
      <header className="bg-bg-base border-b border-default px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-text-primary flex items-center gap-3">
            <Mail className="w-5 h-5 text-amber" />
            Inbox Command Center
            <span className="bg-amber/15 text-amber px-2.5 py-1 rounded-full text-xs font-semibold">
              {unreadCount} unread
            </span>
          </h1>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2.5 bg-bg-elevated border border-default rounded-lg text-text-secondary text-sm font-medium hover:bg-bg-elevated hover:text-text-secondary transition-colors">
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button className="flex items-center gap-2 px-4 py-2.5 bg-bg-elevated border border-default rounded-lg text-text-secondary text-sm font-medium hover:bg-bg-elevated hover:text-text-secondary transition-colors">
            <RefreshCw className="w-4 h-4" />
            Sync
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 grid grid-cols-[420px_1fr] overflow-hidden">
        {/* Inbox List */}
        <div className="bg-bg-base border-r border-default flex flex-col overflow-hidden">
          {/* Filters */}
          <div className="p-4 border-b border-default">
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-bg-void border border-default rounded-lg text-text-primary text-sm placeholder:text-text-muted focus:outline-none focus:border-amber focus:ring-2 focus:ring-amber/20"
              />
            </div>
            <div className="flex gap-2">
              {[
                { key: "all", label: "All", count: mockConversations.length },
                { key: "unread", label: "Unread", count: unreadCount },
                { key: "positive", label: "Positive", count: positiveCount },
                { key: "action", label: "Action" },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key as typeof filter)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    filter === tab.key
                      ? "bg-amber/15 text-amber"
                      : "text-text-muted hover:bg-bg-elevated hover:text-text-secondary"
                  }`}
                >
                  {tab.label}
                  {tab.count !== undefined && (
                    <span className="ml-1.5 opacity-70">{tab.count}</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Message List */}
          <div className="flex-1 overflow-y-auto">
            {filtered.map((conv) => {
              const sentimentBorder = sentimentConfig[conv.sentiment].border;
              const isActive = conv.id === selectedId;
              
              return (
                <div
                  key={conv.id}
                  onClick={() => setSelectedId(conv.id)}
                  className={`p-4 border-b border-default border-l-3 cursor-pointer transition-colors ${sentimentBorder} ${
                    isActive
                      ? "bg-amber/8 border-l-amber"
                      : conv.unread
                      ? "bg-amber/4 hover:bg-bg-elevated"
                      : "hover:bg-bg-elevated"
                  }`}
                >
                  {/* Header */}
                  <div className="flex items-start gap-3 mb-2.5">
                    <MessageAvatar initials={conv.initials} tier={conv.tier} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="font-semibold text-sm text-text-primary flex items-center gap-2">
                          {conv.name}
                          {conv.unread && (
                            <span className="w-2 h-2 rounded-full bg-amber" />
                          )}
                        </span>
                        <ScoreDisplay score={conv.score} tier={conv.tier} />
                      </div>
                      <div className="text-xs text-text-muted">
                        {conv.company} • {conv.title}
                      </div>
                    </div>
                  </div>

                  {/* Preview */}
                  <p className={`text-sm leading-relaxed mb-2.5 line-clamp-2 ${
                    conv.unread ? "text-text-primary" : "text-text-secondary"
                  }`}>
                    {conv.preview}
                  </p>

                  {/* Footer */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="flex items-center gap-1 px-2 py-0.5 bg-bg-elevated rounded text-[11px] text-text-secondary">
                      <ChannelIcon channel={conv.channel} size="sm" bare />
                      <span className="capitalize">{conv.channel}</span>
                    </div>
                    <IntentBadge intent={conv.intent} />
                    <SentimentBadge sentiment={conv.sentiment} />
                    <span className="text-xs text-text-muted ml-auto">{conv.timestamp}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Preview Panel */}
        {selected && (
          <div className="flex flex-col overflow-hidden bg-bg-void">
            {/* Preview Header */}
            <div className="bg-bg-base border-b border-default px-6 py-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-13 h-13 rounded-xl flex items-center justify-center text-text-primary font-bold text-lg ${tierScoreConfig[selected.tier].bg}`}>
                  {selected.initials}
                </div>
                <div>
                  <h2 className="text-lg font-bold text-text-primary mb-1">{selected.name}</h2>
                  <p className="text-sm text-text-muted">
                    {selected.title} at {selected.company} • {selected.email}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => onViewDetail?.(selected)}
                  className="flex items-center gap-2 px-4 py-2.5 bg-amber hover:bg-amber rounded-lg text-text-primary text-sm font-semibold transition-colors"
                >
                  <Calendar className="w-4 h-4" />
                  Schedule Meeting
                </button>
                <button className="flex items-center gap-2 px-4 py-2.5 bg-bg-elevated border border-default rounded-lg text-text-primary text-sm font-semibold hover:bg-bg-elevated transition-colors">
                  <Phone className="w-4 h-4" />
                  Call
                </button>
                <button className="w-10 h-10 flex items-center justify-center bg-bg-elevated border border-default rounded-lg text-text-secondary hover:bg-bg-elevated hover:text-text-primary transition-colors">
                  <User className="w-4 h-4" />
                </button>
                <button className="w-10 h-10 flex items-center justify-center bg-bg-elevated border border-default rounded-lg text-text-secondary hover:bg-bg-elevated hover:text-text-primary transition-colors">
                  <Archive className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Thread Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-[720px]">
                {/* Messages */}
                {selected.messages.map((msg, idx) => {
                  const isFirst = idx === 0 || selected.messages[idx - 1].timestamp.split(",")[0] !== msg.timestamp.split(",")[0];
                  return (
                    <div key={msg.id}>
                      {isFirst && (
                        <div className="text-center text-xs text-text-muted py-4">
                          {msg.timestamp.split(",")[0]}
                        </div>
                      )}
                      <div className={`bg-bg-base border rounded-xl p-5 mb-4 ${
                        msg.sender === "you"
                          ? "bg-amber/8 border-amber/20"
                          : "border-default border-l-3 border-l-amber"
                      }`}>
                        <div className="flex items-center justify-between mb-3 pb-3 border-b border-default">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-text-primary font-semibold text-xs ${
                              msg.sender === "you" ? "bg-gradient-to-br from-amber to-amber-light" : tierScoreConfig[selected.tier].bg
                            }`}>
                              {msg.sender === "you" ? "Y" : selected.initials}
                            </div>
                            <span className="font-semibold text-sm text-text-primary">
                              {msg.sender === "you" ? "You" : selected.name}
                            </span>
                          </div>
                          <span className="text-xs text-text-muted">{msg.timestamp}</span>
                        </div>
                        {msg.subject && (
                          <div className="text-sm font-semibold text-text-primary mb-4">
                            {msg.subject}
                          </div>
                        )}
                        <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
                          {msg.content}
                        </div>
                        {msg.sender === "them" && (
                          <div className="inline-flex items-center gap-2 mt-4 px-3 py-1.5 bg-amber/10 rounded-md text-xs font-medium text-amber">
                            Positive sentiment • Meeting intent detected
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* AI Suggestions */}
                {selected.aiSuggestions.length > 0 && (
                  <div className="bg-bg-base border border-default rounded-xl p-5 mt-5">
                    <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-amber">
                      <Lightbulb className="w-4 h-4" />
                      Suggested Responses
                    </div>
                    <div className="space-y-3">
                      {selected.aiSuggestions.map((sug) => (
                        <div
                          key={sug.id}
                          onClick={() => handleSuggestionClick(sug)}
                          className="p-4 bg-amber/5 border border-amber/15 rounded-lg cursor-pointer hover:bg-amber/10 hover:border-amber/30 hover:-translate-y-0.5 transition-all"
                        >
                          <div className="flex items-center gap-2 mb-2 text-[10px] font-semibold uppercase tracking-wide text-amber">
                            {sug.icon === "chart" && <BarChart3 className="w-3 h-3" />}
                            {sug.icon === "target" && <Target className="w-3 h-3" />}
                            {sug.label}
                          </div>
                          <p className="text-sm text-text-secondary leading-relaxed">
                            {sug.text}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Reply Composer */}
            <div className="bg-bg-base border-t border-default px-6 py-5">
              <div className="max-w-[720px]">
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Write your reply..."
                  className="w-full p-4 bg-bg-void border border-default rounded-xl text-text-primary text-sm placeholder:text-text-muted resize-none min-h-[100px] focus:outline-none focus:border-amber focus:ring-2 focus:ring-amber/20"
                />
                <div className="flex items-center justify-between mt-3">
                  <div className="flex gap-2">
                    <button className="flex items-center gap-2 px-3 py-2 bg-bg-elevated border border-default rounded-md text-xs text-text-secondary hover:bg-bg-elevated hover:text-text-secondary transition-colors">
                      <Paperclip className="w-3.5 h-3.5" />
                      Attach
                    </button>
                    <button className="flex items-center gap-2 px-3 py-2 bg-bg-elevated border border-default rounded-md text-xs text-text-secondary hover:bg-bg-elevated hover:text-text-secondary transition-colors">
                      <Calendar className="w-3.5 h-3.5" />
                      Schedule
                    </button>
                    <button className="flex items-center gap-2 px-3 py-2 bg-bg-elevated border border-default rounded-md text-xs text-text-secondary hover:bg-bg-elevated hover:text-text-secondary transition-colors">
                      <Zap className="w-3.5 h-3.5" />
                      AI Write
                    </button>
                  </div>
                  <button className="flex items-center gap-2 px-5 py-2.5 bg-amber hover:bg-amber rounded-lg text-text-primary text-sm font-semibold transition-colors">
                    <Send className="w-4 h-4" />
                    Send Reply
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default RepliesInbox;
