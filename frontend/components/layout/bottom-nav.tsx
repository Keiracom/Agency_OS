/**
 * FILE: frontend/components/layout/bottom-nav.tsx
 * PURPOSE: Fixed-bottom mobile navigation — 5 thumb-reach destinations.
 *          Mobile-only (md:hidden); desktop uses the left sidebar.
 * REFERENCE: dashboard-master-agency-desk.html — `.bottomnav` block at
 *            lines ~845 and the `--bottomnav-h` (60px) layout token.
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home, BarChart3, Calendar, List, Settings as SettingsIcon,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const ITEMS: NavItem[] = [
  { href: "/dashboard",          label: "Home",     icon: Home },
  { href: "/dashboard/pipeline", label: "Pipeline", icon: BarChart3 },
  { href: "/dashboard/meetings", label: "Meetings", icon: Calendar },
  { href: "/dashboard/activity", label: "Feed",     icon: List },
  { href: "/dashboard/settings", label: "Settings", icon: SettingsIcon },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Mobile navigation"
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-panel border-t border-rule"
      style={{ height: "var(--bottomnav-h)" }}
    >
      <ul className="grid grid-cols-5 h-full">
        {ITEMS.map(item => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <li key={item.href} className="relative">
              <Link
                href={item.href}
                className={cn(
                  "h-full flex flex-col items-center justify-center gap-0.5 transition-colors",
                  active ? "text-amber" : "text-ink-3 hover:text-ink",
                )}
                aria-current={active ? "page" : undefined}
              >
                {active && (
                  <span
                    aria-hidden
                    className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-[2px] rounded-b-[2px] bg-amber"
                  />
                )}
                <Icon className="w-5 h-5" strokeWidth={active ? 2 : 1.6} />
                <span className="font-mono text-[9px] tracking-[0.06em] uppercase">
                  {item.label}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
