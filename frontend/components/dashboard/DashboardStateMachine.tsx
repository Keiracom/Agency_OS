"use client";

/**
 * Contract: frontend/components/dashboard/DashboardStateMachine.tsx
 * Purpose:  Manage 4-state first-login flow: tour → empty → reveal → live
 * Layer:    UI component
 * Consumers: dashboard page
 */

import { useState, useEffect, useCallback } from "react";
import { MayaTourOverlay } from "./MayaTourOverlay";
import { LeaderboardReveal, type ProspectRow } from "./LeaderboardReveal";

// ─── Types ───────────────────────────────────────────────────────────────────

export type DashboardState = "tour" | "empty" | "reveal" | "live";

export interface DashboardStateMachineProps {
  /** Cycle status from backend / Supabase realtime */
  cycleStatus?: string | null;
  /** Real prospect data (used in reveal + live states) */
  prospects?: ProspectRow[];
  /** Rendered when state === 'live' */
  children: React.ReactNode;
}

// ─── Demo data shown during tour ─────────────────────────────────────────────

const DEMO_PROSPECTS: ProspectRow[] = [
  {
    id: "d1",
    company: "Northbeach Consulting",
    location: "Sydney CBD · 12 staff",
    industry: "Construction",
    intent: 84,
    affordability: 78,
    signals: "4 signals",
    status: "drafted",
  },
  {
    id: "d2",
    company: "Elevate Growth Partners",
    location: "Parramatta · 8 staff",
    industry: "Professional Services",
    intent: 79,
    affordability: 82,
    signals: "3 signals",
    status: "drafted",
  },
  {
    id: "d3",
    company: "Harbour Digital",
    location: "St Kilda · 6 staff",
    industry: "Technology",
    intent: 74,
    affordability: 70,
    signals: "5 signals",
    status: "scoring",
  },
  {
    id: "d4",
    company: "Ridgepoint Studio",
    location: "Fitzroy · 4 staff",
    industry: "Design",
    intent: 68,
    affordability: 65,
    signals: "3 signals",
    status: "scoring",
  },
  {
    id: "d5",
    company: "Meridian Brief Advisory",
    location: "Southbank · 15 staff",
    industry: "Finance",
    intent: 62,
    affordability: 88,
    signals: "2 signals",
    status: "enriching",
  },
  {
    id: "d6",
    company: "Clarion Strategy Group",
    location: "Carlton · 6 staff",
    industry: "Consulting",
    intent: 57,
    affordability: 72,
    signals: "2 signals",
    status: "enriching",
  },
];

// ─── Pipeline node visual (STATE 2: empty) ───────────────────────────────────

