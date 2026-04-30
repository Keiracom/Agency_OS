/**
 * CampaignCards.tsx - War Room Campaign Grid
 * Phase: Operation Modular Cockpit
 * 
 * War room style campaign cards with:
 * - Live pulse animations for active campaigns
 * - Performance comparison metrics
 * - Multi-channel icons
 * - Progress bars with status
 * - Bloomberg dark mode styling
 * - Glassmorphic effects
 * 
 * Ported from: agency-os-html/campaigns-v2.html
 */

"use client";

import { useState } from "react";
import {
  Mail,
  Linkedin,
  MessageCircle,
  Phone,
  Package,
  Calendar,
  Pause,
  Play,
  Edit2,
  Copy,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  ChevronRight,
} from "lucide-react";

// ============================================
// Types
// ============================================

export type CampaignStatus = "active" | "paused" | "completed" | "draft";
export type ChannelType = "email" | "linkedin" | "sms" | "voice" | "mail";

export interface CampaignChannel {
  type: ChannelType;
  active: boolean;
}

export interface CampaignMetrics {
  leads: number;
  sent: number;
  opens: number;
  replies: number;
  meetings: number;
}

export interface PerformanceMetric {
  label: string;
  value: string;
  change: number;
  trend: "up" | "down" | "neutral";
}

export interface Campaign {
  id: string;
  name: string;
  status: CampaignStatus;
  channels: CampaignChannel[];
  dateRange: { start: string; end: string | null };
  metrics: CampaignMetrics;
  progress: number;
  performance: PerformanceMetric[];
  lastActivity: string;
  pipeline?: string;
}

interface CampaignCardProps {
  campaign: Campaign;
  onPause?: (id: string) => void;
  onResume?: (id: string) => void;
  onEdit?: (id: string) => void;
  onDuplicate?: (id: string) => void;
  onClick?: (id: string) => void;
}

interface CampaignCardsProps {
  campaigns?: Campaign[];
  isLoading?: boolean;
  onCampaignClick?: (id: string) => void;
  className?: string;
}

interface OverviewStatsProps {
  totalSent: number;
  totalOpened: number;
  totalReplies: number;
  totalMeetings: number;
  pipeline: string;
  changes: {
    sent: string;
    opened: string;
    replies: string;
    meetings: string;
    pipeline: string;
  };
}

// ============================================
// Mock Data (Ready for API swap)
// ============================================

export const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: "camp-1",
    name: "Q1 Agency Blitz",
    status: "active",
    channels: [
      { type: "email", active: true },
      { type: "linkedin", active: true },
      { type: "sms", active: true },
      { type: "voice", active: true },
      { type: "mail", active: true },
    ],
    dateRange: { start: "Jan 15", end: "Mar 31" },
    metrics: { leads: 1245, sent: 2847, opens: 1142, replies: 87, meetings: 12 },
    progress: 68,
    performance: [
      { label: "Reply Rate", value: "3.1%", change: 0.4, trend: "up" },
      { label: "Book Rate", value: "13.8%", change: 2.1, trend: "up" },
    ],
    lastActivity: "12 min ago",
    pipeline: "$48K",
  },
  {
    id: "camp-2",
    name: "SaaS Founders Sprint",
    status: "active",
    channels: [
      { type: "email", active: true },
      { type: "linkedin", active: true },
      { type: "sms", active: false },
      { type: "voice", active: true },
      { type: "mail", active: false },
    ],
    dateRange: { start: "Jan 20", end: "Feb 28" },
    metrics: { leads: 856, sent: 1234, opens: 512, replies: 58, meetings: 9 },
    progress: 45,
    performance: [
      { label: "Reply Rate", value: "4.7%", change: 1.2, trend: "up" },
      { label: "Book Rate", value: "15.5%", change: 3.4, trend: "up" },
    ],
    lastActivity: "3 min ago",
    pipeline: "$42K",
  },
  {
    id: "camp-3",
    name: "December Power Push",
    status: "completed",
    channels: [
      { type: "email", active: true },
      { type: "linkedin", active: false },
      { type: "sms", active: false },
      { type: "voice", active: false },
      { type: "mail", active: false },
    ],
    dateRange: { start: "Dec 1", end: "Dec 31" },
    metrics: { leads: 2100, sent: 4200, opens: 1764, replies: 126, meetings: 18 },
    progress: 100,
    performance: [
      { label: "Reply Rate", value: "3.0%", change: 0, trend: "neutral" },
      { label: "Book Rate", value: "14.3%", change: 0, trend: "neutral" },
    ],
    lastActivity: "Completed: Jan 2",
    pipeline: "$72K",
  },
  {
    id: "camp-4",
    name: "LinkedIn Only Test",
    status: "paused",
    channels: [
      { type: "email", active: false },
      { type: "linkedin", active: true },
      { type: "sms", active: false },
      { type: "voice", active: false },
      { type: "mail", active: false },
    ],
    dateRange: { start: "Jan 10", end: null },
    metrics: { leads: 320, sent: 240, opens: 98, replies: 11, meetings: 2 },
    progress: 32,
    performance: [
      { label: "Reply Rate", value: "4.6%", change: -0.8, trend: "down" },
      { label: "Book Rate", value: "18.2%", change: 2.8, trend: "up" },
    ],
    lastActivity: "Paused: Jan 25",
    pipeline: "$8K",
  },
];

