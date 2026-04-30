"use client";

/**
 * FILE: frontend/app/onboarding/service-area/page.tsx
 * PURPOSE: Service area selection — final onboarding step before dashboard
 * DIRECTIVE: #309 — Onboarding rebuild
 * DESIGN: Cream #F7F3EE, Ink #0C0A08, Amber #D4956A
 * API: POST /api/v1/onboarding/confirm { service_area, finalize: true }
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Check, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

type ServiceArea = "metro" | "state" | "national";

interface AreaOption {
  id: ServiceArea;
  label: string;
  subtitle: string;
}

const AREA_OPTIONS: AreaOption[] = [
  {
    id: "metro",
    label: "Metro",
    subtitle: "Tight local focus, faster delivery, local knowledge.",
  },
  {
    id: "state",
    label: "State",
    subtitle: "Good mix of metro density and regional opportunity.",
  },
  {
    id: "national",
    label: "National",
    subtitle: "Maximum prospect pool, no location constraints.",
  },
];

export default function ServiceAreaPage() {
  const router = useRouter();
  const [selected, setSelected] = useState<ServiceArea | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (!selected) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/onboarding/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          service_area: selected,
          finalize: true,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Save failed (${res.status})`);
      }

      // A7 dispatch: kick off the first pipeline run for this agency
      // immediately after onboarding finalizes. Fire-and-forget — a
      // 404 / 5xx here must NOT block dashboard entry, so we swallow
      // any error and the operator can retrigger from /dashboard.
      // Backend endpoint: POST /api/v1/pipeline/trigger
      // (reuses the same auth cookie as /onboarding/confirm).
      void fetch(`${API_BASE}/api/v1/pipeline/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ source: "onboarding_finalize" }),
      }).catch(() => {
        // Non-fatal; endpoint may not be deployed yet — dashboard
        // still loads with whatever data the seed_demo_tenant or
        // existing pipeline runs have produced.
      });

      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-16 bg-cream text-ink">
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
          Step 4 of 4 — Service Area
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
          Where do your ideal clients <em>operate?</em>
        </h1>

        <p
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 300,
            fontSize: "16px",
            lineHeight: 1.6,
            color: "#4A4540",
            marginBottom: "36px",
          }}
        >
          This determines the geographic scope of prospect discovery. You can
          change it later from Settings.
        </p>

        {/* Area cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "32px" }}>
          {AREA_OPTIONS.map((option) => {
            const isSelected = selected === option.id;
            return (
              <button
                key={option.id}
                onClick={() => setSelected(option.id)}
                style={{
                  background: isSelected
                    ? "linear-gradient(135deg, rgba(212,149,106,0.12) 0%, rgba(247,243,238,0.9) 100%)"
                    : "rgba(255,255,255,0.5)",
                  border: isSelected
                    ? "1px solid #D4956A"
                    : "1px solid rgba(12,10,8,0.12)",
                  backdropFilter: "blur(20px)",
                  WebkitBackdropFilter: "blur(20px)",
                  padding: "20px 24px",
                  textAlign: "left",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "16px",
                  width: "100%",
                  transition: "border-color 0.15s ease, background 0.15s ease",
                }}
              >
                <div>
                  <p
                    style={{
                      fontFamily: "'Playfair Display', serif",
                      fontWeight: 700,
                      fontSize: "20px",
                      color: isSelected ? "#D4956A" : "#0C0A08",
                      marginBottom: "4px",
                    }}
                  >
                    {option.label}
                  </p>
                  <p
                    style={{
                      fontFamily: "'DM Sans', sans-serif",
                      fontWeight: 300,
                      fontSize: "13px",
                      color: "#6A5F55",
                      lineHeight: 1.5,
                    }}
                  >
                    {option.subtitle}
                  </p>
                </div>

                {/* Checkmark circle */}
                <div
                  style={{
                    width: "22px",
                    height: "22px",
                    borderRadius: "50%",
                    border: isSelected ? "1px solid #D4956A" : "1px solid rgba(12,10,8,0.2)",
                    background: isSelected ? "#D4956A" : "transparent",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    transition: "background 0.15s ease, border-color 0.15s ease",
                  }}
                >
                  {isSelected && <Check size={12} style={{ color: "#F7F3EE" }} />}
                </div>
              </button>
            );
          })}
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
            <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: "13px", color: "#DC3232" }}>
              {error}
            </p>
          </div>
        )}

        {/* Primary CTA */}
        <button
          onClick={handleConfirm}
          disabled={!selected || isSubmitting}
          style={{
            width: "100%",
            background:
              !selected || isSubmitting
                ? "rgba(212,149,106,0.4)"
                : "linear-gradient(135deg, #D4956A 0%, #C07D4E 100%)",
            color: "#F7F3EE",
            border: "none",
            padding: "14px 28px",
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 500,
            fontSize: "15px",
            letterSpacing: "0.02em",
            cursor: !selected || isSubmitting ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "10px",
          }}
        >
          {isSubmitting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Starting your first cycle...
            </>
          ) : (
            "Start my first cycle"
          )}
        </button>
      </div>
    </div>
  );
}
