"use client";

/**
 * FILE: frontend/app/dashboard/settings/page.tsx
 * PURPOSE: Settings hub — Agent tab (B2.3 NEW) + Profile/Team/
 *          Integrations/Notifications/Billing tabs (existing).
 * UPDATED: 2026-04-30 — B2.3 visual parity. Added the missing Agent
 *          tab from /demo's renderSettings (lines 2258-2305): BDR
 *          name, agency name, founder, quality-check cadence,
 *          needs-review threshold, agency voice/tone, notification
 *          mode (Dashboard-first / Alerts-only / Reports-only).
 *          Tab pills migrated from raw rgb hex literals to
 *          cream/amber Tailwind tokens.
 */

import { useState } from "react";
import { Bot, User, Users, Link2, Bell, CreditCard, Key, AlertTriangle, Upload, Trash2 } from "lucide-react";
import {
  SettingsHeader,
  ProfileSection,
  IntegrationsSection,
  NotificationsSection,
  BillingSection,
  TeamSection,
} from "@/components/settings";
import {
  mockUserProfile,
  mockIntegrations,
  mockNotifications,
  mockBillingInfo,
  mockTeamMembers,
  mockApiKeys,
} from "@/lib/mock/settings-data";
import { AppShell } from "@/components/layout/AppShell";
import { SectionLabel } from "@/components/dashboard/SectionLabel";

type TabId = "agent" | "profile" | "team" | "integrations" | "notifications" | "billing";

const tabs: { id: TabId; label: string; icon: typeof User }[] = [
  { id: "agent",         label: "Agent",         icon: Bot },
  { id: "profile",       label: "Profile",       icon: User },
  { id: "team",          label: "Team",          icon: Users },
  { id: "integrations",  label: "Integrations",  icon: Link2 },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "billing",       label: "Billing",       icon: CreditCard },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("agent");

  return (
    <AppShell pageTitle="Settings">
      <div className="max-w-4xl mx-auto">
        <SettingsHeader />

        {/* Tabs — wrap on small screens so labels stay readable */}
        <div className="flex flex-wrap gap-1 mb-6 md:mb-8 p-1.5 bg-surface rounded-xl w-full sm:w-fit overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 text-[13px] font-medium rounded-lg transition-colors ${
                  isActive
                    ? "bg-amber-soft text-copper"
                    : "text-ink-3 hover:text-ink hover:bg-panel"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === "agent" && <AgentSection />}
          {activeTab === "profile" && (
            <>
              <ProfileSection profile={mockUserProfile} />
              <ApiKeysSection />
              <DangerZone />
            </>
          )}
          {activeTab === "team"          && <TeamSection members={mockTeamMembers} />}
          {activeTab === "integrations"  && <IntegrationsSection integrations={mockIntegrations} />}
          {activeTab === "notifications" && <NotificationsSection preferences={mockNotifications} />}
          {activeTab === "billing"       && <BillingSection billing={mockBillingInfo} />}
        </div>
      </div>
    </AppShell>
  );
}

// ─── Agent tab — matches /demo's renderSettings (lines 2258-2305) ──

interface NotificationOpt {
  id: "dashboard" | "alerts" | "reports";
  name: string;
  desc: string;
  badge?: string;
  comingSoon?: boolean;
}

const NOTIFY_OPTS: NotificationOpt[] = [
  {
    id: "dashboard",
    name: "Dashboard-first",
    badge: "Recommended for months 1-3",
    desc: "Open the desk daily. Spot-check messages. Review every meeting brief. Build trust with Maya.",
  },
  {
    id: "alerts",
    name: "Alerts-only",
    badge: "coming soon",
    comingSoon: true,
    desc: "Get pinged for booked meetings + flagged exceptions only. Maya runs hands-off in between.",
  },
  {
    id: "reports",
    name: "Reports-only",
    badge: "coming soon",
    comingSoon: true,
    desc: "Weekly digest by email Mondays 7am AEST. No daily touchpoints. Pure background mode.",
  },
];

