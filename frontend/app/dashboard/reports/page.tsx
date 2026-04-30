/**
 * FILE: frontend/app/dashboard/reports/page.tsx
 * PURPOSE: Cycle progress report — 3-section /demo `renderProgress`
 *          pattern (lines 2209-2255). Replaces the prior 11-section
 *          Bloomberg-dark Analytics Terminal layout.
 * UPDATED: 2026-04-30 — B2.3 visual parity.
 *
 * Sections:
 *   1. KPI row — Open Rate · Reply Rate · Meeting Rate · Avg Reply Time
 *   2. Funnel card — proportional bar per stage with % labels
 *   3. ROI grid — Cost/Meeting · Cost/Reply · Cost/Contact · Pipeline ROI
 *
 * Numbers default to placeholder values matching the prototype until
 * the metrics endpoint exposes real cycle telemetry. Each card carries
 * a `your data only` mono note per the prototype's anti-vanity-metric
 * convention.
 */

"use client";

import { AppShell } from "@/components/layout/AppShell";
import { SectionLabel } from "@/components/dashboard/SectionLabel";

// Placeholder numbers until backend exposes a cycle-progress endpoint.
// Each cell is rendered with a `placeholder` flag so the UI can mark
// them honestly rather than presenting fabricated metrics.
const KPIS = [
  { val: "—", unit: "%", label: "Open Rate",      note: "your data only" },
  { val: "—", unit: "%", label: "Reply Rate",     note: "your data only" },
  { val: "—", unit: "%", label: "Meeting Rate",   note: "your data only" },
  { val: "—", unit: "h", label: "Avg Reply Time", note: "contacted → first reply" },
];

const FUNNEL = [
  { label: "Discovered", value: 0, max: 1 },
  { label: "Contacted",  value: 0, max: 1 },
  { label: "Replied",    value: 0, max: 1 },
  { label: "Meetings",   value: 0, max: 1 },
  { label: "Won",        value: 0, max: 1 },
];

const ROI = [
  { val: "—", label: "Cost / Meeting", sub: "subscription ÷ meetings" },
  { val: "—", label: "Cost / Reply",   sub: "subscription ÷ replies"  },
  { val: "—", label: "Cost / Contact", sub: "subscription ÷ contacts" },
  { val: "—", label: "Pipeline ROI",   sub: "closed × deal ÷ subscription" },
];

export default function ReportsPage() {
  return (
    <AppShell pageTitle="Reports">
      <div>
        {/* Headline — Playfair with amber italic emphasis */}
        <h1 className="font-display font-bold text-[28px] md:text-[36px] text-ink leading-[1.06] tracking-[-0.02em]">
          Cycle progress,
          <br />
          <em className="text-amber" style={{ fontStyle: "italic" }}>
            partner-ready report.
          </em>
        </h1>
        <p className="text-[13px] text-ink-3 mt-2 max-w-[820px]">
          Refreshed every 5 minutes · raw metrics only — no unsourced
          benchmark comparisons.
        </p>

        {/* 1. KPI row — 4 cells (matches /demo .kpi-cell) */}
        <SectionLabel className="mt-7 mb-3">Performance</SectionLabel>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-3.5">
          {KPIS.map(k => (
            <div
              key={k.label}
              className="rounded-[10px] border border-rule bg-panel px-[18px] py-4"
            >
              <div className="font-display font-bold text-[28px] leading-none text-ink">
                {k.val}
                <em
                  className="not-italic font-bold text-[18px] text-amber ml-0.5"
                  style={{ fontStyle: "normal" }}
                >
                  {k.unit}
                </em>
              </div>
              <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-ink-3 mt-1.5">
                {k.label}
              </div>
              <div className="font-mono text-[11px] text-ink-3 mt-1">
                {k.note}
              </div>
            </div>
          ))}
        </div>

        {/* 2. Funnel card */}
        <SectionLabel className="mt-7 mb-3">Funnel</SectionLabel>
        <div className="rounded-[10px] border border-rule bg-panel p-5 sm:p-6">
          <div className="space-y-3">
            {FUNNEL.map(row => {
              const pct = Math.max(6, (row.value / Math.max(row.max, 1)) * 100);
              const display = ((row.value / Math.max(row.max, 1)) * 100).toFixed(
                row.value / Math.max(row.max, 1) < 0.05 ? 1 : 0,
              );
              return (
                <div
                  key={row.label}
                  className="grid items-center gap-3"
                  style={{ gridTemplateColumns: "100px 1fr 60px" }}
                >
                  <div className="font-mono text-[11px] tracking-[0.06em] uppercase text-ink-3 truncate">
                    {row.label}
                  </div>
                  <div className="h-7 rounded-[6px] bg-surface overflow-hidden relative">
                    <div
                      className="h-full px-3 flex items-center text-[11px] font-mono font-semibold transition-[width] duration-300"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: "var(--amber)",
                        color: "var(--on-amber)",
                      }}
                    >
                      {row.value}
                    </div>
                  </div>
                  <div className="font-mono text-[11px] text-ink-3 text-right tabular-nums">
                    {display}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 3. ROI grid */}
        <SectionLabel className="mt-7 mb-3">
          Subscription efficiency · AUD
        </SectionLabel>
        <div className="rounded-[10px] border border-rule bg-panel p-5 sm:p-6">
          <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-copper mb-4">
            Based on your active subscription · cycle to date
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
            {ROI.map(c => (
              <div
                key={c.label}
                className="rounded-[10px] border border-rule bg-surface px-[18px] py-4"
              >
                <div className="font-display font-bold text-[24px] leading-none text-ink">
                  {c.val}
                </div>
                <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-ink-3 mt-1.5">
                  {c.label}
                </div>
                <div className="font-mono text-[10.5px] text-ink-3 mt-1">
                  {c.sub}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 font-mono text-[12px] text-ink-3 leading-relaxed">
            Awaiting first cycle of telemetry — values populate after
            Maya's first batch completes.
          </div>
        </div>

        {/* Export PDF button — stubbed */}
        <div className="text-center mt-7">
          <button
            type="button"
            onClick={() =>
              window.alert(
                "Export PDF — endpoint pending. Will produce a partner-ready report from the live cycle data.",
              )
            }
            className="px-5 py-2.5 rounded-[6px] bg-ink text-white font-mono text-[12px] tracking-[0.08em] uppercase font-semibold hover:opacity-90 transition-opacity"
          >
            Export report
          </button>
        </div>
      </div>
    </AppShell>
  );
}
