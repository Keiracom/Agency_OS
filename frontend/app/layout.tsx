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
  // A4 sidebar pre-paint — read agencyos_sidebar from localStorage
  // synchronously and stamp [data-sidebar="collapsed"] on <html>
  // before any paint, so the layout doesn't snap from 232px → 72px
  // (or vice versa) after hydration.
  const sidebarBootScript = `
    try {
      if (localStorage.getItem('agencyos_sidebar') === 'collapsed') {
        document.documentElement.setAttribute('data-sidebar', 'collapsed');
      }
    } catch (e) {}
  `;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: sidebarBootScript }} />
      </head>
      {/* Fonts loaded via @import in globals.css */}
      <body className={`${dmSans.variable} ${jetbrainsMono.variable} ${playfair.variable} font-sans bg-cream text-ink`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
