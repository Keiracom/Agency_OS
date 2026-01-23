"use client";

import { useState } from "react";
import { Search, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { DashboardShell } from "../layout";
import { ALSTierBadge, type ALSTier } from "./ALSTierBadge";
import { LeadBulkActions } from "./LeadBulkActions";

/**
 * Demo lead data type
 */
interface DemoLead {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  company: string;
  title: string;
  industry: string;
  tier: ALSTier;
  status: string;
}

/**
 * Demo data - static leads
 */
const demoLeads: DemoLead[] = [
  {
    id: "1",
    firstName: "Sarah",
    lastName: "Chen",
    email: "sarah@techcorp.io",
    company: "TechCorp",
    title: "VP of Engineering",
    industry: "Technology",
    tier: "hot",
    status: "In Sequence",
  },
  {
    id: "2",
    firstName: "Mike",
    lastName: "Johnson",
    email: "mike@startupxyz.co",
    company: "StartupXYZ",
    title: "CTO",
    industry: "SaaS",
    tier: "hot",
    status: "Scored",
  },
  {
    id: "3",
    firstName: "Lisa",
    lastName: "Park",
    email: "lisa@acme.com",
    company: "Acme Inc",
    title: "Director of Operations",
    industry: "Finance",
    tier: "warm",
    status: "In Sequence",
  },
  {
    id: "4",
    firstName: "James",
    lastName: "Wilson",
    email: "james@globaltech.com",
    company: "GlobalTech",
    title: "Engineering Manager",
    industry: "Technology",
    tier: "warm",
    status: "Enriched",
  },
  {
    id: "5",
    firstName: "Emily",
    lastName: "Brown",
    email: "emily@innovate.io",
    company: "Innovate Labs",
    title: "Product Director",
    industry: "Healthcare",
    tier: "warm",
    status: "Scored",
  },
  {
    id: "6",
    firstName: "David",
    lastName: "Lee",
    email: "david@nextstep.co",
    company: "NextStep",
    title: "VP Product",
    industry: "E-commerce",
    tier: "cool",
    status: "In Sequence",
  },
  {
    id: "7",
    firstName: "Anna",
    lastName: "Martinez",
    email: "anna@cloudware.com",
    company: "CloudWare",
    title: "IT Director",
    industry: "Cloud Computing",
    tier: "cool",
    status: "Enriched",
  },
  {
    id: "8",
    firstName: "Chris",
    lastName: "Taylor",
    email: "chris@dataprime.io",
    company: "DataPrime",
    title: "Data Lead",
    industry: "Analytics",
    tier: "cool",
    status: "New",
  },
  {
    id: "9",
    firstName: "Rachel",
    lastName: "Kim",
    email: "rachel@buildright.com",
    company: "BuildRight",
    title: "Operations Manager",
    industry: "Construction",
    tier: "cold",
    status: "Enriched",
  },
  {
    id: "10",
    firstName: "Tom",
    lastName: "Harris",
    email: "tom@finserve.co",
    company: "FinServe",
    title: "Project Manager",
    industry: "Financial Services",
    tier: "cold",
    status: "New",
  },
  {
    id: "11",
    firstName: "Jennifer",
    lastName: "White",
    email: "jennifer@oldcorp.com",
    company: "OldCorp",
    title: "Account Manager",
    industry: "Manufacturing",
    tier: "dead",
    status: "Bounced",
  },
  {
    id: "12",
    firstName: "Kevin",
    lastName: "Moore",
    email: "kevin@legacy.io",
    company: "Legacy Systems",
    title: "Consultant",
    industry: "Consulting",
    tier: "dead",
    status: "Unsubscribed",
  },
];

/**
 * Tier counts for filter cards
 */
const tierCounts = {
  hot: 23,
  warm: 45,
  cool: 78,
  cold: 34,
  dead: 12,
};

/**
 * Tier card configuration
 */
const tierCardConfig: Record<ALSTier, { label: string; bgHover: string }> = {
  hot: { label: "Hot", bgHover: "hover:bg-[#FEE2E2]" },
  warm: { label: "Warm", bgHover: "hover:bg-[#FFEDD5]" },
  cool: { label: "Cool", bgHover: "hover:bg-[#DBEAFE]" },
  cold: { label: "Cold", bgHover: "hover:bg-[#F3F4F6]" },
  dead: { label: "Dead", bgHover: "hover:bg-[#E5E7EB]" },
};

/**
 * LeadList props
 */
export interface LeadListProps {
  /** Handler for navigating to lead detail */
  onLeadClick?: (leadId: string) => void;
  /** Handler for navigation */
  onNavigate?: (path: string) => void;
}

/**
 * LeadList - Full leads list page component
 *
 * Features:
 * - Search bar
 * - 5 tier filter cards with counts
 * - Lead table with name, company, tier badge, status
 * - Row selection with checkboxes
 * - Pagination
 * - Bulk actions bar
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Content background: #F8FAFC
 * - Card background: #FFFFFF
 * - Card border: #E2E8F0
 *
 * Usage:
 * ```tsx
 * <LeadList onLeadClick={(id) => router.push(`/leads/${id}`)} />
 * ```
 */
export function LeadList({ onLeadClick, onNavigate }: LeadListProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<ALSTier | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Filter leads
  const filteredLeads = demoLeads.filter((lead) => {
    const matchesSearch =
      searchQuery === "" ||
      `${lead.firstName} ${lead.lastName}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.company.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesTier = selectedTier === null || lead.tier === selectedTier;

    return matchesSearch && matchesTier;
  });

  // Pagination
  const totalPages = Math.ceil(filteredLeads.length / pageSize);
  const paginatedLeads = filteredLeads.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Selection handlers
  const toggleSelection = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const toggleAllSelection = () => {
    if (selectedIds.length === paginatedLeads.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(paginatedLeads.map((l) => l.id));
    }
  };

  return (
    <DashboardShell
      title="Leads"
      activePath="/leads"
      onNavigate={onNavigate}
      userName="Acme Agency"
    >
      <div className="space-y-6">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[#94A3B8]" />
          <input
            type="text"
            placeholder="Search by name, email, company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-white border border-[#E2E8F0] rounded-xl text-sm text-[#1E293B] placeholder:text-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
          />
        </div>

        {/* Tier Filter Cards */}
        <div className="grid grid-cols-5 gap-4">
          {(Object.keys(tierCardConfig) as ALSTier[]).map((tier) => {
            const config = tierCardConfig[tier];
            const isSelected = selectedTier === tier;

            return (
              <button
                key={tier}
                onClick={() => setSelectedTier(isSelected ? null : tier)}
                className={`p-4 bg-white rounded-xl border transition-all duration-200 ${
                  isSelected
                    ? "border-[#3B82F6] ring-2 ring-[#3B82F6]/20"
                    : `border-[#E2E8F0] ${config.bgHover}`
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <ALSTierBadge tier={tier} size="sm" />
                </div>
                <div className="text-2xl font-bold text-[#1E293B]">
                  {tierCounts[tier]}
                </div>
              </button>
            );
          })}
        </div>

        {/* Lead Table */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
          {/* Table Header */}
          <div className="px-6 py-4 border-b border-[#E2E8F0] flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              {selectedTier ? `${tierCardConfig[selectedTier].label} Leads` : "All Leads"}
            </h2>
            <span className="text-sm text-[#94A3B8]">
              {filteredLeads.length} total leads
            </span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#E2E8F0]">
                  <th className="px-6 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={
                        paginatedLeads.length > 0 &&
                        selectedIds.length === paginatedLeads.length
                      }
                      onChange={toggleAllSelection}
                      className="h-4 w-4 rounded border-[#D1D5DB] text-[#3B82F6] focus:ring-[#3B82F6]"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#64748B] uppercase tracking-wider">
                    Lead
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#64748B] uppercase tracking-wider">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#64748B] uppercase tracking-wider">
                    Tier
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#64748B] uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-[#64748B] uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedLeads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="border-b border-[#E2E8F0] hover:bg-[#F8FAFC] transition-colors"
                  >
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(lead.id)}
                        onChange={() => toggleSelection(lead.id)}
                        className="h-4 w-4 rounded border-[#D1D5DB] text-[#3B82F6] focus:ring-[#3B82F6]"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-[#1E293B]">
                          {lead.firstName} {lead.lastName}
                        </p>
                        <p className="text-xs text-[#64748B]">{lead.email}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm text-[#1E293B]">{lead.company}</p>
                        <p className="text-xs text-[#64748B]">{lead.industry}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <ALSTierBadge tier={lead.tier} />
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-[#64748B]">{lead.status}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => onLeadClick?.(lead.id)}
                        className="inline-flex items-center gap-1 text-sm text-[#3B82F6] hover:text-[#2563EB] transition-colors"
                      >
                        View
                        <ExternalLink className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="px-6 py-4 border-t border-[#E2E8F0] flex items-center justify-between">
            <span className="text-sm text-[#64748B]">
              Page {currentPage} of {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-[#64748B] hover:text-[#1E293B] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-[#64748B] hover:text-[#1E293B] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      <LeadBulkActions
        selectedCount={selectedIds.length}
        onEnrich={() => console.log("Bulk enrich:", selectedIds)}
        onPause={() => console.log("Bulk pause:", selectedIds)}
        onArchive={() => console.log("Bulk archive:", selectedIds)}
        onClear={() => setSelectedIds([])}
      />
    </DashboardShell>
  );
}

export default LeadList;
