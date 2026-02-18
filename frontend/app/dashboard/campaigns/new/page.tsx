"use client";

/**
 * FILE: frontend/app/dashboard/campaigns/new/page.tsx
 * PURPOSE: New Campaign Wizard - Multi-step form to create a campaign
 * SPRINT: Dashboard Sprint 3a - Campaign Management
 * SSOT: frontend/design/html-prototypes/campaign-new-v2.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useState } from "react";
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
} from "lucide-react";

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

export default function NewCampaignPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    name: "",
    goal: "meetings",
    targetMeetings: 20,
    startDate: "",
    endDate: "",
    ongoing: false,
  });

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
            className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <span className="text-border-strong">·</span>
          <span className="text-text-muted">Campaigns</span>
          <span className="text-border-strong">/</span>
          <span className="text-text-primary font-medium">New Campaign</span>
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
                        ? "bg-status-success text-text-primary"
                        : currentStep === step.id
                        ? "gradient-premium text-text-primary shadow-lg"
                        : "bg-bg-elevated text-text-muted border-2 border-border-default"
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
                        ? "text-text-primary"
                        : currentStep > step.id
                        ? "text-status-success"
                        : "text-text-muted"
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
              <div className="p-6 border-b border-border-subtle">
                <h2 className="text-xl font-serif font-semibold text-text-primary">
                  Campaign Basics
                </h2>
                <p className="text-sm text-text-muted mt-1">
                  Set the foundation for your outreach campaign
                </p>
              </div>
              <div className="p-6 space-y-8">
                {/* Campaign Name */}
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Campaign Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Q1 SaaS Founder Blitz"
                    className="w-full px-4 py-3 rounded-lg text-sm bg-bg-surface border border-border-default text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all"
                  />
                </div>

                {/* Campaign Goal */}
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-3">
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
                              : "bg-bg-surface border-2 border-border-default hover:border-border-strong"
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
                                isSelected ? "text-text-primary" : "text-text-muted"
                              }`}
                            />
                          </div>
                          <p className="text-sm font-semibold text-text-primary mb-1">
                            {goal.name}
                          </p>
                          <p className="text-xs text-text-muted">{goal.description}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Target Monthly Meetings */}
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Target Monthly Meetings
                  </label>
                  <input
                    type="number"
                    value={formData.targetMeetings}
                    onChange={(e) =>
                      setFormData({ ...formData, targetMeetings: parseInt(e.target.value) || 0 })
                    }
                    min={1}
                    className="w-full px-4 py-3 rounded-lg text-sm bg-bg-surface border border-border-default text-text-primary font-mono focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all"
                  />
                  <p className="text-xs text-text-muted mt-1.5">
                    Based on industry benchmarks, you'll need ~{Math.round(formData.targetMeetings * 50)} leads
                  </p>
                </div>

                {/* Date Range */}
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Campaign Duration
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-text-muted mb-1.5">Start Date</label>
                      <input
                        type="date"
                        value={formData.startDate}
                        onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg text-sm bg-bg-surface border border-border-default text-text-primary focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-text-muted mb-1.5">End Date</label>
                      <div className="relative">
                        <input
                          type="date"
                          value={formData.endDate}
                          onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                          disabled={formData.ongoing}
                          className="w-full px-4 py-3 rounded-lg text-sm bg-bg-surface border border-border-default text-text-primary focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        />
                      </div>
                    </div>
                  </div>
                  <label className="flex items-center gap-2 mt-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.ongoing}
                      onChange={(e) => setFormData({ ...formData, ongoing: e.target.checked })}
                      className="w-4 h-4 rounded border-border-default bg-bg-surface text-accent-primary focus:ring-accent-primary/20"
                    />
                    <span className="text-sm text-text-secondary flex items-center gap-1.5">
                      <Clock className="w-4 h-4" />
                      Run indefinitely (no end date)
                    </span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Steps 2-5: Coming Soon Placeholder */}
          {currentStep > 1 && (
            <div className="animate-fade-in">
              <div className="p-6 border-b border-border-subtle">
                <h2 className="text-xl font-serif font-semibold text-text-primary">
                  {STEPS[currentStep - 1].label}
                </h2>
                <p className="text-sm text-text-muted mt-1">
                  Step {currentStep} of {STEPS.length}
                </p>
              </div>
              <div className="p-12 text-center">
                <div className="w-20 h-20 rounded-2xl mx-auto mb-6 bg-bg-surface flex items-center justify-center">
                  <svg
                    className="w-10 h-10 text-text-muted"
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
                <h3 className="text-lg font-serif font-semibold text-text-primary mb-2">
                  Coming Soon
                </h3>
                <p className="text-sm text-text-muted max-w-sm mx-auto">
                  This step is under development. In the meantime, you can navigate through
                  the wizard to see the flow.
                </p>
              </div>
            </div>
          )}

          {/* Navigation Footer */}
          <div className="p-6 border-t border-border-subtle flex items-center justify-between">
            {currentStep > 1 ? (
              <button
                onClick={handleBack}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
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
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-text-primary gradient-premium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
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
