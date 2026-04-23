/**
 * FILE: frontend/components/dashboard/PipelineKanban.tsx
 * PURPOSE: Kanban board — 6 stage columns with HTML drag-drop + click-to-open
 * PHASE: PHASE-2.1-PIPELINE-MEETINGS
 *
 * Dark theme, Tailwind only. No external DnD library — native HTML5 DnD.
 */

"use client";

import { useState } from "react";
import { Mail, Linkedin, Phone, MessageSquare } from "lucide-react";
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

const COLUMNS: Array<{ key: PipelineStage; label: string }> = [
  { key: "discovered", label: "Discovered" },
  { key: "enriched",   label: "Enriched" },
  { key: "contacted",  label: "Contacted" },
  { key: "replied",    label: "Replied" },
  { key: "meeting",    label: "Meeting" },
  { key: "converted",  label: "Converted" },
];

function ChannelGlyph({ channel }: { channel: string | null }) {
  const label = canonicalChannel(channel ?? "");
  const Icon =
    label === "Email"    ? Mail :
    label === "LinkedIn" ? Linkedin :
    label === "SMS"      ? MessageSquare :
    label === "Voice AI" ? Phone :
    Mail;
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] text-gray-400 font-mono uppercase"
      title={label}
    >
      <Icon className="w-3 h-3" strokeWidth={1.75} />
      {label === "Voice AI" ? "Voice" : label}
    </span>
  );
}

function Card({
  p,
  onOpen,
  onDragStart,
}: {
  p: PipelineProspect;
  onOpen: (id: string) => void;
  onDragStart: (e: React.DragEvent<HTMLDivElement>, id: string) => void;
}) {
  const sent = p.lastTouchAt ? new Date(p.lastTouchAt).toLocaleDateString() : "—";
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, p.id)}
      onClick={() => onOpen(p.id)}
      className="cursor-pointer bg-gray-800 border border-gray-700 rounded-lg p-3 hover:border-amber-500/50 hover:bg-gray-800/70 transition"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-serif text-sm text-gray-100 truncate">{p.name}</div>
          <div className="text-xs text-gray-400 truncate">{p.company}</div>
        </div>
        {p.vrGrade && (
          <span className="shrink-0 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
            {p.vrGrade}
          </span>
        )}
      </div>
      <div className="flex items-center justify-between mt-2">
        <ChannelGlyph channel={p.lastChannel} />
        <span className="text-[10px] text-gray-500 font-mono">{sent}</span>
      </div>
    </div>
  );
}

export function PipelineKanban({ prospects, counts, onOpen, onMove, isLoading }: Props) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [overCol, setOverCol] = useState<PipelineStage | null>(null);

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, id: string) => {
    setDragId(id);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", id);
  };
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>, col: PipelineStage) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setOverCol(col);
  };
  const handleDrop = (e: React.DragEvent<HTMLDivElement>, to: PipelineStage) => {
    e.preventDefault();
    const id = dragId || e.dataTransfer.getData("text/plain");
    if (id && onMove) onMove(id, to);
    setDragId(null);
    setOverCol(null);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 overflow-x-auto">
      {COLUMNS.map((col) => {
        const list = prospects.filter((p) => p.stage === col.key);
        const active = overCol === col.key;
        return (
          <div
            key={col.key}
            onDragOver={(e) => handleDragOver(e, col.key)}
            onDrop={(e) => handleDrop(e, col.key)}
            className={`bg-gray-900 border rounded-xl p-3 min-h-[320px] ${
              active ? "border-amber-500/50 bg-amber-500/5" : "border-gray-800"
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-[10px] tracking-widest text-gray-400 uppercase">
                {col.label}
              </span>
              <span className="font-mono text-[11px] text-gray-300">
                {counts[col.key] ?? 0}
              </span>
            </div>
            <div className="space-y-2">
              {list.length === 0 ? (
                <div className="text-[11px] text-gray-600 italic py-4 text-center">
                  {isLoading ? "Loading…" : "No prospects"}
                </div>
              ) : (
                list.map((p) => (
                  <Card key={p.id} p={p} onOpen={onOpen} onDragStart={handleDragStart} />
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
