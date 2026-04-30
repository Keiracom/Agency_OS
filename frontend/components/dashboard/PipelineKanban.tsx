/**
 * FILE: frontend/components/dashboard/PipelineKanban.tsx
 * PURPOSE: Kanban board — 5 stage columns matching /demo's
 *          PIPE_COLS pattern (lines 1735-1745). Cream/amber palette
 *          with the prototype's `.k-card` class translated to
 *          Tailwind tokens.
 *          B2.1 visual parity (2026-04-30) — was on the dark
 *          Bloomberg theme; now matches /demo verbatim.
 *
 * Five columns: Discovered (=New) · Contacted · Replied · Meeting ·
 * Won. Each column gets a top accent stripe in its stage colour
 * (matches prototype's `.col-head::before` rule). Cards use the
 * Playfair name + DM Sans body + JetBrains Mono meta pattern.
 * Native HTML5 drag/drop preserved.
 */

"use client";

import { useState } from "react";
import {
  PipelineProspect,
  PipelineStage,
} from "@/lib/hooks/usePipelineData";
import { canonicalChannel } from "@/lib/provider-labels";

interface Props {
  prospects: PipelineProspect[];
  counts: Record<PipelineStage, number>;
  onOpen: (id: string) => void;
  onMove?: (id: string, to: PipelineStage) => void;
  isLoading?: boolean;
}

type ColumnKey = "discovered" | "contacted" | "replied" | "meeting" | "won";

interface ColDef {
  key: ColumnKey;
  label: string;
  /** Top accent stripe colour — matches /demo's `.col-*-head::before` */
  accent: string;
  /** Stages that map to this column */
  stages: PipelineStage[];
}

const COLUMNS: ColDef[] = [
  { key: "discovered", label: "New",       accent: "var(--ink-3)",  stages: ["discovered", "enriched"] },
  { key: "contacted",  label: "Contacted", accent: "var(--blue)",   stages: ["contacted"] },
  { key: "replied",    label: "Replied",   accent: "var(--amber)",  stages: ["replied"] },
  { key: "meeting",    label: "Meeting",   accent: "var(--green)",  stages: ["meeting"] },
  { key: "won",        label: "Won",       accent: "var(--copper)", stages: ["converted"] },
];

function colCount(
  counts: Record<PipelineStage, number>,
  col: ColDef,
): number {
  return col.stages.reduce((acc, s) => acc + (counts[s] ?? 0), 0);
}

