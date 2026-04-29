"use client";

/**
 * FILE: frontend/app/onboarding/step-3/page.tsx
 * PURPOSE: Demo onboarding — Confirm services (simulated, no real API)
 * DESIGN: Bloomberg cream/amber palette, Playfair Display headings
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, ArrowRight } from "lucide-react";

const DEMO_AGENCY = "Bondi Digital Marketing";

const DEFAULT_SERVICES = [
  { id: "seo", label: "SEO" },
  { id: "google-ads", label: "Google Ads Management" },
  { id: "social", label: "Social Media Marketing" },
];

export default function OnboardingStep3() {
  const router = useRouter();
  const [services, setServices] = useState(DEFAULT_SERVICES.map((s) => ({ ...s, enabled: true })));
  const [newService, setNewService] = useState("");
  const [addingNew, setAddingNew] = useState(false);

  const toggleService = (id: string) => {
    setServices((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const removeService = (id: string) => {
    setServices((prev) => prev.filter((s) => s.id !== id));
  };

  const addService = () => {
    const trimmed = newService.trim();
    if (!trimmed) return;
    setServices((prev) => [
      ...prev,
      { id: `custom-${Date.now()}`, label: trimmed, enabled: true },
    ]);
    setNewService("");
    setAddingNew(false);
  };

  return (
    <div
      style={{ backgroundColor: "#F7F3EE", color: "#0C0A08", minHeight: "100vh" }}
      className="flex items-center justify-center px-4 py-16"
    >
      <div className="w-full" style={{ maxWidth: 640 }}>

        <StepIndicator current={3} total={5} />
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
          Confirm the services
          <br />
          <em style={{ color: "#D4956A" }}>you want to sell</em>
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
          We found these services from your CRM deals. Toggle off any you
          don&apos;t want to prospect for, or add new ones.
        </p>

        {/* Service list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 24 }}>
          {services.map((service) => (
            <div
              key={service.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                background: service.enabled ? "white" : "rgba(0,0,0,0.03)",
                border: `1.5px solid ${service.enabled ? "rgba(212,149,106,0.35)" : "rgba(0,0,0,0.08)"}`,
                padding: "14px 18px",
                transition: "all 0.2s",
              }}
            >
              {/* Toggle */}
              <button
                onClick={() => toggleService(service.id)}
                style={{
                  width: 38,
                  height: 22,
                  borderRadius: 11,
                  backgroundColor: service.enabled ? "#D4956A" : "rgba(0,0,0,0.15)",
                  border: "none",
                  cursor: "pointer",
                  position: "relative",
                  flexShrink: 0,
                  transition: "background-color 0.2s",
                }}
              >
                <div
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: "50%",
                    backgroundColor: "white",
                    position: "absolute",
                    top: 3,
                    left: service.enabled ? 19 : 3,
                    transition: "left 0.2s",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                  }}
                />
              </button>

              <span
                style={{
                  fontFamily: "'DM Sans', sans-serif",
                  fontWeight: 500,
                  fontSize: 15,
                  color: service.enabled ? "#0C0A08" : "#8A7F76",
                  flex: 1,
                  transition: "color 0.2s",
                }}
              >
                {service.label}
              </span>

              <button
                onClick={() => removeService(service.id)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#8A7F76",
                  padding: 4,
                  display: "flex",
                  alignItems: "center",
                  opacity: 0.5,
                  transition: "opacity 0.15s",
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.5"; }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>

        {/* Add service */}
        {addingNew ? (
          <div style={{ display: "flex", gap: 10, marginBottom: 28 }}>
            <input
              autoFocus
              value={newService}
              onChange={(e) => setNewService(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") addService(); if (e.key === "Escape") setAddingNew(false); }}
              placeholder="e.g. Web Design"
              style={{
                flex: 1,
                fontFamily: "'DM Sans', sans-serif",
                fontSize: 14,
                color: "#0C0A08",
                background: "white",
                border: "1.5px solid #D4956A",
                padding: "11px 14px",
                outline: "none",
              }}
            />
            <button
              onClick={addService}
              style={{
                background: "#D4956A",
                color: "white",
                border: "none",
                padding: "11px 20px",
                fontFamily: "'DM Sans', sans-serif",
                fontWeight: 500,
                fontSize: 14,
                cursor: "pointer",
              }}
            >
              Add
            </button>
          </div>
        ) : (
          <button
            onClick={() => setAddingNew(true)}
            style={{
              background: "none",
              border: "1.5px dashed rgba(212,149,106,0.4)",
              padding: "12px 18px",
              width: "100%",
              display: "flex",
              alignItems: "center",
              gap: 8,
              cursor: "pointer",
              marginBottom: 28,
              transition: "border-color 0.15s",
              color: "#8A7F76",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#D4956A"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(212,149,106,0.4)"; }}
          >
            <Plus size={15} style={{ color: "#D4956A" }} />
            <span style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 14 }}>
              Add a service
            </span>
          </button>
        )}

        {/* Next */}
        <button
          onClick={() => router.push("/onboarding/step-4")}
          style={{
            width: "100%",
            background: "linear-gradient(135deg, #D4956A 0%, #C07D4E 100%)",
            color: "#F7F3EE",
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
            transition: "opacity 0.15s",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.9"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
        >
          Next
          <ArrowRight size={16} />
        </button>
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
