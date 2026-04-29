"use client";

/**
 * FILE: frontend/app/onboarding/step-1/page.tsx
 * PURPOSE: Demo onboarding — CRM connect (simulated, no real API)
 * DESIGN: Bloomberg cream/amber palette, Playfair Display headings
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2 } from "lucide-react";

const DEMO_AGENCY = "Bondi Digital Marketing";

const CRMS = [
  {
    id: "hubspot",
    name: "HubSpot",
    color: "#FF7A59",
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="11" fill="#FF7A59" />
        <circle cx="11" cy="8" r="2.5" fill="white" />
        <circle cx="15.5" cy="13" r="2" fill="white" />
        <circle cx="6.5" cy="13" r="2" fill="white" />
        <line x1="11" y1="10.5" x2="15.5" y2="13" stroke="white" strokeWidth="1.2" />
        <line x1="11" y1="10.5" x2="6.5" y2="13" stroke="white" strokeWidth="1.2" />
      </svg>
    ),
  },
  {
    id: "pipedrive",
    name: "Pipedrive",
    color: "#1E7E34",
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="11" fill="#1E7E34" />
        <path d="M8 7h4.5a3 3 0 010 6H8V7z" fill="white" />
        <rect x="8" y="14" width="2" height="4" fill="white" />
      </svg>
    ),
  },
  {
    id: "close",
    name: "Close",
    color: "#6B4FBB",
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="11" fill="#6B4FBB" />
        <path d="M14 8.5A4 4 0 1 0 14 14" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: "ghl",
    name: "GoHighLevel",
    color: "#FF6B2B",
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="11" fill="#FF6B2B" />
        <text x="6" y="15" fill="white" fontSize="10" fontWeight="700" fontFamily="sans-serif">GHL</text>
      </svg>
    ),
  },
];

type Phase = "idle" | "loading" | "done";

export default function OnboardingStep1() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("idle");
  const [selectedCrm, setSelectedCrm] = useState<string | null>(null);

  const handleConnect = (crmId: string) => {
    setSelectedCrm(crmId);
    setPhase("loading");
    setTimeout(() => {
      setPhase("done");
      setTimeout(() => router.push("/onboarding/step-2"), 1200);
    }, 2000);
  };

  return (
    <div
      style={{ backgroundColor: "#F7F3EE", color: "#0C0A08", minHeight: "100vh" }}
      className="flex items-center justify-center px-4 py-16"
    >
      <div className="w-full" style={{ maxWidth: 640 }}>

        {/* Step indicator */}
        <StepIndicator current={1} total={5} />

        {/* Agency badge */}
        <AgencyBadge name={DEMO_AGENCY} />

        {/* Headline */}
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
          Connect your CRM so we know
          <br />
          <em style={{ color: "#D4956A" }}>who your existing clients are</em>
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
          Agency OS uses your CRM deal history as an exclusion list. We will
          never prospect someone already in your pipeline.
        </p>

        {/* CRM grid */}
        {phase === "idle" && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 14,
              marginBottom: 32,
            }}
          >
            {CRMS.map((crm) => (
              <button
                key={crm.id}
                onClick={() => handleConnect(crm.id)}
                style={{
                  background: "white",
                  border: "1.5px solid rgba(212,149,106,0.25)",
                  padding: "18px 20px",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  cursor: "pointer",
                  transition: "border-color 0.15s, box-shadow 0.15s",
                  textAlign: "left",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "#D4956A";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 0 0 3px rgba(212,149,106,0.12)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(212,149,106,0.25)";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow = "none";
                }}
              >
                {crm.icon}
                <span
                  style={{
                    fontFamily: "'DM Sans', sans-serif",
                    fontWeight: 500,
                    fontSize: 14,
                    color: "#0C0A08",
                  }}
                >
                  {crm.name}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Loading state */}
        {phase === "loading" && (
          <LoadingCard label="Extracting services from your deals..." />
        )}

        {/* Done state */}
        {phase === "done" && (
          <DoneCard>
            <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 14, color: "#3A3530", lineHeight: 1.6 }}>
              <strong style={{ color: "#0C0A08" }}>Found 3 services:</strong>{" "}
              SEO, Google Ads Management, Social Media Marketing
            </p>
          </DoneCard>
        )}
      </div>
    </div>
  );
}

/* ── Shared sub-components ── */

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
      <div
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          backgroundColor: "#D4956A",
        }}
      />
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

function LoadingCard({ label }: { label: string }) {
  return (
    <div
      style={{
        border: "1.5px solid rgba(212,149,106,0.35)",
        background: "rgba(212,149,106,0.04)",
        padding: "28px 24px",
        display: "flex",
        alignItems: "center",
        gap: 14,
        marginBottom: 32,
      }}
    >
      <Loader2 size={20} style={{ color: "#D4956A", flexShrink: 0 }} className="animate-spin" />
      <span
        style={{
          fontFamily: "'DM Sans', sans-serif",
          fontSize: 14,
          color: "#4A4540",
        }}
      >
        {label}
      </span>
    </div>
  );
}

function DoneCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        border: "1.5px solid rgba(212,149,106,0.45)",
        background: "rgba(212,149,106,0.06)",
        padding: "20px 24px",
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        marginBottom: 32,
      }}
    >
      <CheckCircle2 size={18} style={{ color: "#D4956A", flexShrink: 0, marginTop: 2 }} />
      {children}
    </div>
  );
}
