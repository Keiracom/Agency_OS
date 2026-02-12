/**
 * FILE: frontend/app/layout.tsx
 * PURPOSE: Root layout with providers and global styles
 * PHASE: 8 (Frontend)
 * SPRINT: Dashboard Sprint 1 - Theme Foundation
 */

import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
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
  return (
    <html lang="en" suppressHydrationWarning>
      {/* Fonts loaded via @import in globals.css */}
      <body className={`${dmSans.variable} ${jetbrainsMono.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
