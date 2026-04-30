/**
 * FILE: frontend/app/layout.tsx
 * PURPOSE: Root layout with providers and global styles
 * PHASE: 8 (Frontend)
 * SPRINT: Dashboard Sprint 1 - Theme Foundation
 */

import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono, Playfair_Display } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

// PR1 dashboard rebuild — Playfair Display drives all serif headlines
// (page titles, brand mark, sum-card values). Italic 700 is loaded so
// the amber `<em>` accents in the prototype render correctly.
const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["700"],
  style: ["normal", "italic"],
  variable: "--font-playfair",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Agency OS - Automated Acquisition Engine",
  description: "Multi-channel outreach automation platform for marketing agencies",
  keywords: ["lead generation", "sales automation", "marketing agency", "outreach"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // A2 dark-mode + A4 sidebar-collapse anti-flash. Both run
  // synchronously before any paint so <html> gets the right class +
  // data attr before React renders — no flicker on reload between
  // server-default state and the user's saved preference. Mirrors
  // the /demo prototype pattern.
  const bootScript = `
    try {
      var t = localStorage.getItem('agencyos_theme');
      if (t === 'dark' || (!t && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
      }
    } catch (e) {}
    try {
      if (localStorage.getItem('agencyos_sidebar') === 'collapsed') {
        document.documentElement.setAttribute('data-sidebar', 'collapsed');
      }
    } catch (e) {}
  `;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: bootScript }} />
      </head>
      {/* Fonts loaded via @import in globals.css */}
      <body className={`${dmSans.variable} ${jetbrainsMono.variable} ${playfair.variable} font-sans bg-cream text-ink`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
