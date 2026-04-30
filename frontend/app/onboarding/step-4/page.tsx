"use client";

/**
 * FILE: frontend/app/onboarding/step-4/page.tsx
 * PURPOSE: Demo onboarding — Service area picker (simulated, no real API)
 * DESIGN: Bloomberg cream/amber palette, Playfair Display headings
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MapPin, Zap } from "lucide-react";

const DEMO_AGENCY = "Bondi Digital Marketing";

const AREAS = [
  { id: "sydney", label: "Sydney", sub: "NSW — Greater Metro" },
  { id: "melbourne", label: "Melbourne", sub: "VIC — Greater Metro" },
  { id: "brisbane", label: "Brisbane", sub: "QLD — Greater Metro" },
  { id: "national", label: "National", sub: "All major Australian cities" },
];

export default function OnboardingStep4() {
  const router = useRouter();
  const [selected, setSelected] = useState("sydney");

  return (
    <div
      style={{ backgroundColor: "#F7F3EE", color: "#0C0A08", minHeight: "100vh" }}
      className="flex items-center justify-center px-4 py-16"
    >
      <div className="w-full" style={{ maxWidth: 640 }}>

        <StepIndicator current={4} total={5} />
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
          Where do you
          <br />
          <em style={{ color: "#D4956A" }}>want new clients from?</em>
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
          Agency OS focuses your prospect universe to the geography you can
          actually service. You can change this anytime from Settings.
        </p>

        {/* Area selector */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 36 }}>
          {AREAS.map((area) => {
            const isActive = selected === area.id;
            return (
              <button
                key={area.id}
                onClick={() => setSelected(area.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  background: isActive ? "rgba(212,149,106,0.08)" : "white",
                  border: `1.5px solid ${isActive ? "#D4956A" : "rgba(0,0,0,0.08)"}`,
                  padding: "16px 20px",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.2s",
                  boxShadow: isActive ? "0 0 0 3px rgba(212,149,106,0.12)" : "none",
                }}
              >
                {/* Radio dot */}
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: "50%",
                    border: `2px solid ${isActive ? "#D4956A" : "rgba(0,0,0,0.2)"}`,
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "border-color 0.2s",
                  }}
                >
                  {isActive && (
                    <div
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        backgroundColor: "#D4956A",
                      }}
                    />
                  )}
                </div>

                <MapPin
                  size={16}
                  style={{
                    color: isActive ? "#D4956A" : "#8A7F76",
                    flexShrink: 0,
                    transition: "color 0.2s",
                  }}
                />

                <div style={{ flex: 1 }}>
                  <p
                    style={{
                      fontFamily: "'DM Sans', sans-serif",
                      fontWeight: 600,
                      fontSize: 15,
                      color: isActive ? "#0C0A08" : "#3A3530",
                      marginBottom: 2,
                    }}
                  >
                    {area.label}
                  </p>
                  <p
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      letterSpacing: "0.06em",
                      color: isActive ? "#D4956A" : "#8A7F76",
                    }}
                  >
                    {area.sub}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* CTA */}
        <button
          onClick={() => router.push("/onboarding/step-5")}
          style={{
            width: "100%",
            background: "linear-gradient(135deg, #D4956A 0%, #C07D4E 100%)",
            color: "#F7F3EE",
            border: "none",
            padding: "15px 28px",
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 500,
            fontSize: 15,
            letterSpacing: "0.02em",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            transition: "opacity 0.15s",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.9"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
        >
          <Zap size={16} />
          Start Discovery
        </button>

        <p
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            letterSpacing: "0.06em",
            color: "#8A7F76",
            textAlign: "center",
            marginTop: 14,
            textTransform: "uppercase",
          }}
        >
          Takes about 30 seconds
        </p>
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