function AgentSection() {
  const [bdrName, setBdrName]       = useState("Maya");
  const [agencyName, setAgencyName] = useState("");
  const [founder, setFounder]       = useState("");
  const [cadence, setCadence]       = useState("3 random / day (current)");
  const [threshold, setThreshold]   = useState("Critic score < 70 (current)");
  const [tone, setTone]             = useState(
    "Direct. Australian. Evidence-led. No corporate fluff. Every message references a specific vulnerability on the prospect's site — never generic.",
  );
  const [notify, setNotify]         = useState<NotificationOpt["id"]>("dashboard");

  return (
    <div>
      <p className="text-[13px] text-ink-3 mb-4">
        Configure Maya, your BDR agent.
      </p>

      <SectionLabel className="mt-0 mb-3">Agent</SectionLabel>
      <div className="rounded-[10px] border border-rule bg-panel p-5 sm:p-6 space-y-4">
        <SetRow label="BDR name">
          <TextInput value={bdrName} onChange={setBdrName} />
        </SetRow>
        <SetRow label="Agency name">
          <TextInput value={agencyName} onChange={setAgencyName} placeholder="e.g. Keiracom Growth" />
        </SetRow>
        <SetRow label="Founder">
          <TextInput value={founder} onChange={setFounder} placeholder="Name · email@example.com" />
        </SetRow>
        <SetRow label="Quality-check cadence">
          <SelectInput
            value={cadence}
            onChange={setCadence}
            options={[
              "3 random / day (current)",
              "5 random / day",
              "10 random / day",
              "Review-all",
            ]}
          />
        </SetRow>
        <SetRow label="Needs-review threshold">
          <SelectInput
            value={threshold}
            onChange={setThreshold}
            options={[
              "Critic score < 80",
              "Critic score < 70 (current)",
              "Critic score < 60",
            ]}
          />
        </SetRow>
        <SetRow label="Agency voice / tone" stack>
          <textarea
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            rows={3}
            className="w-full rounded-[8px] border border-rule bg-surface px-3 py-2.5 text-[13px] text-ink font-sans focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/40 transition-colors resize-y"
          />
        </SetRow>
      </div>

      <SectionLabel className="mt-7 mb-2">Notification mode</SectionLabel>
      <p className="text-[13px] text-ink-3 mb-3">
        As you build trust with Maya, you can step back from daily dashboard
        checks and receive meeting alerts only.
      </p>
      <div className="rounded-[10px] border border-rule bg-panel p-3 sm:p-4 space-y-2">
        {NOTIFY_OPTS.map((opt) => {
          const isActive = notify === opt.id;
          return (
            <label
              key={opt.id}
              className={`flex items-start gap-3 rounded-[8px] border px-4 py-3 cursor-pointer transition-colors ${
                opt.comingSoon
                  ? "opacity-60 cursor-not-allowed"
                  : isActive
                  ? "border-amber bg-amber-soft"
                  : "border-rule hover:border-amber/60"
              }`}
            >
              <input
                type="radio"
                name="notify"
                value={opt.id}
                checked={isActive}
                disabled={opt.comingSoon}
                onChange={() => !opt.comingSoon && setNotify(opt.id)}
                className="mt-1 accent-amber"
              />
              <div className="min-w-0">
                <div className="text-[14px] text-ink font-medium flex items-center gap-2 flex-wrap">
                  {opt.name}
                  {opt.badge && (
                    <span
                      className={`font-mono text-[9px] tracking-[0.1em] uppercase font-semibold px-2 py-[1px] rounded border ${
                        opt.comingSoon
                          ? "text-ink-3 border-rule bg-surface"
                          : "text-copper bg-amber-soft border-amber/40"
                      }`}
                    >
                      {opt.badge}
                    </span>
                  )}
                </div>
                <div className="text-[12.5px] text-ink-2 mt-0.5 leading-relaxed">
                  {opt.desc}
                </div>
              </div>
            </label>
          );
        })}
      </div>

      {/* Save */}
      <div className="mt-5 text-right">
        <button
          type="button"
          onClick={() => window.alert("Save changes — endpoint pending")}
          className="px-5 py-2.5 rounded-[6px] bg-ink text-white font-mono text-[12px] tracking-[0.08em] uppercase font-semibold hover:opacity-90 transition-opacity"
        >
          Save changes
        </button>
      </div>
    </div>
  );
}

