"use client";

/**
 * Contract: frontend/components/dashboard/WelcomeBanner.tsx
 * Purpose:  Amber welcome strip shown within 24h of onboarding completion
 * Layer:    UI component
 * Consumers: dashboard page, layout
 */

import { useState, useEffect } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface WelcomeBannerProps {
  /** ISO timestamp from client.onboarding_completed_at */
  onboardingCompletedAt?: string | null;
  /** ISO timestamp from client.welcome_banner_dismissed_at */
  welcomeBannerDismissedAt?: string | null;
  /** Estimated minutes until first prospects appear */
  estimatedMinutes?: number;
  /** Called when user dismisses — caller should persist to API */
  onDismiss?: () => void;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function isWithin24Hours(isoTimestamp: string): boolean {
  const completed = new Date(isoTimestamp).getTime();
  const now = Date.now();
  return now - completed < 24 * 60 * 60 * 1000;
}

// ─── Component ───────────────────────────────────────────────────────────────

export function WelcomeBanner({
  onboardingCompletedAt,
  welcomeBannerDismissedAt,
  estimatedMinutes = 28,
  onDismiss,
}: WelcomeBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const [visible, setVisible] = useState(false);

  // Determine if banner should show
  useEffect(() => {
    if (!onboardingCompletedAt) return;
    if (welcomeBannerDismissedAt) return;
    if (!isWithin24Hours(onboardingCompletedAt)) return;
    setVisible(true);
  }, [onboardingCompletedAt, welcomeBannerDismissedAt]);

  function handleDismiss() {
    setDismissed(true);
    // Animate out then call parent
    setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, 400);
  }

  if (!visible) return null;

  return (
    <>
      <style>{`
        @keyframes bannerSlideDown {
          from { transform: translateY(-100%); opacity: 0; }
          to   { transform: translateY(0); opacity: 1; }
        }
      `}</style>
      <div
        style={{
          position: "fixed",
          top: 61,
          left: 0,
          right: 0,
          background: "rgba(212,149,106,0.08)",
          borderBottom: "1px solid rgba(212,149,106,0.28)",
          padding: "14px 48px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          zIndex: 99,
          animation: dismissed
            ? "none"
            : "bannerSlideDown 0.6s cubic-bezier(0.2,0.8,0.2,1)",
          opacity: dismissed ? 0 : 1,
          transform: dismissed ? "translateY(-100%)" : "translateY(0)",
          transition: dismissed
            ? "opacity 0.4s cubic-bezier(0.2,0.8,0.2,1), transform 0.4s cubic-bezier(0.2,0.8,0.2,1)"
            : "none",
        }}
        role="status"
        aria-label="Setup complete notification"
      >
        {/* Text */}
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "#2E2B26",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          {/* Amber dot */}
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#D4956A",
              display: "inline-block",
              flexShrink: 0,
            }}
          />
          Setup complete. Your first cycle has started. First prospects appear
          within{" "}
          <strong style={{ color: "#D4956A", fontWeight: 500 }}>
            ~{estimatedMinutes} minutes.
          </strong>
        </div>

        {/* Dismiss button */}
        <button
          onClick={handleDismiss}
          aria-label="Dismiss banner"
          style={{
            background: "transparent",
            border: "none",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: "#7A756D",
            cursor: "pointer",
            padding: "4px 8px",
            transition: "color 0.2s",
          }}
          onMouseEnter={(e) =>
            ((e.target as HTMLButtonElement).style.color = "#D4956A")
          }
          onMouseLeave={(e) =>
            ((e.target as HTMLButtonElement).style.color = "#7A756D")
          }
        >
          Dismiss ×
        </button>
      </div>
    </>
  );
}
