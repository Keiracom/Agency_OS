"use client";

/**
 * DashboardHome.tsx - Full dashboard home page composition
 * Design System: frontend/design/prototype/DESIGN_SYSTEM.md
 *
 * Layout:
 * - Hero KPIs (2 columns)
 * - Campaigns section with cards and Confirm button
 * - Activity + Meetings row (2:1 ratio)
 * - ALS Distribution
 *
 * PROTOTYPE: Uses static demo data, no real API calls
 */

import { useState } from "react";
import { Calendar, TrendingUp, Sparkles } from "lucide-react";

import { KPICard } from "./KPICard";
import { CampaignPriorityCard } from "./CampaignPriorityCard";
import { ActivityFeed } from "./ActivityFeed";
import { MeetingsWidget } from "./MeetingsWidget";
import { ALSDistribution } from "./ALSDistribution";
import { OnTrackIndicator } from "./OnTrackIndicator";

// =============================================================================
// DEMO DATA
// =============================================================================

const demoActivities = [
  {
    id: "1",
    channel: "email" as const,
    leadName: "Sarah Chen",
    company: "TechCorp",
    action: "Opened email - Subject: Scaling your team",
    timestamp: "2m ago",
  },
  {
    id: "2",
    channel: "linkedin" as const,
    leadName: "Mike Johnson",
    company: "StartupXYZ",
    action: "Replied to connection request",
    timestamp: "15m ago",
  },
  {
    id: "3",
    channel: "voice" as const,
    leadName: "Lisa Park",
    company: "Acme Inc",
    action: "Meeting booked - Discovery call",
    timestamp: "1h ago",
  },
  {
    id: "4",
    channel: "sms" as const,
    leadName: "David Lee",
    company: "Growth Co",
    action: "Replied - Interested in learning more",
    timestamp: "2h ago",
  },
  {
    id: "5",
    channel: "email" as const,
    leadName: "Emma Wilson",
    company: "Scale Labs",
    action: "Clicked link - Case study download",
    timestamp: "3h ago",
  },
];

const demoMeetings = [
  {
    id: "1",
    leadName: "Sarah Chen",
    company: "TechCorp",
    scheduledAt: "2026-01-23T14:00:00Z",
    dayLabel: "Today",
    timeLabel: "2:00 PM",
    meetingType: "discovery" as const,
    durationMinutes: 30,
  },
  {
    id: "2",
    leadName: "Mike Johnson",
    company: "StartupXYZ",
    scheduledAt: "2026-01-24T10:00:00Z",
    dayLabel: "Tomorrow",
    timeLabel: "10:00 AM",
    meetingType: "demo" as const,
    durationMinutes: 45,
  },
  {
    id: "3",
    leadName: "Lisa Park",
    company: "Acme Inc",
    scheduledAt: "2026-01-25T15:30:00Z",
    dayLabel: "Sat",
    timeLabel: "3:30 PM",
    meetingType: "follow_up" as const,
    durationMinutes: 30,
  },
];

const demoALSData = [
  { tier: "hot" as const, count: 12, percentage: 8 },
  { tier: "warm" as const, count: 45, percentage: 30 },
  { tier: "cool" as const, count: 52, percentage: 35 },
  { tier: "cold" as const, count: 28, percentage: 19 },
  { tier: "dead" as const, count: 13, percentage: 8 },
];

interface CampaignData {
  id: string;
  name: string;
  isAI: boolean;
  priority: number;
  meetings: number;
  replyRate: number;
  channels: ("email" | "linkedin" | "sms" | "voice")[];
  status: "active" | "paused" | "draft";
}

const initialCampaigns: CampaignData[] = [
  {
    id: "1",
    name: "Tech Decision Makers",
    isAI: true,
    priority: 40,
    meetings: 6,
    replyRate: 3.8,
    channels: ["email", "linkedin", "voice"],
    status: "active",
  },
  {
    id: "2",
    name: "Series A Startups",
    isAI: true,
    priority: 35,
    meetings: 4,
    replyRate: 2.9,
    channels: ["email", "linkedin"],
    status: "active",
  },
  {
    id: "3",
    name: "My Custom Campaign",
    isAI: false,
    priority: 25,
    meetings: 2,
    replyRate: 1.8,
    channels: ["email", "sms"],
    status: "active",
  },
];

