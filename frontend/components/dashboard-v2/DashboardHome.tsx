/**
 * Dashboard Home Page - Main dashboard view
 * Open in Codux to adjust layout, spacing between sections
 */

"use client";

import { Calendar, TrendingUp, Plus } from "lucide-react";
import { DashboardLayout } from "./DashboardLayout";
import { KPICard } from "./KPICard";
import { CampaignCard } from "./CampaignCard";
import { ActivityItem } from "./ActivityItem";
import { MeetingItem } from "./MeetingItem";
import { SectionCard } from "./SectionCard";
import { ALSDistribution } from "./ALSDistribution";

// Demo data - will be replaced with real hooks
const demoData = {
  metrics: {
    meetingsBooked: 12,
    meetingsTrend: 3,
    showRate: 85,
    showRateTrend: 5,
  },
  campaigns: [
    { id: "1", name: "Tech Decision Makers", isAI: true, priority: 40, meetings: 6, replyRate: 3.8, channels: ["email", "linkedin"] as const, status: "active" as const },
    { id: "2", name: "Series A Startups", isAI: true, priority: 35, meetings: 4, replyRate: 2.9, channels: ["email", "linkedin"] as const, status: "active" as const },
    { id: "3", name: "My Custom Campaign", isAI: false, priority: 25, meetings: 2, replyRate: 1.8, channels: ["email"] as const, status: "active" as const },
  ],
  activities: [
    { channel: "email" as const, name: "Sarah Chen", company: "TechCorp", action: "Opened email", timestamp: "2m ago" },
    { channel: "linkedin" as const, name: "Mike Johnson", company: "StartupXYZ", action: "Accepted connection", timestamp: "15m ago" },
    { channel: "meeting" as const, name: "Lisa Park", company: "Acme Inc", action: "Meeting booked", timestamp: "1h ago" },
    { channel: "voice" as const, name: "David Lee", company: "Growth Co", action: "Call completed", timestamp: "2h ago" },
  ],
  meetings: [
    { name: "Sarah Chen", company: "TechCorp", day: "Today", time: "2:00 PM", type: "discovery" as const, duration: 30 },
    { name: "Mike Johnson", company: "StartupXYZ", day: "Tomorrow", time: "10:00 AM", type: "demo" as const, duration: 45 },
    { name: "Lisa Park", company: "Acme Inc", day: "Thu", time: "3:00 PM", type: "follow_up" as const, duration: 30 },
  ],
  alsDistribution: [
    { tier: "hot" as const, count: 45, percentage: 15 },
    { tier: "warm" as const, count: 105, percentage: 35 },
    { tier: "cool" as const, count: 90, percentage: 30 },
    { tier: "cold" as const, count: 45, percentage: 15 },
    { tier: "dead" as const, count: 15, percentage: 5 },
  ],
};

export function DashboardHome() {
  const handleAddCampaign = () => {
    // TODO: Navigate to campaign creation
    console.log("Add campaign clicked");
  };

  const handleConfirmActivate = () => {
    // TODO: Submit campaign priorities
    console.log("Confirm & Activate clicked");
  };

  const handlePriorityChange = (campaignId: string, value: number) => {
    // TODO: Update campaign priority
    console.log(`Campaign ${campaignId} priority: ${value}`);
  };

  return (
    <DashboardLayout title="Dashboard">
      {/* Hero KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <KPICard
          label="Meetings Booked"
          value={demoData.metrics.meetingsBooked}
          trend={demoData.metrics.meetingsTrend}
          icon={Calendar}
          subtitle="On track for 15-25"
        />
        <KPICard
          label="Show Rate"
          value={`${demoData.metrics.showRate}%`}
          trend={demoData.metrics.showRateTrend}
          trendLabel="vs last month"
          icon={TrendingUp}
        />
      </div>

      {/* Campaigns Section */}
      <SectionCard
        title="Your Campaigns"
        action={{ label: "+ Add Campaign", onClick: handleAddCampaign }}
        className="mb-8"
      >
        <div className="space-y-4">
          {demoData.campaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              name={campaign.name}
              isAI={campaign.isAI}
              priority={campaign.priority}
              onPriorityChange={(v) => handlePriorityChange(campaign.id, v)}
              meetings={campaign.meetings}
              replyRate={campaign.replyRate}
              channels={[...campaign.channels]}
              status={campaign.status}
            />
          ))}
        </div>

        {/* Total + Confirm Button */}
        <div className="flex items-center justify-between mt-6 pt-6 border-t border-[#E2E8F0]">
          <span className="text-sm text-[#64748B]">
            Total: <span className="font-semibold text-[#1E293B]">100%</span>
          </span>
          <button
            onClick={handleConfirmActivate}
            className="px-6 py-2.5 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25"
          >
            Confirm & Activate
          </button>
        </div>
      </SectionCard>

      {/* Activity + Meetings Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Activity Feed */}
        <SectionCard
          title="Recent Activity"
          badge={{ label: "Live", variant: "live" }}
          className="lg:col-span-2"
        >
          <div className="space-y-1">
            {demoData.activities.map((activity, i) => (
              <ActivityItem
                key={i}
                channel={activity.channel}
                name={activity.name}
                company={activity.company}
                action={activity.action}
                timestamp={activity.timestamp}
              />
            ))}
          </div>
        </SectionCard>

        {/* Upcoming Meetings */}
        <SectionCard title="Upcoming Meetings">
          <div className="space-y-1">
            {demoData.meetings.map((meeting, i) => (
              <MeetingItem
                key={i}
                name={meeting.name}
                company={meeting.company}
                day={meeting.day}
                time={meeting.time}
                type={meeting.type}
                duration={meeting.duration}
              />
            ))}
          </div>
        </SectionCard>
      </div>

      {/* ALS Distribution */}
      <SectionCard title="Lead Quality Distribution">
        <ALSDistribution data={demoData.alsDistribution} />
      </SectionCard>
    </DashboardLayout>
  );
}

export default DashboardHome;
