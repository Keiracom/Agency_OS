/**
 * LeadTable.tsx - Leads Data Table Component
 * Phase: Operation Modular Cockpit
 * 
 * Displays leads with:
 * - Tier badges (client-friendly labels per LEADS.md)
 * - Status filters
 * - Search functionality
 * 
 * Per LEADS.md spec:
 * - NO raw ALS scores shown to clients
 * - Tier labels: Hot → "High Priority", Warm → "Engaged", etc.
 */

"use client";

import { useState, useMemo } from "react";
import { Search } from "lucide-react";
import { useLeads } from "@/hooks/use-leads";
import type { Lead, ALSTier, LeadStatus } from "@/lib/api/types";
import { TierBadge } from "./TierBadge";

// ============================================
// Types
// ============================================

interface LeadTableProps {
  /** Campaign ID to filter leads */
  campaignId?: string;
  /** Enable compact mode */
  compact?: boolean;
  /** Maximum rows to display */
  maxRows?: number;
  /** Callback when lead is clicked */
  onLeadClick?: (lead: Lead) => void;
}

// ============================================
// Configuration
// ============================================

// Client-friendly status labels per LEADS.md spec
const statusLabels: Record<LeadStatus, { label: string; style: string }> = {
  new: { label: "New", style: "bg-slate-100 text-slate-600" },
  enriched: { label: "Enriched", style: "bg-blue-100 text-blue-700" },
  scored: { label: "Scored", style: "bg-blue-100 text-blue-700" },
  in_sequence: { label: "In Sequence", style: "bg-purple-100 text-purple-700" },
  converted: { label: "Meeting Booked", style: "bg-emerald-100 text-emerald-700" },
  unsubscribed: { label: "Unsubscribed", style: "bg-slate-100 text-slate-500" },
  bounced: { label: "Bounced", style: "bg-red-100 text-red-600" },
};

// Tier filter cards configuration
const tierFilters: { tier: ALSTier; label: string; color: string; textColor: string }[] = [
  { tier: "hot", label: "High Priority", color: "border-orange-500 bg-orange-50", textColor: "text-orange-700" },
  { tier: "warm", label: "Engaged", color: "border-yellow-500 bg-yellow-50", textColor: "text-yellow-700" },
  { tier: "cool", label: "Nurturing", color: "border-blue-500 bg-blue-50", textColor: "text-blue-700" },
  { tier: "cold", label: "Low Activity", color: "border-slate-400 bg-slate-50", textColor: "text-slate-600" },
  { tier: "dead", label: "Inactive", color: "border-slate-300 bg-slate-100", textColor: "text-slate-500" },
];

// ============================================
// Helper Components
// ============================================

function StatusBadge({ status }: { status: LeadStatus }) {
  const config = statusLabels[status] ?? statusLabels.new;
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${config.style}`}>
      {config.label}
    </span>
  );
}

function TierFilterCard({
  tier,
  label,
  count,
  color,
  textColor,
  isSelected,
  onClick,
}: {
  tier: ALSTier;
  label: string;
  count: number;
  color: string;
  textColor: string;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`p-4 rounded-lg border-2 text-left transition-all ${color} ${
        isSelected ? "ring-2 ring-blue-500 ring-offset-2" : "hover:shadow-md"
      }`}
    >
      <div className={`text-2xl font-bold ${textColor}`}>{count}</div>
      <div className="text-sm text-slate-600">{label}</div>
    </button>
  );
}

// ============================================
// LeadTable Component
// ============================================

export function LeadTable({
  campaignId,
  compact = false,
  maxRows,
  onLeadClick,
}: LeadTableProps) {
  const [selectedTier, setSelectedTier] = useState<ALSTier | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Fetch leads with filters
  const { data: leadsResponse, isLoading, error } = useLeads({
    campaign_id: campaignId,
    tier: selectedTier ?? undefined,
    search: searchQuery || undefined,
  });

  const leads = leadsResponse?.items ?? [];

  // Calculate tier counts
  const tierCounts = useMemo(() => {
    const counts: Record<ALSTier, number> = {
      hot: 0,
      warm: 0,
      cool: 0,
      cold: 0,
      dead: 0,
    };
    // If we have unfiltered data, calculate counts
    // For now, use placeholder counts - in production, this would come from API aggregation
    leads.forEach((lead) => {
      const tier = lead.als_tier ?? "cool";
      counts[tier]++;
    });
    return counts;
  }, [leads]);

  // Filter leads
  const filteredLeads = useMemo(() => {
    let result = leads;
    
    if (maxRows) {
      result = result.slice(0, maxRows);
    }
    
    return result;
  }, [leads, maxRows]);

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-8">
        <div className="flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-white rounded-xl border border-red-200 shadow-lg p-8 text-center">
        <p className="text-red-600">Failed to load leads</p>
        <p className="text-sm text-slate-500 mt-1">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header & Search */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Leads</h2>
          <p className="text-sm text-slate-500">
            {filteredLeads.length} prospects in pipeline
          </p>
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

      {/* Tier Filter Cards - Per LEADS.md spec */}
      {!compact && (
        <div className="grid grid-cols-5 gap-4">
          {tierFilters.map((item) => (
            <TierFilterCard
              key={item.tier}
              tier={item.tier}
              label={item.label}
              count={tierCounts[item.tier]}
              color={item.color}
              textColor={item.textColor}
              isSelected={selectedTier === item.tier}
              onClick={() =>
                setSelectedTier(selectedTier === item.tier ? null : item.tier)
              }
            />
          ))}
        </div>
      )}

      {/* Lead Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-xs text-slate-500">
              <th className="text-left p-4 font-medium">Lead</th>
              <th className="text-left p-4 font-medium">Company</th>
              <th className="text-left p-4 font-medium">Priority</th>
              <th className="text-left p-4 font-medium">Status</th>
              {!compact && (
                <th className="text-left p-4 font-medium">Last Activity</th>
              )}
              <th className="text-right p-4 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {filteredLeads.map((lead) => (
              <tr
                key={lead.id}
                className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer"
                onClick={() => onLeadClick?.(lead)}
              >
                <td className="p-4">
                  <div className="font-medium text-slate-900">
                    {lead.first_name} {lead.last_name}
                  </div>
                  <div className="text-xs text-slate-500">{lead.email}</div>
                </td>
                <td className="p-4">
                  <div className="text-slate-900">{lead.company}</div>
                  <div className="text-xs text-slate-500">
                    {lead.organization_industry}
                  </div>
                </td>
                <td className="p-4">
                  {/* Per LEADS.md: Show tier label, NOT raw score */}
                  <TierBadge tier={lead.als_tier ?? "cool"} />
                </td>
                <td className="p-4">
                  <StatusBadge status={lead.status} />
                </td>
                {!compact && (
                  <td className="p-4 text-slate-500 text-xs">
                    {lead.updated_at
                      ? new Date(lead.updated_at).toLocaleDateString()
                      : "—"}
                  </td>
                )}
                <td className="p-4 text-right">
                  <button className="text-blue-600 hover:text-blue-700 text-xs font-medium">
                    View
                  </button>
                </td>
              </tr>
            ))}
            {filteredLeads.length === 0 && (
              <tr>
                <td
                  colSpan={compact ? 5 : 6}
                  className="p-8 text-center text-slate-500"
                >
                  No leads found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default LeadTable;
