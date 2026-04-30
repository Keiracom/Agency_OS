/**
 * FILE: frontend/components/layout/sidebar.tsx
 * PURPOSE: Dark sidebar with amber active borders + Playfair logo accent.
 *          Two desktop states: expanded (232px) and collapsed (72px).
 *          Mobile (<md) drawer pattern unchanged from PR #452.
 * REFERENCE: dashboard-master-agency-desk.html — sb-logo / sb-section /
 *            sb-item / sb-icon / sb-badge / sb-foot styling.
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Megaphone,
  MessageSquareReply,
  BarChart3,
  Settings,
  Radio,
  Inbox,
  Calendar,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Today",
    items: [
      { title: "Command Center", href: "/dashboard", icon: LayoutDashboard },
      { title: "Live Pipeline",  href: "/dashboard/pipeline", icon: Radio },
      { title: "Inbox",          href: "/dashboard/inbox", icon: Inbox },
      { title: "Meetings",       href: "/dashboard/meetings", icon: Calendar },
    ],
  },
  {
    title: "Workflow",
    items: [
      { title: "Leads",     href: "/dashboard/leads", icon: Users },
      { title: "Campaigns", href: "/dashboard/campaigns", icon: Megaphone },
      { title: "Replies",   href: "/dashboard/replies", icon: MessageSquareReply },
    ],
  },
  {
    title: "Insights",
    items: [
      { title: "Reports",  href: "/dashboard/reports", icon: BarChart3 },
      { title: "Settings", href: "/dashboard/settings", icon: Settings },
    ],
  },
];

interface SidebarProps {
  /** Mobile drawer state — controlled by DashboardLayout. Desktop
   *  sidebar always renders; mobile renders only when `open` is true. */
  open?: boolean;
  /** Mobile drawer dismiss callback (X button + backdrop tap + nav click). */
  onClose?: () => void;
  /** A4 — desktop collapse state. Mobile ignores. */
  collapsed?: boolean;
  /** A4 — toggle callback for the chevron button. */
  onToggleCollapsed?: () => void;
}

export function Sidebar({
  open = false, onClose, collapsed = false, onToggleCollapsed,
}: SidebarProps = {}) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile backdrop — click to dismiss. Hidden on md+ where the
          sidebar always renders. */}
      <div
        className={cn(
          "fixed inset-0 z-40 bg-black/55 backdrop-blur-[2px] md:hidden transition-opacity",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={cn(
          "fixed left-0 top-0 bottom-0 bg-brand-bar text-white/80 flex flex-col z-50 overflow-y-auto",
          "transition-[transform,width] duration-300 ease-out",
          // Mobile: off-canvas unless `open`. Desktop (md+): always visible.
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
        // Width comes from the --sidebar-current-w CSS var so first-paint
        // resolves to the correct width before React hydrates (the
        // pre-paint script in app/layout.tsx stamps [data-sidebar=
        // "collapsed"] on <html> when localStorage says so). Mobile
        // drawer always uses the expanded width — looks cramped at 72px.
        style={{
          width: "var(--sidebar-current-w)",
          borderRight: "1px solid rgba(255,255,255,0.06)",
        }}
        aria-label="Primary navigation"
      >
        {/* Logo block + collapse toggle (md+) + close (mobile) */}
        <div
          className={cn(
            "pt-[22px] pb-[18px] flex items-start justify-between gap-2",
            collapsed ? "px-3" : "px-5",
          )}
          style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
        >
          {!collapsed && (
            <div>
              <div className="font-display font-bold text-[20px] tracking-[-0.02em] text-white whitespace-nowrap">
                Agency<em className="text-amber" style={{ fontStyle: "italic" }}>OS</em>
              </div>
              <div className="font-mono text-[9px] tracking-[0.14em] uppercase text-white/30 mt-[3px] whitespace-nowrap">
                Agency Desk
              </div>
            </div>
          )}

          {collapsed && (
            <div
              className="font-display font-bold text-[18px] text-amber w-full text-center"
              style={{ fontStyle: "italic" }}
              title="AgencyOS"
            >
              OS
            </div>
          )}

          {/* Desktop collapse toggle (md+ only) */}
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn(
              "hidden md:grid place-items-center w-7 h-7 rounded-md",
              "text-white/50 hover:text-white hover:bg-white/[0.06]",
              "transition-colors shrink-0",
              collapsed && "absolute top-2 right-2",
            )}
          >
            {collapsed
              ? <ChevronRight className="w-4 h-4" />
              : <ChevronLeft  className="w-4 h-4" />}
          </button>

          {/* Mobile-only close button */}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="md:hidden p-1.5 -mr-1 -mt-1 rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav sections */}
        <nav className="flex-1">
          {navSections.map((section) => (
            <div key={section.title} className="pt-4 pb-1">
              {!collapsed && (
                <div className="font-mono text-[9px] tracking-[0.14em] uppercase text-white/30 px-5 pb-2">
                  {section.title}
                </div>
              )}
              {section.items.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    title={collapsed ? item.title : undefined}
                    className={cn(
                      "group relative flex items-center text-[13px] transition-colors border-l-2",
                      collapsed ? "px-0 py-[10px] justify-center" : "gap-3 px-5 py-[9px]",
                      isActive
                        ? "text-white bg-amber-soft border-amber font-medium"
                        : "text-white/70 border-transparent hover:text-white hover:bg-white/[0.03]",
                    )}
                  >
                    <Icon
                      className={cn(
                        "w-4 h-4 shrink-0",
                        isActive ? "text-amber opacity-100" : "opacity-75",
                      )}
                    />
                    {!collapsed && <span className="truncate">{item.title}</span>}

                    {/* Badge — visible in both states; floats on the
                        right when expanded, top-right corner when collapsed. */}
                    {item.badge && (
                      <span
                        className={cn(
                          "font-mono text-[10px] bg-amber text-on-amber font-semibold rounded-[10px] text-center",
                          collapsed
                            ? "absolute top-1 right-1 px-1 min-w-[16px]"
                            : "ml-auto px-[6px] py-[1px] min-w-[20px]",
                        )}
                      >
                        {item.badge}
                      </span>
                    )}

                    {/* Tooltip on hover when collapsed */}
                    {collapsed && (
                      <span
                        className="absolute left-full ml-2 px-2 py-1 rounded bg-brand-bar border border-white/10 text-[11px] text-white whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10 shadow-lg"
                      >
                        {item.title}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Footer — avatar block (matches prototype .sb-foot) */}
        <div
          className={cn(
            "mt-auto py-4 flex items-center gap-[10px]",
            collapsed ? "px-3 justify-center" : "px-5",
          )}
          style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
        >
          <div
            className="w-[30px] h-[30px] rounded-full bg-amber text-on-amber grid place-items-center font-display font-bold text-[12px] shrink-0"
            title={collapsed ? "Maya · BDR · ON" : undefined}
          >
            M
          </div>
          {!collapsed && (
            <div className="leading-tight min-w-0">
              <div className="text-[13px] text-white">Maya</div>
              <div className="font-mono text-[10.5px] tracking-[0.06em] text-white/40">
                BDR · ON
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
