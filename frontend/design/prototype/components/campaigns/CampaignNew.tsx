"use client";

import { useState } from "react";
import { ArrowLeft, Bot, Users, HandMetal, Info, ExternalLink } from "lucide-react";
import { DashboardShell } from "../layout";

/**
 * Permission mode type
 */
type PermissionMode = "autopilot" | "co_pilot" | "manual";

/**
 * Demo ICP data for prototype
 */
const demoICP = {
  industries: ["Technology", "SaaS", "Fintech"],
  titles: ["CEO", "CTO", "Founder", "VP Engineering"],
  companySize: ["10-50", "51-200"],
  locations: ["Australia", "New Zealand"],
  lastUpdated: "2 days ago",
};

/**
 * Permission mode configuration
 */
const permissionModes: Array<{
  id: PermissionMode;
  name: string;
  description: string;
  icon: typeof Bot;
  features: string[];
}> = [
  {
    id: "autopilot",
    name: "Autopilot",
    description: "Agency OS handles everything automatically",
    icon: Bot,
    features: [
      "Automatic lead sourcing and enrichment",
      "AI-generated personalized content",
      "Automatic sending at optimal times",
      "Smart follow-ups and sequences",
    ],
  },
  {
    id: "co_pilot",
    name: "Co-pilot",
    description: "AI assists, you approve before sending",
    icon: Users,
    features: [
      "AI drafts all content for review",
      "One-click approve or edit",
      "Batch approval for efficiency",
      "Full control over messaging",
    ],
  },
  {
    id: "manual",
    name: "Manual",
    description: "Full control over every action",
    icon: HandMetal,
    features: [
      "Manual lead selection",
      "Write all content yourself",
      "Schedule sends manually",
      "Complete customization",
    ],
  },
];

/**
 * CampaignNew - New campaign creation form
 *
 * Features:
 * - Campaign name input
 * - Description textarea
 * - Permission mode selector (Autopilot/Co-pilot/Manual)
 * - ICP inheritance display with link to edit
 * - Create button
 *
 * Uses DashboardShell for layout.
 */
