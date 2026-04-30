/**
 * QuickActions.tsx - Floating Quick Actions Panel
 * Bloomberg Terminal Dark Mode + Glassmorphic Design
 * 
 * Features:
 * - Floating action button (bottom-right, above Maya)
 * - Expandable panel with 5 actions
 * - Keyboard shortcut hints
 * - Smooth expand/collapse animation
 * - Each action navigates or opens modal
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Plus,
  X,
  Megaphone,
  UserPlus,
  Mail,
  Phone,
  BarChart3,
  Command,
  ChevronUp,
} from "lucide-react";

// ============================================
// Types
// ============================================

export interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  shortcut: string;
  action: () => void;
  color: string;
}

export interface QuickActionsProps {
  /** Callback when New Campaign is clicked */
  onNewCampaign?: () => void;
  /** Callback when Add Leads is clicked */
  onAddLeads?: () => void;
  /** Callback when Send Email is clicked */
  onSendEmail?: () => void;
  /** Callback when Schedule Call is clicked */
  onScheduleCall?: () => void;
  /** Callback when View Reports is clicked */
  onViewReports?: () => void;
  /** Additional className */
  className?: string;
}

// ============================================
// Component
// ============================================

export function QuickActions({
  onNewCampaign,
  onAddLeads,
  onSendEmail,
  onScheduleCall,
  onViewReports,
  className,
}: QuickActionsProps) {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  // Define actions
  const actions: QuickAction[] = [
    {
      id: "new-campaign",
      label: "New Campaign",
      description: "Create a new outreach campaign",
      icon: <Megaphone className="w-5 h-5" />,
      shortcut: "C",
      action: onNewCampaign || (() => router.push("/campaigns?new=true")),
      color: "from-amber to-violet-600",
    },
    {
      id: "add-leads",
      label: "Add Leads",
      description: "Import or enrich leads",
      icon: <UserPlus className="w-5 h-5" />,
      shortcut: "L",
      action: onAddLeads || (() => router.push("/leads?action=import")),
      color: "from-amber to-green-600",
    },
    {
      id: "send-email",
      label: "Send Email",
      description: "Compose a quick email",
      icon: <Mail className="w-5 h-5" />,
      shortcut: "E",
      action: onSendEmail || (() => router.push("/replies?compose=true")),
      color: "from-amber to-amber",
    },
    {
      id: "schedule-call",
      label: "Schedule Call",
      description: "Book a call with a lead",
      icon: <Phone className="w-5 h-5" />,
      shortcut: "K",
      action: onScheduleCall || (() => router.push("/calendar?new=call")),
      color: "from-orange-500 to-amber-600",
    },
    {
      id: "view-reports",
      label: "View Reports",
      description: "Analytics & performance",
      icon: <BarChart3 className="w-5 h-5" />,
      shortcut: "R",
      action: onViewReports || (() => router.push("/reports")),
      color: "from-amber-light to-rose-600",
    },
  ];

  // Toggle with animation
  const toggleOpen = useCallback(() => {
    if (isOpen) {
      setIsAnimating(true);
      setTimeout(() => {
        setIsOpen(false);
        setIsAnimating(false);
      }, 200);
    } else {
      setIsOpen(true);
    }
  }, [isOpen]);

  // Handle action click
  const handleActionClick = useCallback((action: QuickAction) => {
    action.action();
    toggleOpen();
  }, [toggleOpen]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      // Toggle panel with Cmd/Ctrl + K
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        toggleOpen();
        return;
      }

      // Only handle shortcuts when panel is open
      if (!isOpen) return;

      // Escape to close
      if (e.key === "Escape") {
        toggleOpen();
        return;
      }

      // Action shortcuts (with Cmd/Ctrl modifier)
      if (e.metaKey || e.ctrlKey) {
        const action = actions.find(
          (a) => a.shortcut.toLowerCase() === e.key.toLowerCase()
        );
        if (action) {
          e.preventDefault();
          handleActionClick(action);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, toggleOpen, actions, handleActionClick]);

  return (
    <div
      className={cn(
        "fixed bottom-24 right-6 z-40", // Above Maya (bottom-6)
        className
      )}
    >
      {/* Expandable Panel */}
      {(isOpen || isAnimating) && (
        <div
          className={cn(
            "absolute bottom-full right-0 mb-3 w-[280px] rounded-2xl overflow-hidden",
            "bg-bg-cream/70 backdrop-blur-xl border border-slate-700/50",
            "shadow-2xl shadow-black/50",
            "transition-all duration-200 ease-out origin-bottom-right",
            isOpen && !isAnimating
              ? "opacity-100 scale-100 translate-y-0"
              : "opacity-0 scale-95 translate-y-2"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50 bg-bg-surface/40">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-gradient-to-br from-amber/20 to-amber/20 border border-amber/30">
                <Plus className="w-4 h-4 text-amber" />
              </div>
              <span className="text-sm font-medium text-ink">Quick Actions</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-bg-surface/60 border border-slate-600/30">
              <Command className="w-3 h-3 text-ink-2" />
              <span className="text-[10px] text-ink-2 font-medium">K</span>
            </div>
          </div>

          {/* Actions List */}
          <div className="p-2 space-y-1">
            {actions.map((action, index) => (
              <button
                key={action.id}
                onClick={() => handleActionClick(action)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl",
                  "bg-transparent hover:bg-bg-surface/60",
                  "border border-transparent hover:border-slate-700/50",
                  "transition-all duration-150 group",
                  "animate-in fade-in slide-in-from-right-2"
                )}
                style={{
                  animationDelay: `${index * 50}ms`,
                  animationFillMode: "backwards",
                }}
              >
                {/* Icon */}
                <div
                  className={cn(
                    "p-2 rounded-lg bg-gradient-to-br shadow-lg",
                    action.color,
                    "group-hover:scale-110 transition-transform duration-150"
                  )}
                >
                  <span className="text-ink">{action.icon}</span>
                </div>

                {/* Label & Description */}
                <div className="flex-1 text-left">
                  <p className="text-sm font-medium text-ink group-hover:text-violet-300 transition-colors">
                    {action.label}
                  </p>
                  <p className="text-xs text-ink-3 group-hover:text-ink-2 transition-colors">
                    {action.description}
                  </p>
                </div>

                {/* Shortcut */}
                <div className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-bg-surface/60 border border-slate-600/30 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Command className="w-2.5 h-2.5 text-ink-3" />
                  <span className="text-[10px] text-ink-2 font-mono">
                    {action.shortcut}
                  </span>
                </div>
              </button>
            ))}
          </div>

          {/* Footer Hint */}
          <div className="px-4 py-2.5 border-t border-slate-700/50 bg-bg-surface/30">
            <p className="text-[10px] text-ink-3 text-center flex items-center justify-center gap-1.5">
              <span className="inline-flex items-center gap-0.5">
                <Command className="w-2.5 h-2.5" />K
              </span>
              to toggle •
              <span>Esc</span>
              to close
            </p>
          </div>
        </div>
      )}

      {/* Floating Action Button */}
      <button
        onClick={toggleOpen}
        className={cn(
          "group relative w-12 h-12 rounded-full",
          "bg-gradient-to-br from-amber to-amber",
          "border-[3px] border-slate-900",
          "shadow-lg shadow-amber/30",
          "flex items-center justify-center",
          "transition-all duration-200",
          "hover:scale-110 hover:shadow-amber/50",
          "focus:outline-none focus:ring-2 focus:ring-amber/50 focus:ring-offset-2 focus:ring-offset-slate-900",
          isOpen && "rotate-45 bg-gradient-to-br from-slate-600 to-slate-700"
        )}
        aria-label={isOpen ? "Close quick actions" : "Open quick actions"}
        aria-expanded={isOpen}
      >
        {isOpen ? (
          <X className="w-5 h-5 text-ink transition-transform duration-200" />
        ) : (
          <>
            <Plus className="w-5 h-5 text-ink" />
            {/* Pulse ring */}
            <span className="absolute inset-0 rounded-full bg-violet-400 animate-ping opacity-20" />
          </>
        )}
      </button>

      {/* Tooltip when closed */}
      {!isOpen && (
        <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-bg-surface/90 backdrop-blur-sm border border-slate-700/50 rounded-lg whitespace-nowrap">
            <span className="text-xs text-ink">Quick Actions</span>
            <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-slate-700/60 border border-slate-600/30">
              <Command className="w-2.5 h-2.5 text-ink-2" />
              <span className="text-[10px] text-ink-2">K</span>
            </div>
            <ChevronUp className="w-3 h-3 text-ink-2" />
          </div>
        </div>
      )}
    </div>
  );
}

export default QuickActions;
