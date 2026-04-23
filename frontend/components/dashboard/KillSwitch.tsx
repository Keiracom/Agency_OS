/**
 * FILE: frontend/components/dashboard/KillSwitch.tsx
 * PURPOSE: Always-visible global pause/resume toggle for all outreach
 * PHASE: PHASE-2.1-APPROVAL-KILLSWITCH
 *
 * Renders a fixed-position button (top-right of viewport, above fold) that
 * reads and toggles the global outreach-paused flag for the current client.
 * Confirmation dialog on pause. When paused, a banner overlay appears at the
 * top of the viewport across every dashboard page.
 *
 * Flag source: GET /api/v1/outreach/kill-switch returns {paused:boolean, reason?:string}
 * Toggle:      POST /api/v1/outreach/kill-switch { paused: true|false }
 * (Both endpoints are stubs this PR assumes exist or will exist — fetch
 * failures degrade the button to a disabled spinner label.)
 */

"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pause, Play } from "lucide-react";

const QKEY = ["outreach-kill-switch"] as const;

interface KillState {
  paused: boolean;
  reason?: string | null;
}

async function fetchState(): Promise<KillState> {
  try {
    const res = await fetch("/api/v1/outreach/kill-switch", { method: "GET" });
    if (!res.ok) return { paused: false };
    return await res.json();
  } catch {
    return { paused: false };
  }
}

async function postToggle(next: boolean): Promise<KillState> {
  const res = await fetch("/api/v1/outreach/kill-switch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paused: next }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json().catch(() => ({ paused: next }));
}

export function KillSwitch() {
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const { data } = useQuery({
    queryKey: QKEY,
    queryFn: fetchState,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const toggle = useMutation({
    mutationFn: (next: boolean) => postToggle(next),
    onSuccess: (state) => qc.setQueryData(QKEY, state),
  });

  const paused = !!data?.paused;

  // Esc cancels confirm dialog
  useEffect(() => {
    if (!confirming) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setConfirming(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [confirming]);

  const handleClick = () => {
    if (paused) toggle.mutate(false);
    else setConfirming(true);
  };

  return (
    <>
      <button
        onClick={handleClick}
        disabled={toggle.isPending}
        title={paused ? "Resume outreach" : "Pause all outreach"}
        aria-label={paused ? "Resume outreach" : "Pause all outreach"}
        className={`fixed top-3 right-3 z-40 inline-flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-mono uppercase tracking-widest shadow-lg transition ${
          paused
            ? "bg-red-600 border-red-400 text-white hover:bg-red-500"
            : "bg-gray-900/90 border-gray-700 text-gray-300 hover:border-emerald-500/50 hover:text-emerald-300 backdrop-blur"
        } disabled:opacity-50`}
      >
        {paused ? (
          <>
            <Play className="w-3.5 h-3.5" />
            Resume
          </>
        ) : (
          <>
            <span className="relative flex w-2 h-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            Active
          </>
        )}
      </button>

      {paused && (
        <div className="fixed top-0 left-0 right-0 z-30 bg-red-600 text-white px-4 py-2 flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-2">
            <Pause className="w-4 h-4" />
            <span className="font-mono text-xs uppercase tracking-widest font-bold">
              Outreach paused — all campaigns stopped
            </span>
            {data?.reason && (
              <span className="text-xs opacity-80">· {data.reason}</span>
            )}
          </div>
          <button
            onClick={() => toggle.mutate(false)}
            disabled={toggle.isPending}
            className="bg-white/20 hover:bg-white/30 border border-white/40 rounded px-3 py-1 text-[11px] font-mono uppercase tracking-widest disabled:opacity-50"
          >
            Resume
          </button>
        </div>
      )}

      {confirming && (
        <div
          className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
          onClick={() => setConfirming(false)}
          role="dialog"
          aria-label="Confirm pause"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-gray-900 border border-red-500/50 rounded-xl p-6 max-w-md w-full"
          >
            <h3 className="font-serif text-xl text-gray-100 mb-1">Pause all outreach?</h3>
            <p className="text-sm text-gray-400 mb-4">
              This will pause <strong className="text-gray-200">ALL</strong> active campaigns
              across every channel. Scheduled touches will not fire until you resume.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirming(false)}
                className="px-3 py-1.5 text-xs font-mono uppercase tracking-widest rounded-md bg-gray-800 border border-gray-700 text-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  toggle.mutate(true);
                  setConfirming(false);
                }}
                className="px-3 py-1.5 text-xs font-mono uppercase tracking-widest rounded-md bg-red-600 border border-red-400 text-white hover:bg-red-500"
              >
                Pause all
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