export const MOCK_OVERVIEW_STATS: OverviewStatsProps = {
  totalSent: 4521,
  totalOpened: 1847,
  totalReplies: 182,
  totalMeetings: 27,
  pipeline: "$127K",
  changes: {
    sent: "↑ 12% this week",
    opened: "40.8% rate",
    replies: "4.0% rate",
    meetings: "↑ 8 this week",
    pipeline: "↑ $34K added",
  },
};

// ============================================
// Channel Icon Component
// ============================================

const channelConfig: Record<ChannelType, { icon: typeof Mail; bg: string }> = {
  email: { icon: Mail, bg: "bg-amber/20 text-amber" },
  linkedin: { icon: Linkedin, bg: "bg-bg-elevated/20 text-text-secondary" },
  sms: { icon: MessageCircle, bg: "bg-amber/20 text-amber" },
  voice: { icon: Phone, bg: "bg-amber-500/20 text-amber-400" },
  mail: { icon: Package, bg: "bg-amber-light/20 text-amber-light" },
};

function ChannelBadge({ channel }: { channel: CampaignChannel }) {
  const config = channelConfig[channel.type];
  const Icon = config.icon;
  
  return (
    <div
      className={`w-7 h-7 rounded-lg flex items-center justify-center transition-opacity ${
        config.bg
      } ${!channel.active ? "opacity-30" : ""}`}
      title={`${channel.type}${!channel.active ? " (Inactive)" : ""}`}
    >
      <Icon className="w-3.5 h-3.5" />
    </div>
  );
}

// ============================================
// Status Badge Component
// ============================================

const statusConfig: Record<CampaignStatus, { label: string; classes: string; pulse: boolean }> = {
  active: {
    label: "Active",
    classes: "bg-amber-glow text-amber border-amber/30",
    pulse: true,
  },
  paused: {
    label: "Paused",
    classes: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    pulse: false,
  },
  completed: {
    label: "Completed",
    classes: "bg-amber/15 text-amber border-amber/30",
    pulse: false,
  },
  draft: {
    label: "Draft",
    classes: "bg-bg-surface text-text-secondary border-slate-500/30",
    pulse: false,
  },
};

