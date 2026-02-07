"use client";

/**
 * ICP Extraction Progress Bar
 * Matches: dashboard-v3.html extraction-bar design
 * Shows agency analysis progress during onboarding
 */

import { useEffect, useState } from "react";
import { Clock, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ExtractionStep {
  progress: number;
  status: string;
}

const extractionSteps: ExtractionStep[] = [
  { progress: 35, status: "Scraping website & extracting portfolio" },
  { progress: 45, status: "Extracting services & value proposition" },
  { progress: 60, status: "Finding portfolio companies" },
  { progress: 75, status: "Enriching portfolio data via Siege Waterfall" },
  { progress: 90, status: "Deriving ideal client profile" },
  { progress: 100, status: "Complete! Campaign suggestions ready" },
];

interface ExtractionBarProps {
  className?: string;
  initialProgress?: number;
  autoProgress?: boolean;
  onComplete?: () => void;
}

export function ExtractionBar({ 
  className, 
  initialProgress = 35,
  autoProgress = true,
  onComplete 
}: ExtractionBarProps) {
  const [progress, setProgress] = useState(initialProgress);
  const [status, setStatus] = useState(extractionSteps[0].status);
  const [isComplete, setIsComplete] = useState(initialProgress >= 100);

  useEffect(() => {
    if (!autoProgress || isComplete) return;

    let stepIndex = extractionSteps.findIndex(s => s.progress > progress);
    if (stepIndex === -1) stepIndex = extractionSteps.length - 1;

    const interval = setInterval(() => {
      stepIndex++;
      if (stepIndex >= extractionSteps.length) {
        clearInterval(interval);
        setIsComplete(true);
        onComplete?.();
        return;
      }

      const step = extractionSteps[stepIndex];
      setProgress(step.progress);
      setStatus(step.status);

      if (step.progress >= 100) {
        setIsComplete(true);
        onComplete?.();
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [autoProgress, isComplete, onComplete, progress]);

  return (
    <div
      className={cn(
        "rounded-xl p-4 flex items-center gap-5 transition-all duration-500",
        isComplete
          ? "bg-gradient-to-r from-[#10B981]/10 to-[#10B981]/5 border border-[#10B981]/30"
          : "bg-gradient-to-r from-[#7C3AED]/10 to-[#3B82F6]/10 border border-[#7C3AED]/30",
        className
      )}
    >
      {/* Icon */}
      <div className="w-12 h-12 rounded-xl bg-[#12121A] flex items-center justify-center flex-shrink-0">
        {isComplete ? (
          <CheckCircle className="w-6 h-6 text-[#10B981]" />
        ) : (
          <Clock className="w-6 h-6 text-[#7C3AED]" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h4 className="font-semibold text-sm text-white mb-1">
          {isComplete ? "Analysis Complete!" : "Analyzing your agency..."}
        </h4>
        <p className="text-sm text-[#A0A0B0] truncate">{status}</p>
      </div>

      {/* Progress */}
      <div className="w-48">
        <div className="h-2 bg-[#1A1A24] rounded-full overflow-hidden mb-1.5">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              isComplete
                ? "bg-[#10B981]"
                : "bg-gradient-to-r from-[#7C3AED] to-[#3B82F6]"
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-xs text-[#6B6B7B] text-right font-mono">{progress}%</p>
      </div>
    </div>
  );
}
