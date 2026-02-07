/**
 * MayaCompanion.tsx - Maya Digital Assistant Component
 * Phase: Operation Modular Cockpit
 * 
 * Maya is the onboarding assistant that guides users through
 * the Agency OS platform.
 */

"use client";

import { useState } from "react";

// ============================================
// Types
// ============================================

interface MayaStep {
  content: string;
  action: string;
}

interface MayaCompanionProps {
  /** Custom steps (optional) */
  steps?: MayaStep[];
  /** Initial open state */
  initialOpen?: boolean;
  /** Callback when tour completes */
  onComplete?: () => void;
  /** Callback when dismissed */
  onDismiss?: () => void;
  /** Primary color (for theming) */
  primaryColor?: string;
}

// ============================================
// Default Configuration
// ============================================

const defaultSteps: MayaStep[] = [
  {
    content:
      "Welcome to Agency OS! 👋 I'm Maya, your digital employee. I'm currently analyzing your website to understand your agency and find your ideal clients. This usually takes 2-3 minutes.",
    action: "Got it",
  },
  {
    content:
      "While I analyze your website, I'm also setting up your email domains and phone numbers. These are pre-warmed and ready to use! 🚀",
    action: "Continue",
  },
  {
    content:
      "Once the analysis is complete, I'll suggest campaigns based on your ideal client profile. You'll see them on the Campaigns page.",
    action: "Show me",
  },
  {
    content:
      "That's the basics! I'll be here in the corner whenever you need help. Click my avatar anytime to chat. 💬",
    action: "Finish tour",
  },
];

// ============================================
// Component
// ============================================

export function MayaCompanion({
  steps = defaultSteps,
  initialOpen = true,
  onComplete,
  onDismiss,
  primaryColor = "blue",
}: MayaCompanionProps) {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPulsing, setIsPulsing] = useState(true);

  const currentMayaStep = steps[currentStep];

  const handleNext = () => {
    const nextStep = currentStep + 1;

    if (nextStep >= steps.length) {
      setIsOpen(false);
      setIsPulsing(false);
      onComplete?.();
      return;
    }

    setCurrentStep(nextStep);
  };

  const handleDismiss = () => {
    setIsOpen(false);
    setIsPulsing(false);
    onDismiss?.();
  };

  // Color classes based on primaryColor prop
  const colors = {
    blue: {
      gradient: "from-blue-500 to-blue-600",
      bg: "bg-blue-600",
      hover: "hover:bg-blue-700",
      shadow: "rgba(59, 130, 246, 0.4)",
      shadowPulse: "rgba(59, 130, 246, 0.6)",
      shadowRing: "rgba(59, 130, 246, 0.1)",
    },
    purple: {
      gradient: "from-purple-500 to-purple-600",
      bg: "bg-purple-600",
      hover: "hover:bg-purple-700",
      shadow: "rgba(147, 51, 234, 0.4)",
      shadowPulse: "rgba(147, 51, 234, 0.6)",
      shadowRing: "rgba(147, 51, 234, 0.1)",
    },
  };

  const colorSet = colors[primaryColor as keyof typeof colors] ?? colors.blue;

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Bubble */}
      {isOpen && currentMayaStep && (
        <div
          className="absolute bottom-full right-0 mb-4 w-80 rounded-2xl p-5 shadow-2xl animate-in slide-in-from-bottom-3 fade-in duration-300 bg-white border border-slate-200"
          style={{
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.15)",
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-3 mb-3">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold shadow-lg bg-gradient-to-br ${colorSet.gradient}`}
              style={{
                boxShadow: `0 4px 12px ${colorSet.shadow}`,
              }}
            >
              M
            </div>
            <div>
              <p className="font-semibold text-slate-900 text-sm">Maya</p>
              <p className="text-xs text-slate-500">Your Digital Employee</p>
            </div>
          </div>

          {/* Content */}
          <p className="text-sm leading-relaxed mb-4 text-slate-600">
            {currentMayaStep.content}
          </p>

          {/* Progress dots */}
          <div className="flex items-center gap-1.5 mb-4">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-all ${
                  i === currentStep
                    ? `${colorSet.bg} w-4`
                    : i < currentStep
                    ? colorSet.bg
                    : "bg-slate-200"
                }`}
              />
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={handleNext}
              className={`flex-1 px-4 py-2.5 text-white text-sm font-medium rounded-lg transition-colors ${colorSet.bg} ${colorSet.hover}`}
            >
              {currentMayaStep.action}
            </button>
            <button
              onClick={handleDismiss}
              className="px-4 py-2.5 text-sm font-medium rounded-lg transition-colors bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-16 h-16 rounded-full border-[3px] border-white shadow-lg flex items-center justify-center text-white text-2xl font-bold transition-transform hover:scale-105 bg-gradient-to-br ${colorSet.gradient}`}
        style={{
          boxShadow: `0 8px 24px ${colorSet.shadow}`,
          animation: isPulsing ? "maya-pulse 2s infinite" : undefined,
        }}
      >
        M
      </button>

      <style jsx>{`
        @keyframes maya-pulse {
          0%,
          100% {
            box-shadow: 0 8px 24px ${colorSet.shadow};
          }
          50% {
            box-shadow: 0 8px 32px ${colorSet.shadowPulse},
              0 0 0 8px ${colorSet.shadowRing};
          }
        }
      `}</style>
    </div>
  );
}

export default MayaCompanion;
