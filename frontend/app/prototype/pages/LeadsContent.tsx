/**
 * LeadsContent.tsx - Leads Page Content (Bloomberg Dark Mode)
 * Ported from leads-v2.html
 * 
 * Features:
 * - "Why Hot?" badges with tier colors
 * - Tier filter cards (Hot/Warm/Cool/Cold counts)
 * - Lead search input
 * - Channel touch icons with active states
 * - Sortable columns
 * - Bloomberg dark mode styling (#0A0A12 base, #7C3AED accent)
 * - Glassmorphic card styling
 */

"use client";

import { useState, useMemo } from "react";
import {
  Search,
  Filter,
  Download,
  Upload,
  Plus,
  Flame,
  Zap,
  Moon,
  ChevronUp,
  ChevronDown,
  Mail,
  Phone,
  MessageSquare,
  Linkedin,
  ArrowUpRight,
  TrendingUp,
  Sparkles,
  DollarSign,
  UserPlus,
  Link,
} from "lucide-react";

// ============================================
// TypeScript Interfaces
// ============================================

export type LeadTier = "hot" | "warm" | "cool" | "cold";

export type WhyHotReason = 
  | "ceo" 
  | "founder" 
  | "active" 
  | "new_role" 
  | "hiring" 
  | "buyer"
  | "engaged";

export type ChannelType = "email" | "linkedin" | "sms" | "voice" | "mail";

export interface ChannelTouch {
  channel: ChannelType;
  isActive: boolean;
  tooltip?: string;
}

export interface LeadData {
  id: string;
  firstName: string;
  lastName: string;
  initials: string;
  title: string;
  company: string;
  email: string;
  score: number;
  tier: LeadTier;
  whyHot: WhyHotReason[];
  channels: ChannelTouch[];
  lastActivity: string;
  lastActivityRecent: boolean;
}

export interface TierStats {
  hot: number;
  warm: number;
  cool: number;
  cold: number;
  promoted: number;
}

type SortField = "name" | "company" | "score" | "lastActivity";
type SortDirection = "asc" | "desc";

interface LeadsContentProps {
  campaignId?: string | null;
}

// ============================================
// Mock Data (matches leads-v2.html)
// ============================================

