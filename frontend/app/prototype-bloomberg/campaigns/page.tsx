"use client";

/**
 * Bloomberg Terminal Campaigns Page
 * Matches: campaigns-v4.html design
 * Features:
 * - Lead Pool Allocation visual bar
 * - Campaign cards with priority sliders
 * - AI-suggested campaigns
 * - War room style interface
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
  CreditCard,
  Mail,
  Linkedin,
  Phone,
  MessageCircle,
  Sparkles,
  Lock,
  Play,
  Pause,
  ChevronDown,
  Plus,
  LucideIcon,
} from "lucide-react";

// ============================================================================
// THEME CONSTANTS
// ============================================================================

const theme = {
  bgPrimary: "#0A0A12",
  bgSecondary: "#12121A",
  bgTertiary: "#1A1A24",
  borderColor: "#2A2A3A",
  textPrimary: "#FFFFFF",
  textSecondary: "#A0A0B0",
  textMuted: "#6B6B7B",
  accentPurple: "#7C3AED",
  accentPurpleLight: "#9D5CFF",
  accentGreen: "#10B981",
  accentBlue: "#3B82F6",
  accentOrange: "#F59E0B",
  accentRed: "#EF4444",
  accentPink: "#EC4899",
};

// ============================================================================
// SIDEBAR COMPONENT
// ============================================================================

interface NavItem {
  key: string;
  label: string;
  icon: LucideIcon;
  href: string;
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: "Main",
    items: [
      { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/prototype-bloomberg" },
      { key: "leads", label: "Leads", icon: Users, href: "/prototype-bloomberg/leads" },
      { key: "campaigns", label: "Campaigns", icon: Zap, href: "/prototype-bloomberg/campaigns" },
      { key: "replies", label: "Replies", icon: MessageSquare, href: "/prototype-bloomberg/replies" },
    ],
  },
  {
    title: "Analytics",
    items: [
      { key: "reports", label: "Reports", icon: BarChart3, href: "/prototype-bloomberg/reports" },
    ],
  },
  {
    title: "Settings",
    items: [
      { key: "settings", label: "Settings", icon: Settings, href: "/prototype-bloomberg/settings" },
      { key: "billing", label: "Billing", icon: CreditCard, href: "/prototype-bloomberg/billing" },
    ],
  },
];

function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/prototype-bloomberg") {
      return pathname === "/prototype-bloomberg";
    }
    return pathname.startsWith(href);
  };

  return (
    <aside 
      className="fixed left-0 top-0 bottom-0 w-60 border-r z-50 flex flex-col overflow-y-auto"
      style={{ background: theme.bgSecondary, borderColor: theme.borderColor }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div 
          className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg"
          style={{ 
            background: `linear-gradient(135deg, ${theme.accentPurple} 0%, ${theme.accentPurpleLight} 100%)`,
            boxShadow: "0 8px 24px rgba(124, 58, 237, 0.3)"
          }}
        >
          <svg viewBox="0 0 36 36" fill="none" className="w-5 h-5">
            <path d="M10 18L15 23L26 12" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <span className="text-lg font-bold text-white">Agency OS</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        {navSections.map((section) => (
          <div key={section.title} className="mb-6">
            <div className="px-5 mb-2">
              <span 
                className="text-[11px] font-semibold uppercase tracking-wider"
                style={{ color: theme.textMuted }}
              >
                {section.title}
              </span>
            </div>
            {section.items.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.key}
                  href={item.href}
                  className="flex items-center gap-3 px-5 py-3 text-sm font-medium transition-all"
                  style={{ 
                    background: active ? `${theme.accentPurple}10` : "transparent",
                    color: active ? theme.accentPurpleLight : theme.textSecondary,
                    borderRight: active ? `2px solid ${theme.accentPurple}` : "none",
                  }}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}

// ============================================================================
// LEAD POOL ALLOCATION BAR
// ============================================================================

interface CampaignAllocation {
  id: string;
  name: string;
  percentage: number;
  color: string;
}

function LeadPoolBar({ campaigns }: { campaigns: CampaignAllocation[] }) {
  const allocated = campaigns.reduce((sum, c) => sum + c.percentage, 0);
  const unallocated = 100 - allocated;

  return (
    <div
      className="rounded-2xl p-6 mb-6"
      style={{ background: theme.bgSecondary, border: `1px solid ${theme.borderColor}` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-semibold text-white">Lead Pool Allocation</h3>
        <div className="flex gap-6">
          <div>
            <p className="text-xs" style={{ color: theme.textMuted }}>Total Pool</p>
            <p className="text-lg font-bold font-mono" style={{ color: theme.accentGreen }}>150</p>
          </div>
          <div>
            <p className="text-xs" style={{ color: theme.textMuted }}>Unallocated</p>
            <p 
              className="text-lg font-bold font-mono" 
              style={{ color: unallocated > 30 ? theme.accentOrange : theme.accentGreen }}
            >
              {Math.round(150 * unallocated / 100)}
            </p>
          </div>
        </div>
      </div>

      {/* Visual Bar */}
      <div 
        className="h-12 rounded-xl flex overflow-hidden mb-4"
        style={{ background: theme.bgTertiary, border: `1px solid ${theme.borderColor}` }}
      >
        {campaigns.map((campaign) => (
          <div
            key={campaign.id}
            className="h-full flex items-center justify-center transition-all duration-300"
            style={{ 
              width: `${campaign.percentage}%`,
              background: campaign.color,
              minWidth: campaign.percentage > 0 ? "40px" : 0,
            }}
          >
            {campaign.percentage >= 10 && (
              <span className="text-xs font-semibold text-white drop-shadow-md">
                {campaign.percentage}%
              </span>
            )}
          </div>
        ))}
        {unallocated > 0 && (
          <div
            className="h-full flex items-center justify-center"
            style={{ 
              width: `${unallocated}%`,
              background: `repeating-linear-gradient(45deg, ${theme.bgTertiary}, ${theme.bgTertiary} 10px, #1f1f2e 10px, #1f1f2e 20px)`,
            }}
          >
            <span className="text-xs font-medium" style={{ color: theme.textMuted }}>
              {unallocated}%
            </span>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4">
        {campaigns.map((campaign) => (
          <div key={campaign.id} className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded"
              style={{ background: campaign.color }}
            />
            <span className="text-sm" style={{ color: theme.textSecondary }}>
              {campaign.name}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-2">
          <div 
            className="w-3 h-3 rounded"
            style={{ 
              background: `repeating-linear-gradient(45deg, ${theme.bgTertiary}, ${theme.bgTertiary} 2px, #1f1f2e 2px, #1f1f2e 4px)`
            }}
          />
          <span className="text-sm" style={{ color: theme.textMuted }}>
            Unallocated
          </span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// CAMPAIGN CARD COMPONENT
// ============================================================================

interface CampaignData {
  id: string;
  name: string;
  description: string;
  isAI: boolean;
  isActive: boolean;
  allocation: number;
  channels: string[];
  replyRate: number;
  meetingsBooked: number;
  color: string;
}

function CampaignCard({ 
  campaign, 
  onAllocationChange 
}: { 
  campaign: CampaignData;
  onAllocationChange: (id: string, value: number) => void;
}) {
  const channelIcons: Record<string, LucideIcon> = {
    email: Mail,
    linkedin: Linkedin,
    sms: MessageCircle,
    voice: Phone,
  };

  return (
    <div
      className="rounded-2xl p-6 transition-all"
      style={{ 
        background: campaign.isAI 
          ? `linear-gradient(135deg, ${theme.accentPurple}08 0%, transparent 100%)`
          : theme.bgSecondary,
        border: campaign.isAI 
          ? `1px dashed ${theme.accentPurple}` 
          : campaign.isActive 
            ? `1px solid ${theme.accentGreen}` 
            : `1px solid ${theme.borderColor}`,
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          {campaign.isAI && (
            <span 
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wide"
              style={{ background: `${theme.accentPurple}20`, color: theme.accentPurpleLight }}
            >
              <Sparkles className="w-3 h-3" /> AI Suggested
            </span>
          )}
          {campaign.isActive && (
            <span 
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wide"
              style={{ background: `${theme.accentGreen}20`, color: theme.accentGreen }}
            >
              <Play className="w-3 h-3" /> Active
            </span>
          )}
        </div>
        <button 
          className="p-2 rounded-lg transition-colors"
          style={{ color: theme.textMuted }}
        >
          <ChevronDown className="w-5 h-5" />
        </button>
      </div>

      {/* Title & Description */}
      <h3 className="text-lg font-semibold text-white mb-2">{campaign.name}</h3>
      <p className="text-sm mb-4" style={{ color: theme.textSecondary }}>
        {campaign.description}
      </p>

      {/* Meta */}
      <div className="flex flex-wrap gap-3 mb-5">
        {campaign.channels.map((channel) => {
          const Icon = channelIcons[channel] || Mail;
          return (
            <div 
              key={channel}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs"
              style={{ background: theme.bgTertiary, color: theme.textSecondary }}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="capitalize">{channel}</span>
            </div>
          );
        })}
      </div>

      {/* Allocation Slider */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm" style={{ color: theme.textSecondary }}>Lead Allocation</span>
          <span className="text-base font-bold font-mono" style={{ color: theme.accentPurpleLight }}>
            {campaign.allocation}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={campaign.allocation}
          onChange={(e) => onAllocationChange(campaign.id, parseInt(e.target.value))}
          className="w-full h-2 rounded cursor-pointer appearance-none"
          style={{
            background: `linear-gradient(to right, ${theme.accentPurple} 0%, ${theme.accentPurple} ${campaign.allocation}%, ${theme.bgTertiary} ${campaign.allocation}%, ${theme.bgTertiary} 100%)`,
          }}
        />
        <div className="flex justify-between mt-2">
          <span className="text-xs" style={{ color: theme.textMuted }}>
            ≈ {Math.round(150 * campaign.allocation / 100)} leads
          </span>
          <span className="text-xs" style={{ color: theme.accentGreen }}>
            Available: {Math.round(150 * (100 - campaign.allocation) / 100)}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="flex gap-4 mb-5 py-3 border-t border-b" style={{ borderColor: theme.borderColor }}>
        <div>
          <p className="text-xs" style={{ color: theme.textMuted }}>Reply Rate</p>
          <p className="text-lg font-bold" style={{ color: theme.accentBlue }}>
            {campaign.replyRate}%
          </p>
        </div>
        <div>
          <p className="text-xs" style={{ color: theme.textMuted }}>Meetings Booked</p>
          <p className="text-lg font-bold" style={{ color: theme.accentGreen }}>
            {campaign.meetingsBooked}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          className="flex-1 py-3 px-4 rounded-xl text-sm font-medium transition-all"
          style={{ 
            background: `linear-gradient(135deg, ${theme.accentPurple} 0%, ${theme.accentPurpleLight} 100%)`,
            color: "white",
          }}
        >
          {campaign.isActive ? "View Campaign" : "Activate Campaign"}
        </button>
        <button
          className="py-3 px-4 rounded-xl text-sm font-medium transition-all"
          style={{ 
            background: theme.bgTertiary,
            color: theme.textSecondary,
            border: `1px solid ${theme.borderColor}`,
          }}
        >
          Edit
        </button>
      </div>

      {/* Lock Notice for Active */}
      {campaign.isActive && (
        <div 
          className="flex items-center gap-2 mt-4 px-3 py-2.5 rounded-lg text-xs"
          style={{ background: `${theme.accentGreen}15`, color: theme.accentGreen }}
        >
          <Lock className="w-4 h-4" />
          Campaign running • Adjust allocation to redistribute leads
        </div>
      )}
    </div>
  );
}

// ============================================================================
// ADD CAMPAIGN CARD
// ============================================================================

function AddCampaignCard() {
  return (
    <div
      className="rounded-2xl p-6 flex flex-col items-center justify-center min-h-[300px] cursor-pointer transition-all hover:border-[#7C3AED]"
      style={{ 
        border: `2px dashed ${theme.borderColor}`,
        background: "transparent",
      }}
    >
      <div 
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: theme.bgTertiary }}
      >
        <Plus className="w-8 h-8" style={{ color: theme.textMuted }} />
      </div>
      <h3 className="font-semibold text-white mb-2">Create Custom Campaign</h3>
      <p className="text-sm text-center max-w-[200px]" style={{ color: theme.textSecondary }}>
        Build a campaign from scratch with your own targeting criteria
      </p>
    </div>
  );
}

// ============================================================================
// MAIN CAMPAIGNS PAGE
// ============================================================================

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<CampaignData[]>([
    {
      id: "1",
      name: "Tech Decision Makers - Series A+",
      description: "AI-identified campaign targeting CTOs and VPs at funded startups. Based on your portfolio patterns.",
      isAI: true,
      isActive: true,
      allocation: 40,
      channels: ["email", "linkedin", "voice"],
      replyRate: 5.2,
      meetingsBooked: 6,
      color: "linear-gradient(135deg, #7C3AED, #9D5CFF)",
    },
    {
      id: "2",
      name: "SaaS Scale-ups ANZ",
      description: "Targeting high-growth SaaS companies in Australia and New Zealand looking to scale their tech teams.",
      isAI: true,
      isActive: false,
      allocation: 35,
      channels: ["email", "linkedin"],
      replyRate: 4.1,
      meetingsBooked: 3,
      color: "linear-gradient(135deg, #3B82F6, #60A5FA)",
    },
    {
      id: "3",
      name: "Enterprise Accounts",
      description: "Custom campaign for enterprise accounts with 500+ employees.",
      isAI: false,
      isActive: false,
      allocation: 25,
      channels: ["email"],
      replyRate: 2.8,
      meetingsBooked: 2,
      color: "linear-gradient(135deg, #10B981, #34D399)",
    },
  ]);

  const handleAllocationChange = (id: string, value: number) => {
    setCampaigns(prev => 
      prev.map(c => c.id === id ? { ...c, allocation: value } : c)
    );
  };

  const allocations = campaigns.map(c => ({
    id: c.id,
    name: c.name,
    percentage: c.allocation,
    color: c.color,
  }));

  return (
    <div 
      className="min-h-screen"
      style={{ background: theme.bgPrimary }}
    >
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="ml-60 p-6 lg:p-8">
        {/* Page Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-[28px] font-bold text-white mb-2">Campaigns</h1>
            <p style={{ color: theme.textSecondary }}>
              Manage your outreach campaigns and lead allocation
            </p>
          </div>
          <div 
            className="flex items-center gap-3 px-5 py-3 rounded-xl"
            style={{ background: theme.bgSecondary, border: `1px solid ${theme.borderColor}` }}
          >
            <span className="text-sm" style={{ color: theme.textSecondary }}>Tier</span>
            <span className="font-semibold" style={{ color: theme.accentPurpleLight }}>Velocity</span>
          </div>
        </div>

        {/* Lead Pool Allocation */}
        <LeadPoolBar campaigns={allocations} />

        {/* Campaigns Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
          {campaigns.map((campaign) => (
            <CampaignCard 
              key={campaign.id} 
              campaign={campaign} 
              onAllocationChange={handleAllocationChange}
            />
          ))}
          <AddCampaignCard />
        </div>
      </main>

      {/* Custom styles for range input */}
      <style jsx global>{`
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: ${theme.accentPurple};
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(124, 58, 237, 0.4);
        }
        input[type="range"]::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: ${theme.accentPurple};
          cursor: pointer;
          border: none;
          box-shadow: 0 2px 8px rgba(124, 58, 237, 0.4);
        }
      `}</style>
    </div>
  );
}