function Card({
  p, onOpen, onDragStart, accent,
}: {
  p: PipelineProspect;
  onOpen: (id: string) => void;
  onDragStart: (e: React.DragEvent<HTMLDivElement>, id: string) => void;
  accent: string;
}) {
  const lastTouch = p.lastTouchAt
    ? new Date(p.lastTouchAt).toLocaleDateString(undefined, {
        month: "short", day: "numeric",
      })
    : null;
  const channelLabel = p.lastChannel ? canonicalChannel(p.lastChannel) : null;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, p.id)}
      onClick={() => onOpen(p.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(p.id);
        }
      }}
      role="button"
      tabIndex={0}
      className="cursor-pointer bg-panel border border-rule rounded-[6px] px-4 py-3 hover:border-amber hover:shadow-[0_2px_10px_rgba(212,149,106,0.10)] transition-all leading-[1.4]"
      style={{ borderLeft: `3px solid ${accent}` }}
    >
      {/* Name — Playfair */}
      <div className="font-display font-bold text-[14px] text-ink leading-[1.3] truncate">
        {p.company || p.name}
      </div>

      {/* DM */}
      {p.name && (
        <div className="text-[12px] text-ink-2 mt-0.5 truncate">{p.name}</div>
      )}

      {/* Meta — channel · date */}
      {(channelLabel || lastTouch) && (
        <div className="font-mono text-[10.5px] text-ink-3 mt-1 tracking-[0.03em] truncate">
          {channelLabel}
          {channelLabel && lastTouch ? " · " : ""}
          {lastTouch}
        </div>
      )}

      {/* Foot — VR grade + score on left, no right slot for now */}
      <div className="flex justify-between items-center mt-2.5 pt-2 border-t border-dashed border-rule gap-1.5 flex-wrap">
        <div className="flex items-center gap-1.5 min-w-0">
          {p.vrGrade && (
            <span
              className="font-display font-bold text-[12px] grid place-items-center w-6 h-6 rounded-[5px]"
              style={{
                backgroundColor:
                  p.vrGrade === "A" || p.vrGrade === "B" ? "var(--green)" :
                  p.vrGrade === "C" ? "var(--amber)" :
                  p.vrGrade === "D" ? "var(--copper)" :
                  "var(--red)",
                color: p.vrGrade === "C" ? "var(--on-amber)" : "white",
              }}
            >
              {p.vrGrade}
            </span>
          )}
          {p.score != null && (
            <span className="font-mono text-[14px] font-semibold text-copper tabular-nums">
              {p.score}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function PipelineKanban({
  prospects, counts, onOpen, onMove, isLoading,
}: Props) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [overCol, setOverCol] = useState<ColumnKey | null>(null);

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, id: string) => {
    setDragId(id);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", id);
  };
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>, col: ColumnKey) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setOverCol(col);
  };
  const handleDrop = (e: React.DragEvent<HTMLDivElement>, to: ColumnKey) => {
    e.preventDefault();
    const id = dragId || e.dataTransfer.getData("text/plain");
    if (id && onMove) {
      // First stage in the merged column wins (e.g. "discovered" for New).
      const target = COLUMNS.find(c => c.key === to);
      if (target) onMove(id, target.stages[0]);
    }
    setDragId(null);
    setOverCol(null);
  };

  const total = prospects.length || 1;

  return (
    <div
      className="grid gap-3 overflow-x-auto pb-3.5 -mx-1 px-1 snap-x"
      style={{ gridTemplateColumns: "repeat(5, minmax(260px, 1fr))" }}
    >
      {COLUMNS.map((col) => {
        const list = prospects.filter((p) => col.stages.includes(p.stage));
        const count = colCount(counts, col);
        const pct = Math.round((count / total) * 100);
        const active = overCol === col.key;
        return (
          <div
            key={col.key}
            onDragOver={(e) => handleDragOver(e, col.key)}
            onDrop={(e) => handleDrop(e, col.key)}
            className={`min-w-0 bg-surface border border-rule rounded-[10px] flex flex-col snap-start ${
              active ? "border-amber" : ""
            }`}
            style={{ maxHeight: "calc(100vh - 240px)" }}
          >
            {/* Column head with top accent stripe (matches .col-head::before) */}
            <div
              className="px-3.5 py-3 border-b border-rule flex items-center justify-between gap-2.5 bg-panel rounded-t-[10px] relative shrink-0"
            >
              <span
                aria-hidden
                className="absolute top-0 left-2.5 right-2.5 h-[3px] rounded-b-[3px]"
                style={{ backgroundColor: col.accent }}
              />
              <span className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-ink-2 font-semibold">
                {col.label}
              </span>
              <span className="inline-flex gap-1.5 font-mono text-[10px] items-center">
                <span className="bg-ink text-white px-[7px] py-[1px] rounded-[10px] font-semibold">
                  {count}
                </span>
                <span className="text-ink-3">{pct}%</span>
              </span>
            </div>

            {/* Column body */}
            <div className="p-2.5 flex flex-col gap-2.5 overflow-y-auto min-h-[80px] flex-1">
              {list.length === 0 ? (
                <div className="text-[11.5px] italic text-ink-3 text-center py-4 px-2.5">
                  {isLoading ? "Loading…" : "Empty — awaiting prospects"}
                </div>
              ) : (
                list.map((p) => (
                  <Card
                    key={p.id}
                    p={p}
                    onOpen={onOpen}
                    onDragStart={handleDragStart}
                    accent={col.accent}
                  />
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