const mockLeads: LeadData[] = [
  {
    id: "1",
    firstName: "Sarah",
    lastName: "Chen",
    initials: "SC",
    title: "Marketing Director",
    company: "Bloom Digital",
    email: "sarah@bloomdigital.com.au",
    score: 94,
    tier: "hot",
    whyHot: ["active", "buyer"],
    channels: [
      { channel: "email", isActive: true, tooltip: "5 opens today" },
      { channel: "linkedin", isActive: true, tooltip: "Connected" },
      { channel: "voice", isActive: false, tooltip: "Voice AI" },
    ],
    lastActivity: "2 minutes ago",
    lastActivityRecent: true,
  },
  {
    id: "2",
    firstName: "Michael",
    lastName: "Jones",
    initials: "MJ",
    title: "CEO",
    company: "Growth Labs",
    email: "michael@growthlabs.com.au",
    score: 91,
    tier: "hot",
    whyHot: ["ceo", "hiring"],
    channels: [
      { channel: "email", isActive: true, tooltip: "3 opens" },
      { channel: "linkedin", isActive: true },
      { channel: "sms", isActive: false },
    ],
    lastActivity: "15 minutes ago",
    lastActivityRecent: true,
  },
  {
    id: "3",
    firstName: "David",
    lastName: "Park",
    initials: "DP",
    title: "Founder & CEO",
    company: "Momentum Media",
    email: "david@momentummedia.co",
    score: 88,
    tier: "hot",
    whyHot: ["founder", "new_role", "active"],
    channels: [
      { channel: "email", isActive: false },
      { channel: "linkedin", isActive: true, tooltip: "Replied" },
      { channel: "voice", isActive: true, tooltip: "Booked" },
    ],
    lastActivity: "1 hour ago",
    lastActivityRecent: true,
  },
  {
    id: "4",
    firstName: "Lisa",
    lastName: "Wong",
    initials: "LW",
    title: "Founder",
    company: "Pixel Perfect",
    email: "lisa@pixelperfect.com.au",
    score: 82,
    tier: "warm",
    whyHot: ["founder"],
    channels: [
      { channel: "email", isActive: true, tooltip: "2 opens" },
      { channel: "linkedin", isActive: false },
    ],
    lastActivity: "3 hours ago",
    lastActivityRecent: false,
  },
  {
    id: "5",
    firstName: "James",
    lastName: "Cooper",
    initials: "JC",
    title: "Managing Director",
    company: "Creative Co",
    email: "james@creativeco.com.au",
    score: 76,
    tier: "warm",
    whyHot: ["ceo", "buyer"],
    channels: [
      { channel: "email", isActive: false },
      { channel: "sms", isActive: true, tooltip: "Replied" },
    ],
    lastActivity: "1 day ago",
    lastActivityRecent: false,
  },
  {
    id: "6",
    firstName: "Emma",
    lastName: "Wilson",
    initials: "EW",
    title: "Head of Marketing",
    company: "Brand Forward",
    email: "emma@brandforward.com.au",
    score: 71,
    tier: "warm",
    whyHot: ["active"],
    channels: [
      { channel: "email", isActive: true },
      { channel: "linkedin", isActive: false },
      { channel: "sms", isActive: false },
    ],
    lastActivity: "2 days ago",
    lastActivityRecent: false,
  },
  {
    id: "7",
    firstName: "Tom",
    lastName: "Brown",
    initials: "TB",
    title: "Director",
    company: "Scale Agency",
    email: "tom@scaleagency.com.au",
    score: 58,
    tier: "cool",
    whyHot: [],
    channels: [{ channel: "email", isActive: false }],
    lastActivity: "5 days ago",
    lastActivityRecent: false,
  },
  {
    id: "8",
    firstName: "Sophie",
    lastName: "Martinez",
    initials: "SM",
    title: "Marketing Manager",
    company: "Digital Edge",
    email: "sophie@digitaledge.com.au",
    score: 45,
    tier: "cool",
    whyHot: [],
    channels: [
      { channel: "email", isActive: false },
      { channel: "linkedin", isActive: false },
    ],
    lastActivity: "1 week ago",
    lastActivityRecent: false,
  },
];

const mockStats: TierStats = {
  hot: 127,
  warm: 384,
  cool: 736,
  cold: 0,
  promoted: 23,
};

// ============================================
// Why Hot Badge Configuration
// ============================================

const whyHotConfig: Record<
  WhyHotReason,
  { label: string; icon: React.ReactNode; className: string }
> = {
  ceo: {
    label: "CEO",
    icon: <Sparkles className="w-3 h-3" />,
    className: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  },
  founder: {
    label: "Founder",
    icon: <Zap className="w-3 h-3" />,
    className: "bg-pink-500/15 text-pink-400 border-pink-500/30",
  },
  active: {
    label: "Active",
    icon: <TrendingUp className="w-3 h-3" />,
    className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  },
  new_role: {
    label: "New Role",
    icon: <UserPlus className="w-3 h-3" />,
    className: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  },
  hiring: {
    label: "Hiring",
    icon: <TrendingUp className="w-3 h-3" />,
    className: "bg-teal-500/15 text-teal-400 border-teal-500/30",
  },
  buyer: {
    label: "Buyer Signal",
    icon: <DollarSign className="w-3 h-3" />,
    className: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  },
  engaged: {
    label: "Engaged",
    icon: <Link className="w-3 h-3" />,
    className: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  },
};

// ============================================
// Tier Configuration
// ============================================

const tierConfig: Record<
  LeadTier,
  { label: string; bgClass: string; textClass: string; borderClass: string; avatarGradient: string }
