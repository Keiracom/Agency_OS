"use client";

/**
 * FILE: frontend/app/dashboard/campaigns/new/page.tsx
 * PURPOSE: New Campaign Wizard - Multi-step form to create a campaign
 * SPRINT: Dashboard Sprint 3a - Campaign Management + Step 5/8 Targeting Filters
 * SSOT: frontend/design/html-prototypes/campaign-new-v2.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Calendar,
  Eye,
  Heart,
  Clock,
  Sparkles,
  Wand2,
} from "lucide-react";
import { TargetingFilters, TargetingFiltersData } from "@/components/campaigns/TargetingFilters";
import { useICPAutoPopulate } from "@/hooks/useICPAutoPopulate";

// Wizard steps
const STEPS = [
  { id: 1, label: "Basics" },
  { id: 2, label: "Audience" },
  { id: 3, label: "Channels" },
  { id: 4, label: "Messaging" },
  { id: 5, label: "Review" },
];

// Campaign goals
const GOALS = [
  {
    id: "meetings",
    icon: Calendar,
    name: "Book Meetings",
    description: "Drive qualified demos and discovery calls",
  },
  {
    id: "awareness",
    icon: Eye,
    name: "Build Awareness",
    description: "Get your brand in front of ideal customers",
  },
  {
    id: "nurture",
    icon: Heart,
    name: "Nurture Leads",
    description: "Warm up cold leads over time",
  },
];

// Industry options
const INDUSTRIES = [
  "Technology", "SaaS", "Fintech", "Healthcare", "E-commerce",
  "Manufacturing", "Professional Services", "Real Estate", "Education", "Media"
];

// Company size options
const COMPANY_SIZES = [
  { id: "1-10", label: "1-10 employees" },
  { id: "11-50", label: "11-50 employees" },
  { id: "51-200", label: "51-200 employees" },
  { id: "201-500", label: "201-500 employees" },
  { id: "500+", label: "500+ employees" },
];

// Location options
const LOCATIONS = [
  "Australia", "New Zealand", "Singapore", "United States", 
  "United Kingdom", "Canada", "Germany", "Global"
];

export default function NewCampaignPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    name: "",
    goal: "meetings",
    targetMeetings: 20,
    startDate: "",
    endDate: "",
    ongoing: false,
    // Step 2: Audience targeting
    targetIndustries: [] as string[],
    targetCompanySizes: [] as string[],
    targetLocations: [] as string[],
    targeting: {
      alsTiers: ["Hot", "Warm"] as string[],
      hiringOnly: false,
      revenueMinAud: null as number | null,
      revenueMaxAud: null as number | null,
      fundingStages: [] as string[],
    } as TargetingFiltersData,
    // ICP tracking
    icpPrefilled: false,
    icpSourceProfileId: null as string | null,
  });
  
  // TODO: Replace with actual client ID from session/context
  const clientId = "demo-client-id";
  const { suggestion: icpSuggestion, loading: icpLoading, applyToForm } = useICPAutoPopulate(clientId);
  const [icpApplied, setIcpApplied] = useState(false);

  // Auto-apply ICP suggestion when available and not yet applied
  useEffect(() => {
    if (icpSuggestion && !icpApplied && currentStep === 2) {
      applyToForm(setFormData);
      setIcpApplied(true);
    }
  }, [icpSuggestion, icpApplied, currentStep, applyToForm]);

  const handleNext = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <AppShell pageTitle="New Campaign">
      <div className="max-w-3xl mx-auto">
        {/* Breadcrumb */}
        <div className="flex items-center gap-3 text-sm mb-6">
          <Link
            href="/dashboard/campaigns"
            className="flex items-center gap-2 text-ink-3 hover:text-ink transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <span className="text-border-strong">·</span>
          <span className="text-ink-3">Campaigns</span>
          <span className="text-border-strong">/</span>
          <span className="text-ink font-medium">New Campaign</span>
        </div>

        {/* Step Progress Indicator */}
        <div className="glass-surface rounded-xl p-6 mb-6">
          <div className="flex items-center justify-center">
            {STEPS.map((step, idx) => (
              <div key={step.id} className="flex items-center">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                      currentStep > step.id
                        ? "bg-status-success text-ink"
                        : currentStep === step.id
                        ? "gradient-premium text-ink shadow-lg"
                        : "bg-bg-elevated text-ink-3 border-2 border-rule-strong"
                    }`}
                    style={
                      currentStep === step.id
                        ? { boxShadow: "0 0 20px rgba(212, 149, 106, 0.4)" }
                        : undefined
                    }
                  >
                    {currentStep > step.id ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      step.id
                    )}
                  </div>
                  <span
                    className={`text-sm font-medium transition-colors ${
                      currentStep === step.id
                        ? "text-ink"
                        : currentStep > step.id
                        ? "text-status-success"
                        : "text-ink-3"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`w-16 h-0.5 mx-4 transition-colors ${
                      currentStep > step.id ? "bg-status-success" : "bg-border-default"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="glass-surface rounded-xl overflow-hidden">
          {/* Step 1: Campaign Basics */}
          {currentStep === 1 && (
            <div className="animate-fade-in">
              <div className="p-6 border-b border-rule">
                <h2 className="text-xl font-serif font-semibold text-ink">
                  Campaign Basics
                </h2>
                <p className="text-sm text-ink-3 mt-1">
                  Set the foundation for your outreach campaign
                </p>
              </div>
              <div className="p-6 space-y-8">
                {/* Campaign Name */}
                <div>
                  <label className="block text-sm font-medium text-ink mb-2">
                    Campaign Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Q1 SaaS Founder Blitz"
                    className="w-full px-4 py-3 rounded-lg text-sm bg-bg-panel border border-rule-strong text-ink placeholder-text-muted focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all"
                  />
                </div>

                {/* Campaign Goal */}
                <div>
                  <label className="block text-sm font-medium text-ink mb-3">
                    Campaign Goal
                  </label>
                  <div className="grid grid-cols-3 gap-4">
                    {GOALS.map((goal) => {
                      const Icon = goal.icon;
                      const isSelected = formData.goal === goal.id;
                      return (
                        <button
                          key={goal.id}
                          onClick={() => setFormData({ ...formData, goal: goal.id })}
                          className={`p-5 rounded-xl text-center transition-all ${
                            isSelected
                              ? "bg-accent-primary/10 border-2 border-accent-primary"
                              : "bg-bg-panel border-2 border-rule-strong hover:border-border-strong"
                          }`}
                        >
                          <div
                            className={`w-12 h-12 rounded-xl mx-auto mb-3 flex items-center justify-center transition-colors ${
                              isSelected
                                ? "gradient-premium"
                                : "bg-bg-elevated"
                            }`}
                          >
                            <Icon
                              className={`w-6 h-6 ${
                                isSelected ? "text-ink" : "text-ink-3"
                              }`}
                            />
                          </div>
                          <p className="text-sm font-semibold text-ink mb-1">
                            {goal.name}
                          </p>
                          <p className="text-xs text-ink-3">{goal.description}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Target Monthly Meetings */}
                <div>
                  <label className="block text-sm font-medium text-ink mb-2">
                    Target Monthly Meetings
                  </label>
                  <input
                    type="number"
                    value={formData.targetMeetings}
                    onChange={(e) =>
                      setFormData({ ...formData, targetMeetings: parseInt(e.target.value) || 0 })
                    }
                    min={1}
                    className="w-full px-4 py-3 rounded-lg text-sm bg-bg-panel border border-rule-strong text-ink font-mono focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all"
                  />
                  <p className="text-xs text-ink-3 mt-1.5">
                    Based on industry benchmarks, you'll need ~{Math.round(formData.targetMeetings * 50)} leads
                  </p>
                </div>

                {/* Date Range */}
                <div>
                  <label className="block text-sm font-medium text-ink mb-2">
                    Campaign Duration
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-ink-3 mb-1.5">Start Date</label>
                      <input
                        type="date"
                        value={formData.startDate}
                        onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg text-sm bg-bg-panel border border-rule-strong text-ink focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-ink-3 mb-1.5">End Date</label>
                      <div className="relative">
                        <input
                          type="date"
                          value={formData.endDate}
                          onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                          disabled={formData.ongoing}
                          className="w-full px-4 py-3 rounded-lg text-sm bg-bg-panel border border-rule-strong text-ink focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        />
                      </div>
                    </div>
                  </div>
                  <label className="flex items-center gap-2 mt-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.ongoing}
                      onChange={(e) => setFormData({ ...formData, ongoing: e.target.checked })}
                      className="w-4 h-4 rounded border-rule-strong bg-bg-panel text-accent-primary focus:ring-accent-primary/20"
                    />
                    <span className="text-sm text-ink-2 flex items-center gap-1.5">
                      <Clock className="w-4 h-4" />
                      Run indefinitely (no end date)
                    </span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Audience Targeting */}
          {currentStep === 2 && (
            <div className="animate-fade-in">
              <div className="p-6 border-b border-rule">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-serif font-semibold text-ink">
                      Target Audience
                    </h2>
                    <p className="text-sm text-ink-3 mt-1">
                      Define who you want to reach with this campaign
                    </p>
                  </div>
                  {icpSuggestion && (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-primary/10 border border-accent-primary/30">
                      <Wand2 className="w-4 h-4 text-accent-primary" />
                      <span className="text-sm font-medium text-accent-primary">
                        Pre-filled from your ICP
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="p-6 space-y-8">
                {/* ICP Suggestion Banner */}
                {icpSuggestion && formData.icpPrefilled && (
                  <div className="p-4 rounded-xl bg-gradient-to-r from-accent-primary/10 to-accent-secondary/10 border border-accent-primary/20">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-lg bg-accent-primary/20 flex items-center justify-center shrink-0">
                        <Sparkles className="w-5 h-5 text-accent-primary" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-ink">
                          Suggested by Maya based on your ICP
                        </h4>
                        <p className="text-xs text-ink-3 mt-1">
                          We've pre-filled targeting based on your agency profile. 
                          Feel free to adjust any settings below.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Target Industries */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <label className="block text-sm font-medium text-ink">
                      Target Industries
                    </label>
                    {(icpSuggestion?.targetIndustries?.length ?? 0) > 0 && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-primary/20 text-accent-primary">
                        <Sparkles className="w-3 h-3" />
                        Suggested
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {INDUSTRIES.map((industry) => {
                      const isSelected = formData.targetIndustries.includes(industry);
                      return (
                        <button
                          key={industry}
                          onClick={() => {
                            setFormData((prev) => ({
                              ...prev,
                              targetIndustries: isSelected
                                ? prev.targetIndustries.filter((i) => i !== industry)
                                : [...prev.targetIndustries, industry],
                            }));
                          }}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                            isSelected
                              ? "bg-accent-primary/20 text-accent-primary border border-accent-primary/50"
                              : "bg-bg-panel text-ink-2 border border-rule-strong hover:border-border-strong"
                          }`}
                        >
                          {industry}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Target Locations */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <label className="block text-sm font-medium text-ink">
                      Geographic Focus
                    </label>
                    {(icpSuggestion?.targetLocations?.length ?? 0) > 0 && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-primary/20 text-accent-primary">
                        <Sparkles className="w-3 h-3" />
                        Suggested
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {LOCATIONS.map((location) => {
                      const isSelected = formData.targetLocations.includes(location);
                      return (
                        <button
                          key={location}
                          onClick={() => {
                            setFormData((prev) => ({
                              ...prev,
                              targetLocations: isSelected
                                ? prev.targetLocations.filter((l) => l !== location)
                                : [...prev.targetLocations, location],
                            }));
                          }}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                            isSelected
                              ? "bg-blue-500/20 text-blue-400 border border-blue-500/50"
                              : "bg-bg-panel text-ink-2 border border-rule-strong hover:border-border-strong"
                          }`}
                        >
                          {location}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Company Size */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <label className="block text-sm font-medium text-ink">
                      Company Size
                    </label>
                    {(icpSuggestion?.targetCompanySizes?.length ?? 0) > 0 && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-primary/20 text-accent-primary">
                        <Sparkles className="w-3 h-3" />
                        Suggested
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-5 gap-3">
                    {COMPANY_SIZES.map((size) => {
                      const isSelected = formData.targetCompanySizes.includes(size.id);
                      return (
                        <button
                          key={size.id}
                          onClick={() => {
                            setFormData((prev) => ({
                              ...prev,
                              targetCompanySizes: isSelected
                                ? prev.targetCompanySizes.filter((s) => s !== size.id)
                                : [...prev.targetCompanySizes, size.id],
                            }));
                          }}
                          className={`p-3 rounded-xl text-center transition-all ${
                            isSelected
                              ? "bg-green-500/20 text-green-400 border-2 border-green-500/50"
                              : "bg-bg-panel text-ink-2 border-2 border-rule-strong hover:border-border-strong"
                          }`}
                        >
                          <span className="text-sm font-medium">{size.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Advanced Targeting Filters (4 new filters) */}
                <div className="pt-6 border-t border-rule">
                  <h3 className="text-lg font-serif font-semibold text-ink mb-4">
                    Advanced Targeting
                  </h3>
                  <TargetingFilters
                    value={formData.targeting}
                    onChange={(targeting) => setFormData((prev) => ({ ...prev, targeting }))}
                    icpSuggested={icpSuggestion?.targeting}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Steps 3-5: Coming Soon Placeholder */}
          {currentStep > 2 && (
            <div className="animate-fade-in">
              <div className="p-6 border-b border-rule">
                <h2 className="text-xl font-serif font-semibold text-ink">
                  {STEPS[currentStep - 1].label}
                </h2>
                <p className="text-sm text-ink-3 mt-1">
                  Step {currentStep} of {STEPS.length}
                </p>
              </div>
              <div className="p-12 text-center">
                <div className="w-20 h-20 rounded-2xl mx-auto mb-6 bg-bg-panel flex items-center justify-center">
                  <svg
                    className="w-10 h-10 text-ink-3"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-serif font-semibold text-ink mb-2">
                  Coming Soon
                </h3>
                <p className="text-sm text-ink-3 max-w-sm mx-auto">
                  This step is under development. In the meantime, you can navigate through
                  the wizard to see the flow.
                </p>
              </div>
            </div>
          )}

          {/* Navigation Footer */}
          <div className="p-6 border-t border-rule flex items-center justify-between">
            {currentStep > 1 ? (
              <button
                onClick={handleBack}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-ink-2 hover:text-ink transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </button>
            ) : (
              <div />
            )}
            <button
              onClick={handleNext}
              disabled={currentStep === STEPS.length}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-ink gradient-premium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {currentStep === STEPS.length ? "Create Campaign" : "Continue"}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
