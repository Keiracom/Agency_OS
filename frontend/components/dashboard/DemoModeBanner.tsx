/**
 * FILE: frontend/components/dashboard/DemoModeBanner.tsx
 * PURPOSE: Persistent amber banner shown when the backend reports
 *          IS_DEMO_MODE=true. Cannot be dismissed in the UI — only
 *          the env toggle clears it.
 * PHASE:   DEMO-BUILD-V1
 *
 * Reads /api/v1/dashboard/demo-mode on mount. Renders nothing when the
 * flag is off (or the fetch fails).
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import api from "@/lib/api";

interface DemoModeResponse {
  is_demo_mode: boolean;
  message?: string | null;
}

async function fetchDemoMode(): Promise<DemoModeResponse> {
  try {
    return await api.get<DemoModeResponse>("/api/v1/dashboard/demo-mode");
  } catch {
    return { is_demo_mode: false };
  }
}

export function DemoModeBanner() {
  const { data } = useQuery({
    queryKey: ["demo-mode"],
    queryFn: fetchDemoMode,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  if (!data?.is_demo_mode) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="w-full bg-amber-500/15 border-b border-amber-500/40 text-amber-100 px-4 py-2.5 flex items-center gap-3 font-mono text-xs uppercase tracking-widest"
    >
      <AlertTriangle className="w-4 h-4 text-amber-300 shrink-0" strokeWidth={2} />
      <span className="font-bold text-amber-200">DEMO MODE</span>
      <span className="text-amber-100/90 normal-case tracking-normal text-[12px]">
        {data.message ??
          "No outreach will be sent. Data is real prospect intelligence."}
      </span>
    </div>
  );
}