// ─── set-row helpers (matches /demo .set-row grid) ────────────────

function SetRow({
  label, children, stack = false,
}: {
  label: string;
  children: React.ReactNode;
  stack?: boolean;
}) {
  if (stack) {
    return (
      <div>
        <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 mb-1.5">
          {label}
        </div>
        {children}
      </div>
    );
  }
  return (
    <div className="grid items-center gap-3" style={{ gridTemplateColumns: "180px 1fr" }}>
      <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 truncate">
        {label}
      </div>
      <div>{children}</div>
    </div>
  );
}

function TextInput({
  value, onChange, placeholder,
}: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <input
      type="text"
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-[8px] border border-rule bg-surface px-3 py-2 text-[13px] text-ink font-mono focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/40 transition-colors"
    />
  );
}

function SelectInput({
  value, onChange, options,
}: { value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-[8px] border border-rule bg-surface px-3 py-2 text-[13px] text-ink font-mono focus:outline-none focus:border-amber focus:ring-1 focus:ring-amber/40 transition-colors"
    >
      {options.map((o) => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  );
}

// ─── Existing Profile / API Keys / Danger Zone (cream-rebranded) ──

function ApiKeysSection() {
  return (
    <div className="rounded-[10px] border border-rule bg-panel overflow-hidden">
      <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Key className="w-5 h-5 text-amber" />
          <span className="font-display font-bold text-[16px] text-ink">API Keys</span>
        </div>
        <button className="px-4 py-2 text-[13px] font-medium rounded-[6px] border border-rule text-ink-2 hover:border-amber hover:text-copper transition-colors">
          + Generate New Key
        </button>
      </div>
      <div className="p-6 space-y-3">
        {mockApiKeys.map((key) => (
          <div key={key.id} className="flex items-center justify-between p-4 bg-surface rounded-[8px]">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-amber-soft rounded-[8px] flex items-center justify-center">
                <Key className="w-5 h-5 text-amber" />
              </div>
              <div>
                <div className="text-[14px] font-semibold text-ink">{key.name}</div>
                <div className="text-[13px] text-ink-3 font-mono">{key.value}</div>
              </div>
            </div>
            <div className="flex gap-2">
              <button className="px-3 py-1.5 text-[12px] font-medium rounded-md bg-panel text-ink-2 hover:bg-amber-soft hover:text-copper transition-colors">Copy</button>
              <button className="px-3 py-1.5 text-[12px] font-medium rounded-md bg-panel text-ink-2 hover:bg-amber-soft hover:text-copper transition-colors">Regenerate</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DangerZone() {
  return (
    <div className="rounded-[10px] border border-red/40 bg-red/[0.05] p-6">
      <h3 className="flex items-center gap-2.5 text-[15px] font-semibold text-red mb-4">
        <AlertTriangle className="w-5 h-5" />
        Danger Zone
      </h3>
      <div className="flex gap-3 flex-wrap">
        <button className="flex items-center gap-2 px-5 py-2.5 text-[13px] font-medium rounded-[6px] bg-red/10 text-red border border-red/30 hover:bg-red/20 transition-colors">
          <Upload className="w-4 h-4" />
          Export All Data
        </button>
        <button className="flex items-center gap-2 px-5 py-2.5 text-[13px] font-medium rounded-[6px] bg-red/10 text-red border border-red/30 hover:bg-red/20 transition-colors">
          <Trash2 className="w-4 h-4" />
          Delete Account
        </button>
      </div>
    </div>
  );
}
