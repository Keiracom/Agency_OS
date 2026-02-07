/**
 * LeadsContent.tsx - Leads Page Content
 * Phase: Operation Modular Cockpit
 * Uses LeadTable and TierBadge components
 */

"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { LeadTable, TierBadge } from "@/components/dashboard";
import { useLeads } from "@/hooks/use-leads";
import type { ALSTier } from "@/lib/api/types";

interface LeadsContentProps {
  campaignId?: string | null;
}

// Tier filter configuration per LEADS.md spec
const tierFilters: { tier: ALSTier; label: string; color: string; textColor: string }[] = [
  { tier: "hot", label: "High Priority", color: "border-orange-500 bg-orange-50", textColor: "text-orange-700" },
  { tier: "warm", label: "Engaged", color: "border-yellow-500 bg-yellow-50", textColor: "text-yellow-700" },
  { tier: "cool", label: "Nurturing", color: "border-blue-500 bg-blue-50", textColor: "text-blue-700" },
  { tier: "cold", label: "Low Activity", color: "border-slate-400 bg-slate-50", textColor: "text-slate-600" },
  { tier: "dead", label: "Inactive", color: "border-slate-300 bg-slate-100", textColor: "text-slate-500" },
];

export function LeadsContent({ campaignId }: LeadsContentProps) {
  const [selectedTier, setSelectedTier] = useState<ALSTier | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: leadsData, isLoading } = useLeads({
    campaignId: campaignId ?? undefined,
    tier: selectedTier ?? undefined,
  });

  const leads = leadsData?.items ?? [];
  const totalCount = leadsData?.total ?? 0;

  // Calculate tier counts (would be from API in production)
  const tierCounts: Record<ALSTier, number> = {
    hot: leads.filter(l => l.als_tier === "hot").length,
    warm: leads.filter(l => l.als_tier === "warm").length,
    cool: leads.filter(l => l.als_tier === "cool").length,
    cold: leads.filter(l => l.als_tier === "cold").length,
    dead: leads.filter(l => l.als_tier === "dead").length,
  };

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Leads</h2>
          <p className="text-sm text-slate-500">{totalCount} prospects in pipeline</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search name, email, company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Tier Filter Cards */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        {tierFilters.map((item) => (
          <button
            key={item.tier}
            onClick={() => setSelectedTier(selectedTier === item.tier ? null : item.tier)}
            className={`p-4 rounded-lg border-2 text-left transition-all ${item.color} ${
              selectedTier === item.tier ? "ring-2 ring-blue-500 ring-offset-2" : "hover:shadow-md"
            }`}
          >
            <div className={`text-2xl font-bold ${item.textColor}`}>{tierCounts[item.tier]}</div>
            <div className="text-sm text-slate-600">{item.label}</div>
          </button>
        ))}
      </div>

      {/* Lead Table - Uses modular component */}
      <LeadTable
        leads={leads}
        isLoading={isLoading}
        onLeadClick={(lead) => console.log("Lead clicked:", lead)}
      />
    </div>
  );
}

export default LeadsContent;
