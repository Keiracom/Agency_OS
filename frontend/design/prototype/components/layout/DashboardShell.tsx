"use client";

import { ReactNode } from "react";
import { Sidebar, SidebarProps } from "./Sidebar";
import { Header, HeaderProps } from "./Header";

/**
 * DashboardShell props
 */
export interface DashboardShellProps {
  /** Page content */
  children: ReactNode;
  /** Page title for the header */
  title: string;
  /** Currently active navigation path */
  activePath?: string;
  /** Navigation handler */
  onNavigate?: (path: string) => void;
  /** Notification count */
  notificationCount?: number;
  /** User name */
  userName?: string;
  /** User avatar URL */
  avatarUrl?: string;
}

/**
 * DashboardShell - Main layout wrapper component
 *
 * Features:
 * - Fixed 256px sidebar on left
 * - Header with title, search, notifications, user
 * - Main content area with proper spacing
 * - Scrollable content area
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Content background: #F8FAFC (content-bg)
 * - Sidebar width: 256px (16rem)
 *
 * Usage:
 * ```tsx
 * <DashboardShell title="Dashboard" activePath="/dashboard">
 *   <YourPageContent />
 * </DashboardShell>
 * ```
 */
export function DashboardShell({
  children,
  title,
  activePath = "/dashboard",
  onNavigate,
  notificationCount,
  userName,
  avatarUrl,
}: DashboardShellProps) {
  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      {/* Fixed Sidebar */}
      <Sidebar activePath={activePath} onNavigate={onNavigate} />

      {/* Main Content Area */}
      <div className="ml-64 min-h-screen flex flex-col">
        {/* Header */}
        <Header
          title={title}
          notificationCount={notificationCount}
          userName={userName}
          avatarUrl={avatarUrl}
        />

        {/* Scrollable Content */}
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

export default DashboardShell;