function StatusBadge({ status }: { status: CampaignStatus }) {
  const config = statusConfig[status];
  
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider rounded-full border ${config.classes}`}
    >
      {config.pulse && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber" />
        </span>
      )}
      {config.label}
    </span>
  );
}

// ============================================
// Overview Stats Component
// ============================================

export function OverviewStats({
  stats = MOCK_OVERVIEW_STATS,
  isLoading = false,
}: {
  stats?: OverviewStatsProps;
  isLoading?: boolean;
}) {
  const items = [
    { label: "Total Sent", value: stats.totalSent.toLocaleString(), change: stats.changes.sent },
    { label: "Opened", value: stats.totalOpened.toLocaleString(), change: stats.changes.opened },
    { label: "Replies", value: stats.totalReplies.toString(), change: stats.changes.replies },
    { label: "Meetings", value: stats.totalMeetings.toString(), change: stats.changes.meetings },
    { label: "Pipeline", value: stats.pipeline, change: stats.changes.pipeline },
  ];

  if (isLoading) {
    return (
      <div className="grid grid-cols-5 gap-4 mb-8">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="bg-bg-void/40 backdrop-blur-md rounded-xl border border-white/10 p-5 animate-pulse"
          >
            <div className="h-7 w-16 bg-bg-surface/10 rounded mb-2" />
            <div className="h-3 w-20 bg-bg-surface/10 rounded mb-2" />
            <div className="h-3 w-24 bg-bg-surface/10 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-5 gap-4 mb-8">
      {items.map((item) => (
        <div
          key={item.label}
          className="relative bg-bg-void/40 backdrop-blur-md rounded-xl border border-white/10 p-5 text-center overflow-hidden hover:border-amber/30 transition-colors"
        >
          {/* Gradient top border accent */}
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber to-amber opacity-50" />
          
          <div className="text-2xl font-extrabold font-mono text-text-primary drop-shadow-sm">
            {item.value}
          </div>
          <div className="text-[11px] font-medium text-text-secondary uppercase tracking-wider mt-1.5">
            {item.label}
          </div>
          <div className={`text-xs font-medium mt-2 ${
            item.change.includes("↑") ? "text-amber" : 
            item.change.includes("↓") ? "text-amber" : "text-text-secondary"
          }`}>
            {item.change}
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================
// Campaign Card Component
// ============================================

export function CampaignCard({
  campaign,
  onPause,
  onResume,
  onEdit,
  onDuplicate,
  onClick,
}: CampaignCardProps) {
  const handleAction = (e: React.MouseEvent, action: () => void) => {
    e.stopPropagation();
    action();
  };

  return (
    <div
      className="bg-bg-void/40 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden cursor-pointer transition-all duration-200 hover:border-amber/50 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-amber/10"
      onClick={() => onClick?.(campaign.id)}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-5 border-b border-white/5">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-text-primary">{campaign.name}</span>
          <StatusBadge status={campaign.status} />
        </div>
        <div className="flex gap-2">
          {campaign.status === "active" && onPause && (
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary hover:bg-amber-500/20 hover:text-amber-400 transition-colors"
              onClick={(e) => handleAction(e, () => onPause(campaign.id))}
              title="Pause"
            >
              <Pause className="w-4 h-4" />
            </button>
          )}
          {campaign.status === "paused" && onResume && (
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary hover:bg-amber/20 hover:text-amber transition-colors"
              onClick={(e) => handleAction(e, () => onResume(campaign.id))}
              title="Resume"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          {campaign.status !== "completed" && onEdit && (
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary hover:bg-bg-elevated/20 hover:text-text-secondary transition-colors"
              onClick={(e) => handleAction(e, () => onEdit(campaign.id))}
              title="Edit"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
          {onDuplicate && (
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary hover:bg-amber/20 hover:text-amber transition-colors"
              onClick={(e) => handleAction(e, () => onDuplicate(campaign.id))}
              title="Duplicate"
            >
              <Copy className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Channels Bar */}
      <div className="flex items-center gap-4 px-6 py-3 bg-bg-surface/[0.02]">
        <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
          Channels:
        </span>
        <div className="flex gap-2">
          {campaign.channels.map((channel) => (
            <ChannelBadge key={channel.type} channel={channel} />
          ))}
        </div>
        <div className="ml-auto flex items-center gap-1.5 text-xs text-text-secondary">
          <Calendar className="w-3.5 h-3.5" />
          {campaign.dateRange.start} — {campaign.dateRange.end || "Paused"}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-5 gap-3 px-6 py-5">
        {[
          { label: "Leads", value: campaign.metrics.leads },
          { label: "Sent", value: campaign.metrics.sent },
          { label: "Opens", value: campaign.metrics.opens },
          { label: "Replies", value: campaign.metrics.replies },
          { label: "Meetings", value: campaign.metrics.meetings, highlight: true },
        ].map((stat) => (
          <div
            key={stat.label}
            className="text-center py-3 px-2 bg-bg-void rounded-lg"
          >
            <div
              className={`text-xl font-bold font-mono ${
                stat.highlight ? "text-amber" : "text-text-primary"
              }`}
            >
              {stat.value.toLocaleString()}
            </div>
            <div className="text-[9px] font-medium text-text-muted uppercase tracking-wider mt-1">
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Progress Section */}
      <div className="px-6 py-4 border-t border-white/5">
        <div className="flex justify-between items-center mb-2.5">
          <span className="text-xs text-text-secondary">Sequence Progress</span>
          <span className="text-sm font-semibold font-mono text-amber">
            {campaign.progress}%
          </span>
        </div>
        <div className="h-1.5 bg-bg-void rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-amber to-amber rounded-full transition-all duration-500"
            style={{ width: `${campaign.progress}%` }}
          />
        </div>
      </div>

      {/* Performance Row */}
      <div className="flex items-center gap-5 px-6 py-4 border-t border-white/5">
        {campaign.performance.map((perf) => (
          <div key={perf.label} className="flex items-center gap-2 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                perf.trend === "up"
                  ? "bg-amber"
                  : perf.trend === "down"
                  ? "bg-amber"
                  : "bg-slate-500"
              }`}
            />
            <span className="text-text-secondary">{perf.label}:</span>
            <span className="font-semibold font-mono text-text-primary">{perf.value}</span>
            {perf.change !== 0 && (
              <span
                className={`font-medium ${
                  perf.trend === "up" ? "text-amber" : "text-amber"
                }`}
              >
                {perf.trend === "up" ? "↑" : "↓"} {Math.abs(perf.change)}%
              </span>
            )}
            {perf.change === 0 && (
              <span className="text-text-muted">baseline</span>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-6 py-4 bg-bg-void border-t border-white/5">
        <button className="flex items-center gap-1.5 text-sm font-medium text-amber hover:text-amber-light transition-colors">
          Explore Campaign
          <ChevronRight className="w-4 h-4" />
        </button>
        <span className="text-xs text-text-muted">
          {campaign.lastActivity}
        </span>
      </div>
    </div>
  );
}

