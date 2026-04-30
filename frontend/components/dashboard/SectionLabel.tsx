/**
 * FILE: frontend/components/dashboard/SectionLabel.tsx
 * PURPOSE: Reusable section label for dashboard surfaces.
 * REFERENCE: dashboard-master-agency-desk.html — `.section-label`
 *            (JetBrains Mono 10px uppercase, letter-spacing 0.14em,
 *            ink-3 colour, 600 weight) and `.eyebrow` at line 61.
 *
 * Usage:
 *   <SectionLabel>Cycle funnel</SectionLabel>
 *   <SectionLabel as="h2" className="mb-2">Today's meetings</SectionLabel>
 *
 * Replaces the ad-hoc inline strings of `font-mono uppercase
 * tracking-[…]` that have been pasted across the dashboard.
 */

"use client";

import { cn } from "@/lib/utils";

interface Props {
  children: React.ReactNode;
  /** HTML element. Defaults to a div — pass "h2" / "h3" for semantics. */
  as?: "div" | "h2" | "h3" | "h4" | "p";
  /** Margin tweaks per slot. Default mirrors /demo's
   *  `margin: 24px 0 12px`, but use `mb-2` / `mb-3` etc. when you want
   *  the surface that follows to sit closer. */
  className?: string;
}

export function SectionLabel({ children, as: Tag = "div", className }: Props) {
  return (
    <Tag
      className={cn(
        "font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3 font-semibold mt-6 mb-3",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
