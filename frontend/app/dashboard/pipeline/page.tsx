"use client";

/**
 * FILE: frontend/app/dashboard/pipeline/page.tsx
 * PURPOSE: Pipeline route — PR3 dashboard rebuild.
 *          State-machine tabs (Review / Outreach / Complete) +
 *          intent-bar prospect rows + filter chips.
 *          Kanban / Table views preserved as alt views.
 */

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PipelineKanban } from "@/components/dashboard/PipelineKanban";
import { PipelineTable } from "@/components/dashboard/PipelineTable";
import { ProspectDrawer } from "@/components/dashboard/ProspectDrawer";
import { PipelineRow, inferIntent } from "@/components/dashboard/PipelineRow";
import {
  PipelineFilters,
  type PipelineFilterKey,
} from "@/components/dashboard/PipelineFilters";
import {
  PipelineStateTabs,
  type PipelineMode,
} from "@/components/dashboard/PipelineStateTabs";
import { usePipelineData } from "@/lib/hooks/usePipelineData";

type View = "list" | "kanban" | "table";

export default function PipelinePage() {
  const [view, setView] = useState<View>("list");
  const [activeLead, setActiveLead] = useState<string | null>(null);
  const [filter, setFilter] = useState<PipelineFilterKey>("all");
  const [mode, setMode] = useState<PipelineMode>("outreach");
  const { prospects, counts, isLoading } = usePipelineData();

  // ─── Derived counts for filter chips + state tabs ───
  const intentCounts = useMemo(() => {
    let struggling = 0, trying = 0, dabbling = 0;
    for (const p of prospects) {
      const tier = inferIntent(p.score);
      if (tier === "struggling") struggling++;
      else if (tier === "trying") trying++;
      else dabbling++;
    }
    return { struggling, trying, dabbling };
  }, [prospects]);

  // Filter + rank
  const ranked = useMemo(() => {
    const sorted = [...prospects].sort(
      (a, b) => (b.score ?? 0) - (a.score ?? 0),
    );
    let filtered = sorted;
    if (filter === "top10")      filtered = sorted.slice(0, 10);
    else if (filter === "top50") filtered = sorted.slice(0, 50);
    else if (filter === "struggling")
      filtered = sorted.filter(p => inferIntent(p.score) === "struggling");
    else if (filter === "trying")
      filtered = sorted.filter(p => inferIntent(p.score) === "trying");
    else if (filter === "dabbling")
      filtered = sorted.filter(p => inferIntent(p.score) === "dabbling");
    return filtered;
  }, [prospects, filter]);

  // State-tab metric inputs (live where possible)
  const total = prospects.length;
  const reviewed = counts.discovered ? total - counts.discovered : total; // TODO(api): real reviewed count
  const contactedCount = (counts.contacted ?? 0) + (counts.replied ?? 0) + (counts.meeting ?? 0) + (counts.converted ?? 0);
  const repliedCount   = (counts.replied ?? 0)  + (counts.meeting ?? 0)  + (counts.converted ?? 0);
  const meetingsCount  = (counts.meeting ?? 0)  + (counts.converted ?? 0);

  return (
    <AppShell pageTitle="Pipeline">
      <div className="px-4 md:px-6 py-6 space-y-6">
        {/* Header */}
        <header className="flex items-start md:items-center justify-between flex-col md:flex-row gap-3">
          <div>
            <h1 className="font-display font-bold text-[28px] text-ink leading-tight tracking-[-0.02em]">
              Pipeline,{" "}
              <em className="text-amber" style={{ fontStyle: "italic" }}>
                ranked
              </em>
            </h1>
            <p className="text-[13px] text-ink-3 mt-1">
              {total} {total === 1 ? "prospect" : "prospects"} across the cycle ·
              click any row for the briefing card.
            </p>
          </div>

          {/* View toggle */}
          <div className="inline-flex p-[2px] rounded-md bg-surface">
            {(["list", "kanban", "table"] as View[]).map(v => {
              const isActive = v === view;
              return (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={[
                    "px-3.5 py-1.5 font-mono text-[11px] tracking-[0.06em] rounded-[4px] uppercase transition-colors",
                    isActive
                      ? "bg-ink text-white font-semibold"
                      : "text-ink-3 hover:text-ink",
                  ].join(" ")}
                >
                  {v}
                </button>
              );
            })}
          </div>
        </header>

        {/* State-machine tabs */}
        <PipelineStateTabs
          mode={mode}
          onChange={setMode}
          {...(mode === "review"
            ? {
                mode: "review" as const,
                total,
                reviewed,
                onReleaseAll: () => {/* TODO(api): wire batch-release endpoint */},
              }
            : mode === "outreach"
            ? {
                mode: "outreach" as const,
                contacted: contactedCount,
                replied:   repliedCount,
                meetingsBooked: meetingsCount,
              }
            : {
                mode: "complete" as const,
                cycleNumber: 1, // TODO(api): real cycle number from metrics
                contacted: contactedCount,
                replied:   repliedCount,
                meetingsBooked: meetingsCount,
                nextCycleAt: null, // TODO(api): real next-cycle ISO timestamp
              })}
        />

        {/* Filter chips */}
        <PipelineFilters
          active={filter}
          onChange={setFilter}
          options={[
            { key: "all",        label: "All",        count: total },
            { key: "top10",      label: "Top 10",     count: Math.min(10, total) },
            { key: "top50",      label: "Top 50",     count: Math.min(50, total) },
            { key: "struggling", label: "Struggling", count: intentCounts.struggling },
            { key: "trying",     label: "Trying",     count: intentCounts.trying },
            { key: "dabbling",   label: "Dabbling",   count: intentCounts.dabbling },
          ]}
        />

        {/* Body — list / kanban / table */}
        {view === "list" && (
          <div className="space-y-2">
            {isLoading ? (
              <div className="rounded-[10px] border border-dashed border-rule bg-surface/50 px-5 py-6 text-[13px] text-ink-3">
                Loading prospects…
              </div>
            ) : ranked.length === 0 ? (
              <div className="rounded-[10px] border border-dashed border-rule bg-surface/50 px-5 py-6 text-[13px] text-ink-3">
                No prospects match this filter yet.
              </div>
            ) : (
              ranked.map((p, i) => (
                <PipelineRow
                  key={p.id}
                  rank={i + 1}
                  prospect={p}
                  onClick={(id) => setActiveLead(id)}
                />
              ))
            )}
          </div>
        )}

        {view === "kanban" && (
          <PipelineKanban
            prospects={ranked}
            counts={counts}
            onOpen={(id) => setActiveLead(id)}
            isLoading={isLoading}
          />
        )}

        {view === "table" && (
          <PipelineTable
            prospects={ranked}
            onOpen={(id) => setActiveLead(id)}
            isLoading={isLoading}
          />
        )}

        {/* Footer nav */}
        <nav className="text-[11px] font-mono text-ink-3 flex gap-3 pt-4 border-t border-rule">
          <Link href="/dashboard" className="hover:text-copper transition-colors">
            ← Home
          </Link>
          <Link
            href="/dashboard/meetings"
            className="hover:text-copper transition-colors"
          >
            Meetings →
          </Link>
        </nav>
      </div>

      <ProspectDrawer leadId={activeLead} onClose={() => setActiveLead(null)} />
    </AppShell>
  );
}
