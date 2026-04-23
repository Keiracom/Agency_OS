"use client";

/**
 * FILE: frontend/app/dashboard/pipeline/page.tsx
 * PURPOSE: Pipeline route — Kanban ↔ Table toggle over live Supabase prospect data
 * PHASE: PHASE-2.1-PIPELINE-MEETINGS
 *
 * Replaces the SSE stream view (preserved in git history at prior commits).
 * Uses usePipelineData for counts + prospect list.
 */

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PipelineKanban } from "@/components/dashboard/PipelineKanban";
import { PipelineTable } from "@/components/dashboard/PipelineTable";
import { usePipelineData } from "@/lib/hooks/usePipelineData";

type View = "kanban" | "table";

export default function PipelinePage() {
  const [view, setView] = useState<View>("kanban");
  const { prospects, counts, isLoading } = usePipelineData();

  const total = prospects.length;

  return (
    <AppShell pageTitle="Pipeline">
      <div className="min-h-screen bg-gray-950 text-gray-100 p-4 md:p-6">
        <header className="flex items-start md:items-center justify-between flex-col md:flex-row gap-3 mb-4">
          <div>
            <h1 className="font-serif text-2xl md:text-3xl text-gray-100">
              Pipeline
            </h1>
            <p className="text-sm text-gray-400">
              {total} {total === 1 ? "prospect" : "prospects"} across six stages
            </p>
          </div>
          <div className="inline-flex rounded-lg border border-gray-800 bg-gray-900 p-0.5">
            {(["kanban", "table"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`px-3 py-1.5 text-xs font-mono uppercase tracking-widest rounded-md ${
                  view === v
                    ? "bg-amber-500/10 text-amber-300 border border-amber-500/40"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </header>

        {view === "kanban" ? (
          <PipelineKanban
            prospects={prospects}
            counts={counts}
            onOpen={(id) => { window.location.href = `/dashboard/leads/${id}`; }}
            isLoading={isLoading}
          />
        ) : (
          <PipelineTable
            prospects={prospects}
            onOpen={(id) => { window.location.href = `/dashboard/leads/${id}`; }}
            isLoading={isLoading}
          />
        )}

        <nav className="mt-6 text-xs text-gray-500 font-mono flex gap-3">
          <Link href="/dashboard" className="hover:text-gray-300">← Home</Link>
          <Link href="/dashboard/meetings" className="hover:text-gray-300">Meetings →</Link>
        </nav>
      </div>
    </AppShell>
  );
}
