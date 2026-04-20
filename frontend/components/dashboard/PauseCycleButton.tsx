/**
 * FILE: frontend/components/dashboard/PauseCycleButton.tsx
 * PURPOSE: Customer-facing Pause Cycle button with modal confirmation
 * DIRECTIVE: #314 — Task F
 * DESIGN: Amber pulsing dot, JetBrains Mono, cream/ink/amber palette
 *   - Paused state: shows "Cycle Paused" banner
 *   - Confirmation modal before pause/resume
 */

"use client";

import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://agency-os-production.up.railway.app";

interface PauseCycleButtonProps {
  clientId: string;
  cycleId: string;
  initialStatus?: "active" | "paused" | string;
  onStatusChange?: (status: string) => void;
}

async function patchCycleStatus(
  clientId: string,
  cycleId: string,
  action: "pause" | "resume"
): Promise<{ status: string }> {
  const res = await fetch(
    `${API_BASE}/api/v1/clients/${clientId}/cycles/${cycleId}/${action}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    }
  );
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Failed to ${action} cycle`);
  }
  return res.json();
}

export function PauseCycleButton({
  clientId,
  cycleId,
  initialStatus = "active",
  onStatusChange,
}: PauseCycleButtonProps) {
  const [status, setStatus] = useState(initialStatus);
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const isPaused = status === "paused";

  const handleConfirm = async () => {
    setLoading(true);
    try {
      const action = isPaused ? "resume" : "pause";
      const result = await patchCycleStatus(clientId, cycleId, action);
      setStatus(result.status);
      onStatusChange?.(result.status);
      setModalOpen(false);
      toast({
        title: result.status === "paused" ? "Cycle paused" : "Cycle resumed",
        description:
          result.status === "paused"
            ? "No outreach will be sent until you resume."
            : "Your cycle is active again.",
      });
    } catch (err) {
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Something went wrong",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Paused banner */}
      {isPaused && (
        <div
          style={{
            background: "rgba(212,149,106,0.12)",
            border: "1px solid rgba(212,149,106,0.4)",
            padding: "10px 20px",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "11px",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "#D4956A",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            marginBottom: "12px",
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "#D4956A",
              display: "inline-block",
              flexShrink: 0,
            }}
          />
          Cycle Paused — no outreach sending
        </div>
      )}

      {/* Button */}
      <button
        onClick={() => setModalOpen(true)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 20px",
          background: "transparent",
          border: isPaused
            ? "1px solid rgba(212,149,106,0.5)"
            : "1px solid rgba(12,10,8,0.15)",
          cursor: "pointer",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "11px",
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: isPaused ? "#D4956A" : "#7A756D",
          transition: "all 0.2s",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor =
            "rgba(212,149,106,0.7)";
          (e.currentTarget as HTMLButtonElement).style.color = "#D4956A";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = isPaused
            ? "rgba(212,149,106,0.5)"
            : "rgba(12,10,8,0.15)";
          (e.currentTarget as HTMLButtonElement).style.color = isPaused
            ? "#D4956A"
            : "#7A756D";
        }}
        disabled={loading}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: isPaused ? "#D4956A" : "#D4956A",
            boxShadow: isPaused
              ? "none"
              : "0 0 0 3px rgba(212,149,106,0.18)",
            animation: isPaused ? "none" : "pcb-pulse 2.4s ease-in-out infinite",
            display: "inline-block",
            flexShrink: 0,
          }}
        />
        <style>{`
          @keyframes pcb-pulse {
            0%, 100% { box-shadow: 0 0 0 3px rgba(212,149,106,0.18); }
            50% { box-shadow: 0 0 0 5px rgba(212,149,106,0.08); }
          }
        `}</style>
        {isPaused ? "Resume Cycle" : "Pause Cycle"}
      </button>

      {/* Confirmation Modal */}
      {modalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(12,10,8,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 999,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setModalOpen(false);
          }}
        >
          <div
            style={{
              background: "#F7F3EE",
              padding: "40px 44px",
              maxWidth: 480,
              width: "100%",
              position: "relative",
            }}
          >
            {/* amber top border */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: 2,
                background: "#D4956A",
              }}
            />

            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "9px",
                letterSpacing: "0.2em",
                textTransform: "uppercase",
                color: "#7A756D",
                marginBottom: 16,
              }}
            >
              {isPaused ? "Resume cycle" : "Pause cycle"}
            </div>

            <h3
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: 22,
                fontWeight: 700,
                color: "#0C0A08",
                marginBottom: 12,
                lineHeight: 1.2,
              }}
            >
              {isPaused
                ? "Resume outreach?"
                : "Pause all outreach?"}
            </h3>

            <p
              style={{
                fontSize: 14,
                color: "#7A756D",
                lineHeight: 1.7,
                marginBottom: 28,
                fontFamily: "'DM Sans', sans-serif",
                fontWeight: 300,
              }}
            >
              {isPaused
                ? "Your cycle will resume sending outreach immediately. You can pause again at any time."
                : "No emails, LinkedIn messages, or voice calls will be sent while paused. Your cycle remains intact — resume at any time."}
            </p>

            <div style={{ display: "flex", gap: 12 }}>
              <button
                onClick={handleConfirm}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "14px 24px",
                  background: "#0C0A08",
                  color: "#F7F3EE",
                  border: "none",
                  cursor: loading ? "not-allowed" : "pointer",
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 14,
                  fontWeight: 500,
                  opacity: loading ? 0.7 : 1,
                }}
              >
                {loading
                  ? "..."
                  : isPaused
                  ? "Yes, resume"
                  : "Yes, pause"}
              </button>
              <button
                onClick={() => setModalOpen(false)}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "14px 24px",
                  background: "transparent",
                  color: "#7A756D",
                  border: "1px solid rgba(12,10,8,0.15)",
                  cursor: "pointer",
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 14,
                  fontWeight: 400,
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