> = {
  hot: {
    label: "HOT",
    bgClass: "bg-red-500/10",
    textClass: "text-red-400",
    borderClass: "border-red-500/30",
    avatarGradient: "from-red-500 to-orange-500",
  },
  warm: {
    label: "WARM",
    bgClass: "bg-amber-500/10",
    textClass: "text-amber-400",
    borderClass: "border-amber-500/30",
    avatarGradient: "from-amber-500 to-yellow-400",
  },
  cool: {
    label: "COOL",
    bgClass: "bg-blue-500/10",
    textClass: "text-blue-400",
    borderClass: "border-blue-500/30",
    avatarGradient: "from-blue-500 to-blue-400",
  },
  cold: {
    label: "COLD",
    bgClass: "bg-slate-500/10",
    textClass: "text-slate-400",
    borderClass: "border-slate-500/30",
    avatarGradient: "from-slate-500 to-slate-400",
  },
};

// ============================================
// Channel Icon Component
// ============================================

function ChannelIcon({
  channel,
  isActive,
  tooltip,
}: {
  channel: ChannelType;
  isActive: boolean;
  tooltip?: string;
}) {
  const channelStyles: Record<ChannelType, { bg: string; icon: React.ReactNode }> = {
    email: {
      bg: "bg-violet-500/15",
      icon: <Mail className="w-3.5 h-3.5 text-violet-400" />,
    },
    linkedin: {
      bg: "bg-sky-600/15",
      icon: <Linkedin className="w-3.5 h-3.5 text-sky-400" />,
    },
    sms: {
      bg: "bg-teal-500/15",
      icon: <MessageSquare className="w-3.5 h-3.5 text-teal-400" />,
    },
    voice: {
      bg: "bg-amber-500/15",
      icon: <Phone className="w-3.5 h-3.5 text-amber-400" />,
    },
    mail: {
      bg: "bg-pink-500/15",
      icon: <Mail className="w-3.5 h-3.5 text-pink-400" />,
    },
  };

  const style = channelStyles[channel];

  return (
    <div
      className={`relative w-7 h-7 rounded-md flex items-center justify-center ${style.bg}`}
      title={tooltip}
    >
      {style.icon}
      {isActive && (
        <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-emerald-500 rounded-full border-2 border-[#0A0A12]" />
      )}
    </div>
  );
}

// ============================================
// Why Hot Badges Component
// ============================================

function WhyHotBadges({ reasons }: { reasons: WhyHotReason[] }) {
  if (reasons.length === 0) {
    return (
      <span className="text-xs text-slate-500 bg-slate-800/50 px-2 py-1 rounded">
        Good fit
      </span>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {reasons.map((reason) => {
        const config = whyHotConfig[reason];
        return (
          <span
            key={reason}
            className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded border ${config.className}`}
          >
            {config.icon}
            {config.label}
          </span>
        );
      })}
    </div>
  );
}

// ============================================
// Stat Card Component
// ============================================

function StatCard({
  icon,
  value,
  label,
  iconBg,
}: {
  icon: React.ReactNode;
  value: number | string;
  label: string;
  iconBg: string;
}) {
  return (
    <div className="bg-slate-900/40 backdrop-blur-md border border-white/10 rounded-xl p-4 flex items-center gap-4 shadow-lg shadow-black/20">
      <div
        className={`w-11 h-11 rounded-xl flex items-center justify-center ${iconBg}`}
      >
        {icon}
      </div>
      <div className="flex-1">
        <div className="text-2xl font-bold font-mono text-white">{value}</div>
        <div className="text-xs text-slate-400">{label}</div>
      </div>
    </div>
  );
}

// ============================================
// Sortable Header Component
// ============================================

function SortableHeader({
  label,
  field,
  currentSort,
  currentDirection,
  onSort,
}: {
  label: string;
  field: SortField;
  currentSort: SortField;
  currentDirection: SortDirection;
  onSort: (field: SortField) => void;
}) {
  const isActive = currentSort === field;

  return (
    <th
      className="text-left p-4 font-medium cursor-pointer hover:bg-white/5 transition-colors"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        <span>{label}</span>
        <div className="flex flex-col -space-y-1">
          <ChevronUp
            className={`w-3 h-3 ${
              isActive && currentDirection === "asc"
                ? "text-violet-400"
                : "text-slate-600"
            }`}
          />
          <ChevronDown
            className={`w-3 h-3 ${
              isActive && currentDirection === "desc"
                ? "text-violet-400"
                : "text-slate-600"
            }`}
          />
        </div>
      </div>
    </th>
  );
}

// ============================================
// Main LeadsContent Component
// ============================================

export function LeadsContent({ campaignId }: LeadsContentProps) {
  const [selectedTier, setSelectedTier] = useState<LeadTier | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selectedLeads, setSelectedLeads] = useState<Set<string>>(new Set());

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  // Filter and sort leads
  const filteredLeads = useMemo(() => {
    let result = [...mockLeads];

    // Filter by tier
    if (selectedTier) {
      result = result.filter((lead) => lead.tier === selectedTier);
    }

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (lead) =>
          lead.firstName.toLowerCase().includes(query) ||
          lead.lastName.toLowerCase().includes(query) ||
          lead.company.toLowerCase().includes(query) ||
          lead.email.toLowerCase().includes(query)
      );
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case "name":
          comparison = `${a.firstName} ${a.lastName}`.localeCompare(
            `${b.firstName} ${b.lastName}`
          );
          break;
        case "company":
          comparison = a.company.localeCompare(b.company);
          break;
        case "score":
          comparison = a.score - b.score;
          break;
        case "lastActivity":
          // Simple comparison - in production use proper date parsing
          comparison = a.lastActivityRecent === b.lastActivityRecent ? 0 : a.lastActivityRecent ? -1 : 1;
          break;
      }
      return sortDirection === "asc" ? comparison : -comparison;
    });

    return result;
  }, [selectedTier, searchQuery, sortField, sortDirection]);

  // Handle checkbox
  const toggleLead = (id: string) => {
    setSelectedLeads((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedLeads.size === filteredLeads.length) {
      setSelectedLeads(new Set());
    } else {
      setSelectedLeads(new Set(filteredLeads.map((l) => l.id)));
    }
  };

  return (
    <div className="min-h-screen bg-[#05050A] p-6">
      {/* Header */}
      <div className="bg-slate-900/60 backdrop-blur-xl border border-white/10 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              Leads
              <span className="text-sm font-semibold font-mono px-2.5 py-1 bg-violet-500/15 text-violet-400 rounded-md">
                1,247
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Track and engage your leads across all channels
            </p>
          </div>
          <div className="flex gap-3">
            <button className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-300 bg-slate-800/60 border border-slate-700 rounded-lg hover:bg-slate-800 hover:border-slate-600 transition-all">
              <Download className="w-4 h-4" />
              Export
            </button>
            <button className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-300 bg-slate-800/60 border border-slate-700 rounded-lg hover:bg-slate-800 hover:border-slate-600 transition-all">
              <Upload className="w-4 h-4" />
              Import
            </button>
            <button className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-blue-600 rounded-lg hover:opacity-90 hover:-translate-y-0.5 transition-all shadow-lg shadow-violet-500/20">
              <Plus className="w-4 h-4" />
              Add Lead
            </button>
          </div>
        </div>

        {/* Filters Row */}
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="flex-1 max-w-md relative">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, company, or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-[#0A0A12] border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
            />
          </div>

          {/* Filter Button */}
          <button className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-300 bg-slate-800/60 border border-slate-700 rounded-lg hover:bg-slate-800 hover:border-slate-600 transition-all">
            <Filter className="w-4 h-4" />
            Filters
          </button>

          {/* Tier Tabs */}
          <div className="flex bg-[#0A0A12] border border-slate-700 rounded-lg p-1 gap-1">
            <button
              onClick={() => setSelectedTier(null)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
                selectedTier === null
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:text-slate-300 hover:bg-slate-800/50"
              }`}
            >
              All
              <span className="text-xs font-mono bg-slate-700/50 px-1.5 py-0.5 rounded">
                1,247
              </span>
            </button>
            <button
              onClick={() => setSelectedTier("hot")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
                selectedTier === "hot"
                  ? "bg-slate-800 text-red-400"
                  : "text-slate-400 hover:text-slate-300 hover:bg-slate-800/50"
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              Hot
              <span className="text-xs font-mono bg-slate-700/50 px-1.5 py-0.5 rounded">
                {mockStats.hot}
              </span>
            </button>
            <button
              onClick={() => setSelectedTier("warm")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
                selectedTier === "warm"
                  ? "bg-slate-800 text-amber-400"
                  : "text-slate-400 hover:text-slate-300 hover:bg-slate-800/50"
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              Warm
              <span className="text-xs font-mono bg-slate-700/50 px-1.5 py-0.5 rounded">
                {mockStats.warm}
              </span>
            </button>
            <button
              onClick={() => setSelectedTier("cool")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
                selectedTier === "cool"
                  ? "bg-slate-800 text-blue-400"
                  : "text-slate-400 hover:text-slate-300 hover:bg-slate-800/50"
              }`}
            >
              <Moon className="w-3.5 h-3.5" />
              Cool
              <span className="text-xs font-mono bg-slate-700/50 px-1.5 py-0.5 rounded">
                {mockStats.cool}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={<Flame className="w-5 h-5 text-red-400" />}
          value={mockStats.hot}
          label="Hot Leads (85-100)"
          iconBg="bg-red-500/10"
        />
        <StatCard
          icon={<Zap className="w-5 h-5 text-amber-400" />}
          value={mockStats.warm}
          label="Warm Leads (60-84)"
          iconBg="bg-amber-500/10"
        />
        <StatCard
          icon={<Moon className="w-5 h-5 text-blue-400" />}
          value={mockStats.cool}
          label="Cool Leads (20-59)"
          iconBg="bg-blue-500/10"
        />
        <StatCard
          icon={<TrendingUp className="w-5 h-5 text-violet-400" />}
          value={`+${mockStats.promoted}`}
          label="Promoted to Hot (7d)"
          iconBg="bg-violet-500/15"
        />
      </div>

      {/* Table */}
      <div className="bg-slate-900/40 backdrop-blur-md border border-white/10 rounded-xl overflow-hidden shadow-lg shadow-black/20">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-white/5 border-b border-white/10 text-xs text-slate-400 uppercase tracking-wider">
              <th className="w-10 p-4">
                <input
                  type="checkbox"
                  checked={selectedLeads.size === filteredLeads.length && filteredLeads.length > 0}
                  onChange={toggleAll}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-violet-500 focus:ring-violet-500/20 focus:ring-offset-0"
                />
              </th>
              <SortableHeader
                label="Lead"
                field="name"
                currentSort={sortField}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                label="Company"
                field="company"
                currentSort={sortField}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                label="Score"
                field="score"
                currentSort={sortField}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
              <th className="text-left p-4 font-medium">Why Hot?</th>
              <th className="text-left p-4 font-medium">Channels</th>
              <SortableHeader
                label="Last Activity"
                field="lastActivity"
                currentSort={sortField}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
              <th className="w-24 p-4 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredLeads.map((lead) => {
              const tier = tierConfig[lead.tier];
              return (
                <tr
                  key={lead.id}
                  className={`border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors ${
                    lead.tier === "hot"
                      ? "hover:shadow-[inset_4px_0_0_theme(colors.red.500)]"
                      : lead.tier === "warm"
                      ? "hover:shadow-[inset_4px_0_0_theme(colors.amber.500)]"
                      : lead.tier === "cool"
                      ? "hover:shadow-[inset_4px_0_0_theme(colors.blue.500)]"
                      : ""
                  }`}
                >
                  <td className="p-4">
                    <input
                      type="checkbox"
                      checked={selectedLeads.has(lead.id)}
                      onChange={() => toggleLead(lead.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-violet-500 focus:ring-violet-500/20 focus:ring-offset-0"
                    />
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-3.5">
                      <div
                        className={`w-11 h-11 rounded-xl bg-gradient-to-br ${tier.avatarGradient} flex items-center justify-center text-white font-semibold text-sm flex-shrink-0`}
                      >
                        {lead.initials}
                      </div>
                      <div>
                        <div className="font-semibold text-white">
                          {lead.firstName} {lead.lastName}
                        </div>
                        <div className="text-slate-400 text-sm">{lead.title}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="font-medium text-white">{lead.company}</div>
                    <div className="text-slate-500 text-xs">{lead.email}</div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <span
                        className={`text-xl font-bold font-mono ${tier.textClass}`}
                      >
                        {lead.score}
                      </span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-1 rounded uppercase tracking-wider border ${tier.bgClass} ${tier.textClass} ${tier.borderClass}`}
                      >
                        {tier.label}
                      </span>
                    </div>
                  </td>
                  <td className="p-4">
                    <WhyHotBadges reasons={lead.whyHot} />
                  </td>
                  <td className="p-4">
                    <div className="flex gap-1.5">
                      {lead.channels.map((ch, idx) => (
                        <ChannelIcon
                          key={idx}
                          channel={ch.channel}
                          isActive={ch.isActive}
                          tooltip={ch.tooltip}
                        />
                      ))}
                    </div>
                  </td>
                  <td className="p-4">
                    <span
                      className={`text-sm ${
                        lead.lastActivityRecent ? "text-emerald-400" : "text-slate-500"
                      }`}
                    >
                      {lead.lastActivity}
                    </span>
                  </td>
                  <td className="p-4">
                    <button
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium text-violet-400 bg-violet-500/10 rounded-md hover:bg-violet-500/20 transition-colors"
                    >
                      Details
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
            {filteredLeads.length === 0 && (
              <tr>
                <td colSpan={8} className="p-12 text-center text-slate-500">
                  No leads found matching your criteria
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-5 px-1">
        <span className="text-sm text-slate-500">
          Showing <span className="text-slate-300 font-mono">1-{filteredLeads.length}</span> of{" "}
          <span className="text-slate-300 font-mono">1,247</span> leads
        </span>
        <div className="flex gap-2">
          <button className="px-3.5 py-2 text-sm font-medium text-slate-400 bg-slate-900/60 border border-slate-700 rounded-md hover:bg-slate-800 hover:border-slate-600 transition-all">
            ← Previous
          </button>
          <button className="px-3.5 py-2 text-sm font-medium text-white bg-violet-600 border border-violet-600 rounded-md">
            1
          </button>
          <button className="px-3.5 py-2 text-sm font-medium text-slate-400 bg-slate-900/60 border border-slate-700 rounded-md hover:bg-slate-800 hover:border-slate-600 transition-all">
            2
          </button>
          <button className="px-3.5 py-2 text-sm font-medium text-slate-400 bg-slate-900/60 border border-slate-700 rounded-md hover:bg-slate-800 hover:border-slate-600 transition-all">
            3
          </button>
          <button className="px-3.5 py-2 text-sm font-medium text-slate-500 bg-slate-900/60 border border-slate-700 rounded-md">
            ...
          </button>
          <button className="px-3.5 py-2 text-sm font-medium text-slate-400 bg-slate-900/60 border border-slate-700 rounded-md hover:bg-slate-800 hover:border-slate-600 transition-all">
            156
          </button>
          <button className="px-3.5 py-2 text-sm font-medium text-slate-400 bg-slate-900/60 border border-slate-700 rounded-md hover:bg-slate-800 hover:border-slate-600 transition-all">
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}

export default LeadsContent;
