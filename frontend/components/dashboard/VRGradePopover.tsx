/**
 * FILE: frontend/components/dashboard/VRGradePopover.tsx
 * PURPOSE: Clickable VR grade badge + breakdown popover (sub-scores, strengths,
 *          improvements, evidence).
 * PHASE: PHASE-2.1-TIMELINE-VR-POPOVERS
 *
 * Renders nothing for breakdown details if all sub-scores are null — falls
 * back to just the grade letter. Smart positioning based on viewport space.
 */

"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import type { VRBreakdown } from "@/lib/hooks/useProspectDetail";

interface Props {
  grade: string | null;
  score: number | null;
  vr: VRBreakdown;
  /** Optional evidence bullets derived by caller from enrichment data. */
  evidence?: string[];
}

const GRADE_COLOR: Record<string, string> = {
  A: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  B: "bg-amber-500/10 text-amber-300 border-amber-500/40",
  C: "bg-amber-500/10 text-amber-300 border-amber-500/40",
  D: "bg-red-500/10 text-red-300 border-red-500/40",
  F: "bg-red-500/10 text-red-300 border-red-500/40",
};

export function VRGradePopover({ grade, score, vr, evidence = [] }: Props) {
  const [open, setOpen] = useState(false);
  const [placeAbove, setPlaceAbove] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const popRef = useRef<HTMLDivElement>(null);

  // Close on outside click / Esc
  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (
        popRef.current?.contains(e.target as Node) ||
        btnRef.current?.contains(e.target as Node)
      ) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Smart positioning: if the button is in the bottom half of the viewport,
  // render the popover above.
  useLayoutEffect(() => {
    if (!open || !btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    setPlaceAbove(rect.bottom > window.innerHeight / 2);
  }, [open]);

  if (!grade) return <span className="text-gray-600">—</span>;

  const hasSubScores =
    vr.intent !== null || vr.affordability !== null ||
    vr.authority !== null || vr.timing !== null;

  return (
    <div className="relative inline-block">
      <button
        ref={btnRef}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={`inline-flex items-center gap-1 text-[11px] font-mono font-bold px-2 py-0.5 rounded border ${GRADE_COLOR[grade] ?? ""}`}
      >
        {grade}
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          ref={popRef}
          className={`absolute right-0 z-50 w-72 bg-gray-950 border border-gray-700 rounded-lg shadow-xl p-3 ${
            placeAbove ? "bottom-full mb-2" : "top-full mt-2"
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500">
                VR grade
              </div>
              <div className={`text-2xl font-bold ${GRADE_COLOR[grade]?.split(" ").find((c) => c.startsWith("text-")) ?? ""}`}>
                {grade}
              </div>
            </div>
            {score !== null && (
              <div className="text-right">
                <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500">
                  Score
                </div>
                <div className="text-xl font-mono text-gray-100">{score}</div>
              </div>
            )}
          </div>

          {/* Sub-scores */}
          {hasSubScores ? (
            <div className="space-y-1.5 mb-3">
              <SubScoreBar label="Intent"        value={vr.intent} />
              <SubScoreBar label="Affordability" value={vr.affordability} />
              <SubScoreBar label="Authority"     value={vr.authority} />
              <SubScoreBar label="Timing"        value={vr.timing} />
            </div>
          ) : (
            <div className="text-[11px] text-gray-500 italic mb-3">
              Sub-scores not yet computed for this prospect.
            </div>
          )}

          {/* Strengths (A grades) / Improvements (D-F grades) */}
          {hasSubScores && (grade === "A" ? (
            <StrengthsList vr={vr} />
          ) : (grade === "D" || grade === "F") ? (
            <ImprovementsList vr={vr} />
          ) : null)}

          {/* Evidence */}
          {evidence.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-800">
              <div className="font-mono text-[10px] uppercase tracking-widest text-gray-500 mb-1">
                Evidence
              </div>
              <ul className="text-[11px] text-gray-300 space-y-1">
                {evidence.slice(0, 3).map((line, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-gray-600">·</span>
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SubScoreBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) {
    return (
      <div className="flex justify-between items-center text-[11px]">
        <span className="text-gray-500 font-mono uppercase tracking-wider">{label}</span>
        <span className="text-gray-600">—</span>
      </div>
    );
  }
  const pct = Math.max(0, Math.min(100, value));
  const barColor =
    pct >= 75 ? "bg-emerald-500" :
    pct >= 50 ? "bg-amber-500"   :
                "bg-red-500";
  return (
    <div className="text-[11px]">
      <div className="flex justify-between items-center mb-0.5">
        <span className="text-gray-400 font-mono uppercase tracking-wider">{label}</span>
        <span className="text-gray-200 font-mono">{pct}</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function rank(vr: VRBreakdown): Array<[string, number]> {
  return (
    [
      ["Intent",        vr.intent],
      ["Affordability", vr.affordability],
      ["Authority",     vr.authority],
      ["Timing",        vr.timing],
    ].filter(([, v]) => v !== null) as Array<[string, number]>
  );
}

function StrengthsList({ vr }: { vr: VRBreakdown }) {
  const strong = rank(vr).filter(([, v]) => v >= 75);
  if (strong.length === 0) return null;
  return (
    <div className="pt-2 border-t border-gray-800">
      <div className="font-mono text-[10px] uppercase tracking-widest text-emerald-400 mb-1">
        Strengths
      </div>
      <ul className="text-[11px] text-gray-300 space-y-0.5">
        {strong.map(([name, v]) => (
          <li key={name}>{name} is strong ({v})</li>
        ))}
      </ul>
    </div>
  );
}

function ImprovementsList({ vr }: { vr: VRBreakdown }) {
  const weak = rank(vr).filter(([, v]) => v < 50);
  if (weak.length === 0) return null;
  return (
    <div className="pt-2 border-t border-gray-800">
      <div className="font-mono text-[10px] uppercase tracking-widest text-red-400 mb-1">
        Improvements needed
      </div>
      <ul className="text-[11px] text-gray-300 space-y-0.5">
        {weak.map(([name, v]) => (
          <li key={name}>{name} is weak ({v})</li>
        ))}
      </ul>
    </div>
  );
}
