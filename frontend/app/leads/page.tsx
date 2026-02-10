"use client";

/**
 * Leads List Page - Sprint 2 Port
 * Ported from: frontend/design/html-prototypes/leads-v2.html
 */

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { LeadsFilters } from "@/components/leads/LeadsFilters";
import { LeadsTable } from "@/components/leads/LeadsTable";
import { mockLeads, mockLeadStats, LeadTier } from "@/data/mock-leads";
import { useRouter } from "next/navigation";

export default function LeadsPage() {
  const router = useRouter();
  const [activeTier, setActiveTier] = useState<LeadTier | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Filter leads based on active tier and search
  const filteredLeads = mockLeads.filter((lead) => {
    const matchesTier = activeTier === "all" || lead.tier === activeTier;
    const matchesSearch =
      searchQuery === "" ||
      lead.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.company.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTier && matchesSearch;
  });

  const handleLeadClick = (leadId: string) => {
    router.push(`/leads/${leadId}`);
  };

  return (
    <AppShell>
      <div className="p-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
              Leads
              <span className="text-sm font-mono font-medium px-2 py-1 bg-accent-primary/15 text-accent-primary rounded">
                {mockLeadStats.total}
              </span>
            </h1>
            <p className="text-text-muted mt-1">
              Your enriched leads scored by the ALS algorithm
            </p>
          </div>
        </div>

        {/* Filters */}
        <LeadsFilters
          activeTier={activeTier}
          onTierChange={setActiveTier}
          searchQuery={searchQuery}
          onSearch={setSearchQuery}
          counts={mockLeadStats}
        />

        {/* Leads Table */}
        <div className="mt-6">
          <LeadsTable leads={filteredLeads} onLeadClick={handleLeadClick} />
        </div>
      </div>
    </AppShell>
  );
}
