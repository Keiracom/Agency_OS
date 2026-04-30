"use client";

/**
 * FILE: frontend/app/onboarding/step-2/page.tsx
 * PURPOSE: Demo onboarding — LinkedIn connect (simulated, no real API)
 * DESIGN: Bloomberg cream/amber palette, Playfair Display headings
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Linkedin, Loader2, CheckCircle2, ShieldCheck } from "lucide-react";

const DEMO_AGENCY = "Bondi Digital Marketing";

type Phase = "idle" | "loading" | "done";

export default function OnboardingStep2() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("idle");

  const handleConnect = () => {
    setPhase("loading");
    setTimeout(() => {
      setPhase("done");
      setTimeout(() => router.push("/onboarding/step-3"), 1400);
    }, 2000);
  };

  return (
    <div
      style={{ backgroundColor: "#F7F3EE", color: "#0C0A08", minHeight: "100vh" }}
      className="flex items-center justify-center px-4 py-16"
    >
      <div className="w-full" style={{ maxWidth: 640 }}>

        <StepIndicator current={2} total={5} />
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
          Connect LinkedIn to personalise
          <br />
          <em style={{ color: "#D4956A" }}>every outreach message</em>
        </h1>

        <p
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 300,
            fontSize: 15,
            lineHeight: 1.65,
            color: "#4A4540",
            marginBottom: 32,
          }}
        >
          Agency OS analyses your writing style, existing connections, and
          network so every message sounds like you — not a bot.
        </p>

        {/* Privacy note */}
        {phase === "idle" && (
          <div
            style={{
              border: "1px solid rgba(212,149,106,0.35)",
              background: "linear-gradient(135deg, rgba(212,149,106,0.05) 0%, rgba(247,243,238,0.9) 100%)",
              padding: "18px 20px",
              marginBottom: 28,
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
            }}
          >
            <ShieldCheck size={16} style={{ color: "#D4956A", flexShrink: 0, marginTop: 2 }} />
            <p
              style={{
                fontFamily: "'DM Sans', sans-serif",
                fontSize: 13,
                lineHeight: 1.65,
                color: "#3A3530",
              }}
            >
              Read-only access. We never post on your behalf or send messages
              without your approval. Your connection list is used as an
              exclusion list only.
            </p>
          </div>
        )}

        {/* Action */}
        {phase === "idle" && (
          <button
            onClick={handleConnect}
            style={{
              width: "100%",
              background: "linear-gradient(135deg, #0A66C2 0%, #0952A0 100%)",
              color: "white",
              border: "none",
              padding: "14px 28px",
              fontFamily: "'DM Sans', sans-serif",
              fontWeight: 500,
              fontSize: 15,
              letterSpacing: "0.02em",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              marginBottom: 14,
              transition: "opacity 0.15s",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.9"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
          >
            <Linkedin size={17} />
            Connect LinkedIn
          </button>
        )}

        {phase === "loading" && (
          <LoadingCard label="Analysing your communication style..." />
        )}

        {phase === "done" && (
          <DoneCard>
            <div>
              <p
                style={{
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 14,
                  color: "#3A3530",
                  lineHeight: 1.6,
                  marginBottom: 6,
                }}
              >
                <strong style={{ color: "#0C0A08" }}>Tone:</strong> Professional-casual.
              </p>
              <p
                style={{
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 14,
                  color: "#3A3530",
                  lineHeight: 1.6,
                }}
              >
                <strong style={{ color: "#0C0A08" }}>Connection exclusion list loaded.</strong>{" "}
                341 existing contacts will be excluded from outreach.
              </p>
            </div>
          </DoneCard>
        )}

        {phase === "idle" && (
          <div className="text-center">
            <button
              onClick={() => router.push("/onboarding/step-3")}
              style={{
                background: "none",
                border: "none",
                fontFamily: "'DM Sans', sans-serif",
                fontWeight: 400,
                fontSize: 13,
                color: "#8A7F76",
                cursor: "pointer",
                textDecoration: "underline",
                textUnderlineOffset: 3,
              }}
            >
              I&apos;ll connect this later
            </button>
          </div>
        )}
      </div>
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
      <span style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 14, color: "#4A4540" }}>
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
