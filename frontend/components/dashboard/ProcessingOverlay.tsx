/**
 * ProcessingOverlay.tsx - Campaign Processing Overlay
 * Phase: Operation Modular Cockpit
 * 
 * Full-screen overlay shown during campaign activation.
 * Displays progress through processing stages.
 */

"use client";

import { RefreshCw, Search, Users, Send, Play, CheckCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

// ============================================
// Types
// ============================================

interface ProcessingStage {
  label: string;
  icon: LucideIcon;
}

interface ProcessingOverlayProps {
  isVisible: boolean;
  /** Current stage index (0-based) */
  stage: number;
  /** Custom stages (optional) */
  stages?: ProcessingStage[];
  /** Title text */
  title?: string;
  /** Subtitle text */
  subtitle?: string;
}

// ============================================
// Default Configuration
// ============================================

const defaultStages: ProcessingStage[] = [
  { label: "Preparing your campaigns...", icon: RefreshCw },
  { label: "Finding ideal prospects...", icon: Search },
  { label: "Researching & qualifying leads...", icon: Users },
  { label: "Setting up outreach sequences...", icon: Send },
  { label: "Activating campaigns...", icon: Play },
];

// ============================================
// Component
// ============================================

export function ProcessingOverlay({
  isVisible,
  stage,
  stages = defaultStages,
  title,
  subtitle = "This usually takes a few moments. Your campaigns will be ready shortly.",
}: ProcessingOverlayProps) {
  if (!isVisible) return null;

  const currentStage = stages[stage] ?? stages[0];

  return (
    <div className="fixed inset-0 bg-white/95 flex items-center justify-center z-50 animate-in fade-in duration-300">
      <div className="text-center max-w-md mx-4">
        {/* Spinner */}
        <div className="w-16 h-16 mx-auto mb-6 relative">
          <div className="absolute inset-0 border-4 border-blue-100 rounded-full" />
          <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin" />
        </div>

        {/* Title */}
        <h2 className="text-xl font-semibold text-slate-900 mb-2">
          {title ?? currentStage?.label ?? "Processing..."}
        </h2>
        <p className="text-sm text-slate-500 mb-8">{subtitle}</p>

        {/* Progress Steps */}
        <div className="space-y-3">
          {stages.map((s, i) => (
            <div
              key={i}
              className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all duration-300 ${
                i < stage
                  ? "bg-emerald-50"
                  : i === stage
                  ? "bg-blue-50"
                  : "bg-slate-50"
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center transition-all duration-300 ${
                  i < stage
                    ? "bg-emerald-500 text-white"
                    : i === stage
                    ? "bg-blue-500 text-white"
                    : "bg-slate-200 text-slate-400"
                }`}
              >
                {i < stage ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <s.icon
                    className={`w-3 h-3 ${i === stage ? "animate-pulse" : ""}`}
                  />
                )}
              </div>
              <span
                className={`text-sm transition-all duration-300 ${
                  i < stage
                    ? "text-emerald-700"
                    : i === stage
                    ? "text-blue-700 font-medium"
                    : "text-slate-400"
                }`}
              >
                {s.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ProcessingOverlay;
