"use client";

/**
 * FILE: frontend/app/onboarding/linkedin/page.tsx
 * PURPOSE: LinkedIn connection onboarding step — Unipile OAuth
 * DIRECTIVE: #309 — Onboarding rebuild (full content replacement)
 * DESIGN: Cream #F7F3EE, Ink #0C0A08, Amber #D4956A
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ExternalLink, Loader2, ShieldCheck } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function LinkedInOnboardingPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLinkedInConnect = async () => {
    setError(null);
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/linkedin/connect`, {
        method: "GET",
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(
          data.detail || data.message || `LinkedIn connect failed (${res.status})`
        );
      }
      const data = await res.json();
      const authUrl =
        data.auth_url || data.oauth_url || data.redirect_url || data.url;
      if (authUrl) {
        window.location.href = authUrl;
      } else {
        router.push("/onboarding/agency");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-16 bg-cream text-ink"
    >
      <div className="w-full max-w-xl">
        {/* Step label */}
        <p
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "11px",
            letterSpacing: "0.12em",
            color: "#D4956A",
            textTransform: "uppercase",
            marginBottom: "24px",
          }}
        >
          Step 2 of 4 — LinkedIn
        </p>

        {/* Headline */}
        <h1
          style={{
            fontFamily: "'Playfair Display', serif",
            fontWeight: 700,
            fontSize: "clamp(28px, 5vw, 40px)",
            lineHeight: 1.15,
            color: "#0C0A08",
            marginBottom: "12px",
          }}
        >
          Connect your <em>LinkedIn</em>
        </h1>

        {/* Subhead */}
        <p
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 300,
            fontSize: "16px",
            lineHeight: 1.6,
            color: "#4A4540",
            marginBottom: "32px",
          }}
        >
          Agency OS reads your recent posts to match your agency&apos;s voice when
          writing outreach. Your existing connections become an exclusion list
          so we never cold-message someone you already know.
        </p>

        {/* Disclosure panel */}
        <div
          style={{
            border: "1px solid rgba(212, 149, 106, 0.45)",
            background:
              "linear-gradient(135deg, rgba(212,149,106,0.06) 0%, rgba(247,243,238,0.85) 100%)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            padding: "24px",
            marginBottom: "32px",
          }}
        >
          <div className="flex items-start gap-3">
            <ShieldCheck
              size={18}
              style={{ color: "#D4956A", flexShrink: 0, marginTop: "2px" }}
            />
            <div>
              <p
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: "11px",
                  letterSpacing: "0.1em",
                  color: "#D4956A",
                  textTransform: "uppercase",
                  marginBottom: "12px",
                }}
              >
                What Agency OS does with your LinkedIn account
              </p>
              <div
                style={{
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: 400,
                  fontSize: "14px",
                  lineHeight: 1.75,
                  color: "#3A3530",
                }}
              >
                <p style={{ marginBottom: "10px" }}>
                  <strong style={{ fontWeight: 500 }}>READS</strong> your
                  profile and recent posts to match your agency&apos;s voice when
                  writing outreach.
                </p>
                <p style={{ marginBottom: "10px" }}>
                  <strong style={{ fontWeight: 500 }}>READS</strong> your
                  connections as an exclusion list — we never cold-message
                  someone you already know.
                </p>
                <p style={{ marginBottom: "10px" }}>
                  <strong style={{ fontWeight: 500 }}>SENDS</strong>{" "}
                  connection requests and follow-up messages from your account
                  to prospects Agency OS identifies. Personalised, timed
                  naturally, within conservative limits below LinkedIn&apos;s own
                  guidelines. Randomised delays, business hours only, gradual
                  warmup on new cycles.
                </p>
                <p>
                  Connection requests and messages always come from you, not
                  from Agency OS. You can pause LinkedIn outreach at any time
                  and revoke access instantly.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              border: "1px solid rgba(220,50,50,0.3)",
              background: "rgba(220,50,50,0.05)",
              padding: "12px 16px",
              marginBottom: "20px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <AlertCircle size={15} style={{ color: "#DC3232", flexShrink: 0 }} />
            <p
              style={{
                fontFamily: "'DM Sans', sans-serif",
                fontSize: "13px",
                color: "#DC3232",
              }}
            >
              {error}
            </p>
          </div>
        )}

        {/* Primary CTA */}
        <button
          onClick={handleLinkedInConnect}
          disabled={isLoading}
          style={{
            width: "100%",
            background: isLoading
              ? "rgba(212,149,106,0.5)"
              : "linear-gradient(135deg, #D4956A 0%, #C07D4E 100%)",
            color: "#F7F3EE",
            border: "none",
            padding: "14px 28px",
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 500,
            fontSize: "15px",
            letterSpacing: "0.02em",
            cursor: isLoading ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "10px",
            marginBottom: "16px",
          }}
        >
          {isLoading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <ExternalLink size={16} />
              Connect LinkedIn via Unipile
            </>
          )}
        </button>

        {/* Skip link */}
        <div className="text-center">
          <button
            onClick={() => router.push("/onboarding/agency")}
            style={{
              background: "none",
              border: "none",
              fontFamily: "'DM Sans', sans-serif",
              fontWeight: 400,
              fontSize: "13px",
              color: "#8A7F76",
              cursor: "pointer",
              textDecoration: "underline",
              textUnderlineOffset: "3px",
            }}
          >
            Skip — email and voice only for now
          </button>
        </div>
      </div>
    </div>
  );
}
