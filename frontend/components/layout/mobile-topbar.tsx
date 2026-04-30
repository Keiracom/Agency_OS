/**
 * FILE: frontend/components/layout/mobile-topbar.tsx
 * PURPOSE: Compact 52px topbar for <md viewports. Replaces the desktop
 *          Header on mobile.
 *          Contains: hamburger (opens sidebar drawer) · AgencyOS brand
 *          mark · theme toggle · compact pause button.
 * REFERENCE: dashboard-master-agency-desk.html — `#mobile-topbar` block
 *            lines ~787-793 and the `--topbar-h` token (52px on mobile,
 *            56px desktop).
 */

"use client";

import { useEffect, useState } from "react";
import { Menu, Sun, Moon } from "lucide-react";
import { EmergencyPauseButton } from "@/components/dashboard/EmergencyPauseButton";

const THEME_KEY = "agencyos_theme";

interface Props {
  onOpenMenu: () => void;
  client?: {
    id: string;
    pausedAt?: string | null;
    pauseReason?: string | null;
  };
}

/**
 * Self-contained theme toggle so this PR doesn't depend on the A2
 * `theme-toggle.tsx` PR landing first. Mirrors the same localStorage
 * key (`agencyos_theme`) so the two implementations stay compatible.
 */
function useThemeToggle() {
  const [isDark, setIsDark] = useState(false);
  useEffect(() => {
    if (typeof document !== "undefined") {
      setIsDark(document.documentElement.classList.contains("dark"));
    }
  }, []);
  const toggle = () => {
    if (typeof document === "undefined") return;
    const next = !isDark;
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem(THEME_KEY, next ? "dark" : "light"); } catch {}
    setIsDark(next);
  };
  return { isDark, toggle };
}

export function MobileTopbar({ onOpenMenu, client }: Props) {
  const { isDark, toggle } = useThemeToggle();
  const [isPaused, setIsPaused] = useState(!!client?.pausedAt);

  return (
    <header
      className="md:hidden sticky top-0 z-40 flex items-center justify-between px-3 border-b border-rule"
      style={{
        height: "52px",
        backgroundColor: "rgba(247, 243, 238, 0.85)",
        backdropFilter: "saturate(140%) blur(8px)",
        WebkitBackdropFilter: "saturate(140%) blur(8px)",
      }}
    >
      {/* Left: hamburger + logo */}
      <div className="flex items-center gap-2 min-w-0">
        <button
          type="button"
          onClick={onOpenMenu}
          aria-label="Open navigation"
          className="-ml-1 p-2 rounded-md text-ink hover:bg-rule transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="font-display font-bold text-[16px] tracking-[-0.01em] text-ink whitespace-nowrap">
          Agency<em className="text-amber" style={{ fontStyle: "italic" }}>OS</em>
        </div>
      </div>

      {/* Right: theme toggle + compact pause */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={toggle}
          aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
          title={isDark ? "Switch to light theme" : "Switch to dark theme"}
          className="grid place-items-center w-8 h-8 rounded-full border border-rule text-ink-3 hover:text-amber hover:border-amber transition-colors"
        >
          {isDark
            ? <Moon className="w-4 h-4" strokeWidth={1.6} />
            : <Sun  className="w-4 h-4" strokeWidth={1.6} />}
        </button>

        {client?.id && (
          <div className="scale-90 origin-right">
            <EmergencyPauseButton
              clientId={client.id}
              isPaused={isPaused}
              pausedAt={client.pausedAt}
              pauseReason={client.pauseReason}
              onPauseChange={setIsPaused}
            />
          </div>
        )}
      </div>
    </header>
  );
}
