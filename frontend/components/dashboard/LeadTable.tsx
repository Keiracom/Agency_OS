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
import { LeadDetailModal } from "./LeadDetailModal";

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

// Glass-themed status labels per LEADS.md spec
const statusLabels: Record<LeadStatus, { label: string; style: string }> = {
  new: { label: "New", style: "bg-slate-500/20 text-text-secondary border border-slate-500/20" },
  enriched: { label: "Enriched", style: "bg-bg-elevated/20 text-text-secondary border border-default/20" },
  scored: { label: "Scored", style: "bg-bg-elevated/20 text-text-secondary border border-default/20" },
  in_sequence: { label: "In Sequence", style: "bg-amber/20 text-amber border border-amber/20" },
  converted: { label: "Meeting Booked", style: "bg-amber/20 text-amber border border-amber/20" },
  unsubscribed: { label: "Unsubscribed", style: "bg-slate-500/20 text-text-secondary border border-slate-500/20" },
  bounced: { label: "Bounced", style: "bg-amber/20 text-amber border border-amber/20" },
};

// Glass-themed tier filter cards configuration
const tierFilters: { tier: ALSTier; label: string; color: string; textColor: string }[] = [
  { tier: "hot", label: "High Priority", color: "border-orange-500/40 bg-orange-500/10 backdrop-blur-md", textColor: "text-orange-400" },
  { tier: "warm", label: "Engaged", color: "border-yellow-500/40 bg-yellow-500/10 backdrop-blur-md", textColor: "text-yellow-400" },
  { tier: "cool", label: "Nurturing", color: "border-default/40 bg-bg-elevated/10 backdrop-blur-md", textColor: "text-text-secondary" },
  { tier: "cold", label: "Low Activity", color: "border-slate-400/40 bg-bg-surface backdrop-blur-md", textColor: "text-text-secondary" },
  { tier: "dead", label: "Inactive", color: "border-slate-500/40 bg-bg-elevated/10 backdrop-blur-md", textColor: "text-text-muted" },
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
      className={`p-4 rounded-lg border text-left transition-all ${color} ${
        isSelected ? "ring-2 ring-amber/50 ring-offset-2 ring-offset-transparent" : "hover:bg-bg-surface/5"
      }`}
    >
      <div className={`text-2xl font-bold ${textColor} drop-shadow-sm`}>{count}</div>
      <div className="text-sm text-text-secondary">{label}</div>
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
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Handle row click - open modal or call external handler
  const handleRowClick = (lead: Lead) => {
    if (onLeadClick) {
      onLeadClick(lead);
    } else {
      setSelectedLead(lead);
      setIsModalOpen(true);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedLead(null);
  };

  // Fetch leads with filters
  const { leads, isLoading, error } = useLeads({
    campaign_id: campaignId,
    tier: selectedTier ?? undefined,
    search: searchQuery || undefined,
  });

  // Calculate tier counts
  const tierCounts = useMemo(() => {
    const counts: Record<ALSTier, number> = {
      hot: 0,
      warm: 0,
      cool: 0,
      cold: 0,
      dead: 0,
    };
    // Per-tier counts aggregated from the loaded `leads` array. When
    // pagination is added, swap to GET /api/leads/counts?by=tier so
    // the bar reflects the full dataset, not just the current page.
    leads.forEach((lead) => {
      const tier = lead.propensity_tier ?? "cool";
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
      <div className="bg-bg-void/40 backdrop-blur-md rounded-xl border border-white/10 shadow-lg shadow-black/20 p-8">
        <div className="flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-default border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-bg-void/40 backdrop-blur-md rounded-xl border border-amber/30 shadow-lg shadow-black/20 p-8 text-center">
        <p className="text-amber">Failed to load leads</p>
        <p className="text-sm text-text-secondary mt-1">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header & Search */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-text-primary drop-shadow-sm">Leads</h2>
          <p className="text-sm text-text-secondary">
            {filteredLeads.length} prospects in pipeline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
            <input
              type="text"
              placeholder="Search name, email, company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 pl-9 pr-4 py-2 text-sm bg-bg-surface/10 border border-white/20 rounded-lg text-text-primary placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber/50 backdrop-blur-sm"
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

      {/* Lead Table - Glass themed */}
      <div className="bg-bg-void/40 backdrop-blur-md rounded-xl border border-white/10 shadow-lg shadow-black/20 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-xs text-text-secondary bg-bg-surface/5">
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
                className="border-b border-white/5 hover:bg-bg-surface/5 cursor-pointer transition-colors"
                onClick={() => handleRowClick(lead)}
              >
                <td className="p-4">
                  <div className="font-medium text-text-primary">
                    {lead.first_name} {lead.last_name}
                  </div>
                  <div className="text-xs text-text-secondary">{lead.email}</div>
                </td>
                <td className="p-4">
                  <div className="text-text-secondary">{lead.company}</div>
                  <div className="text-xs text-text-muted">
                    {lead.organization_industry}
                  </div>
                </td>
                <td className="p-4">
                  {/* Per LEADS.md: Show tier label, NOT raw score */}
                  <TierBadge tier={lead.propensity_tier ?? "cool"} />
                </td>
                <td className="p-4">
                  <StatusBadge status={lead.status} />
                </td>
                {!compact && (
                  <td className="p-4 text-text-secondary text-xs">
                    {lead.updated_at
                      ? new Date(lead.updated_at).toLocaleDateString()
                      : "—"}
                  </td>
                )}
                <td className="p-4 text-right">
                  <button className="text-text-secondary hover:text-amber-light text-xs font-medium transition-colors">
                    View
                  </button>
                </td>
              </tr>
            ))}
            {filteredLeads.length === 0 && (
              <tr>
                <td
                  colSpan={compact ? 5 : 6}
                  className="p-8 text-center text-text-secondary"
                >
                  No leads found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Lead Detail Modal */}
      <LeadDetailModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        lead={selectedLead ? {
          id: selectedLead.id,
          firstName: selectedLead.first_name ?? "",
          lastName: selectedLead.last_name ?? "",
          email: selectedLead.email,
          phone: selectedLead.phone ?? undefined,
          linkedinUrl: selectedLead.linkedin_url ?? undefined,
          title: selectedLead.title ?? "Unknown",
          company: {
            id: selectedLead.id,
            name: selectedLead.company ?? "Unknown Company",
            domain: selectedLead.domain ?? "",
            logoEmoji: "",
            employees: selectedLead.organization_employee_count?.toString() ?? "Unknown",
            industry: selectedLead.organization_industry ?? "Unknown",
            estimatedRevenue: "Unknown",
            location: selectedLead.organization_country ?? "Unknown",
            recentIntelligence: [],
          },
          score: selectedLead.propensity_score ?? 50,
          tier: selectedLead.propensity_tier ?? "cool",
          whyHot: [],
          engagementProfile: {
            dataQuality: { label: "Data Quality", value: selectedLead.als_data_quality ?? 15, maxValue: 20, level: "medium" as const },
            authority: { label: "Authority (Title)", value: selectedLead.als_authority ?? 15, maxValue: 25, level: "medium" as const },
            companyFit: { label: "Company Fit", value: selectedLead.als_company_fit ?? 15, maxValue: 25, level: "medium" as const },
            timing: { label: "Timing", value: selectedLead.als_timing ?? 10, maxValue: 15, level: "medium" as const },
            engagement: { label: "Engagement", value: 10, maxValue: 20, level: "medium" as const },
          },
          timeline: [],
          callLogs: [],
          emailThread: [],
          linkedinThread: [],
          notes: [],
          createdAt: selectedLead.created_at ?? new Date().toISOString(),
          updatedAt: selectedLead.updated_at ?? new Date().toISOString(),
        } : null}
      />
    </div>
  );
}

export default LeadTable;
