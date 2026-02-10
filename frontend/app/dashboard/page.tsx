"use client";

/**
 * Dashboard (Command Center) - Sprint 2 Port
 * Ported from: frontend/design/html-prototypes/dashboard-v3.html
 */

import { AppShell } from "@/components/layout/AppShell";
import { StatsRow } from "@/components/dashboard/StatsRow";
import { ActivityFeedSimple } from "@/components/dashboard/ActivityFeedSimple";
import { QuickActionsSimple } from "@/components/dashboard/QuickActionsSimple";
import { mockDashboardStats, mockActivityFeed, mockQuickActions } from "@/data/mock-dashboard";

export default function DashboardPage() {
  return (
    <AppShell>
      <div className="p-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-text-primary">Command Center</h1>
          <p className="text-text-muted mt-1">
            Welcome back. Here's what's happening with your outreach.
          </p>
        </div>

        {/* Stats Row */}
        <StatsRow
          leads={mockDashboardStats.leadsThisMonth}
          emails={mockDashboardStats.emailsSent}
          meetings={mockDashboardStats.meetingsBooked}
          responseRate={mockDashboardStats.responseRate}
        />

        {/* Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
          {/* Activity Feed - 2/3 width */}
          <div className="lg:col-span-2">
            <ActivityFeedSimple items={mockActivityFeed} />
          </div>

          {/* Quick Actions - 1/3 width */}
          <div>
            <QuickActionsSimple actions={mockQuickActions} />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
