/**
 * FILE: frontend/app/(auth)/layout.tsx
 * PURPOSE: Auth pages shell — cream/amber palette + Playfair brand
 *          mark. Pure-CSS background pattern matches the /demo
 *          prototype's editorial feel.
 * PHASE: 8 (Frontend) · A6 dispatch (2026-04-30)
 *
 * SSG: Static shell — auth forms are client-side and live inside.
 */

import Link from "next/link";

// Static shell, revalidate daily.
export const revalidate = 86400;

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className="min-h-screen flex items-start sm:items-center justify-center bg-cream text-ink px-4 py-10 sm:py-16"
      style={{
        // Soft amber-glow radial gradients top-left + bottom-right —
        // matches the dashboard's ambient page background.
        backgroundImage: `
          radial-gradient(ellipse at 10% 0%, rgba(212,149,106,0.08) 0%, transparent 45%),
          radial-gradient(ellipse at 90% 100%, rgba(212,149,106,0.05) 0%, transparent 45%)
        `,
      }}
    >
      <div className="w-full max-w-[420px] flex flex-col items-center">
        {/* Brand mark — Playfair with amber italic OS accent. Links
            home for users who landed on auth by accident. */}
        <Link
          href="/"
          className="font-display font-bold text-[28px] tracking-[-0.02em] text-ink mb-1"
          aria-label="AgencyOS home"
        >
          Agency<em className="text-amber" style={{ fontStyle: "italic" }}>OS</em>
        </Link>
        <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-ink-3 mb-8">
          Agency Desk
        </div>

        {children}

        {/* Footer link — investor demo bypass */}
        <div className="mt-8 text-center text-[12px] text-ink-3">
          Want to look around first?{" "}
          <Link
            href="/?demo=true"
            className="font-mono uppercase tracking-[0.08em] text-copper hover:text-amber transition-colors"
          >
            Try the demo →
          </Link>
        </div>
      </div>
    </div>
  );
}
