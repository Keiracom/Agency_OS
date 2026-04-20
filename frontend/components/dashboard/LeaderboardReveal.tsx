"use client";

import { useEffect, useRef, useState } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ProspectRow {
  id: string;
  company: string;
  location: string;
  industry: string;
  intent: number;
  affordability: number;
  signals: string;
  status: "drafted" | "scoring" | "enriching";
}

interface LeaderboardRevealProps {
  prospects: ProspectRow[];
  onRevealComplete: () => void;
  isDemo?: boolean;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function scoreClass(n: number) {
  if (n >= 80) return { color: "#D4956A" };
  if (n >= 65) return { color: "#0C0A08" };
  return { color: "#7A756D" };
}

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  drafted: { background: "rgba(212,149,106,0.10)", color: "#D4956A" },
  scoring: { background: "rgba(12,10,8,0.06)", color: "#7A756D" },
  enriching: { background: "rgba(12,10,8,0.04)", color: "#A8A298" },
};

// ─── FLIP sort animation ──────────────────────────────────────────────────────

function flipSort(
  container: HTMLElement,
  onRanksVisible: () => void
) {
  const rows = Array.from(
    container.querySelectorAll<HTMLElement>("[data-intent]")
  );

  // Capture FIRST positions
  const first = rows.map((r) => r.getBoundingClientRect());

  // Sort descending by intent
  rows.sort(
    (a, b) =>
      parseInt(b.dataset.intent ?? "0") - parseInt(a.dataset.intent ?? "0")
  );
  rows.forEach((r) => container.appendChild(r));

  // Capture LAST positions
  const last = rows.map((r) => r.getBoundingClientRect());

  // Invert + play
  rows.forEach((r, i) => {
    const dy = first[i].top - last[i].top;
    r.style.transform = `translateY(${dy}px)`;
    r.style.transition = "none";

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        r.style.transition = "transform 0.8s cubic-bezier(0.2,0.8,0.2,1)";
        r.style.transform = "translateY(0)";
      });
    });
  });

  // Update ranks after animation
  setTimeout(() => {
    rows.forEach((r, i) => {
      const rankEl = r.querySelector<HTMLElement>("[data-rank]");
      if (rankEl) {
        rankEl.textContent = "#" + (i + 1);
        rankEl.style.color = i < 3 ? "#D4956A" : "#7A756D";
      }
    });
    onRanksVisible();
  }, 900);
}

// ─── Component ───────────────────────────────────────────────────────────────

export function LeaderboardReveal({
  prospects,
  onRevealComplete,
  isDemo = false,
}: LeaderboardRevealProps) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [sorted, setSorted] = useState(false);
  const [dataTag, setDataTag] = useState<"demo" | "live">(
    isDemo ? "demo" : "live"
  );
  const bodyRef = useRef<HTMLDivElement>(null);

  // Sort ascending by intent for reveal (lowest first)
  const revealOrder = [...prospects].sort((a, b) => a.intent - b.intent);

  // Staggered reveal: one card every 350ms
  useEffect(() => {
    if (visibleCount >= revealOrder.length) return;
    const t = setTimeout(() => setVisibleCount((c) => c + 1), 350);
    return () => clearTimeout(t);
  }, [visibleCount, revealOrder.length]);

  // After all revealed, trigger FLIP sort after 600ms
  useEffect(() => {
    if (visibleCount < revealOrder.length) return;
    const t = setTimeout(() => {
      if (bodyRef.current) {
        flipSort(bodyRef.current, () => {
          setDataTag("live");
          setSorted(true);
        });
      }
    }, 600);
    return () => clearTimeout(t);
  }, [visibleCount, revealOrder.length]);

  // Signal completion ~8 seconds total
  useEffect(() => {
    if (!sorted) return;
    const t = setTimeout(onRevealComplete, 1200);
    return () => clearTimeout(t);
  }, [sorted, onRevealComplete]);

  return (
    <div style={{ border: "1px solid rgba(12,10,8,0.08)", marginBottom: 44 }}>
      {/* Label row */}
      <div
        className="flex items-center gap-3 mb-4"
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "#7A756D",
          padding: "0 0 0 0",
          marginBottom: 18,
        }}
      >
        <span>Prospect leaderboard</span>
        <span
          style={{
            fontSize: 9,
            letterSpacing: "0.1em",
            padding: "3px 10px",
            ...(dataTag === "demo"
              ? { background: "rgba(212,149,106,0.10)", color: "#D4956A" }
              : { background: "rgba(127,166,136,0.12)", color: "#7FA688" }),
            transition: "all 0.4s",
          }}
        >
          {dataTag === "demo" ? "Demo data" : "Live data"}
        </span>
        <div style={{ flex: 1, height: 1, background: "rgba(12,10,8,0.08)" }} />
      </div>

      {/* Table header */}
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
          textTransform: "uppercase",
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

      {/* Table body */}
      <div ref={bodyRef}>
        {revealOrder.slice(0, visibleCount).map((p) => (
          <div
            key={p.id}
            data-intent={p.intent}
            style={{
              display: "grid",
              gridTemplateColumns: "48px 1.4fr 1fr 0.7fr 0.7fr 0.7fr 120px",
              padding: "18px 24px",
              borderBottom: "1px solid rgba(12,10,8,0.08)",
              alignItems: "center",
              fontSize: 13,
              color: "#2E2B26",
              background: "#F7F3EE",
              animation: "rowReveal 0.6s cubic-bezier(0.2,0.8,0.2,1) backwards",
            }}
          >
            <style>{`
              @keyframes rowReveal {
                from { opacity: 0; transform: translateY(12px); }
                to   { opacity: 1; transform: translateY(0); }
              }
            `}</style>
            {/* Rank */}
            <div
              data-rank
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                fontWeight: 500,
                color: "#7A756D",
              }}
            >
              —
            </div>
            {/* Company */}
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
            {/* Industry */}
            <div style={{ fontSize: 12, color: "#7A756D" }}>{p.industry}</div>
            {/* Intent */}
            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 15,
                fontWeight: 500,
                ...scoreClass(p.intent),
              }}
            >
              {p.intent}
            </div>
            {/* Affordability */}
            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 15,
                fontWeight: 500,
                ...scoreClass(p.affordability),
              }}
            >
              {p.affordability}
            </div>
            {/* Signals */}
            <div
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10,
                color: "#7A756D",
              }}
            >
              {p.signals}
            </div>
            {/* Status */}
            <div>
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  padding: "5px 12px",
                  ...STATUS_STYLES[p.status],
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
