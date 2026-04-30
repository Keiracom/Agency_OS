/**
 * FILE: frontend/components/layout/theme-toggle.tsx
 * PURPOSE: Sun/moon theme toggle button — mirrors /demo's `.tb-theme`
 *          pattern (frontend/landing/demo/index.html lines ~2333-2338).
 *
 * Behaviour:
 *   - Click flips `html.dark` class on document.documentElement.
 *   - Persists the choice in localStorage under `agencyos_theme`.
 *   - Reads localStorage on mount so React state stays in sync with
 *     whatever the inline pre-paint script (in app/layout.tsx) wrote
 *     before hydration. No flash of wrong theme.
 *
 * The `.dark` class drives the html.dark CSS-var block in
 * app/globals.css. Tailwind's darkMode: ["class"] config reads the
 * same class for utility variants. Single source of truth.
 */

"use client";

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

const STORAGE_KEY = "agencyos_theme";

type Theme = "light" | "dark";

function readTheme(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

function applyTheme(next: Theme) {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("dark", next === "dark");
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // localStorage may be blocked (Safari private mode); the class
    // change still wins for the current session.
  }
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  // Hydration-safe: start with `light` and reconcile in useEffect.
  // The pre-paint script has already set the right class before this
  // renders, so the reconciliation is a single state update with no
  // visual flicker.
  const [theme, setTheme] = useState<Theme>("light");
  useEffect(() => { setTheme(readTheme()); }, []);

  const next: Theme = theme === "dark" ? "light" : "dark";
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={() => {
        applyTheme(next);
        setTheme(next);
      }}
      className={[
        "tb-theme grid place-items-center w-8 h-8 rounded-full",
        "border border-rule text-ink-3 hover:text-amber hover:border-amber",
        "transition-colors",
        className,
      ].join(" ")}
    >
      {theme === "dark"
        ? <Moon className="w-4 h-4" strokeWidth={1.6} />
        : <Sun  className="w-4 h-4" strokeWidth={1.6} />}
    </button>
  );
}
