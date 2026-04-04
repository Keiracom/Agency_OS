"use client";

/**
 * FILE: app/dashboard/pipeline/page.tsx
 * PURPOSE: Live ProspectCard stream page — SSE-fed pipeline feed with intent filters
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Radio } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { ProspectCardView } from "@/components/pipeline/ProspectCardView";
import { usePipelineStream } from "@/hooks/use-pipeline-stream";
import type { IntentBand, ProspectCard } from "@/lib/types/prospect-card";

type FilterBand = IntentBand | "ALL";

const FILTER_PILLS: Array<{ value: FilterBand; label: string; color: string }> =
  [
    { value: "ALL", label: "All", color: "bg-bg-elevated text-text-primary border-border-subtle" },
    {
      value: "STRUGGLING",
      label: "HOT",
      color: "bg-amber-glow text-amber border-amber/40",
    },
    {
      value: "TRYING",
      label: "TRYING",
      color: "bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/30",
    },
    {
      value: "DABBLING",
      label: "DABBLING",
      color: "bg-bg-elevated text-text-secondary border-border-subtle",
    },
    {
      value: "NOT_TRYING",
      label: "NOT TRYING",
      color: "bg-bg-surface text-text-muted border-border-subtle",
    },
  ];

function bandCount(cards: ProspectCard[], band: IntentBand): number {
  return cards.filter((c) => c.intent_band === band).length;
}

export default function PipelinePage() {
  const { cards, isConnected, cardCount } = usePipelineStream();
  const [filter, setFilter] = useState<FilterBand>("ALL");

  const visibleCards =
    filter === "ALL" ? cards : cards.filter((c) => c.intent_band === filter);

  return (
    <AppShell pageTitle="Live Pipeline">
      <div className="p-6 min-h-screen"
        style={{
          background: `
            radial-gradient(ellipse at 10% 0%, rgba(212,149,106,0.06) 0%, transparent 50%),
            var(--bg-void)
          `,
        }}
      >
        {/* Page header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-extrabold text-text-primary font-mono tracking-tight">
              Live Pipeline
            </h1>
            {/* Connection indicator */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold border ${
                isConnected
                  ? "bg-[#10B981]/10 border-[#10B981]/30 text-[#10B981]"
                  : "bg-[#EF4444]/10 border-[#EF4444]/30 text-[#EF4444]"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isConnected ? "bg-[#10B981] animate-pulse" : "bg-[#EF4444]"
                }`}
              />
              {isConnected ? "Connected" : "Reconnecting..."}
            </div>
            {/* Card count */}
            <div className="flex items-center gap-1.5 text-xs font-mono text-text-muted">
              <Radio className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span className="text-amber font-semibold">{cardCount}</span> cards
            </div>
          </div>
          <p className="text-sm text-text-muted">
            Streaming in real-time as prospects are scored
          </p>
        </div>

        {/* Filter pills */}
        <div className="flex flex-wrap gap-2 mb-6">
          {FILTER_PILLS.map((pill) => {
            const count =
              pill.value === "ALL"
                ? cardCount
                : bandCount(cards, pill.value as IntentBand);
            const isActive = filter === pill.value;
            return (
              <button
                key={pill.value}
                onClick={() => setFilter(pill.value)}
                className={`
                  px-3 py-1.5 rounded-full text-xs font-mono font-semibold border transition-all
                  ${pill.color}
                  ${isActive ? "ring-1 ring-amber/40 scale-[1.03]" : "opacity-70 hover:opacity-100"}
                `}
              >
                {pill.label}
                <span className="ml-1.5 opacity-70">{count}</span>
              </button>
            );
          })}
        </div>

        {/* Card grid */}
        {visibleCards.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Radio className="w-10 h-10 text-text-muted mb-4 animate-pulse" strokeWidth={1} />
            <p className="text-text-muted font-mono text-sm">
              {isConnected
                ? "Waiting for pipeline cards..."
                : "Connecting to pipeline stream..."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            <AnimatePresence initial={false}>
              {visibleCards.map((card) => (
                <motion.div
                  key={card.domain}
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                  layout
                >
                  <ProspectCardView card={card} />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </AppShell>
  );
}
