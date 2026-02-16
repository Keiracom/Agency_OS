/**
 * CampaignWizard.tsx - 5-Step Campaign Creation Wizard
 * Phase: Operation Modular Cockpit
 *
 * Multi-step wizard for creating new campaigns:
 * - Step 1: Basics (name, goal, dates)
 * - Step 2: Audience (ICP selection, filters)
 * - Step 3: Channels (multi-channel selection, sequence preview)
 * - Step 4: Messaging (tone, value props, AI-generated templates)
 * - Step 5: Review & Launch (summary, projections, schedule)
 *
 * Ported from: agency-os-html/campaign-new-v2.html
 */

"use client";

import { useState, useCallback } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Calendar,
  Eye,
  Heart,
  Users,
  MessageCircle,
  Send,
  Rocket,
  Zap,
  Edit2,
  RefreshCw,
  Clock,
  Lightbulb,
  FileText,
  Mail,
  Linkedin,
  Phone,
  Package,
  ChevronRight,
  Sparkles,
  Target,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

// ============================================
// Types
// ============================================

export type CampaignGoal = "meetings" | "awareness" | "nurture";
export type ChannelType = "email" | "linkedin" | "sms" | "voice" | "mail";
export type ToneType = "professional" | "friendly" | "direct";
export type MessageGeneration = "ai" | "manual";
export type LaunchSchedule = "now" | "scheduled";

export interface ICPOption {
  id: string;
  name: string;
  details: string;
  leadCount: number;
}

export interface FilterOption {
  id: string;
  label: string;
  selected: boolean;
}

export interface FilterGroup {
  id: string;
  label: string;
  options: FilterOption[];
}

export interface WizardState {
  // Step 1: Basics
  name: string;
  goal: CampaignGoal;
  targetMeetings: number;
  startDate: string;
  endDate: string;
  // Step 2: Audience
  selectedICP: string;
  filters: Record<string, string[]>;
  estimatedLeads: number;
  // Step 3: Channels
  selectedChannels: ChannelType[];
  // Step 4: Messaging
  tone: ToneType;
  valueProps: string[];
  messageGeneration: MessageGeneration;
  // Step 5: Review
  launchSchedule: LaunchSchedule;
  scheduledDate?: string;
}

interface CampaignWizardProps {
  onBack?: () => void;
  onComplete?: (data: WizardState) => void;
  isSubmitting?: boolean;
}

// ============================================
// Constants & Config
// ============================================

const goalOptions: { value: CampaignGoal; label: string; desc: string; icon: LucideIcon }[] = [
  { value: "meetings", label: "Meetings", desc: "Book sales calls", icon: Calendar },
  { value: "awareness", label: "Awareness", desc: "Build brand presence", icon: Eye },
  { value: "nurture", label: "Nurture", desc: "Warm up cold leads", icon: Heart },
];

const icpOptions: ICPOption[] = [
  { id: "saas-founders", name: "SaaS Founders & CEOs", details: "Series A-C • $5M-$50M ARR • 25-200 employees", leadCount: 1847 },
  { id: "marketing-leaders", name: "Marketing Leaders", details: "CMO, VP Marketing, Head of Growth • B2B Tech", leadCount: 2134 },
  { id: "agency-owners", name: "Agency Owners", details: "Digital, Creative, Performance • $1M-$20M revenue", leadCount: 956 },
  { id: "custom", name: "Create Custom Segment", details: "Define your own targeting criteria", leadCount: 0 },
];

