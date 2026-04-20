"use client";

/**
 * FILE: frontend/app/onboarding/crm/page.tsx
 * PURPOSE: CRM connection onboarding step — HubSpot OAuth
 * DIRECTIVE: #309 — Onboarding rebuild
 * DESIGN: Cream #F7F3EE, Ink #0C0A08, Amber #D4956A
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ExternalLink, Loader2, ShieldCheck } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function CRMOnboardingPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleHubspotConnect = async () => {
    setError(null);
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/crm/connect/hubspot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(
          data.detail || data.message || `HubSpot connect failed (${res.status})`
        );
      }
      const data = await res.json();
      const oauthUrl =
        data.oauth_url || data.redirect_url || data.auth_url || data.url;
      if (oauthUrl) {
        window.location.href = oauthUrl;
      } else {
        router.push("/onboarding/linkedin");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{ backgroundColor: "#F7F3EE", color: "#0C0A08", minHeight: "100vh" }}
      className="flex items-center justify-center px-4 py-16"
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
          Step 1 of 4 — CRM
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
          Connect your CRM so we know
          <br />
          <em>who your existing clients are</em>
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
          Agency OS uses your HubSpot contact and deal history as an exclusion
          list. We will never prospect someone already in your pipeline or
          client base. Meeting bookings flow back into HubSpot automatically.
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
                  marginBottom: "10px",
                }}
              >
                Write access disclosure
              </p>
              <p
                style={{
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: 400,
                  fontSize: "14px",
                  lineHeight: 1.7,
                  color: "#3A3530",
                }}
              >
                When you book a meeting through Agency OS, the new contact,
                deal, and calendar event will be written to your HubSpot so
                meetings land in your existing workflow. We never modify or
                delete records that didn&apos;t come from Agency OS. Every write is
                traceable in your HubSpot activity log. You can revoke access
                at any time from Settings.
              </p>
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
          onClick={handleHubspotConnect}
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
              Connect HubSpot
            </>
          )}
        </button>

        {/* Skip link */}
        <div className="text-center">
          <button
            onClick={() => router.push("/onboarding/linkedin")}
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
            I&apos;ll connect this later
          </button>
        </div>
      </div>
    </div>
  );
}
