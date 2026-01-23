"use client";

import { useState } from "react";
import {
  Building2,
  Users,
  Target,
  Sparkles,
  RefreshCw,
  Clock,
} from "lucide-react";

/**
 * ICP profile data
 */
export interface ICPProfile {
  targetIndustries: string;
  targetCompanySizes: string;
  targetLocations: string;
  revenueRangeMin: string;
  revenueRangeMax: string;
  targetJobTitles: string;
  keywords: string;
  exclusions: string;
  painPoints: string;
  valuePropositions: string;
  lastExtractedAt: string | null;
}

/**
 * ICPSettingsForm props
 */
export interface ICPSettingsFormProps {
  /** Initial ICP data */
  initialValues?: Partial<ICPProfile>;
  /** Called when form is saved */
  onSave?: (values: ICPProfile) => void;
  /** Called when re-analyze is clicked */
  onReanalyze?: () => void;
  /** Whether re-analyze is in progress */
  isReanalyzing?: boolean;
}

/**
 * Section card wrapper
 */
function SectionCard({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#EFF6FF] rounded-lg">
            <Icon className="h-5 w-5 text-[#3B82F6]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[#1E293B]">{title}</h3>
            <p className="text-xs text-[#64748B] mt-0.5">{description}</p>
          </div>
        </div>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

/**
 * Format extraction timestamp
 */
function formatExtractionDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-AU", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * ICPSettingsForm - Form for configuring Ideal Customer Profile
 *
 * Features:
 * - Target industries input
 * - Company sizes input
 * - Locations input
 * - Revenue range inputs
 * - Job titles input
 * - Keywords input
 * - Exclusions input
 * - Pain points textarea
 * - Value propositions textarea
 * - Re-analyze button
 * - Last extraction timestamp
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Primary: #3B82F6
 * - Input background: #F8FAFC
 * - Border: #E2E8F0
 */
export function ICPSettingsForm({
  initialValues,
  onSave,
  onReanalyze,
  isReanalyzing = false,
}: ICPSettingsFormProps) {
  const [values, setValues] = useState<ICPProfile>({
    targetIndustries: initialValues?.targetIndustries ?? "Technology, SaaS, Fintech",
    targetCompanySizes: initialValues?.targetCompanySizes ?? "10-50, 51-200, 201-500",
    targetLocations: initialValues?.targetLocations ?? "Sydney, Melbourne, Brisbane",
    revenueRangeMin: initialValues?.revenueRangeMin ?? "1000000",
    revenueRangeMax: initialValues?.revenueRangeMax ?? "50000000",
    targetJobTitles: initialValues?.targetJobTitles ?? "CEO, CTO, VP Engineering, Founder",
    keywords: initialValues?.keywords ?? "AI, machine learning, automation, B2B",
    exclusions: initialValues?.exclusions ?? "agency, consulting, freelance",
    painPoints:
      initialValues?.painPoints ??
      "Struggling to scale lead generation\nManual outreach is time-consuming\nLow reply rates from cold outreach",
    valuePropositions:
      initialValues?.valuePropositions ??
      "Automated multi-channel outreach\nAI-powered personalization at scale\nConsistent pipeline of qualified meetings",
    lastExtractedAt: initialValues?.lastExtractedAt ?? "2026-01-20T10:30:00Z",
  });

  const handleSave = () => {
    if (onSave) {
      onSave(values);
    }
  };

  return (
    <div className="space-y-6">
      {/* AI Extracted Badge */}
      {values.lastExtractedAt && (
        <div className="flex items-center justify-between p-4 bg-[#EFF6FF] rounded-xl border border-[#BFDBFE]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white rounded-lg">
              <Sparkles className="h-5 w-5 text-[#3B82F6]" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#1D4ED8]">
                AI-Extracted Profile
              </p>
              <p className="text-xs text-[#3B82F6] flex items-center gap-1 mt-0.5">
                <Clock className="h-3 w-3" />
                Last extracted from your website on{" "}
                {formatExtractionDate(values.lastExtractedAt)}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onReanalyze}
            disabled={isReanalyzing}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-[#3B82F6] rounded-lg text-sm font-medium text-[#3B82F6] hover:bg-[#EFF6FF] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${isReanalyzing ? "animate-spin" : ""}`} />
            {isReanalyzing ? "Analyzing..." : "Re-analyze Website"}
          </button>
        </div>
      )}

      {/* Target Companies */}
      <SectionCard
        icon={Building2}
        title="Target Companies"
        description="Define the types of companies you want to reach"
      >
        <div className="space-y-4">
          {/* Industries */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Industries
            </label>
            <input
              type="text"
              value={values.targetIndustries}
              onChange={(e) => setValues({ ...values, targetIndustries: e.target.value })}
              className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
              placeholder="Technology, SaaS, Healthcare..."
            />
            <p className="text-xs text-[#94A3B8] mt-1">Separate multiple industries with commas</p>
          </div>

          {/* Company Sizes and Locations */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#1E293B] mb-2">
                Company Sizes
              </label>
              <input
                type="text"
                value={values.targetCompanySizes}
                onChange={(e) => setValues({ ...values, targetCompanySizes: e.target.value })}
                className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                placeholder="10-50, 51-200..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#1E293B] mb-2">
                Locations
              </label>
              <input
                type="text"
                value={values.targetLocations}
                onChange={(e) => setValues({ ...values, targetLocations: e.target.value })}
                className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                placeholder="Sydney, Melbourne..."
              />
            </div>
          </div>

          {/* Revenue Range */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#1E293B] mb-2">
                Revenue Min (AUD)
              </label>
              <input
                type="text"
                value={values.revenueRangeMin}
                onChange={(e) => setValues({ ...values, revenueRangeMin: e.target.value })}
                className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                placeholder="1000000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#1E293B] mb-2">
                Revenue Max (AUD)
              </label>
              <input
                type="text"
                value={values.revenueRangeMax}
                onChange={(e) => setValues({ ...values, revenueRangeMax: e.target.value })}
                className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                placeholder="50000000"
              />
            </div>
          </div>
        </div>
      </SectionCard>

      {/* Target Contacts */}
      <SectionCard
        icon={Users}
        title="Target Contacts"
        description="Define the roles you want to reach"
      >
        <div>
          <label className="block text-sm font-medium text-[#1E293B] mb-2">
            Job Titles
          </label>
          <input
            type="text"
            value={values.targetJobTitles}
            onChange={(e) => setValues({ ...values, targetJobTitles: e.target.value })}
            className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
            placeholder="CEO, CTO, VP Engineering..."
          />
          <p className="text-xs text-[#94A3B8] mt-1">Separate multiple titles with commas</p>
        </div>
      </SectionCard>

      {/* Keywords & Exclusions */}
      <SectionCard
        icon={Target}
        title="Keywords & Exclusions"
        description="Refine your targeting with keywords"
      >
        <div className="space-y-4">
          {/* Include Keywords */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Include Keywords
            </label>
            <input
              type="text"
              value={values.keywords}
              onChange={(e) => setValues({ ...values, keywords: e.target.value })}
              className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
              placeholder="AI, automation, B2B..."
            />
            <p className="text-xs text-[#94A3B8] mt-1">
              Companies with these keywords in their profile will be prioritized
            </p>
          </div>

          {/* Exclude Keywords */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Exclude Keywords
            </label>
            <input
              type="text"
              value={values.exclusions}
              onChange={(e) => setValues({ ...values, exclusions: e.target.value })}
              className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
              placeholder="agency, consultant, competitor..."
            />
            <p className="text-xs text-[#94A3B8] mt-1">
              Companies with these keywords will be excluded from targeting
            </p>
          </div>
        </div>
      </SectionCard>

      {/* Messaging Context */}
      <SectionCard
        icon={Sparkles}
        title="Messaging Context"
        description="Help the AI craft better personalized messages"
      >
        <div className="space-y-4">
          {/* Pain Points */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Pain Points
            </label>
            <textarea
              value={values.painPoints}
              onChange={(e) => setValues({ ...values, painPoints: e.target.value })}
              rows={4}
              className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent resize-none"
              placeholder="List the common problems your ideal customers face..."
            />
            <p className="text-xs text-[#94A3B8] mt-1">One pain point per line</p>
          </div>

          {/* Value Propositions */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Value Propositions
            </label>
            <textarea
              value={values.valuePropositions}
              onChange={(e) => setValues({ ...values, valuePropositions: e.target.value })}
              rows={4}
              className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent resize-none"
              placeholder="List how your solution addresses these pain points..."
            />
            <p className="text-xs text-[#94A3B8] mt-1">One value proposition per line</p>
          </div>
        </div>
      </SectionCard>

      {/* Save Button */}
      <div className="flex justify-end gap-3">
        <button
          type="button"
          className="px-6 py-2.5 border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:bg-[#F8FAFC] transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          className="px-6 py-2.5 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
}

export default ICPSettingsForm;
