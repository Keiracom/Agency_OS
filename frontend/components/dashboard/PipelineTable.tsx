/**
 * FILE: frontend/components/dashboard/PipelineTable.tsx
 * PURPOSE: Sortable table view of pipeline prospects
 * PHASE: PHASE-2.1-PIPELINE-MEETINGS
 *
 * Dark theme, Tailwind only. Column headers sort asc/desc on click.
 */

"use client";

import { useMemo, useState } from "react";
import { PipelineProspect, PipelineStage } from "@/lib/hooks/usePipelineData";
import { canonicalChannel } from "@/lib/provider-labels";

interface Props {
  prospects: PipelineProspect[];
  onOpen: (id: string) => void;
  isLoading?: boolean;
}

type SortKey =
  | "name" | "company" | "stage" | "lastChannel"
  | "lastTouchAt" | "nextTouchAt" | "vrGrade";

const STAGE_LABEL: Record<PipelineStage, string> = {
  discovered: "Discovered",
  enriched:   "Enriched",
  contacted:  "Contacted",
  replied:    "Replied",
  meeting:    "Meeting",
  converted:  "Converted",
};

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "—";
  }
}

function compare(a: PipelineProspect, b: PipelineProspect, key: SortKey): number {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const av = (a as any)[key] ?? "";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const bv = (b as any)[key] ?? "";
  if (typeof av === "number" && typeof bv === "number") return av - bv;
  return String(av).localeCompare(String(bv));
}

function HeaderCell({
  label, sortKey, active, dir, onClick,
}: {
  label: string; sortKey: SortKey;
  active: SortKey | null; dir: "asc" | "desc";
  onClick: (k: SortKey) => void;
}) {
  const is = active === sortKey;
  return (
    <th
      onClick={() => onClick(sortKey)}
      className="text-left px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-gray-400 cursor-pointer select-none hover:text-gray-200"
    >
      {label}{is ? (dir === "asc" ? " ↑" : " ↓") : ""}
    </th>
  );
}

export function PipelineTable({ prospects, onOpen, isLoading }: Props) {
  const [sortKey, setSortKey] = useState<SortKey | null>("vrGrade");
  const [dir, setDir] = useState<"asc" | "desc">("asc");

  const handleSort = (k: SortKey) => {
    if (k === sortKey) setDir(dir === "asc" ? "desc" : "asc");
    else { setSortKey(k); setDir("asc"); }
  };

  const sorted = useMemo(() => {
    if (!sortKey) return prospects;
    const arr = [...prospects];
    arr.sort((a, b) => compare(a, b, sortKey));
    return dir === "desc" ? arr.reverse() : arr;
  }, [prospects, sortKey, dir]);

  return (
    <div className="md:overflow-x-auto md:bg-gray-900 md:border md:border-gray-800 md:rounded-xl">
      <table className="w-full text-sm mobile-card-table">
        <thead className="border-b border-gray-800">
          <tr>
            <HeaderCell label="Prospect"   sortKey="name"         active={sortKey} dir={dir} onClick={handleSort} />
            <HeaderCell label="Company"    sortKey="company"      active={sortKey} dir={dir} onClick={handleSort} />
            <HeaderCell label="Stage"      sortKey="stage"        active={sortKey} dir={dir} onClick={handleSort} />
            <HeaderCell label="Channel"    sortKey="lastChannel"  active={sortKey} dir={dir} onClick={handleSort} />
            <HeaderCell label="Last Touch" sortKey="lastTouchAt"  active={sortKey} dir={dir} onClick={handleSort} />
            <HeaderCell label="Next Touch" sortKey="nextTouchAt"  active={sortKey} dir={dir} onClick={handleSort} />
            <HeaderCell label="VR Grade"   sortKey="vrGrade"      active={sortKey} dir={dir} onClick={handleSort} />
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={7} className="px-3 py-8 text-center text-gray-500 italic">
                {isLoading ? "Loading…" : "No prospects yet"}
              </td>
            </tr>
          ) : sorted.map((p) => (
            <tr
              key={p.id}
              onClick={() => onOpen(p.id)}
              className="border-b border-gray-800/60 hover:bg-gray-800/60 cursor-pointer"
            >
              <td className="px-3 py-2 text-gray-100">{p.name}</td>
              <td className="px-3 py-2 text-gray-300">{p.company}</td>
              <td className="px-3 py-2 text-gray-300">{STAGE_LABEL[p.stage]}</td>
              <td className="px-3 py-2 text-gray-400 font-mono text-xs">
                {p.lastChannel ? canonicalChannel(p.lastChannel) : "—"}
              </td>
              <td className="px-3 py-2 text-gray-400 font-mono text-xs">{fmtDate(p.lastTouchAt)}</td>
              <td className="px-3 py-2 text-gray-400 font-mono text-xs">{fmtDate(p.nextTouchAt)}</td>
              <td className="px-3 py-2">
                {p.vrGrade ? (
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                    {p.vrGrade}
                  </span>
                ) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