export function CampaignNew() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [permissionMode, setPermissionMode] = useState<PermissionMode>("autopilot");
  const [isCreating, setIsCreating] = useState(false);

  const selectedMode = permissionModes.find((m) => m.id === permissionMode);

  const handleCreate = () => {
    setIsCreating(true);
    // Simulate API call
    setTimeout(() => {
      setIsCreating(false);
      console.log("Campaign created:", { name, description, permissionMode });
    }, 2000);
  };

  const isValid = name.trim().length > 0;

  return (
    <DashboardShell title="New Campaign" activePath="/campaigns">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Back Button */}
        <button className="flex items-center gap-2 text-sm font-medium text-[#64748B] hover:text-[#1E293B] transition-colors">
          <ArrowLeft className="h-4 w-4" />
          Back to Campaigns
        </button>

        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Create New Campaign</h1>
          <p className="text-[#64748B] mt-1">
            Set up a new outreach campaign for your target audience
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
          <div className="p-6 space-y-6">
            {/* Campaign Name */}
            <div>
              <label
                htmlFor="campaign-name"
                className="block text-sm font-medium text-[#1E293B] mb-2"
              >
                Campaign Name <span className="text-[#EF4444]">*</span>
              </label>
              <input
                id="campaign-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Tech Decision Makers Q1 2026"
                className="w-full px-4 py-2 bg-white border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent transition-all"
              />
              <p className="mt-1.5 text-xs text-[#94A3B8]">
                Choose a descriptive name to identify this campaign
              </p>
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="campaign-description"
                className="block text-sm font-medium text-[#1E293B] mb-2"
              >
                Description
              </label>
              <textarea
                id="campaign-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the campaign goals and target audience..."
                rows={3}
                className="w-full px-4 py-2 bg-white border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent transition-all resize-none"
              />
            </div>

            {/* Permission Mode */}
            <div>
              <label className="block text-sm font-medium text-[#1E293B] mb-3">
                Permission Mode
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {permissionModes.map((mode) => {
                  const Icon = mode.icon;
                  const isSelected = permissionMode === mode.id;

                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => setPermissionMode(mode.id)}
                      className={`p-4 rounded-xl border-2 text-left transition-all ${
                        isSelected
                          ? "border-[#3B82F6] bg-[#EFF6FF]"
                          : "border-[#E2E8F0] hover:border-[#94A3B8] bg-white"
                      }`}
                    >
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${
                          isSelected
                            ? "bg-[#3B82F6] text-white"
                            : "bg-[#F1F5F9] text-[#64748B]"
                        }`}
                      >
                        <Icon className="h-5 w-5" />
                      </div>
                      <h3
                        className={`font-semibold mb-1 ${
                          isSelected ? "text-[#1E293B]" : "text-[#64748B]"
                        }`}
                      >
                        {mode.name}
                      </h3>
                      <p className="text-xs text-[#94A3B8]">{mode.description}</p>
                    </button>
                  );
                })}
              </div>

              {/* Selected Mode Features */}
              {selectedMode && (
                <div className="mt-4 p-4 bg-[#F8FAFC] rounded-lg border border-[#E2E8F0]">
                  <h4 className="text-sm font-medium text-[#1E293B] mb-2">
                    {selectedMode.name} Features:
                  </h4>
                  <ul className="space-y-1.5">
                    {selectedMode.features.map((feature, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-sm text-[#64748B]"
                      >
                        <span className="text-[#3B82F6] mt-0.5">-</span>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ICP Inheritance Card */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
          <div className="px-6 py-4 border-b border-[#E2E8F0]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
                  Target Settings (ICP)
                </h3>
                <div className="group relative">
                  <Info className="h-4 w-4 text-[#94A3B8] cursor-help" />
                  <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block w-64 p-3 bg-[#1E293B] text-white text-xs rounded-lg shadow-lg z-10">
                    Campaign inherits your ICP settings. Edit in Settings to update all campaigns.
                  </div>
                </div>
              </div>
              <button className="flex items-center gap-1.5 text-sm font-medium text-[#3B82F6] hover:text-[#2563EB] transition-colors">
                <ExternalLink className="h-4 w-4" />
                Edit ICP
              </button>
            </div>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 gap-4">
              {/* Industries */}
              <div>
                <span className="text-xs font-medium text-[#94A3B8] uppercase tracking-wider block mb-2">
                  Industries
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {demoICP.industries.map((industry) => (
                    <span
                      key={industry}
                      className="px-2 py-1 bg-[#F1F5F9] text-[#475569] text-xs rounded-md"
                    >
                      {industry}
                    </span>
                  ))}
                </div>
              </div>

              {/* Titles */}
              <div>
                <span className="text-xs font-medium text-[#94A3B8] uppercase tracking-wider block mb-2">
                  Titles
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {demoICP.titles.map((title) => (
                    <span
                      key={title}
                      className="px-2 py-1 bg-[#F1F5F9] text-[#475569] text-xs rounded-md"
                    >
                      {title}
                    </span>
                  ))}
                </div>
              </div>

              {/* Company Size */}
              <div>
                <span className="text-xs font-medium text-[#94A3B8] uppercase tracking-wider block mb-2">
                  Company Size
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {demoICP.companySize.map((size) => (
                    <span
                      key={size}
                      className="px-2 py-1 bg-[#F1F5F9] text-[#475569] text-xs rounded-md"
                    >
                      {size}
                    </span>
                  ))}
                </div>
              </div>

              {/* Locations */}
              <div>
                <span className="text-xs font-medium text-[#94A3B8] uppercase tracking-wider block mb-2">
                  Locations
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {demoICP.locations.map((location) => (
                    <span
                      key={location}
                      className="px-2 py-1 bg-[#F1F5F9] text-[#475569] text-xs rounded-md"
                    >
                      {location}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <p className="mt-4 text-xs text-[#94A3B8]">
              Last updated {demoICP.lastUpdated}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4">
          <button className="px-4 py-2 text-sm font-medium text-[#64748B] hover:text-[#1E293B] hover:bg-[#F8FAFC] rounded-lg transition-colors">
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!isValid || isCreating}
            className="px-6 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating ? "Creating..." : "Create Campaign"}
          </button>
        </div>
      </div>
    </DashboardShell>
  );
}

export default CampaignNew;
