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
      className="text-left px-[18px] py-3.5 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3 cursor-pointer select-none hover:text-amber bg-surface border-b border-rule font-semibold"
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
    <div className="md:overflow-x-auto md:bg-panel md:border md:border-rule md:rounded-[10px]">
      <table className="w-full text-[13px] mobile-card-table">
        <thead>
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
              <td colSpan={7} className="px-[18px] py-8 text-center text-ink-3 italic">
                {isLoading ? "Loading…" : "No prospects yet"}
              </td>
            </tr>
          ) : sorted.map((p) => (
            <tr
              key={p.id}
              onClick={() => onOpen(p.id)}
              data-label="Row"
              className="border-b border-rule hover:bg-amber-soft cursor-pointer transition-colors"
            >
              <td data-label="Prospect"   className="px-[18px] py-4 font-display font-bold text-[14px] text-ink">
                {p.name}
              </td>
              <td data-label="Company"    className="px-[18px] py-4 text-ink-2">{p.company}</td>
              <td data-label="Stage"      className="px-[18px] py-4 text-ink-2">{STAGE_LABEL[p.stage]}</td>
              <td data-label="Channel"    className="px-[18px] py-4 font-mono text-[11px] text-ink-3">
                {p.lastChannel ? canonicalChannel(p.lastChannel) : "—"}
              </td>
              <td data-label="Last touch" className="px-[18px] py-4 font-mono text-[11px] text-ink-3">{fmtDate(p.lastTouchAt)}</td>
              <td data-label="Next touch" className="px-[18px] py-4 font-mono text-[11px] text-ink-3">{fmtDate(p.nextTouchAt)}</td>
              <td data-label="Grade"      className="px-[18px] py-4">
                {p.vrGrade ? (
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
                ) : <span className="text-ink-3">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
