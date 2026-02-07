"use client";

/**
 * Maya AI Companion
 * Matches: dashboard-v3.html maya-companion design
 * Floating assistant bubble with onboarding walkthrough
 */

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

interface MayaStep {
  content: string;
  action: string;
  highlight?: string;
}

const mayaSteps: MayaStep[] = [
  {
    content: "Welcome to Agency OS! 👋 I'm Maya, your digital employee. I'm currently analyzing your website to understand your agency and find your ideal clients. This usually takes 2-3 minutes.",
    action: "Got it",
  },
  {
    content: "While I analyze your website, I'm also setting up your email domains and phone numbers. These are pre-warmed and ready to use! 🚀",
    action: "Continue",
  },
  {
    content: "Once the analysis is complete, I'll suggest campaigns based on your ideal client profile. You'll see them on the Campaigns page.",
    action: "Show me",
    highlight: "campaigns-nav",
  },
  {
    content: "That's the basics! I'll be here in the corner whenever you need help. Click my avatar anytime to chat. 💬",
    action: "Finish tour",
  },
];

interface MayaCompanionProps {
  className?: string;
  defaultOpen?: boolean;
  showPulse?: boolean;
  onStepChange?: (step: number) => void;
  onComplete?: () => void;
}

export function MayaCompanion({
  className,
  defaultOpen = true,
  showPulse = true,
  onStepChange,
  onComplete,
}: MayaCompanionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPulsing, setIsPulsing] = useState(showPulse);

  const currentMayaStep = mayaSteps[currentStep];

  const handleNext = () => {
    const nextStep = currentStep + 1;
    
    if (nextStep >= mayaSteps.length) {
      setIsOpen(false);
      setIsPulsing(false);
      onComplete?.();
      return;
    }

    setCurrentStep(nextStep);
    onStepChange?.(nextStep);
  };

  const handleDismiss = () => {
    setIsOpen(false);
    setIsPulsing(false);
  };

  const toggleBubble = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className={cn("fixed bottom-6 right-6 z-50", className)}>
      {/* Bubble */}
      {isOpen && currentMayaStep && (
        <div 
          className="absolute bottom-full right-0 mb-4 w-80 bg-[#12121A] border border-[#2A2A3A] rounded-2xl p-5 shadow-2xl shadow-black/40 animate-in slide-in-from-bottom-3 fade-in duration-300"
        >
          {/* Header */}
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#7C3AED] to-[#9D5CFF] flex items-center justify-center text-white font-bold shadow-lg shadow-purple-500/30">
              M
            </div>
            <div>
              <p className="font-semibold text-white text-sm">Maya</p>
              <p className="text-xs text-[#6B6B7B]">Your Digital Employee</p>
            </div>
          </div>

          {/* Content */}
          <p className="text-sm text-[#A0A0B0] leading-relaxed mb-4">
            {currentMayaStep.content}
          </p>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={handleNext}
              className="flex-1 px-4 py-2.5 bg-[#7C3AED] hover:bg-[#9D5CFF] text-white text-sm font-medium rounded-lg transition-colors"
            >
              {currentMayaStep.action}
            </button>
            <button
              onClick={handleDismiss}
              className="px-4 py-2.5 bg-[#1A1A24] hover:bg-[#2A2A3A] text-[#A0A0B0] text-sm font-medium rounded-lg border border-[#2A2A3A] transition-colors"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Avatar Button */}
      <button
        onClick={toggleBubble}
        className={cn(
          "w-16 h-16 rounded-full bg-gradient-to-br from-[#7C3AED] to-[#9D5CFF] border-[3px] border-[#12121A] shadow-lg shadow-purple-500/40 flex items-center justify-center text-white text-2xl font-bold transition-transform hover:scale-105",
          isPulsing && "animate-pulse"
        )}
        style={{
          animation: isPulsing ? "maya-pulse 2s infinite" : undefined,
        }}
      >
        M
      </button>

      <style jsx>{`
        @keyframes maya-pulse {
          0%, 100% {
            box-shadow: 0 8px 24px rgba(124, 58, 237, 0.4);
          }
          50% {
            box-shadow: 0 8px 32px rgba(124, 58, 237, 0.6), 0 0 0 8px rgba(124, 58, 237, 0.1);
          }
        }
      `}</style>
    </div>
  );
}
