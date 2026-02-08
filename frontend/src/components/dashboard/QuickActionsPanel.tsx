"use client";

/**
 * FILE: frontend/src/components/dashboard/QuickActionsPanel.tsx
 * PURPOSE: Floating Action Button with expandable quick actions menu
 * PHASE: 8 (Frontend)
 * FEATURES:
 *   - Floating FAB in bottom-right corner
 *   - Expandable menu with 5 quick actions
 *   - Staggered animation on expand
 *   - Bloomberg dark mode + glassmorphic styling
 *   - Keyboard accessible (Escape to close)
 *   - Click outside to close
 *   - Touch-friendly for mobile
 */

import React, { useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  IconPlus,
  IconX,
  IconRocket,
  IconUserPlus,
  IconMail,
  IconPhone,
  IconChartBar,
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";

interface QuickAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  color: string;
  href?: string;
  onClick?: () => void;
}

interface QuickActionsPanelProps {
  className?: string;
  onActionClick?: (actionId: string) => void;
}

const defaultActions: QuickAction[] = [
  {
    id: "new-campaign",
    label: "New Campaign",
    icon: <IconRocket className="h-5 w-5" />,
    color: "from-cyan-500 to-blue-500",
    href: "/dashboard/campaigns/new",
  },
  {
    id: "add-leads",
    label: "Add Leads",
    icon: <IconUserPlus className="h-5 w-5" />,
    color: "from-emerald-500 to-teal-500",
    href: "/dashboard/leads/import",
  },
  {
    id: "send-email",
    label: "Send Email",
    icon: <IconMail className="h-5 w-5" />,
    color: "from-violet-500 to-purple-500",
    href: "/dashboard/outreach/compose",
  },
  {
    id: "schedule-call",
    label: "Schedule Call",
    icon: <IconPhone className="h-5 w-5" />,
    color: "from-orange-500 to-amber-500",
    href: "/dashboard/calls/schedule",
  },
  {
    id: "view-reports",
    label: "View Reports",
    icon: <IconChartBar className="h-5 w-5" />,
    color: "from-pink-500 to-rose-500",
    href: "/dashboard/analytics",
  },
];

export function QuickActionsPanel({
  className,
  onActionClick,
}: QuickActionsPanelProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen]);

  const handleActionClick = useCallback(
    (action: QuickAction) => {
      if (onActionClick) {
        onActionClick(action.id);
      }
      if (action.onClick) {
        action.onClick();
      }
      setIsOpen(false);
    },
    [onActionClick]
  );

  return (
    <div
      ref={containerRef}
      className={cn(
        "fixed bottom-6 right-6 z-50",
        "flex flex-col items-end gap-3",
        className
      )}
    >
      {/* Menu Items */}
      <AnimatePresence mode="popLayout">
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex flex-col items-end gap-2"
          >
            {defaultActions.map((action, index) => (
              <motion.div
                key={action.id}
                initial={{ opacity: 0, x: 20, scale: 0.8 }}
                animate={{
                  opacity: 1,
                  x: 0,
                  scale: 1,
                  transition: {
                    delay: index * 0.05,
                    type: "spring",
                    stiffness: 400,
                    damping: 25,
                  },
                }}
                exit={{
                  opacity: 0,
                  x: 20,
                  scale: 0.8,
                  transition: {
                    delay: (defaultActions.length - 1 - index) * 0.03,
                    duration: 0.15,
                  },
                }}
                className="flex items-center gap-3"
              >
                {/* Label tooltip */}
                <motion.span
                  initial={{ opacity: 0, x: 10 }}
                  animate={{
                    opacity: 1,
                    x: 0,
                    transition: { delay: index * 0.05 + 0.1 },
                  }}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-sm font-medium",
                    // Glassmorphic styling
                    "bg-neutral-900/90 backdrop-blur-xl",
                    "border border-white/10",
                    "text-white shadow-lg shadow-black/30",
                    "whitespace-nowrap"
                  )}
                >
                  {action.label}
                </motion.span>

                {/* Action Button */}
                <a
                  href={action.href}
                  onClick={(e) => {
                    if (!action.href || action.onClick) {
                      e.preventDefault();
                    }
                    handleActionClick(action);
                  }}
                  className={cn(
                    "group relative flex h-12 w-12 items-center justify-center rounded-full",
                    "transition-all duration-200 ease-out",
                    // Gradient background
                    `bg-gradient-to-br ${action.color}`,
                    // Glassmorphic overlay
                    "before:absolute before:inset-0 before:rounded-full",
                    "before:bg-white/10 before:opacity-0 before:transition-opacity",
                    "hover:before:opacity-100",
                    // Shadow and glow
                    "shadow-lg shadow-black/30",
                    "hover:shadow-xl hover:shadow-black/40",
                    "hover:scale-110",
                    // Ring effect
                    "ring-1 ring-white/20",
                    "focus:outline-none focus:ring-2 focus:ring-white/50"
                  )}
                  aria-label={action.label}
                >
                  <span className="relative z-10 text-white">
                    {action.icon}
                  </span>
                </a>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main FAB */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative flex h-14 w-14 items-center justify-center rounded-full",
          "transition-all duration-300 ease-out",
          // Bloomberg dark + glassmorphic
          "bg-neutral-900/90 backdrop-blur-xl",
          "border border-white/10",
          // Cyan accent glow on hover
          "hover:border-cyan-500/50",
          "hover:shadow-[0_0_30px_rgba(6,182,212,0.3)]",
          // Shadow
          "shadow-2xl shadow-black/50",
          // Ring
          "ring-1 ring-inset ring-white/5",
          "focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
        )}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label={isOpen ? "Close quick actions" : "Open quick actions"}
        aria-expanded={isOpen}
      >
        {/* Animated icon */}
        <motion.div
          animate={{ rotate: isOpen ? 45 : 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="relative"
        >
          <AnimatePresence mode="wait">
            {isOpen ? (
              <motion.div
                key="close"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.5 }}
                transition={{ duration: 0.1 }}
              >
                <IconX className="h-6 w-6 text-white" />
              </motion.div>
            ) : (
              <motion.div
                key="plus"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.5 }}
                transition={{ duration: 0.1 }}
              >
                <IconPlus className="h-6 w-6 text-cyan-400" />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Pulse ring effect when closed */}
        {!isOpen && (
          <motion.span
            className="absolute inset-0 rounded-full border-2 border-cyan-500/30"
            initial={{ scale: 1, opacity: 0.5 }}
            animate={{
              scale: [1, 1.3, 1.3],
              opacity: [0.5, 0, 0],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        )}
      </motion.button>

      {/* Backdrop overlay for mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 -z-10 bg-black/30 backdrop-blur-sm md:hidden"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default QuickActionsPanel;
