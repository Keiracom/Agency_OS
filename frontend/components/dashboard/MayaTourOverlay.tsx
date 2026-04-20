"use client";

import { useState, useEffect, useRef } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

export type TourHighlightId =
  | "highlightHeader"
  | "highlightPipeline"
  | "highlightLeaderboard"
  | "highlightPause"
  | null;

interface TourStep {
  text: string;
  highlightLabel: string;
  highlight: TourHighlightId;
  isFinal?: boolean;
}

interface MayaTourOverlayProps {
  onComplete: () => void;
  onSkip: () => void;
}

// ─── Tour script (8 steps extracted from prototype) ──────────────────────────

const TOUR_STEPS: TourStep[] = [
  {
    text: `Welcome to your dashboard. While we're talking, the system is already running — discovering prospects across your target area, enriching their data, and scoring their intent. <strong>By the time we finish this tour, your real prospects will be ready.</strong>`,
    highlight: null,
    highlightLabel: "",
  },
  {
    text: `This is your <span class="text-amber-500">cycle header</span>. It tells you where you are — which cycle, which day, how long it's been running. You're on Ignition at your founding rate. <strong>Each cycle runs for 30 days</strong>, then a new one starts automatically with fresh prospects.`,
    highlight: "highlightHeader",
    highlightLabel: "Cycle header",
  },
  {
    text: `This is the <span class="text-amber-500">pipeline</span>. Four stages: Discover finds businesses. Enrich reads their website, ads, reviews, hiring activity. Score rates their intent and affordability. Draft generates personalised outreach across email, LinkedIn, and voice. <strong>Every prospect passes through all four stages before you see them.</strong>`,
    highlight: "highlightPipeline",
    highlightLabel: "Pipeline stages",
  },
  {
    text: `This is the <span class="text-amber-500">prospect leaderboard</span>. Right now it's showing example data so you can see the layout. When your real prospects arrive, they'll appear here ranked by intent score — highest first. <strong>The prospects most likely to need your services are always at the top.</strong>`,
    highlight: "highlightLeaderboard",
    highlightLabel: "Prospect leaderboard",
  },
  {
    text: `Each prospect has two scores. <span class="text-amber-500">Intent</span> measures buying signals — are they actively looking for what you sell? Ad spend, hiring, declining reviews, founder posts about lead generation. <span class="text-amber-500">Affordability</span> checks whether they can pay — GST registration, entity type, business size. <strong>Both have to pass before a prospect enters your outreach.</strong>`,
    highlight: "highlightLeaderboard",
    highlightLabel: "Scoring explained",
  },
  {
    text: `Every message across every channel is <strong>visible in your dashboard before it sends</strong>. Email, LinkedIn connection requests, voice call scripts — all drafted, all editable. You can release everything in one click, or pause, edit, or cancel anything individually. <strong>You see all of it, always.</strong>`,
    highlight: null,
    highlightLabel: "Outreach control",
  },
  {
    text: `See that button in the top right? <span class="text-amber-500">Pause Cycle</span>. One click halts everything — all outreach, all channels, immediately. No support ticket, no waiting. You pause, you decide, you resume when you're ready. <strong>It's always there, always one click.</strong>`,
    highlight: "highlightPause",
    highlightLabel: "Pause Cycle",
  },
  {
    text: `That's everything you need to know to start. When I close, your real prospect data will appear — ranked by intent, with outreach drafts ready for your review. <strong>Welcome to Agency OS.</strong>`,
    highlight: null,
    highlightLabel: "",
    isFinal: true,
  },
];

// ─── Highlight ring management (applies amber outline to referenced elements) -

function useHighlightRing(highlightId: TourHighlightId) {
  const prevId = useRef<TourHighlightId>(null);

  useEffect(() => {
    // Remove previous highlight
    if (prevId.current) {
      const el = document.getElementById(prevId.current);
      if (el) {
        el.style.outline = "";
        el.style.outlineOffset = "";
        el.style.boxShadow = "";
        el.style.transition = "";
      }
    }
    // Apply new highlight
    if (highlightId) {
      const el = document.getElementById(highlightId);
      if (el) {
        el.style.outline = "2px solid #D4956A";
        el.style.outlineOffset = "6px";
        el.style.boxShadow = "0 0 0 8px rgba(212,149,106,0.08)";
        el.style.transition = "all 0.4s cubic-bezier(0.2,0.8,0.2,1)";
      }
    }
    prevId.current = highlightId;

    return () => {
      // Cleanup on unmount
      if (highlightId) {
        const el = document.getElementById(highlightId);
        if (el) {
          el.style.outline = "";
          el.style.outlineOffset = "";
          el.style.boxShadow = "";
        }
      }
    };
  }, [highlightId]);
}