function EmptyPipelineVisual() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        marginBottom: 48,
      }}
    >
      <style>{`
        @keyframes barPulse { 0%,100%{ opacity:.3; } 50%{ opacity:1; } }
      `}</style>
      {(["01", "02", "03", "04"] as const).map((label, i) => {
        const isWorking = i < 2;
        return (
          <div key={label} className="flex items-center gap-6">
            <div
              style={{
                width: 64,
                height: 64,
                border: `1px solid ${isWorking ? "#D4956A" : "rgba(12,10,8,0.14)"}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 9,
                letterSpacing: "0.1em",
                textTransform: "uppercase" as const,
                color: isWorking ? "#D4956A" : "#7A756D",
                position: "relative" as const,
              }}
            >
              {isWorking && (
                <div
                  style={{
                    position: "absolute",
                    top: -1,
                    left: 0,
                    right: 0,
                    height: 2,
                    background: "#D4956A",
                    animation: "barPulse 2s ease-in-out infinite",
                  }}
                />
              )}
              {label}
            </div>
            {i < 3 && (
              <div
                style={{
                  width: 40,
                  height: 1,
                  background: i < 1 ? "#D4956A" : "rgba(12,10,8,0.14)",
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Demo leaderboard (tour state, static, no animation) ─────────────────────

function DemoLeaderboard() {
  return (
    <div style={{ marginBottom: 44 }}>
      <div
        className="flex items-center gap-3"
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase" as const,
          color: "#7A756D",
          marginBottom: 18,
        }}
      >
        <span>Prospect leaderboard</span>
        <span
          style={{
            fontSize: 9,
            letterSpacing: "0.1em",
            padding: "3px 10px",
            background: "rgba(212,149,106,0.10)",
            color: "#D4956A",
          }}
        >
          Demo data
        </span>
        <div style={{ flex: 1, height: 1, background: "rgba(12,10,8,0.08)" }} />
      </div>
      <div style={{ border: "1px solid rgba(12,10,8,0.08)" }}>
        {/* Header */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "48px 1.4fr 1fr 0.7fr 0.7fr 0.7fr 120px",
            padding: "14px 24px",
            background: "#EDE8E0",
            borderBottom: "1px solid rgba(12,10,8,0.08)",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9,
            letterSpacing: "0.12em",
            textTransform: "uppercase" as const,
            color: "#7A756D",
          }}
        >
          <div>#</div>
          <div>Prospect</div>
          <div>Industry</div>
          <div>Intent</div>
          <div>Afford.</div>
          <div>Signals</div>
          <div>Status</div>
        </div>
        {/* Rows */}
        {DEMO_PROSPECTS.map((p) => (
          <div
            key={p.id}
            style={{
              display: "grid",
              gridTemplateColumns: "48px 1.4fr 1fr 0.7fr 0.7fr 0.7fr 120px",
              padding: "18px 24px",
              borderBottom: "1px solid rgba(12,10,8,0.08)",
              alignItems: "center",
              fontSize: 13,
              color: "#2E2B26",
              background: "#F7F3EE",
            }}
          >
            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: "#7A756D",
              }}
            >
              —
            </div>
            <div>
              <span style={{ fontWeight: 500, color: "#0C0A08" }}>
                {p.company}
              </span>
              <span
                style={{
                  display: "block",
                  fontSize: 11,
                  color: "#7A756D",
                  fontWeight: 300,
                  marginTop: 2,
                }}
              >
                {p.location}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "#7A756D" }}>{p.industry}</div>
            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 15,
                fontWeight: 500,
                color: p.intent >= 80 ? "#D4956A" : p.intent >= 65 ? "#0C0A08" : "#7A756D",
              }}
            >
              {p.intent}
            </div>
            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 15,
                fontWeight: 500,
                color:
                  p.affordability >= 80
                    ? "#D4956A"
                    : p.affordability >= 65
                    ? "#0C0A08"
                    : "#7A756D",
              }}
            >
              {p.affordability}
            </div>
            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10,
                color: "#7A756D",
              }}
            >
              {p.signals}
            </div>
            <div>
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase" as const,
                  padding: "5px 12px",
                  background:
                    p.status === "drafted"
                      ? "rgba(212,149,106,0.10)"
                      : "rgba(12,10,8,0.06)",
                  color:
                    p.status === "drafted" ? "#D4956A" : "#7A756D",
                }}
              >
                {p.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main state machine ───────────────────────────────────────────────────────

export function DashboardStateMachine({
  cycleStatus,
  prospects = [],
  children,
}: DashboardStateMachineProps) {
  const [state, setState] = useState<DashboardState>(() => {
    if (typeof window !== "undefined" &&
        localStorage.getItem("agencyos_tour_seen")) {
      return "live";
    }
    return "tour";
  });

  // Watch for backend ready signal
  useEffect(() => {
    if (state === "empty" && cycleStatus === "ready_for_reveal") {
      setState("reveal");
    }
  }, [cycleStatus, state]);

  const handleTourComplete = useCallback(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("agencyos_tour_seen", "true");
    }
    if (cycleStatus === "ready_for_reveal") {
      setState("reveal");
    } else {
      setState("empty");
    }
  }, [cycleStatus]);

  const handleRevealComplete = useCallback(() => {
    setState("live");
  }, []);

  // ── STATE 4: Live (all subsequent logins) ──────────────────────────────────
  if (state === "live") {
    return <>{children}</>;
  }

  // ── STATE 3: Reveal ────────────────────────────────────────────────────────
  if (state === "reveal") {
    return (
      <div id="highlightLeaderboard">
        <LeaderboardReveal
          prospects={prospects.length > 0 ? prospects : DEMO_PROSPECTS}
          onRevealComplete={handleRevealComplete}
          isDemo={prospects.length === 0}
        />
      </div>
    );
  }

  // ── STATE 2: Empty (tour done, data not ready) ─────────────────────────────
  if (state === "empty") {
    return (
      <div
        style={{
          padding: "80px 0",
          textAlign: "center",
          animation: "fadeIn 0.6s",
        }}
      >
        <style>{`@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }`}</style>
        <EmptyPipelineVisual />
        <h2
          style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: 28,
            fontWeight: 700,
            lineHeight: 1.15,
            marginBottom: 14,
          }}
        >
          Your prospects are being{" "}
          <em style={{ fontStyle: "italic", color: "#D4956A" }}>
            discovered and scored.
          </em>
        </h2>
        <p
          style={{
            fontSize: 15,
            color: "#7A756D",
            lineHeight: 1.7,
            maxWidth: 460,
            margin: "0 auto 28px",
          }}
        >
          The enrichment pipeline is running right now. Once scoring is
          complete, your prospect leaderboard will appear here — highest intent
          first, outreach drafts ready for review.
        </p>
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            letterSpacing: "0.08em",
            color: "#D4956A",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#D4956A",
              display: "inline-block",
              animation: "blink 1.4s ease-in-out infinite",
            }}
          />
          <style>{`@keyframes blink { 0%,100%{ opacity:1; } 50%{ opacity:.25; } }`}</style>
          Processing · Estimated 4 minutes remaining
        </div>
      </div>
    );
  }

  // ── STATE 1: Tour (first login) ────────────────────────────────────────────
  return (
    <>
      {/* Demo leaderboard visible behind tour overlay */}
      <div id="highlightLeaderboard">
        <DemoLeaderboard />
      </div>

      {/* Maya tour overlay */}
      <MayaTourOverlay
        onComplete={handleTourComplete}
        onSkip={handleTourComplete}
      />
    </>
  );
}
