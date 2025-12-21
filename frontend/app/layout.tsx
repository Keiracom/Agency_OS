/**
 * FILE: frontend/app/layout.tsx
 * PURPOSE: Root layout with providers and global styles
 * PHASE: 8 (Frontend)
 * TASK: FE-001
 */

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

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
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