const filterGroups: FilterGroup[] = [
  {
    id: "industry",
    label: "Industry",
    options: [
      { id: "saas", label: "SaaS", selected: true },
      { id: "technology", label: "Technology", selected: true },
      { id: "finance", label: "Finance", selected: false },
      { id: "healthcare", label: "Healthcare", selected: false },
      { id: "ecommerce", label: "E-commerce", selected: false },
    ],
  },
  {
    id: "size",
    label: "Company Size",
    options: [
      { id: "1-10", label: "1-10", selected: false },
      { id: "11-50", label: "11-50", selected: true },
      { id: "51-200", label: "51-200", selected: true },
      { id: "201-500", label: "201-500", selected: false },
      { id: "500+", label: "500+", selected: false },
    ],
  },
  {
    id: "titles",
    label: "Titles",
    options: [
      { id: "ceo", label: "CEO", selected: true },
      { id: "founder", label: "Founder", selected: true },
      { id: "cto", label: "CTO", selected: false },
      { id: "vp", label: "VP", selected: false },
      { id: "director", label: "Director", selected: false },
    ],
  },
  {
    id: "geography",
    label: "Geography",
    options: [
      { id: "us", label: "United States", selected: true },
      { id: "canada", label: "Canada", selected: true },
      { id: "uk", label: "UK", selected: false },
      { id: "australia", label: "Australia", selected: false },
      { id: "eu", label: "EU", selected: false },
    ],
  },
];

const channelConfig: { type: ChannelType; label: string; icon: LucideIcon }[] = [
  { type: "email", label: "Email", icon: Mail },
  { type: "linkedin", label: "LinkedIn", icon: Linkedin },
  { type: "sms", label: "SMS", icon: MessageCircle },
  { type: "voice", label: "Voice AI", icon: Phone },
  { type: "mail", label: "Direct Mail", icon: Package },
];

const toneOptions: { value: ToneType; label: string; example: string }[] = [
  { value: "professional", label: "Professional", example: '"I noticed your company is scaling..."' },
  { value: "friendly", label: "Friendly", example: '"Hey! Came across your profile and..."' },
  { value: "direct", label: "Direct", example: '"Quick question: Are you looking for..."' },
];

const valuePropOptions = [
  "ROI & Results",
  "Time Savings",
  "Industry Expertise",
  "Case Studies",
  "Awards & Recognition",
  "Speed to Results",
  "White Glove Service",
  "AI-Powered",
];

const sequencePreview = [
  { type: "email" as ChannelType, day: 0 },
  { type: "linkedin" as ChannelType, day: 1 },
  { type: "email" as ChannelType, day: 3 },
  { type: "voice" as ChannelType, day: 5 },
  { type: "sms" as ChannelType, day: 7 },
  { type: "email" as ChannelType, day: 10 },
];

// ============================================
// Progress Stepper
// ============================================

