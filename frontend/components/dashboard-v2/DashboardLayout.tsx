/**
 * Dashboard Layout - Main container with sidebar and content area
 * Open in Codux to visually edit colors, spacing, etc.
 */

"use client";

import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

interface DashboardLayoutProps {
  children: ReactNode;
  title?: string;
}

export function DashboardLayout({ children, title = "Dashboard" }: DashboardLayoutProps) {
  return (
    <div className="flex min-h-screen bg-[#F8FAFC]">
      {/* Sidebar - Navy blue from mockup */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 ml-64">
        <Header title={title} />
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

export default DashboardLayout;