// ─── Component ───────────────────────────────────────────────────────────────

export function MayaTourOverlay({ onComplete, onSkip }: MayaTourOverlayProps) {
  const [stepIdx, setStepIdx] = useState(0);
  const [visible, setVisible] = useState(true);

  const step = TOUR_STEPS[stepIdx];
  useHighlightRing(step.highlight);

  function handleNext() {
    if (stepIdx < TOUR_STEPS.length - 1) {
      setStepIdx((i) => i + 1);
    }
  }

  function handleFinish() {
    setVisible(false);
    setTimeout(onComplete, 420);
  }

  function handleSkip() {
    setVisible(false);
    setTimeout(onSkip, 420);
  }

  return (
    <div
      className="fixed bottom-8 right-8 z-[200] flex flex-col items-end gap-4 max-w-[420px]"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(20px)",
        transition: "opacity 0.4s, transform 0.4s",
        animation: "mayaIn 0.6s cubic-bezier(0.2,0.8,0.2,1)",
      }}
    >
      <style>{`
        @keyframes mayaIn {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Speech bubble */}
      <div
        className="relative w-full p-7"
        style={{
          background: "#0C0A08",
          color: "#F7F3EE",
          boxShadow: "0 16px 48px rgba(12,10,8,0.18)",
        }}
      >
        {/* Caret */}
        <div
          className="absolute"
          style={{
            bottom: -8,
            right: 48,
            width: 16,
            height: 16,
            background: "#0C0A08",
            transform: "rotate(45deg)",
          }}
        />

        {/* Maya name row */}
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: "#D4956A" }}
          >
            <span
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 12,
                fontWeight: 500,
                color: "#0C0A08",
              }}
            >
              M
            </span>
          </div>
          <div>
            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "#D4956A",
              }}
            >
              Maya
            </div>
            <div style={{ fontSize: 10, color: "rgba(247,243,238,0.5)" }}>
              Your Agency OS guide
            </div>
          </div>
        </div>

        {/* Highlight label */}
        {step.highlightLabel && (
          <div
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 9,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "#D4956A",
              marginBottom: 10,
            }}
          >
            {step.highlightLabel}
          </div>
        )}

        {/* Tour text */}
        <div
          className="text-sm leading-relaxed mb-5"
          style={{
            color: "rgba(247,243,238,0.85)",
            minHeight: 80,
            fontWeight: 300,
          }}
          dangerouslySetInnerHTML={{ __html: step.text }}
        />

        {/* Controls */}
        <div className="flex items-center justify-between">
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 9,
              letterSpacing: "0.1em",
              color: "rgba(247,243,238,0.45)",
            }}
          >
            {stepIdx + 1} of {TOUR_STEPS.length}
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleSkip}
              className="px-4 py-2 text-xs transition-all"
              style={{
                background: "transparent",
                color: "rgba(247,243,238,0.5)",
                border: "1px solid rgba(255,255,255,0.12)",
                fontFamily: "'DM Sans', sans-serif",
                fontWeight: 500,
                cursor: "pointer",
              }}
              onMouseEnter={(e) => {
                (e.target as HTMLButtonElement).style.color = "#D4956A";
                (e.target as HTMLButtonElement).style.borderColor = "#D4956A";
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLButtonElement).style.color =
                  "rgba(247,243,238,0.5)";
                (e.target as HTMLButtonElement).style.borderColor =
                  "rgba(255,255,255,0.12)";
              }}
            >
              Skip tour
            </button>

            {step.isFinal ? (
              <button
                onClick={handleFinish}
                className="px-4 py-2 text-xs font-medium transition-opacity hover:opacity-88"
                style={{
                  background: "#D4956A",
                  color: "#0C0A08",
                  border: "none",
                  fontFamily: "'DM Sans', sans-serif",
                  cursor: "pointer",
                }}
              >
                Show my prospects →
              </button>
            ) : (
              <button
                onClick={handleNext}
                className="px-4 py-2 text-xs font-medium transition-opacity hover:opacity-88"
                style={{
                  background: "#D4956A",
                  color: "#0C0A08",
                  border: "none",
                  fontFamily: "'DM Sans', sans-serif",
                  cursor: "pointer",
                }}
              >
                Next →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
