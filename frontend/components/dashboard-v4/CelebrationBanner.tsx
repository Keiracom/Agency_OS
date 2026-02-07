/**
 * FILE: frontend/components/dashboard-v4/CelebrationBanner.tsx
 * PURPOSE: Celebration banner shown when targets are hit early
 * PHASE: Dashboard V4 Implementation
 */

"use client";

import { motion } from "framer-motion";
import { PartyPopper, X } from "lucide-react";
import { useState } from "react";

interface CelebrationBannerProps {
  title: string;
  subtitle: string;
  onDismiss?: () => void;
}

export function CelebrationBanner({ title, subtitle, onDismiss }: CelebrationBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="relative bg-gradient-to-r from-mint-500 to-mint-600 rounded-2xl p-5 flex items-center gap-4 text-white shadow-lg shadow-mint-500/25"
    >
      <div className="flex-shrink-0 text-3xl">
        <PartyPopper className="h-8 w-8" />
      </div>
      <div className="flex-1">
        <p className="text-lg font-semibold">{title}</p>
        <p className="text-sm text-mint-100">{subtitle}</p>
      </div>
      {onDismiss && (
        <button
          onClick={handleDismiss}
          className="absolute top-3 right-3 p-1 rounded-full hover:bg-white/10 transition-colors"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </motion.div>
  );
}
