"use client";

import { useState } from "react";
import { Search, Plus, Filter } from "lucide-react";
import { DashboardShell } from "../layout";
import { CampaignAllocationManager, CampaignWithPriority } from "./CampaignAllocationManager";

/**
 * Status filter type
 */
type StatusFilter = "all" | "active" | "paused" | "draft";

/**
 * Demo campaign data for prototype
 */
const demoCampaigns: CampaignWithPriority[] = [
  {
    id: "camp-1",
    name: "Tech Decision Makers",
    status: "active",
    priority_pct: 40,
    is_ai_suggested: true,
    meetings_this_month: 6,
    reply_rate: 3.8,
    show_rate: 85,
  },
  {
    id: "camp-2",
    name: "Series A Startups",
    status: "active",
    priority_pct: 35,
    is_ai_suggested: true,
    meetings_this_month: 4,
    reply_rate: 2.9,
    show_rate: 80,
  },
  {
    id: "camp-3",
    name: "My Custom Campaign",
    status: "paused",
    priority_pct: 25,
    is_ai_suggested: false,
    meetings_this_month: 2,
    reply_rate: 1.8,
    show_rate: 75,
  },
];

/**
 * CampaignList - Full campaigns page
 *
 * Features:
 * - Search bar
 * - Status filters (All, Active, Paused, Draft)
 * - Slot usage indicator
 * - CampaignAllocationManager with priority sliders
 * - Add campaign button
 *
 * Uses DashboardShell for layout.
 */
export function CampaignList() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [isConfirming, setIsConfirming] = useState(false);

  // Filter campaigns based on search and status
  const filteredCampaigns = demoCampaigns.filter((campaign) => {
    const matchesSearch = campaign.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || campaign.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Handle confirm action
  const handleConfirm = (allocations: Array<{ campaign_id: string; priority_pct: number }>) => {
    setIsConfirming(true);
    // Simulate API call
    setTimeout(() => {
      setIsConfirming(false);
      console.log("Allocations confirmed:", allocations);
    }, 2000);
  };

  // Status filter buttons
  const filterButtons: { value: StatusFilter; label: string }[] = [
    { value: "all", label: "All" },
    { value: "active", label: "Active" },
    { value: "paused", label: "Paused" },
    { value: "draft", label: "Draft" },
  ];

  return (
    <DashboardShell title="Campaigns" activePath="/campaigns">
      <div className="space-y-6">
        {/* Top Actions Bar */}
        <div className="flex flex-col sm:flex-row gap-4 sm:items-center sm:justify-between">
          {/* Search Bar */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#94A3B8]" />
            <input
              type="text"
              placeholder="Search campaigns..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent transition-all"
            />
          </div>

          {/* Filters and Add Button */}
          <div className="flex items-center gap-3">
            {/* Status Filter */}
            <div className="flex items-center gap-1 bg-white border border-[#E2E8F0] rounded-lg p-1">
              {filterButtons.map((filter) => (
                <button
                  key={filter.value}
                  onClick={() => setStatusFilter(filter.value)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    statusFilter === filter.value
                      ? "bg-[#3B82F6] text-white shadow-sm"
                      : "text-[#64748B] hover:text-[#1E293B] hover:bg-[#F8FAFC]"
                  }`}
                >
                  {filter.label}
                </button>
              ))}
            </div>

            {/* Add Campaign Button */}
            <button className="flex items-center gap-2 px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25">
              <Plus className="h-4 w-4" />
              New Campaign
            </button>
          </div>
        </div>

        {/* Slot Usage Indicator */}
        <div className="flex items-center gap-3 p-4 bg-white border border-[#E2E8F0] rounded-xl">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-[#64748B]">
                Campaign Slots
              </span>
              <span className="text-sm font-semibold text-[#1E293B]">
                {demoCampaigns.length} of 3 used
              </span>
            </div>
            <div className="h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#3B82F6] rounded-full transition-all duration-300"
                style={{ width: `${(demoCampaigns.length / 3) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Campaign Allocation Manager */}
        {filteredCampaigns.length > 0 ? (
          <CampaignAllocationManager
            campaigns={filteredCampaigns}
            maxCampaigns={3}
            onConfirm={handleConfirm}
            isConfirming={isConfirming}
          />
        ) : (
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-8 text-center">
            <div className="mx-auto w-12 h-12 bg-[#F1F5F9] rounded-xl flex items-center justify-center mb-4">
              <Filter className="h-6 w-6 text-[#94A3B8]" />
            </div>
            <h3 className="text-lg font-semibold text-[#1E293B] mb-2">
              No campaigns found
            </h3>
            <p className="text-[#64748B] mb-4">
              {searchQuery
                ? `No campaigns match "${searchQuery}"`
                : `No ${statusFilter} campaigns`}
            </p>
            <button className="px-4 py-2 text-sm font-medium text-[#3B82F6] hover:bg-[#F8FAFC] rounded-lg transition-colors">
              Clear filters
            </button>
          </div>
        )}
      </div>
    </DashboardShell>
  );
}

export default CampaignList;
