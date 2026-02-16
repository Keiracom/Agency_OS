"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Megaphone,
  MessageSquareReply,
  BarChart3,
  Settings,
  Check,
} from "lucide-react";

interface AppShellProps {
  children: ReactNode;
  pageTitle?: string;
}

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Command Center" },
  { href: "/leads", icon: Users, label: "Leads" },
  { href: "/campaigns", icon: Megaphone, label: "Campaigns" },
  { href: "/replies", icon: MessageSquareReply, label: "Replies" },
  { href: "/reports", icon: BarChart3, label: "Reports" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function AppShell({ children, pageTitle = 'Agency OS' }: AppShellProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Base dark background */}
      <div className="fixed inset-0 bg-bg-void -z-10" />
      
      {/* Ambient Background Orbs - for glassmorphism depth */}
      <div className="pointer-events-none fixed inset-0 z-0">
        {/* Purple orb - top right */}
        <div 
          className="absolute -top-32 -right-32 w-[600px] h-[600px] rounded-full opacity-30"
          style={{
            background: 'radial-gradient(circle, #7C3AED 0%, transparent 60%)',
            filter: 'blur(80px)',
          }}
        />
        {/* Blue orb - bottom left */}
        <div 
          className="absolute -bottom-32 -left-32 w-[550px] h-[550px] rounded-full opacity-25"
          style={{
            background: 'radial-gradient(circle, #3B82F6 0%, transparent 60%)',
            filter: 'blur(70px)',
          }}
        />
        {/* Cyan orb - center area */}
        <div 
          className="absolute top-1/3 right-1/4 w-[400px] h-[400px] rounded-full opacity-20"
          style={{
            background: 'radial-gradient(circle, #06B6D4 0%, transparent 60%)',
            filter: 'blur(60px)',
          }}
        />
      </div>

      {/* Fixed Left Sidebar - 72px */}
      <aside className="fixed left-0 top-0 h-full w-[72px] bg-bg-surface border-r border-border-subtle flex flex-col items-center py-4 z-50">
        {/* Logo */}
        <div className="mb-8">
          <div className="w-[42px] h-[42px] bg-gradient-to-br from-accent-primary to-accent-blue rounded-xl flex items-center justify-center shadow-glow-sm">
            <Check className="w-5 h-5 text-text-primary" strokeWidth={3} />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-2 flex-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  group relative w-11 h-11 rounded-xl flex items-center justify-center
                  transition-all duration-200
                  ${
                    isActive
                      ? "bg-accent-primary/15 text-accent-primary"
                      : "text-text-muted hover:bg-bg-surface-hover hover:text-text-secondary"
                  }
                `}
                title={item.label}
              >
                <Icon className="w-5 h-5" />
                {/* Tooltip */}
                <span className="absolute left-14 px-2 py-1 bg-bg-elevated text-text-primary text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity">
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="ml-[72px] min-h-screen flex flex-col">
        {/* Top Header Bar */}
        <header className="h-16 bg-bg-surface border-b border-border-subtle flex items-center justify-between px-6 sticky top-0 z-40">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-text-primary">
              {pageTitle}
            </h1>
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-status-success/15 border border-status-success/30 rounded-full text-xs font-semibold text-status-success">
              <span className="w-1.5 h-1.5 bg-status-success rounded-full animate-pulse" />
              LIVE
            </span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1">{children}</main>
      </div>

      {/* Maya AI Bubble - Fixed Bottom Right */}
      <div className="fixed bottom-6 right-6 z-50">
        <button
          className="relative w-14 h-14 rounded-full bg-gradient-to-br from-accent-primary to-accent-blue 
            flex items-center justify-center shadow-glow-md hover:shadow-glow-lg transition-shadow"
          title="Maya AI Assistant"
        >
          {/* Avatar placeholder - using "M" for Maya */}
          <span className="text-text-primary font-bold text-lg">M</span>
          {/* Online indicator */}
          <span className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-status-success rounded-full border-2 border-bg-void">
            <span className="absolute inset-0 bg-status-success rounded-full animate-ping opacity-75" />
          </span>
        </button>
      </div>
    </div>
  );
}