// ============================================
// Campaign Comparison Table
// ============================================

export function CampaignComparison({
  campaigns = MOCK_CAMPAIGNS,
  isLoading = false,
}: {
  campaigns?: Campaign[];
  isLoading?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="bg-bg-void/40 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden animate-pulse">
        <div className="px-6 py-5 border-b border-white/5">
          <div className="h-5 w-48 bg-bg-surface/10 rounded" />
        </div>
        <div className="p-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 bg-bg-surface/5 rounded mb-2" />
          ))}
        </div>
      </div>
    );
  }

  // Calculate best values for highlighting
  const metrics = campaigns.map((c) => ({
    id: c.id,
    openRate: (c.metrics.opens / c.metrics.sent * 100).toFixed(1),
    replyRate: (c.metrics.replies / c.metrics.sent * 100).toFixed(1),
    bookRate: (c.metrics.meetings / c.metrics.replies * 100).toFixed(1),
    meetings: c.metrics.meetings,
    pipeline: c.pipeline,
  }));

  const bestOpen = Math.max(...metrics.map((m) => parseFloat(m.openRate)));
  const bestReply = Math.max(...metrics.map((m) => parseFloat(m.replyRate)));
  const bestBook = Math.max(...metrics.map((m) => parseFloat(m.bookRate) || 0));
  const bestMeetings = Math.max(...metrics.map((m) => m.meetings));
  const bestPipeline = Math.max(...metrics.map((m) => parseFloat(m.pipeline?.replace(/[$K]/g, "") || "0")));

  return (
    <div className="mt-8 bg-bg-void/40 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-6 py-5 border-b border-white/5">
        <BarChart3 className="w-5 h-5 text-amber" />
        <h2 className="text-base font-semibold text-text-primary">Performance Comparison</h2>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-bg-surface/[0.02]">
              {["Campaign", "Status", "Open Rate", "Reply Rate", "Book Rate", "Meetings", "Pipeline"].map((header) => (
                <th
                  key={header}
                  className="text-left px-5 py-3.5 text-[10px] font-semibold text-text-muted uppercase tracking-wider border-b border-white/5"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {campaigns.map((campaign, idx) => {
              const m = metrics[idx];
              return (
                <tr
                  key={campaign.id}
                  className="border-b border-white/5 last:border-b-0 hover:bg-bg-surface/[0.02] transition-colors"
                >
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          campaign.status === "active"
                            ? "bg-amber"
                            : campaign.status === "paused"
                            ? "bg-amber-400"
                            : "bg-amber"
                        }`}
                      />
                      <span className="font-semibold text-text-primary">{campaign.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={campaign.status} />
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`font-mono font-medium ${
                        parseFloat(m.openRate) === bestOpen ? "text-amber font-bold" : "text-text-primary"
                      }`}
                    >
                      {m.openRate}%
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`font-mono font-medium ${
                        parseFloat(m.replyRate) === bestReply ? "text-amber font-bold" : "text-text-primary"
                      }`}
                    >
                      {m.replyRate}%
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`font-mono font-medium ${
                        parseFloat(m.bookRate) === bestBook ? "text-amber font-bold" : "text-text-primary"
                      }`}
                    >
                      {isNaN(parseFloat(m.bookRate)) ? "N/A" : `${m.bookRate}%`}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`font-mono font-medium ${
                        m.meetings === bestMeetings ? "text-amber font-bold" : "text-text-primary"
                      }`}
                    >
                      {m.meetings}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`font-mono font-medium ${
                        parseFloat(m.pipeline?.replace(/[$K]/g, "") || "0") === bestPipeline
                          ? "text-amber font-bold"
                          : "text-text-primary"
                      }`}
                    >
                      {m.pipeline}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================
// Main CampaignCards Grid Component
// ============================================

export function CampaignCards({
  campaigns = MOCK_CAMPAIGNS,
  isLoading = false,
  onCampaignClick,
  className = "",
}: CampaignCardsProps) {
  const [localCampaigns, setLocalCampaigns] = useState(campaigns);

  const handlePause = (id: string) => {
    setLocalCampaigns((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status: "paused" as CampaignStatus } : c))
    );
  };

  const handleResume = (id: string) => {
    setLocalCampaigns((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status: "active" as CampaignStatus } : c))
    );
  };

  const handleEdit = (id: string) => {
    console.log("Edit campaign:", id);
    // TODO: Open edit modal
  };

  const handleDuplicate = (id: string) => {
    const campaign = localCampaigns.find((c) => c.id === id);
    if (campaign) {
      const newCampaign: Campaign = {
        ...campaign,
        id: `camp-${Date.now()}`,
        name: `${campaign.name} (Copy)`,
        status: "draft",
        progress: 0,
        metrics: { leads: 0, sent: 0, opens: 0, replies: 0, meetings: 0 },
        lastActivity: "Just created",
      };
      setLocalCampaigns((prev) => [...prev, newCampaign]);
    }
  };

  if (isLoading) {
    return (
      <div className={`grid grid-cols-2 gap-3 md:gap-6 ${className}`}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="bg-bg-void/40 backdrop-blur-md rounded-2xl border border-white/10 h-96 animate-pulse"
          >
            <div className="p-6">
              <div className="h-6 w-48 bg-bg-surface/10 rounded mb-4" />
              <div className="h-4 w-32 bg-bg-surface/10 rounded mb-6" />
              <div className="grid grid-cols-5 gap-3">
                {Array.from({ length: 5 }).map((_, j) => (
                  <div key={j} className="h-16 bg-bg-surface/5 rounded" />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-2 gap-3 md:gap-6 ${className}`}>
      {localCampaigns.map((campaign) => (
        <CampaignCard
          key={campaign.id}
          campaign={campaign}
          onPause={handlePause}
          onResume={handleResume}
          onEdit={handleEdit}
          onDuplicate={handleDuplicate}
          onClick={onCampaignClick}
        />
      ))}
    </div>
  );
}

export default CampaignCards;