function ProgressStepper({ currentStep, totalSteps }: { currentStep: number; totalSteps: number }) {
  const steps = ["Basics", "Audience", "Channels", "Messaging", "Review"];

  return (
    <div className="bg-bg-void/40 backdrop-blur-md border-b border-white/10 py-6 px-8">
      <div className="flex items-center justify-center gap-0 max-w-3xl mx-auto">
        {steps.map((step, idx) => {
          const stepNum = idx + 1;
          const isCompleted = stepNum < currentStep;
          const isActive = stepNum === currentStep;

          return (
            <div key={step} className="flex items-center">
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                    isCompleted
                      ? "bg-amber text-text-primary"
                      : isActive
                      ? "bg-amber text-text-primary shadow-lg shadow-amber/30"
                      : "bg-slate-700 text-text-secondary"
                  }`}
                >
                  {isCompleted ? <Check className="w-5 h-5" /> : stepNum}
                </div>
                <span
                  className={`text-sm font-medium transition-colors ${
                    isActive ? "text-text-primary" : isCompleted ? "text-amber" : "text-text-muted"
                  }`}
                >
                  {step}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <div
                  className={`w-16 h-0.5 mx-3 transition-colors ${
                    stepNum < currentStep ? "bg-amber" : "bg-slate-700"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// Step 1: Campaign Basics
// ============================================

function StepBasics({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (updates: Partial<WizardState>) => void;
}) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3 mb-1">
          <FileText className="w-5 h-5 text-amber" />
          <h2 className="text-lg font-semibold text-text-primary">Campaign Basics</h2>
        </div>
        <p className="text-sm text-text-muted ml-8">Start by naming your campaign and setting your primary goal</p>
      </div>
      <div className="p-6 space-y-6">
        {/* Campaign Name */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">Campaign Name</label>
          <input
            type="text"
            value={state.name}
            onChange={(e) => onChange({ name: e.target.value })}
            placeholder="e.g., Q1 SaaS Founder Blitz"
            className="w-full px-4 py-3 bg-slate-950/60 border border-white/10 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/30"
          />
        </div>

        {/* Campaign Goal */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-3">Campaign Goal</label>
          <div className="grid grid-cols-3 gap-4">
            {goalOptions.map((goal) => {
              const Icon = goal.icon;
              const isSelected = state.goal === goal.value;
              return (
                <button
                  key={goal.value}
                  onClick={() => onChange({ goal: goal.value })}
                  className={`p-5 rounded-xl border-2 text-center transition-all ${
                    isSelected
                      ? "border-amber bg-amber/10"
                      : "border-white/10 bg-slate-950/40 hover:border-white/20"
                  }`}
                >
                  <div
                    className={`w-12 h-12 mx-auto mb-3 rounded-xl flex items-center justify-center ${
                      isSelected ? "bg-amber" : "bg-slate-700"
                    }`}
                  >
                    <Icon className={`w-6 h-6 ${isSelected ? "text-text-primary" : "text-text-secondary"}`} />
                  </div>
                  <p className="text-sm font-semibold text-text-primary">{goal.label}</p>
                  <p className="text-xs text-text-muted">{goal.desc}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Target Meetings */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">Target Monthly Meetings</label>
          <input
            type="number"
            value={state.targetMeetings}
            onChange={(e) => onChange({ targetMeetings: parseInt(e.target.value) || 0 })}
            className="w-48 px-4 py-3 bg-slate-950/60 border border-white/10 rounded-lg text-text-primary focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/30"
          />
        </div>

        {/* Dates */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">Start Date</label>
            <input
              type="date"
              value={state.startDate}
              onChange={(e) => onChange({ startDate: e.target.value })}
              className="w-full px-4 py-3 bg-slate-950/60 border border-white/10 rounded-lg text-text-primary focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/30"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              End Date <span className="font-normal text-text-muted">(or ongoing)</span>
            </label>
            <input
              type="date"
              value={state.endDate}
              onChange={(e) => onChange({ endDate: e.target.value })}
              className="w-full px-4 py-3 bg-slate-950/60 border border-white/10 rounded-lg text-text-primary focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/30"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Step 2: Audience
// ============================================

function StepAudience({
  state,
  filterState,
  onICPChange,
  onFilterToggle,
}: {
  state: WizardState;
  filterState: FilterGroup[];
  onICPChange: (id: string) => void;
  onFilterToggle: (groupId: string, optionId: string) => void;
}) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3 mb-1">
          <Users className="w-5 h-5 text-amber" />
          <h2 className="text-lg font-semibold text-text-primary">Target Audience</h2>
        </div>
        <p className="text-sm text-text-muted ml-8">Select an existing ICP or create a custom segment</p>
      </div>
      <div className="p-6 space-y-6">
        {/* ICP Selection */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-3">Select ICP</label>
          <div className="space-y-3">
            {icpOptions.map((icp) => {
              const isSelected = state.selectedICP === icp.id;
              return (
                <button
                  key={icp.id}
                  onClick={() => onICPChange(icp.id)}
                  className={`w-full flex items-center gap-4 p-4 rounded-xl border-2 text-left transition-all ${
                    isSelected
                      ? "border-amber bg-amber/10"
                      : "border-white/10 bg-slate-950/40 hover:border-white/20"
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                      isSelected ? "border-amber bg-amber" : "border-slate-500"
                    }`}
                  >
                    {isSelected && <div className="w-2 h-2 bg-bg-surface rounded-full" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-text-primary">{icp.name}</p>
                    <p className="text-xs text-text-muted">{icp.details}</p>
                  </div>
                  <span className="text-sm font-semibold font-mono text-amber">
                    {icp.leadCount > 0 ? icp.leadCount.toLocaleString() : "—"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Additional Filters */}
        <div className="pt-6 border-t border-white/10">
          <label className="block text-sm font-medium text-text-primary mb-4">Additional Filters</label>
          <div className="grid grid-cols-2 gap-4">
            {filterState.map((group) => (
              <div key={group.id} className="bg-slate-950/40 border border-white/5 rounded-xl p-4">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
                  {group.label}
                </p>
                <div className="flex flex-wrap gap-2">
                  {group.options.map((option) => (
                    <button
                      key={option.id}
                      onClick={() => onFilterToggle(group.id, option.id)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                        option.selected
                          ? "bg-amber/20 border-amber/50 text-amber"
                          : "bg-bg-base/60 border-white/10 text-text-secondary hover:bg-slate-700/60"
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Lead Preview */}
        <div className="flex items-center justify-between p-5 bg-slate-950/40 border border-white/10 rounded-xl">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber flex items-center justify-center">
              <Users className="w-6 h-6 text-text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-text-primary">~{state.estimatedLeads.toLocaleString()} leads</p>
              <p className="text-sm text-text-muted">match this criteria</p>
            </div>
          </div>
          <button className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-amber text-text-primary text-sm font-medium rounded-lg hover:shadow-lg hover:shadow-amber/25 transition-shadow">
            <Zap className="w-4 h-4" />
            Use AI to find best matches
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Step 3: Channels
// ============================================

function StepChannels({
  state,
  onChannelToggle,
}: {
  state: WizardState;
  onChannelToggle: (channel: ChannelType) => void;
}) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3 mb-1">
          <MessageCircle className="w-5 h-5 text-amber" />
          <h2 className="text-lg font-semibold text-text-primary">Channel Strategy</h2>
        </div>
        <p className="text-sm text-text-muted ml-8">Select which channels to use in your outreach sequence</p>
      </div>
      <div className="p-6 space-y-6">
        {/* Channel Toggles */}
        <div className="grid grid-cols-5 gap-3">
          {channelConfig.map((channel) => {
            const Icon = channel.icon;
            const isActive = state.selectedChannels.includes(channel.type);
            return (
              <button
                key={channel.type}
                onClick={() => onChannelToggle(channel.type)}
                className={`flex flex-col items-center p-5 rounded-xl border-2 transition-all ${
                  isActive
                    ? "border-amber bg-amber/10"
                    : "border-white/10 bg-slate-950/40 hover:border-white/20"
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${
                    isActive ? "bg-amber" : "bg-slate-700"
                  }`}
                >
                  <Icon className={`w-6 h-6 ${isActive ? "text-text-primary" : "text-text-secondary"}`} />
                </div>
                <span className="text-sm font-semibold text-text-primary mb-3">{channel.label}</span>
                <div
                  className={`w-5 h-5 rounded flex items-center justify-center border-2 ${
                    isActive ? "bg-amber border-amber" : "border-slate-500"
                  }`}
                >
                  {isActive && <Check className="w-3.5 h-3.5 text-text-primary" />}
                </div>
              </button>
            );
          })}
        </div>

        {/* Sequence Preview */}
        <div className="bg-slate-950/40 border border-white/10 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-5 text-sm font-semibold text-text-primary">
            <TrendingUp className="w-4 h-4 text-amber" />
            Sequence Preview
          </div>
          <div className="flex items-center flex-wrap gap-2">
            {sequencePreview
              .filter((step) => state.selectedChannels.includes(step.type))
              .map((step, idx, arr) => {
                const config = channelConfig.find((c) => c.type === step.type);
                if (!config) return null;
                const Icon = config.icon;
                const borderColor =
                  step.type === "email"
                    ? "border-l-amber"
                    : step.type === "linkedin"
                    ? "border-l-amber"
                    : step.type === "sms"
                    ? "border-l-amber"
                    : step.type === "voice"
                    ? "border-l-amber-500"
                    : "border-l-amber-light";

                return (
                  <div key={`${step.type}-${step.day}`} className="flex items-center gap-2">
                    <div className={`flex items-center gap-2 px-3 py-2 bg-bg-base/60 border border-white/10 ${borderColor} border-l-2 rounded-lg`}>
                      <Icon className="w-4 h-4 text-text-secondary" />
                      <span className="text-xs text-text-secondary">Day {step.day}</span>
                    </div>
                    {idx < arr.length - 1 && <ChevronRight className="w-4 h-4 text-text-muted" />}
                  </div>
                );
              })}
          </div>

          {/* AI Recommendation */}
          <div className="flex items-start gap-3 mt-5 p-4 bg-amber/10 border border-amber/30 rounded-lg">
            <div className="w-9 h-9 rounded-lg bg-amber flex items-center justify-center flex-shrink-0">
              <Lightbulb className="w-5 h-5 text-text-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text-primary">Recommended for your ICP</p>
              <p className="text-xs text-text-secondary mt-1">
                Based on SaaS Founders, we recommend Email + LinkedIn + Voice AI. This combination has a 23% higher
                meeting book rate for similar audiences.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Step 4: Messaging
// ============================================

function StepMessaging({
  state,
  onChange,
  onValuePropToggle,
}: {
  state: WizardState;
  onChange: (updates: Partial<WizardState>) => void;
  onValuePropToggle: (prop: string) => void;
}) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3 mb-1">
          <Send className="w-5 h-5 text-amber" />
          <h2 className="text-lg font-semibold text-text-primary">Messaging</h2>
        </div>
        <p className="text-sm text-text-muted ml-8">Define your tone and let AI craft your outreach messages</p>
      </div>
      <div className="p-6 space-y-6">
        {/* Tone Selection */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-3">Tone</label>
          <div className="grid grid-cols-3 gap-4">
            {toneOptions.map((tone) => {
              const isSelected = state.tone === tone.value;
              return (
                <button
                  key={tone.value}
                  onClick={() => onChange({ tone: tone.value })}
                  className={`p-5 rounded-xl border-2 text-left transition-all ${
                    isSelected
                      ? "border-amber bg-amber/10"
                      : "border-white/10 bg-slate-950/40 hover:border-white/20"
                  }`}
                >
                  <p className="text-sm font-semibold text-text-primary mb-1">{tone.label}</p>
                  <p className="text-xs text-text-muted italic">{tone.example}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Value Props */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-3">Key Value Props to Emphasize</label>
          <div className="flex flex-wrap gap-2">
            {valuePropOptions.map((prop) => {
              const isSelected = state.valueProps.includes(prop);
              return (
                <button
                  key={prop}
                  onClick={() => onValuePropToggle(prop)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
                    isSelected
                      ? "bg-amber/20 border-amber/50 text-amber"
                      : "bg-slate-950/40 border-white/10 text-text-secondary hover:bg-bg-base/60"
                  }`}
                >
                  {prop}
                </button>
              );
            })}
          </div>
        </div>

        {/* Message Generation */}
        <div className="pt-6 border-t border-white/10">
          <label className="block text-sm font-medium text-text-primary mb-4">Message Generation</label>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <button
              onClick={() => onChange({ messageGeneration: "ai" })}
              className={`p-6 rounded-xl border-2 text-center transition-all ${
                state.messageGeneration === "ai"
                  ? "border-amber bg-amber/10"
                  : "border-white/10 bg-slate-950/40 hover:border-white/20"
              }`}
            >
              <div
                className={`w-14 h-14 mx-auto mb-4 rounded-xl flex items-center justify-center ${
                  state.messageGeneration === "ai" ? "bg-amber" : "bg-slate-700"
                }`}
              >
                <Zap className={`w-7 h-7 ${state.messageGeneration === "ai" ? "text-text-primary" : "text-text-secondary"}`} />
              </div>
              <p className="text-sm font-semibold text-text-primary">Let AI generate messaging</p>
              <p className="text-xs text-text-muted mt-1">Based on your tone and value props</p>
            </button>
            <button
              onClick={() => onChange({ messageGeneration: "manual" })}
              className={`p-6 rounded-xl border-2 text-center transition-all ${
                state.messageGeneration === "manual"
                  ? "border-amber bg-amber/10"
                  : "border-white/10 bg-slate-950/40 hover:border-white/20"
              }`}
            >
              <div
                className={`w-14 h-14 mx-auto mb-4 rounded-xl flex items-center justify-center ${
                  state.messageGeneration === "manual" ? "bg-amber" : "bg-slate-700"
                }`}
              >
                <Edit2 className={`w-7 h-7 ${state.messageGeneration === "manual" ? "text-text-primary" : "text-text-secondary"}`} />
              </div>
              <p className="text-sm font-semibold text-text-primary">I'll provide templates</p>
              <p className="text-xs text-text-muted mt-1">Write your own copy</p>
            </button>
          </div>
        </div>

        {/* AI Preview */}
        {state.messageGeneration === "ai" && (
          <div className="bg-slate-950/40 border border-white/10 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 bg-bg-base/40 border-b border-white/10">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                <Eye className="w-4 h-4 text-amber" />
                First Touch Preview
              </div>
              <span className="flex items-center gap-1.5 px-2.5 py-1 bg-gradient-to-r from-violet-600 to-amber text-[10px] font-semibold uppercase tracking-wide text-text-primary rounded">
                <Sparkles className="w-3 h-3" />
                AI Generated
              </span>
            </div>
            <div className="p-5">
              <p className="text-sm font-semibold text-text-primary mb-3">Re: Quick question about {"{{company}}"}'s growth</p>
              <div className="text-sm text-text-secondary space-y-3 leading-relaxed">
                <p>Hi {"{{firstName}}"},</p>
                <p>
                  I noticed {"{{company}}"} has been scaling rapidly — congrats on the recent momentum.
                </p>
                <p>
                  We've helped similar SaaS companies cut their lead generation time by 60% while increasing qualified
                  meetings by 3x. Our AI-powered outreach handles the heavy lifting so founders can focus on closing.
                </p>
                <p>
                  Would it make sense to chat for 15 minutes this week? I'd love to share what's working for companies
                  at your stage.
                </p>
                <p>
                  Best,
                  <br />
                  {"{{senderName}}"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 px-5 py-4 bg-bg-base/40 border-t border-white/10">
              <button className="flex items-center gap-2 px-4 py-2 bg-slate-700/60 hover:bg-bg-elevated/60 border border-white/10 rounded-lg text-sm text-text-secondary transition-colors">
                <RefreshCw className="w-4 h-4" />
                Regenerate
              </button>
              <button className="flex items-center gap-2 px-4 py-2 bg-slate-700/60 hover:bg-bg-elevated/60 border border-white/10 rounded-lg text-sm text-text-secondary transition-colors">
                <Edit2 className="w-4 h-4" />
                Edit
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// Step 5: Review & Launch
// ============================================

function StepReview({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (updates: Partial<WizardState>) => void;
}) {
  const goalLabel = goalOptions.find((g) => g.value === state.goal)?.label || "Meetings";
  const icpLabel = icpOptions.find((i) => i.id === state.selectedICP)?.name || "Custom";
  const toneLabel = toneOptions.find((t) => t.value === state.tone)?.label || "Professional";

  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3 mb-1">
          <Target className="w-5 h-5 text-amber" />
          <h2 className="text-lg font-semibold text-text-primary">Review & Launch</h2>
        </div>
        <p className="text-sm text-text-muted ml-8">Review your campaign settings before going live</p>
      </div>
      <div className="p-6 space-y-6">
        {/* Summary Card */}
        <div className="bg-slate-950/40 border border-white/10 rounded-xl overflow-hidden divide-y divide-white/5">
          <div className="p-5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">Campaign Details</p>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Campaign Name</span>
                <span className="font-semibold text-text-primary">{state.name || "Untitled Campaign"}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Goal</span>
                <span className="font-semibold text-text-primary">{goalLabel}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Target</span>
                <span className="font-semibold text-text-primary">{state.targetMeetings} meetings / month</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Duration</span>
                <span className="font-semibold text-text-primary">
                  {state.startDate || "TBD"} — {state.endDate || "Ongoing"}
                </span>
              </div>
            </div>
          </div>
          <div className="p-5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">Audience</p>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">ICP</span>
                <span className="font-semibold text-text-primary">{icpLabel}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Total Leads</span>
                <span className="font-semibold text-amber">{state.estimatedLeads.toLocaleString()} leads</span>
              </div>
            </div>
          </div>
          <div className="p-5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">Channels</p>
            <div className="flex gap-2">
              {state.selectedChannels.map((channel) => {
                const config = channelConfig.find((c) => c.type === channel);
                if (!config) return null;
                const Icon = config.icon;
                return (
                  <span
                    key={channel}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 bg-bg-base/60 rounded-lg text-xs font-medium text-text-secondary"
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {config.label}
                  </span>
                );
              })}
            </div>
          </div>
          <div className="p-5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">Messaging</p>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Tone</span>
                <span className="font-semibold text-text-primary">{toneLabel}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-secondary">Generation</span>
                <span className="font-semibold text-text-primary">
                  {state.messageGeneration === "ai" ? "AI Generated" : "Custom Templates"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Projected Metrics */}
        <div className="grid grid-cols-3 gap-4">
          <div className="p-6 bg-slate-950/40 border border-white/10 rounded-xl text-center">
            <p className="text-3xl font-bold font-mono text-text-primary mb-1">~42%</p>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Projected Opens</p>
            <p className="text-[10px] text-text-muted mt-2">Industry avg: 35%</p>
          </div>
          <div className="p-6 bg-slate-950/40 border border-white/10 rounded-xl text-center">
            <p className="text-3xl font-bold font-mono text-text-primary mb-1">~8%</p>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Projected Replies</p>
            <p className="text-[10px] text-text-muted mt-2">Industry avg: 4%</p>
          </div>
          <div className="p-6 bg-slate-950/40 border border-white/10 rounded-xl text-center">
            <p className="text-3xl font-bold font-mono text-amber mb-1">8-12</p>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Projected Meetings</p>
            <p className="text-[10px] text-text-muted mt-2">Based on similar campaigns</p>
          </div>
        </div>

        {/* Schedule Options */}
        <div className="pt-6 border-t border-white/10">
          <label className="block text-sm font-medium text-text-primary mb-4">Launch Schedule</label>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => onChange({ launchSchedule: "now" })}
              className={`p-5 rounded-xl border-2 text-left transition-all ${
                state.launchSchedule === "now"
                  ? "border-amber bg-amber/10"
                  : "border-white/10 bg-slate-950/40 hover:border-white/20"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    state.launchSchedule === "now" ? "bg-amber" : "bg-slate-700"
                  }`}
                >
                  <Zap className={`w-5 h-5 ${state.launchSchedule === "now" ? "text-text-primary" : "text-text-secondary"}`} />
                </div>
                <span className="text-sm font-semibold text-text-primary">Launch Now</span>
              </div>
              <p className="text-xs text-text-muted ml-13">Start sending immediately</p>
            </button>
            <button
              onClick={() => onChange({ launchSchedule: "scheduled" })}
              className={`p-5 rounded-xl border-2 text-left transition-all ${
                state.launchSchedule === "scheduled"
                  ? "border-amber bg-amber/10"
                  : "border-white/10 bg-slate-950/40 hover:border-white/20"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    state.launchSchedule === "scheduled" ? "bg-amber" : "bg-slate-700"
                  }`}
                >
                  <Clock className={`w-5 h-5 ${state.launchSchedule === "scheduled" ? "text-text-primary" : "text-text-secondary"}`} />
                </div>
                <span className="text-sm font-semibold text-text-primary">Schedule</span>
              </div>
              <p className="text-xs text-text-muted ml-13">Pick a date and time</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function CampaignWizard({ onBack, onComplete, isSubmitting = false }: CampaignWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [state, setState] = useState<WizardState>({
    name: "",
    goal: "meetings",
    targetMeetings: 10,
    startDate: "",
    endDate: "",
    selectedICP: "saas-founders",
    filters: {},
    estimatedLeads: 847,
    selectedChannels: ["email", "linkedin", "sms", "voice"],
    tone: "professional",
    valueProps: ["ROI & Results", "Time Savings", "Speed to Results"],
    messageGeneration: "ai",
    launchSchedule: "now",
  });

  const [filterState, setFilterState] = useState<FilterGroup[]>(filterGroups);

  const updateState = useCallback((updates: Partial<WizardState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  const handleICPChange = useCallback((id: string) => {
    const icp = icpOptions.find((i) => i.id === id);
    setState((prev) => ({
      ...prev,
      selectedICP: id,
      estimatedLeads: icp?.leadCount || 0,
    }));
  }, []);

  const handleFilterToggle = useCallback((groupId: string, optionId: string) => {
    setFilterState((prev) =>
      prev.map((group) =>
        group.id === groupId
          ? {
              ...group,
              options: group.options.map((opt) =>
                opt.id === optionId ? { ...opt, selected: !opt.selected } : opt
              ),
            }
          : group
      )
    );
  }, []);

  const handleChannelToggle = useCallback((channel: ChannelType) => {
    setState((prev) => ({
      ...prev,
      selectedChannels: prev.selectedChannels.includes(channel)
        ? prev.selectedChannels.filter((c) => c !== channel)
        : [...prev.selectedChannels, channel],
    }));
  }, []);

  const handleValuePropToggle = useCallback((prop: string) => {
    setState((prev) => ({
      ...prev,
      valueProps: prev.valueProps.includes(prop)
        ? prev.valueProps.filter((p) => p !== prop)
        : [...prev.valueProps, prop],
    }));
  }, []);

  const nextStep = useCallback(() => {
    if (currentStep < 5) {
      setCurrentStep((prev) => prev + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [currentStep]);

  const prevStep = useCallback(() => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [currentStep]);

  const handleLaunch = useCallback(() => {
    onComplete?.(state);
  }, [state, onComplete]);

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="bg-bg-void/40 backdrop-blur-md border-b border-white/10 px-8 py-4">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-2 text-sm text-text-muted hover:text-text-secondary rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <div className="w-px h-6 bg-bg-surface/10" />
          <h1 className="text-lg font-semibold text-text-primary">New Campaign</h1>
        </div>
      </div>

      {/* Progress */}
      <ProgressStepper currentStep={currentStep} totalSteps={5} />

      {/* Content */}
      <div className="max-w-3xl mx-auto px-8 py-8">
        {currentStep === 1 && <StepBasics state={state} onChange={updateState} />}
        {currentStep === 2 && (
          <StepAudience
            state={state}
            filterState={filterState}
            onICPChange={handleICPChange}
            onFilterToggle={handleFilterToggle}
          />
        )}
        {currentStep === 3 && <StepChannels state={state} onChannelToggle={handleChannelToggle} />}
        {currentStep === 4 && (
          <StepMessaging state={state} onChange={updateState} onValuePropToggle={handleValuePropToggle} />
        )}
        {currentStep === 5 && <StepReview state={state} onChange={updateState} />}

        {/* Footer */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-white/10">
          {currentStep > 1 ? (
            <button
              onClick={prevStep}
              className="flex items-center gap-2 px-5 py-2.5 bg-bg-base/60 hover:bg-slate-700/60 border border-white/10 rounded-lg text-sm text-text-primary transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
          ) : (
            <div />
          )}

          {currentStep < 5 ? (
            <button
              onClick={nextStep}
              className="flex items-center gap-2 px-5 py-2.5 bg-amber hover:bg-amber rounded-lg text-sm font-medium text-text-primary transition-colors"
            >
              Continue
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleLaunch}
              disabled={isSubmitting}
              className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-violet-600 to-amber hover:shadow-lg hover:shadow-amber/25 rounded-lg text-sm font-semibold text-text-primary transition-all disabled:opacity-50"
            >
              <Rocket className="w-4 h-4" />
              {isSubmitting ? "Launching..." : "Launch Campaign"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default CampaignWizard;
