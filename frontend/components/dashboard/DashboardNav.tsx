/**
 * FILE: frontend/components/dashboard/DashboardNav.tsx
 * PURPOSE: Vertical sidebar nav for every /dashboard/* route
 * PHASE: PHASE-2.1-FRONTEND-POLISH-HMAC (nav portion)
 *
 * Desktop: always-visible rail.
 * Mobile  (< md): collapses behind a hamburger toggle; tap-outside closes.
 * Active route indicated by left-border accent + tinted background.
 * Approval link shows a live count badge (useApprovalQueue).
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home, Users, Calendar, Activity, ShieldCheck, Menu, X,
  type LucideIcon,
} from "lucide-react";
import { useApprovalQueue } from "@/lib/hooks/useApprovalQueue";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const ITEMS: NavItem[] = [
  { href: "/dashboard",          label: "Home",     icon: Home },
  { href: "/dashboard/pipeline", label: "Pipeline", icon: Users },
  { href: "/dashboard/meetings", label: "Meetings", icon: Calendar },
  { href: "/dashboard/activity", label: "Activity", icon: Activity },
  { href: "/dashboard/approval", label: "Approval", icon: ShieldCheck },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function DashboardNav() {
  const pathname = usePathname() ?? "";
  const [open, setOpen] = useState(false);
  const { touches } = useApprovalQueue();
  const approvalCount = touches.length;

  // Close the mobile drawer on route change.
  useEffect(() => { setOpen(false); }, [pathname]);

  // Close on Esc.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      {/* Mobile toggle (hidden on md+) */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close nav" : "Open nav"}
        className="md:hidden fixed top-3 left-3 z-40 p-2 rounded-md border border-gray-800 bg-gray-900/90 backdrop-blur text-gray-300 hover:text-amber-300 hover:border-amber-500/40"
      >
        {open ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
      </button>

      {/* Mobile backdrop */}
      {open && (
        <div
          className="md:hidden fixed inset-0 z-30 bg-black/60"
          onClick={() => setOpen(false)}
          aria-hidden
        />
      )}

      <aside
        aria-label="Dashboard navigation"
        className={`fixed md:sticky md:top-0 md:left-0 top-0 left-0 z-30 md:z-10 h-screen w-56 flex-shrink-0
          bg-gray-900 border-r border-gray-800
          transition-transform duration-200 md:translate-x-0
          ${open ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        {/* Brand */}
        <div className="px-4 py-4 border-b border-gray-800">
          <div className="font-serif text-lg text-gray-100">Keira</div>
          <div className="font-mono text-[10px] tracking-widest uppercase text-gray-500">
            Agency desk
          </div>
        </div>

        {/* Items */}
        <nav className="px-2 py-3 space-y-1">
          {ITEMS.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            const showBadge = href === "/dashboard/approval" && approvalCount > 0;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm border-l-2 transition ${
                  active
                    ? "bg-emerald-500/10 border-emerald-400 text-gray-100"
                    : "border-transparent text-gray-400 hover:text-gray-100 hover:bg-gray-800/60"
                }`}
              >
                <Icon className="w-4 h-4" strokeWidth={1.75} />
                <span className="flex-1">{label}</span>
                {showBadge && (
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                    {approvalCount}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer spacer — leaves room for the KillSwitch fixed top-right */}
        <div className="md:hidden h-14" aria-hidden />
      </aside>
    </>
  );
}
