/**
 * FILE: frontend/components/dashboard/ClientDemoBanner.tsx
 * PURPOSE: Client-side banner shown when ?demo=true was set (cookie agency_os_demo=true).
 *          Tells visitors the dashboard is showing Keiracom's own internal usage data,
 *          not a paying client's data.
 *
 * No backend dependency — reads the same cookie middleware sets.
 */

"use client";

import { useEffect, useState } from "react";

export function ClientDemoBanner() {
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const has = document.cookie
      .split("; ")
      .some((r) => r.startsWith("agency_os_demo=true"));
    setIsDemo(has);
  }, []);

  if (!isDemo) return null;

  return (
    <div
      style={{
        background: "#F7E8D8",
        borderBottom: "1px solid #D4956A",
        color: "#5A3818",
        padding: "10px 20px",
        fontSize: 13,
        fontFamily: "'DM Sans', system-ui, sans-serif",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
      }}
    >
      <span>
        <strong style={{ fontWeight: 700 }}>Demo view —</strong> showing Keiracom&rsquo;s own
        internal Agency OS usage. Real pipeline, real CIS scores, real outreach. Not a paying
        client&rsquo;s data.
      </span>
      <a
        href="/dashboard?demo=false"
        style={{
          color: "#5A3818",
          textDecoration: "underline",
          fontSize: 12,
          whiteSpace: "nowrap",
        }}
      >
        Exit demo
      </a>
    </div>
  );
}
