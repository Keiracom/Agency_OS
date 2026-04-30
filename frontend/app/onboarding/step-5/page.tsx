"use client";

/**
 * FILE: frontend/app/onboarding/step-5/page.tsx
 * PURPOSE: Demo onboarding — Prospect universe build (simulated, no real API)
 * DESIGN: Bloomberg cream/amber palette, Playfair Display headings
 * NOTE: Animated 5-stage progress, then redirect to /dashboard
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2 } from "lucide-react";

const DEMO_AGENCY = "Bondi Digital Marketing";

const STAGES = [
  { id: "discovery", label: "Discovery" },
  { id: "verification", label: "Verification" },
  { id: "decision-maker", label: "Decision-Maker Identification" },
  { id: "scoring", label: "Scoring" },
  { id: "cards", label: "Card Generation" },
];

export default function OnboardingStep5() {
  const router = useRouter();

  // stageIndex: how many stages are complete (0-5)
  const [stageIndex, setStageIndex] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (stageIndex < STAGES.length) {
      const t = setTimeout(() => setStageIndex((s) => s + 1), 1000);
      return () => clearTimeout(t);
    } else {
      // All stages complete
      const t1 = setTimeout(() => setDone(true), 300);
      const t2 = setTimeout(() => router.push("/dashboard?demo=true"), 2300);
      return () => { clearTimeout(t1); clearTimeout(t2); };
    }
  }, [stageIndex, router]);

  // Progress 0–100 based on completed stages
  const progressPct = Math.round((stageIndex / STAGES.length) * 100);

  return (
    <div
      style={{ backgroundColor: "#F7F3EE", color: "#0C0A08", minHeight: "100vh" }}
      className="flex items-center justify-center px-4 py-16"
    >
      <div className="w-full" style={{ maxWidth: 640 }}>

        <StepIndicator current={5} total={5} />
        <AgencyBadge name={DEMO_AGENCY} />

        <h1
          style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 700,
            fontSize: "clamp(26px, 4.5vw, 38px)",
            lineHeight: 1.15,
            color: "#0C0A08",
            marginBottom: 12,
          }}
        >
          Building your
          <br />
          <em style={{ color: "#D4956A" }}>prospect universe</em>
        </h1>

        <p
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 300,
            fontSize: 15,
            lineHeight: 1.65,
            color: "#4A4540",
            marginBottom: 36,
          }}
        >
          Scanning Google Maps, verifying businesses, identifying decision-makers,
          and scoring each prospect. This only runs once.
        </p>

        {/* Progress bar */}
        <div
          style={{
            height: 6,
            background: "rgba(212,149,106,0.15)",
            borderRadius: 3,
            marginBottom: 32,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progressPct}%`,
              background: "linear-gradient(90deg, #D4956A 0%, #C07D4E 100%)",
              borderRadius: 3,
              transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
            }}
          />
        </div>

        {/* Stage list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 36 }}>
          {STAGES.map((stage, idx) => {
            const isComplete = idx < stageIndex;
            const isActive = idx === stageIndex;

            return (
              <div
                key={stage.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                  opacity: isComplete || isActive ? 1 : 0.3,
                  transition: "opacity 0.4s",
                }}
              >
                {isComplete ? (
                  <CheckCircle2
                    size={20}
                    style={{ color: "#D4956A", flexShrink: 0 }}
                  />
                ) : isActive ? (
                  <Loader2
                    size={20}
                    style={{ color: "#D4956A", flexShrink: 0 }}
                    className="animate-spin"
                  />
                ) : (
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      border: "1.5px solid rgba(212,149,106,0.35)",
                      flexShrink: 0,
                    }}
                  />
                )}

                <span
                  style={{
                    fontFamily: "'DM Sans', sans-serif",
                    fontWeight: isComplete ? 500 : 400,
                    fontSize: 15,
                    color: isComplete ? "#0C0A08" : isActive ? "#3A3530" : "#8A7F76",
                    transition: "color 0.3s, font-weight 0.3s",
                  }}
                >
                  {stage.label}
                </span>

                {isComplete && (
                  <span
                    style={{
                      marginLeft: "auto",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      letterSpacing: "0.08em",
                      color: "#D4956A",
                      textTransform: "uppercase",
                    }}
                  >
                    Done
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Completion message */}
        {done && (
          <div
            style={{
              border: "1.5px solid rgba(212,149,106,0.5)",
              background: "rgba(212,149,106,0.06)",
              padding: "22px 24px",
              display: "flex",
              alignItems: "center",
              gap: 14,
              animation: "fadeIn 0.5s ease-out",
            }}
          >
            <CheckCircle2 size={22} style={{ color: "#D4956A", flexShrink: 0 }} />
            <div>
              <p
                style={{
                  fontFamily: "'Playfair Display', serif",
                  fontWeight: 700,
                  fontSize: 18,
                  color: "#0C0A08",
                  marginBottom: 4,
                }}
              >
                23 prospects found.
              </p>
              <p
                style={{
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 14,
                  color: "#4A4540",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <Loader2 size={12} className="animate-spin" style={{ color: "#D4956A" }} />
                Opening dashboard...
              </p>
            </div>
          </div>
        )}

        {/* Progress counter */}
        {!done && (
          <p
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              letterSpacing: "0.1em",
              color: "#8A7F76",
              textTransform: "uppercase",
            }}
          >
            {progressPct}% complete
          </p>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 28 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 3,
            flex: 1,
            borderRadius: 2,
            backgroundColor: i < current ? "#D4956A" : "rgba(212,149,106,0.2)",
            transition: "background-color 0.3s",
          }}
        />
      ))}
      <span
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          letterSpacing: "0.1em",
          color: "#D4956A",
          marginLeft: 8,
          whiteSpace: "nowrap",
          textTransform: "uppercase",
        }}
      >
        {current} / {total}
      </span>
    </div>
  );
}

function AgencyBadge({ name }: { name: string }) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        background: "rgba(212,149,106,0.08)",
        border: "1px solid rgba(212,149,106,0.3)",
        padding: "5px 12px",
        marginBottom: 22,
      }}
    >
      <div style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: "#D4956A" }} />
      <span
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          letterSpacing: "0.08em",
          color: "#D4956A",
          textTransform: "uppercase",
        }}
      >
        {name}
      </span>
    </div>
  );
}