// =============================================================================
// COMPONENT
// =============================================================================

export function DashboardHome() {
  const [campaigns, setCampaigns] = useState<CampaignData[]>(initialCampaigns);
  const [isConfirming, setIsConfirming] = useState(false);

  // Calculate total priority (should be 100%)
  const totalPriority = campaigns.reduce((sum, c) => sum + c.priority, 0);

  // Handle priority change for a single campaign
  const handlePriorityChange = (campaignId: string, newPriority: number) => {
    setCampaigns((prev) =>
      prev.map((c) => (c.id === campaignId ? { ...c, priority: newPriority } : c))
    );
  };

  // Handle confirm button
  const handleConfirm = () => {
    setIsConfirming(true);
    // Simulate API call
    setTimeout(() => {
      setIsConfirming(false);
      alert("Priorities confirmed and activated!");
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      {/* Page header */}
      <div className="px-8 py-6 border-b border-[#E2E8F0] bg-white">
        <h1 className="text-2xl font-bold text-[#1E293B]">Dashboard</h1>
        <p className="text-sm text-[#64748B] mt-1">
          Welcome back. Here is your outreach performance this month.
        </p>
      </div>

      {/* Main content */}
      <div className="p-8 space-y-8">
        {/* Hero KPIs - 2 columns */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <KPICard
            label="Meetings Booked"
            value={12}
            trend="up"
            trendLabel="+3 vs last month"
            icon={Calendar}
          />
          <KPICard
            label="Show Rate"
            value="85%"
            trend="up"
            trendLabel="+5%"
            icon={TrendingUp}
            subtitle="vs last month"
          />
        </div>

        {/* On Track Indicator */}
        <OnTrackIndicator
          status="on_track"
          current={12}
          targetLow={15}
          targetHigh={25}
        />

        {/* Campaigns Section */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
          {/* Section header */}
          <div className="px-6 py-4 border-b border-[#E2E8F0] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
                Your Campaigns
              </h2>
              <Sparkles className="h-4 w-4 text-[#8B5CF6]" />
            </div>
            <div className="flex items-center gap-4">
              {/* Total indicator */}
              <span
                className={`text-sm font-medium ${
                  totalPriority === 100 ? "text-[#10B981]" : "text-[#F97316]"
                }`}
              >
                Total: {totalPriority}%
              </span>
            </div>
          </div>

          {/* Campaign cards */}
          <div className="p-6 space-y-4">
            {campaigns.map((campaign) => (
              <CampaignPriorityCard
                key={campaign.id}
                name={campaign.name}
                isAI={campaign.isAI}
                priority={campaign.priority}
                onPriorityChange={(value) => handlePriorityChange(campaign.id, value)}
                meetings={campaign.meetings}
                replyRate={campaign.replyRate}
                channels={campaign.channels}
                status={campaign.status}
              />
            ))}
          </div>

          {/* Confirm button */}
          <div className="px-6 py-4 border-t border-[#E2E8F0] flex justify-end">
            <button
              onClick={handleConfirm}
              disabled={isConfirming || totalPriority !== 100}
              className={`px-6 py-2.5 rounded-lg font-medium transition-all ${
                totalPriority === 100
                  ? "bg-[#3B82F6] hover:bg-[#2563EB] text-white shadow-lg shadow-blue-500/25"
                  : "bg-[#E2E8F0] text-[#94A3B8] cursor-not-allowed"
              }`}
            >
              {isConfirming ? "Confirming..." : "Confirm & Activate"}
            </button>
          </div>
        </div>

        {/* Activity + Meetings Row - 2:1 ratio */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <ActivityFeed activities={demoActivities} />
          </div>
          <div className="lg:col-span-1">
            <MeetingsWidget meetings={demoMeetings} />
          </div>
        </div>

        {/* ALS Distribution */}
        <ALSDistribution data={demoALSData} />
      </div>
    </div>
  );
}
