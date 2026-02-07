"use client";

/**
 * Bloomberg Terminal Leads Page
 * Matches: leads-v2.html design
 * Features:
 * - Lead table with tier badges
 * - "Why Hot?" signal badges
 * - Channel activity indicators
 * - Compact sidebar navigation
 */

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Zap,
  MessageSquare,
  BarChart3,
  Settings,
  Search,
  Filter,
  Download,
  Plus,
  Mail,
  Linkedin,
  Phone,
  MessageCircle,
  Building,
  MapPin,
  Calendar,
  ChevronRight,
  ExternalLink,
  Flame,
  TrendingUp,
  Eye,
  MousePointer,
  LucideIcon,
} from "lucide-react";

// ============================================================================
// THEME CONSTANTS
// ============================================================================

const theme = {
  bgVoid: "#05050A",
  bgBase: "#0A0A12",
  bgSurface: "#12121D",
  bgSurfaceHover: "#1A1A28",
  bgElevated: "#222233",
  borderSubtle: "#1E1E2E",
  borderDefault: "#2A2A3D",
  borderStrong: "#3A3A50",
  textPrimary: "#F8F8FC",
  textSecondary: "#B4B4C4",
  textMuted: "#6E6E82",
  accentPrimary: "#7C3AED",
  accentPrimaryHover: "#9061F9",
  accentTeal: "#14B8A6",
  accentBlue: "#3B82F6",
  tierHot: "#EF4444",
  tierWarm: "#F59E0B",
  tierCool: "#3B82F6",
  tierCold: "#6B7280",
  channelEmail: "#7C3AED",
  channelLinkedin: "#0077B5",
  channelSms: "#14B8A6",
  channelVoice: "#F59E0B",
};

// ============================================================================
// COMPACT SIDEBAR COMPONENT
// ============================================================================

interface NavItem {
  key: string;
  icon: LucideIcon;
  href: string;
}

const navItems: NavItem[] = [
  { key: "dashboard", icon: LayoutDashboard, href: "/prototype-bloomberg" },
  { key: "leads", icon: Users, href: "/prototype-bloomberg/leads" },
  { key: "campaigns", icon: Zap, href: "/prototype-bloomberg/campaigns" },
  { key: "replies", icon: MessageSquare, href: "/prototype-bloomberg/replies" },
  { key: "reports", icon: BarChart3, href: "/prototype-bloomberg/reports" },
  { key: "settings", icon: Settings, href: "/prototype-bloomberg/settings" },
];

function CompactSidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/prototype-bloomberg") {
      return pathname === "/prototype-bloomberg";
    }
    return pathname.startsWith(href);
  };

  return (
    <aside 
      className="fixed left-0 top-0 bottom-0 w-[72px] flex flex-col items-center py-5 z-50"
      style={{ background: theme.bgSurface, borderRight: `1px solid ${theme.borderSubtle}` }}
    >
      {/* Logo */}
      <div 
        className="w-[42px] h-[42px] rounded-xl flex items-center justify-center mb-8 text-white font-extrabold text-lg shadow-lg"
        style={{ 
          background: `linear-gradient(135deg, ${theme.accentPrimary} 0%, ${theme.accentPrimaryHover} 100%)`,
          boxShadow: "0 0 20px rgba(124, 58, 237, 0.3)"
        }}
      >
        A
      </div>

      {/* Nav Items */}
      <nav className="flex flex-col items-center gap-2">
        {navItems.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.key}
              href={item.href}
              className="w-11 h-11 rounded-xl flex items-center justify-center transition-all"
              style={{
                background: active ? `${theme.accentPrimary}20` : "transparent",
                color: active ? theme.accentPrimary : theme.textMuted,
              }}
            >
              <item.icon className="w-[22px] h-[22px]" />
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

// ============================================================================
// TIER BADGE COMPONENT
// ============================================================================

type TierType = "hot" | "warm" | "cool" | "cold";

const tierConfig: Record<TierType, { label: string; color: string; bgColor: string }> = {
  hot: { label: "Hot", color: theme.tierHot, bgColor: `${theme.tierHot}15` },
  warm: { label: "Warm", color: theme.tierWarm, bgColor: `${theme.tierWarm}15` },
  cool: { label: "Cool", color: theme.tierCool, bgColor: `${theme.tierCool}15` },
  cold: { label: "Cold", color: theme.tierCold, bgColor: `${theme.tierCold}15` },
};

function TierBadge({ tier }: { tier: TierType }) {
  const config = tierConfig[tier];
  return (
    <span 
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold"
      style={{ background: config.bgColor, color: config.color }}
    >
      {tier === "hot" && <Flame className="w-3 h-3" />}
      {config.label}
    </span>
  );
}

// ============================================================================
// WHY HOT SIGNAL BADGES
// ============================================================================

interface Signal {
  type: "opened" | "clicked" | "replied" | "visited" | "engaged";
  label: string;
}

const signalIcons: Record<string, LucideIcon> = {
  opened: Eye,
  clicked: MousePointer,
  replied: MessageSquare,
  visited: ExternalLink,
  engaged: TrendingUp,
};

function SignalBadges({ signals }: { signals: Signal[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {signals.map((signal, index) => {
        const Icon = signalIcons[signal.type] || Eye;
        return (
          <span
            key={index}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium"
            style={{ 
              background: `${theme.accentPrimary}15`, 
              color: theme.accentPrimaryHover,
              border: `1px solid ${theme.accentPrimary}30`
            }}
          >
            <Icon className="w-2.5 h-2.5" />
            {signal.label}
          </span>
        );
      })}
    </div>
  );
}

// ============================================================================
// CHANNEL ACTIVITY INDICATOR
// ============================================================================

function ChannelIndicator({ channels }: { channels: string[] }) {
  const channelColors: Record<string, string> = {
    email: theme.channelEmail,
    linkedin: theme.channelLinkedin,
    sms: theme.channelSms,
    voice: theme.channelVoice,
  };

  const icons: Record<string, LucideIcon> = {
    email: Mail,
    linkedin: Linkedin,
    sms: MessageCircle,
    voice: Phone,
  };

  return (
    <div className="flex gap-1">
      {channels.map((channel) => {
        const Icon = icons[channel] || Mail;
        return (
          <div
            key={channel}
            className="w-6 h-6 rounded flex items-center justify-center"
            style={{ background: `${channelColors[channel]}20` }}
          >
            <Icon className="w-3 h-3" style={{ color: channelColors[channel] }} />
          </div>
        );
      })}
    </div>
  );
}

// ============================================================================
// LEAD ROW COMPONENT
// ============================================================================

interface LeadData {
  id: string;
  name: string;
  title: string;
  company: string;
  location: string;
  tier: TierType;
  signals: Signal[];
  channels: string[];
  lastActivity: string;
  campaign: string;
}

function LeadRow({ lead }: { lead: LeadData }) {
  return (
    <tr 
      className="border-b transition-colors hover:bg-[#1A1A28]"
      style={{ borderColor: theme.borderSubtle }}
    >
      {/* Name & Title */}
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <div 
            className="w-10 h-10 rounded-lg flex items-center justify-center font-semibold text-white"
            style={{ background: `linear-gradient(135deg, ${theme.accentPrimary} 0%, ${theme.accentBlue} 100%)` }}
          >
            {lead.name.split(" ").map(n => n[0]).join("")}
          </div>
          <div>
            <p className="font-medium text-white text-sm">{lead.name}</p>
            <p className="text-xs" style={{ color: theme.textMuted }}>{lead.title}</p>
          </div>
        </div>
      </td>

      {/* Company */}
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <Building className="w-4 h-4" style={{ color: theme.textMuted }} />
          <span className="text-sm" style={{ color: theme.textSecondary }}>{lead.company}</span>
        </div>
      </td>

      {/* Location */}
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4" style={{ color: theme.textMuted }} />
          <span className="text-sm" style={{ color: theme.textMuted }}>{lead.location}</span>
        </div>
      </td>

      {/* Tier */}
      <td className="py-3 px-4">
        <TierBadge tier={lead.tier} />
      </td>

      {/* Why Hot / Signals */}
      <td className="py-3 px-4">
        <SignalBadges signals={lead.signals} />
      </td>

      {/* Channels */}
      <td className="py-3 px-4">
        <ChannelIndicator channels={lead.channels} />
      </td>

      {/* Last Activity */}
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4" style={{ color: theme.textMuted }} />
          <span className="text-sm" style={{ color: theme.textMuted }}>{lead.lastActivity}</span>
        </div>
      </td>

      {/* Actions */}
      <td className="py-3 px-4">
        <button 
          className="p-2 rounded-lg transition-colors hover:bg-[#2A2A3D]"
          style={{ color: theme.textMuted }}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </td>
    </tr>
  );
}

// ============================================================================
// MAIN LEADS PAGE
// ============================================================================

const demoLeads: LeadData[] = [
  {
    id: "1",
    name: "Sarah Chen",
    title: "CTO",
    company: "TechCorp",
    location: "Sydney, AU",
    tier: "hot",
    signals: [
      { type: "opened", label: "Opened 3x" },
      { type: "clicked", label: "Clicked link" },
      { type: "replied", label: "Requested demo" },
    ],
    channels: ["email", "linkedin"],
    lastActivity: "2 mins ago",
    campaign: "Tech Decision Makers",
  },
  {
    id: "2",
    name: "Mike Johnson",
    title: "VP Engineering",
    company: "StartupXYZ",
    location: "Melbourne, AU",
    tier: "hot",
    signals: [
      { type: "visited", label: "Visited site" },
      { type: "engaged", label: "LinkedIn engaged" },
    ],
    channels: ["email", "linkedin", "voice"],
    lastActivity: "15 mins ago",
    campaign: "SaaS Scale-ups",
  },
  {
    id: "3",
    name: "Lisa Park",
    title: "Head of Product",
    company: "Acme Inc",
    location: "Brisbane, AU",
    tier: "warm",
    signals: [
      { type: "opened", label: "Opened email" },
    ],
    channels: ["email"],
    lastActivity: "1 hour ago",
    campaign: "Tech Decision Makers",
  },
  {
    id: "4",
    name: "David Lee",
    title: "CEO",
    company: "Growth Co",
    location: "Perth, AU",
    tier: "warm",
    signals: [
      { type: "clicked", label: "Clicked pricing" },
    ],
    channels: ["email", "sms"],
    lastActivity: "3 hours ago",
    campaign: "Enterprise Accounts",
  },
  {
    id: "5",
    name: "Emma Wilson",
    title: "Director of Engineering",
    company: "Scale Labs",
    location: "Auckland, NZ",
    tier: "cool",
    signals: [],
    channels: ["linkedin"],
    lastActivity: "1 day ago",
    campaign: "SaaS Scale-ups",
  },
  {
    id: "6",
    name: "Tom Richards",
    title: "CTO",
    company: "DataFlow",
    location: "Sydney, AU",
    tier: "cool",
    signals: [
      { type: "opened", label: "Opened 1x" },
    ],
    channels: ["email"],
    lastActivity: "2 days ago",
    campaign: "Tech Decision Makers",
  },
];

export default function LeadsPage() {
  const [activeTier, setActiveTier] = useState<TierType | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  const tiers: { key: TierType | "all"; label: string; count: number }[] = [
    { key: "all", label: "All Leads", count: 150 },
    { key: "hot", label: "Hot", count: 12 },
    { key: "warm", label: "Warm", count: 35 },
    { key: "cool", label: "Cool", count: 58 },
    { key: "cold", label: "Cold", count: 45 },
  ];

  const filteredLeads = demoLeads.filter(lead => {
    if (activeTier !== "all" && lead.tier !== activeTier) return false;
    if (searchQuery && !lead.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div 
      className="min-h-screen flex"
      style={{ background: theme.bgBase }}
    >
      {/* Compact Sidebar */}
      <CompactSidebar />

      {/* Main Content */}
      <main className="flex-1 ml-[72px]" style={{ background: theme.bgVoid }}>
        {/* Header */}
        <header 
          className="px-8 py-5"
          style={{ background: theme.bgSurface, borderBottom: `1px solid ${theme.borderSubtle}` }}
        >
          {/* Top Row */}
          <div className="flex items-center justify-between mb-5">
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                Leads
                <span 
                  className="px-2.5 py-1 rounded text-sm font-semibold font-mono"
                  style={{ background: `${theme.accentPrimary}20`, color: theme.accentPrimary }}
                >
                  {demoLeads.length}
                </span>
              </h1>
              <p className="text-sm mt-1" style={{ color: theme.textMuted }}>
                Manage and track your lead pipeline
              </p>
            </div>
            <div className="flex gap-3">
              <button 
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all"
                style={{ 
                  background: theme.bgSurfaceHover,
                  color: theme.textSecondary,
                  border: `1px solid ${theme.borderDefault}`
                }}
              >
                <Download className="w-4 h-4" /> Export
              </button>
              <button 
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all text-white"
                style={{ 
                  background: `linear-gradient(135deg, ${theme.accentPrimary} 0%, ${theme.accentBlue} 100%)`
                }}
              >
                <Plus className="w-4 h-4" /> Add Leads
              </button>
            </div>
          </div>

          {/* Filters Row */}
          <div className="flex items-center gap-4">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search 
                className="absolute left-3 top-1/2 -translate-y-1/2 w-[18px] h-[18px]"
                style={{ color: theme.textMuted }}
              />
              <input
                type="text"
                placeholder="Search leads..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm outline-none transition-all"
                style={{ 
                  background: theme.bgBase,
                  border: `1px solid ${theme.borderDefault}`,
                  color: theme.textPrimary,
                }}
              />
            </div>

            {/* Tier Tabs */}
            <div 
              className="flex gap-1 p-1 rounded-lg"
              style={{ background: theme.bgBase, border: `1px solid ${theme.borderDefault}` }}
            >
              {tiers.map((tier) => (
                <button
                  key={tier.key}
                  onClick={() => setActiveTier(tier.key)}
                  className="px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2"
                  style={{
                    background: activeTier === tier.key ? theme.bgSurface : "transparent",
                    color: activeTier === tier.key ? theme.textPrimary : theme.textMuted,
                  }}
                >
                  {tier.label}
                  <span 
                    className="px-1.5 py-0.5 rounded text-[10px] font-mono"
                    style={{ 
                      background: activeTier === tier.key ? `${theme.accentPrimary}20` : theme.bgSurfaceHover,
                      color: activeTier === tier.key ? theme.accentPrimary : theme.textMuted,
                    }}
                  >
                    {tier.count}
                  </span>
                </button>
              ))}
            </div>

            {/* Filter Button */}
            <button 
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all"
              style={{ 
                background: theme.bgSurfaceHover,
                color: theme.textSecondary,
                border: `1px solid ${theme.borderDefault}`
              }}
            >
              <Filter className="w-4 h-4" /> Filters
            </button>
          </div>
        </header>

        {/* Table */}
        <div className="p-6">
          <div 
            className="rounded-xl overflow-hidden"
            style={{ background: theme.bgSurface, border: `1px solid ${theme.borderSubtle}` }}
          >
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: `1px solid ${theme.borderSubtle}` }}>
                  <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: theme.textMuted }}>
                    Lead
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: theme.textMuted }}>
                    Company
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: theme.textMuted }}>
                    Location
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: theme.textMuted }}>
                    Tier
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: theme.textMuted }}>
                    Why Hot?
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: theme.textMuted }}>
                    Channels
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: theme.textMuted }}>
                    Last Activity
                  </th>
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.map((lead) => (
                  <LeadRow key={lead.id} lead={lead} />
                ))}
              </tbody>
            </table>

            {filteredLeads.length === 0 && (
              <div className="py-12 text-center">
                <p style={{ color: theme.textMuted }}>No leads found matching your criteria</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
